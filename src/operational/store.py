"""Operational DB: 仮名加工情報 + 質問/回答/citation を JSONL で保管 (ADR-006 inherit)。

embedding / retrieval / LLM が literal 読む source。 vault と link は ID token のみ。
漏洩しても仮名加工情報 = 個人情報保護法 2026 改正方針で報告義務 ZERO。

T2 tables:
  - ddproject_op: DDP-XXXXXX → {company_name, industry, revenue_jpy, status, ...}
  - question: Q-XXXXXX (data/questionnaire/questions.jsonl 経由)
  - answer: A-XXXXXX → {question_id, ddp_id, answer_text, fit_label, citations, created_at}
  - jp_pattern_hit: JPP-XXXXXX → JPPatternHit serialized
"""
from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
OP_DIR = DATA_DIR / "operational"


def _op_file(table: str) -> Path:
    return OP_DIR / f"{table}.jsonl"


def _id_key_for_table(table: str) -> str:
    mapping = {
        "ddproject_op": "ddp_id",
        "question": "q_id",
        "answer": "a_id",
        "jp_pattern_hit": "jpp_id",
    }
    return mapping.get(table, "id")


def _load_all(table: str) -> dict[str, dict[str, Any]]:
    path = _op_file(table)
    if not path.exists():
        return {}
    id_key = _id_key_for_table(table)
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec[id_key]] = rec
    return out


def _save_all(table: str, records: dict[str, dict[str, Any]]) -> None:
    path = _op_file(table)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(rec, ensure_ascii=False) for rec in records.values()),
        encoding="utf-8",
    )


# ─── public API ────────────────────────────


def list_ddprojects() -> list[dict[str, Any]]:
    """全 DDP 一覧 (UI list page で利用)."""
    return list(_load_all("ddproject_op").values())


def get_ddproject(ddp_id: str) -> dict[str, Any] | None:
    return _load_all("ddproject_op").get(ddp_id)


def put_ddproject(record: dict[str, Any]) -> None:
    records = _load_all("ddproject_op")
    records[record["ddp_id"]] = record
    _save_all("ddproject_op", records)


def list_questions(category: str | None = None) -> list[dict[str, Any]]:
    """質問票 list (category filter 可)。 source = data/questionnaire/questions.jsonl"""
    qpath = DATA_DIR / "questionnaire" / "questions.jsonl"
    if not qpath.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in qpath.read_text(encoding="utf-8").splitlines():
        if line.strip():
            q = json.loads(line)
            if category is None or q.get("category") == category:
                out.append(q)
    return out


def get_question(q_id: str) -> dict[str, Any] | None:
    for q in list_questions():
        if q["q_id"] == q_id:
            return q
    return None


def put_answer(answer: dict[str, Any]) -> None:
    answer.setdefault("a_id", f"A-{secrets.token_urlsafe(12)}")
    answer.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    records = _load_all("answer")
    records[answer["a_id"]] = answer
    _save_all("answer", records)


def list_answers(ddp_id: str | None = None) -> list[dict[str, Any]]:
    items = list(_load_all("answer").values())
    if ddp_id:
        items = [a for a in items if a.get("ddp_id") == ddp_id]
    return items


def put_jp_pattern_hit(hit: dict[str, Any]) -> None:
    records = _load_all("jp_pattern_hit")
    records[hit["jpp_id"]] = hit
    _save_all("jp_pattern_hit", records)


def list_jp_pattern_hits(ddp_id: str | None = None) -> list[dict[str, Any]]:
    items = list(_load_all("jp_pattern_hit").values())
    if ddp_id:
        items = [h for h in items if h.get("ddp_id") == ddp_id]
    return items


def list_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    """vault access audit log の literal tail (UI audit page で利用)."""
    log_path = DATA_DIR / "audit" / "access_log.jsonl"
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[-limit:]:
        if line.strip():
            out.append(json.loads(line))
    return out
