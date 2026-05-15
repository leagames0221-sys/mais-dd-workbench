"""FastAPI app — T2 DD 自動化 UI (internal ADR inherit + ADR-100-106 統合).

Run: uvicorn src.api.app:app --reload --port 8000

Routes:
  GET  /                              landing (T2 brand + 5 DDP sample table)
  POST /mock-signin                   Mock OAuth: MAIS 担当者 user_id で session 開始
  GET  /dd-projects                   案件一覧
  GET  /dd-project/{ddp_id}           案件詳細 + chunks 統計 + jp_patterns hit
  GET  /dd-project/{ddp_id}/questionnaire  300 質問 list (category filter)
  POST /dd-project/{ddp_id}/answer    1 質問で 5-stage pipeline + Citation 生成 + 保存
  GET  /dd-project/{ddp_id}/jp-patterns   中堅 fit pattern alert page
  GET  /audit-log                     全 vault access audit log
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from src.auth.session import SESSION_SECRET, is_provider_configured
from src.clause.extract_clauses import detect_clauses, hits_by_kind
from src.ingestion.parse_vdr_docs import parse_ddp
from src.jp_patterns.detect import detect_all as detect_jp_all
from src.operational.store import (
    get_ddproject,
    list_audit_log,
    list_ddprojects,
    list_jp_pattern_hits,
    list_questions,
    put_answer,
    put_ddproject,
    put_jp_pattern_hit,
    list_answers,
)
from src.pipeline.pipeline import hybrid_search_with_citations

load_dotenv()

APP_DIR = Path(__file__).parent
TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
VDR_ROOT = DATA_DIR / "vdr_synthetic"
CHUNK_CACHE = DATA_DIR / "cache" / "chunks"

app = FastAPI(title="MAIS — DD 自動化 (PoC)")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=3600)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# ─── helpers ─────────────────────────────────


def _current_user(request: Request) -> str:
    uid = request.session.get("user_id")
    if not uid:
        raise HTTPException(status_code=401, detail="未ログイン (/ から mock-signin してください)")
    return uid


def _bootstrap_ddprojects() -> None:
    """data/vdr_synthetic/ddp_summary.jsonl を operational DB に literal sync."""
    summary_path = VDR_ROOT / "ddp_summary.jsonl"
    if not summary_path.exists():
        return
    existing = {d["ddp_id"] for d in list_ddprojects()}
    for line in summary_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec["ddp_id"] in existing:
            continue
        rec.setdefault("status", "ingestion_pending")
        put_ddproject(rec)


@app.on_event("startup")
async def on_startup() -> None:
    _bootstrap_ddprojects()


def _chunks_for_ddp(ddp_id: str) -> list[dict]:
    out: list[dict] = []
    base = CHUNK_CACHE / ddp_id
    if not base.exists():
        return out
    for jp in sorted(base.glob("*.jsonl")):
        with open(jp, encoding="utf-8") as f:
            out.extend(json.loads(line) for line in f if line.strip())
    return out


# ─── routes ──────────────────────────────────


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    """landing: T2 brand + 5 DDP sample list + Web UI scope 説明."""
    ddps = list_ddprojects()
    providers = {
        "google": is_provider_configured("google"),
        "linkedin": is_provider_configured("linkedin"),
    }
    return templates.TemplateResponse(
        request,
        "landing.html",
        {
            "ddps": ddps,
            "providers": providers,
            "current_user": request.session.get("user_id"),
        },
    )


@app.post("/mock-signin")
def post_mock_signin(request: Request, user_id: str = Form(...)):
    """Mock OAuth: MAIS 担当者 user_id で session 開始 (PoC demo 専用)."""
    request.session.clear()
    request.session["user_id"] = user_id
    request.session["provider"] = "mock"
    return RedirectResponse(url="/dd-projects", status_code=303)


@app.post("/signout")
def signout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/dd-projects", response_class=HTMLResponse)
def dd_projects(request: Request):
    """案件一覧 (MAIS 担当者の mypage 相当)."""
    _current_user(request)
    ddps = list_ddprojects()
    return templates.TemplateResponse(
        request,
        "dd_projects.html",
        {"ddps": ddps, "current_user": request.session.get("user_id")},
    )


@app.get("/dd-project/{ddp_id}", response_class=HTMLResponse)
def dd_project_detail(request: Request, ddp_id: str):
    """案件詳細: 業種 + 売上 + chunks 統計 + jp_patterns hit + Q-A links."""
    _current_user(request)
    ddp = get_ddproject(ddp_id)
    if not ddp:
        raise HTTPException(404, f"DDP {ddp_id} 不在")
    chunks = _chunks_for_ddp(ddp_id)
    jp_hits = list_jp_pattern_hits(ddp_id)
    answers = list_answers(ddp_id)
    return templates.TemplateResponse(
        request,
        "dd_project_detail.html",
        {
            "ddp": ddp,
            "chunk_count": len(chunks),
            "jp_hits": jp_hits,
            "answers": answers,
            "current_user": request.session.get("user_id"),
        },
    )


@app.post("/dd-project/{ddp_id}/ingest")
def trigger_ingestion(request: Request, ddp_id: str):
    """Docling ingestion を literal 実行 (UI ボタン経由、 PoC では同期実行)."""
    _current_user(request)
    ddp_dir = VDR_ROOT / ddp_id
    if not ddp_dir.exists():
        raise HTTPException(404, f"VDR dir 不在: {ddp_dir}")
    # 既存 chunks clean (idempotent)
    target = CHUNK_CACHE / ddp_id
    if target.exists():
        for f in target.glob("*.jsonl"):
            f.unlink()
    stats = parse_ddp(ddp_dir, output_root=CHUNK_CACHE)
    # JP patterns + clause を literal 検出 + DB 保存
    chunks = _chunks_for_ddp(ddp_id)
    jp_hits = detect_jp_all(ddp_id, chunks)
    for hit in jp_hits:
        put_jp_pattern_hit(
            {
                "jpp_id": hit.jpp_id,
                "ddp_id": hit.ddp_id,
                "kind": hit.kind,
                "evidence_chunk_ids": hit.evidence_chunk_ids,
                "evidence_phrases": hit.evidence_phrases,
                "confidence": hit.confidence,
                "notes": hit.notes,
            }
        )
    # status update
    ddp = get_ddproject(ddp_id) or {"ddp_id": ddp_id}
    ddp["status"] = "ingested"
    ddp["chunk_count"] = sum(stats.values())
    put_ddproject(ddp)
    return RedirectResponse(url=f"/dd-project/{ddp_id}", status_code=303)


@app.get("/dd-project/{ddp_id}/questionnaire", response_class=HTMLResponse)
def questionnaire(request: Request, ddp_id: str, category: str | None = None):
    """300 質問 list + category filter (financial / legal / business)."""
    _current_user(request)
    ddp = get_ddproject(ddp_id)
    if not ddp:
        raise HTTPException(404, f"DDP {ddp_id} 不在")
    qs = list_questions(category=category)
    answers = {a["question_id"]: a for a in list_answers(ddp_id) if "question_id" in a}
    return templates.TemplateResponse(
        request,
        "questionnaire.html",
        {
            "ddp": ddp,
            "questions": qs[:60],  # 表示量制御 (page top 60、 全 300 は API でも export 可)
            "category": category,
            "answers_map": answers,
            "current_user": request.session.get("user_id"),
        },
    )


@app.post("/dd-project/{ddp_id}/answer")
def generate_answer(request: Request, ddp_id: str, q_id: str = Form(...)):
    """1 質問で 5-stage pipeline + Citation 生成 + operational DB に保存."""
    _current_user(request)
    ddp = get_ddproject(ddp_id)
    if not ddp:
        raise HTTPException(404, f"DDP {ddp_id} 不在")
    question = None
    for q in list_questions():
        if q["q_id"] == q_id:
            question = q
            break
    if not question:
        raise HTTPException(404, f"Q {q_id} 不在")

    reasoned, citations = hybrid_search_with_citations(
        question["question_text"], ddp_id=ddp_id, top_k=5,
    )
    answer_text = "\n".join(f"[{r[1]}] {r[2]}" for r in reasoned) or "(該当 chunk なし)"
    answer = {
        "question_id": q_id,
        "ddp_id": ddp_id,
        "answer_text": answer_text,
        "fit_label": reasoned[0][1] if reasoned else "low",
        "citations": [c.model_dump() for c in citations],
    }
    put_answer(answer)
    return RedirectResponse(
        url=f"/dd-project/{ddp_id}/questionnaire?category={question.get('category', '')}",
        status_code=303,
    )


@app.get("/dd-project/{ddp_id}/jp-patterns", response_class=HTMLResponse)
def jp_patterns_page(request: Request, ddp_id: str):
    """中堅日本企業 fit pattern alert page (differentiation core)."""
    _current_user(request)
    ddp = get_ddproject(ddp_id)
    if not ddp:
        raise HTTPException(404, f"DDP {ddp_id} 不在")
    hits = list_jp_pattern_hits(ddp_id)
    return templates.TemplateResponse(
        request,
        "jp_patterns.html",
        {
            "ddp": ddp,
            "hits": hits,
            "current_user": request.session.get("user_id"),
        },
    )


@app.get("/audit-log", response_class=HTMLResponse)
def audit_log_page(request: Request):
    """全 vault access audit log (admin / 透明性 demo 用)."""
    _current_user(request)
    entries = list_audit_log(limit=200)
    return templates.TemplateResponse(
        request,
        "audit.html",
        {
            "entries": list(reversed(entries)),
            "current_user": request.session.get("user_id"),
        },
    )
