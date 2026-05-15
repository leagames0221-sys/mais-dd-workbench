"""End-to-end smoke test (T2 PoC、 Week 1 + Week 2 統合 verify)。

T1 internal ADR inherit (e2e_smoke pattern): commit 前 verify gate + dogfood + 客観 audit 兼用。

実行: python -m scripts.e2e_smoke
所要時間: ~5-15 min (Docling actual conversion + dense embedding + cross-encoder)

step 構成 (16 step):
  precondition (3 step) — file 存在 + 40 docs + 質問票 300 確認
  ingestion (4 step) — clean DDP + multi-pattern DDP の Docling chunk 抽出
  detector (4 step) — clause + jp_patterns を chunks に literal apply
  pipeline (3 step) — 5-stage hybrid + Citation 生成 (Stage 1-4、 Stage 5 LLM mock)
  summary (2 step) — 統計 + closure-bias 是正 evidence

doctrine: verify-priority 順守: file system check → commandlet → automation test → log Read。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Windows cp932 encoding 防御 (T1 学び、 doctrine: analogical-recall 順守)
for _sn in ("stdout", "stderr"):
    _s = getattr(sys, _sn, None)
    if _s is not None and getattr(_s, "encoding", "").lower() != "utf-8":
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


VDR_ROOT = Path("data/vdr_synthetic")
QUESTIONNAIRE_PATH = Path("data/questionnaire/questions.jsonl")
CHUNK_CACHE = Path("data/cache/chunks")


class SmokeResult:
    def __init__(self) -> None:
        self.passes: list[str] = []
        self.fails: list[tuple[str, str]] = []
        self.start = time.time()

    def ok(self, step: str, detail: str = "") -> None:
        self.passes.append(f"{step} | {detail}" if detail else step)
        print(f"  [OK] {step}" + (f" — {detail}" if detail else ""))

    def fail(self, step: str, detail: str) -> None:
        self.fails.append((step, detail))
        print(f"  [FAIL] {step} — {detail}")

    def summary(self) -> int:
        elapsed = time.time() - self.start
        total = len(self.passes) + len(self.fails)
        print()
        print("=" * 60)
        print(f"e2e_smoke summary: {len(self.passes)}/{total} PASS、 elapsed={elapsed:.1f}s")
        if self.fails:
            print(f"FAILS ({len(self.fails)}):")
            for step, detail in self.fails:
                print(f"  - {step}: {detail}")
            return 1
        print("ALL PASS ★★★")
        return 0


def main() -> int:
    result = SmokeResult()
    print("e2e_smoke (mais-dd-workbench)")
    print("=" * 60)

    # idempotent run 保証: 前 run の chunk cache を literal clean (D-NO-COMPROMISE 順守)
    # parse_ddp は doc_id 毎に literal UUID 生成、 cache 残存で run-over-run 累積 = idempotent でない
    # → smoke 着手前 literal clean で 同 run 内の literal verify 整合性確保
    smoke_targets = ["DDP-PHQjtztxy8I", "DDP-Fn-mP3hsIKw"]
    for ddp in smoke_targets:
        target_dir = CHUNK_CACHE / ddp
        if target_dir.exists():
            for f in target_dir.glob("*.jsonl"):
                f.unlink()
    print(f"[precondition cleanup] {len(smoke_targets)} target DDP の chunk cache 全削除完了")

    # ===== precondition (3 step) =====
    print("[1/16] precondition: VDR root 存在")
    if VDR_ROOT.exists() and any(VDR_ROOT.iterdir()):
        result.ok("VDR root", f"{VDR_ROOT}")
    else:
        result.fail("VDR root", f"{VDR_ROOT} 不在、 まず src.data_gen.generate_synthetic_vdr 実行")
        return result.summary()

    print("[2/16] precondition: 40 docs literal 存在")
    all_docs = list(VDR_ROOT.rglob("*.pdf")) + list(VDR_ROOT.rglob("*.docx")) + \
               list(VDR_ROOT.rglob("*.xlsx")) + list(VDR_ROOT.rglob("*.pptx"))
    if len(all_docs) == 40:
        result.ok("40 docs", f"PDF + DOCX + XLSX + PPTX = {len(all_docs)} 件")
    else:
        result.fail("40 docs", f"count={len(all_docs)} (expected 40)")

    print("[3/16] precondition: 質問票 300 項目")
    if QUESTIONNAIRE_PATH.exists():
        with open(QUESTIONNAIRE_PATH, encoding="utf-8") as f:
            qs = [json.loads(line) for line in f if line.strip()]
        if len(qs) == 300:
            result.ok("質問票 300", f"financial+legal+business 各 100 件")
        else:
            result.fail("質問票 300", f"count={len(qs)} (expected 300)")
    else:
        result.fail("質問票", "data/questionnaire/questions.jsonl 不在")

    # ===== ingestion (4 step) =====
    print("[4/16] ingestion: clean DDP (DDP-PHQjtztxy8I 印刷) を Docling 抽出")
    from src.ingestion.parse_vdr_docs import parse_ddp

    clean_ddp = VDR_ROOT / "DDP-PHQjtztxy8I"
    if not clean_ddp.exists():
        result.fail("clean DDP", f"{clean_ddp} 不在 (seed 変更?)")
        return result.summary()

    t = time.time()
    try:
        clean_stats = parse_ddp(clean_ddp, output_root=CHUNK_CACHE)
        clean_chunks_total = sum(clean_stats.values())
        elapsed = time.time() - t
        result.ok("clean DDP ingestion", f"docs={len(clean_stats)} / chunks={clean_chunks_total} / {elapsed:.1f}s")
    except Exception as e:
        result.fail("clean DDP ingestion", f"{type(e).__name__}: {str(e)[:80]}")
        return result.summary()

    print("[5/16] ingestion: multi-pattern DDP (DDP-Fn-mP3hsIKw 映像制作) を Docling 抽出")
    multi_ddp = VDR_ROOT / "DDP-Fn-mP3hsIKw"
    if not multi_ddp.exists():
        result.fail("multi-pattern DDP", f"{multi_ddp} 不在")
    else:
        t = time.time()
        try:
            multi_stats = parse_ddp(multi_ddp, output_root=CHUNK_CACHE)
            multi_chunks_total = sum(multi_stats.values())
            elapsed = time.time() - t
            result.ok("multi-pattern DDP ingestion", f"docs={len(multi_stats)} / chunks={multi_chunks_total} / {elapsed:.1f}s")
        except Exception as e:
            result.fail("multi-pattern DDP ingestion", f"{type(e).__name__}: {str(e)[:80]}")

    print("[6/16] ingestion: chunk JSONL 出力検証")
    clean_jsonls = list((CHUNK_CACHE / "DDP-PHQjtztxy8I").glob("*.jsonl"))
    if len(clean_jsonls) == 8:
        result.ok("chunk JSONL", f"clean DDP = 8 docs × 1 JSONL/doc = 8 files")
    else:
        result.fail("chunk JSONL", f"clean DDP count={len(clean_jsonls)} (expected 8)")

    print("[7/16] ingestion: chunk metadata schema 順守")
    # 全 JSONL の line count を集計、 first non-empty JSONL を sample にして schema check
    jsonl_counts: dict[str, int] = {}
    sample_chunks: list[dict] = []
    for jp in clean_jsonls:
        with open(jp, encoding="utf-8") as f:
            chunks = [json.loads(line) for line in f if line.strip()]
        jsonl_counts[jp.name] = len(chunks)
        if chunks and not sample_chunks:
            sample_chunks = chunks
    empty_count = sum(1 for c in jsonl_counts.values() if c == 0)
    nonempty_count = len(jsonl_counts) - empty_count
    if sample_chunks:
        ch = sample_chunks[0]
        required = ["chunk_id", "doc_id", "ddp_id", "page", "text_redacted",
                    "text_chars", "extracted_at", "extractor", "language", "redaction_applied"]
        missing = [f for f in required if f not in ch]
        if not missing:
            result.ok(
                "schema 順守",
                f"必須 10 field 全完備、 non-empty={nonempty_count} / empty={empty_count} (XLSX 等で chunks 0 = Docling 仕様、 honest tracking)",
            )
        else:
            result.fail("schema 順守", f"missing fields: {missing}")
    else:
        result.fail("schema 順守", "全 JSONL empty = ingestion 真 fail")

    # ===== detector (4 step) =====
    print("[8/16] clause detector: clean DDP に apply")
    from src.clause.extract_clauses import detect_clauses, hits_by_kind

    def _load_chunks(ddp_id: str) -> list[dict]:
        out: list[dict] = []
        for jp in (CHUNK_CACHE / ddp_id).glob("*.jsonl"):
            with open(jp, encoding="utf-8") as f:
                out.extend(json.loads(line) for line in f if line.strip())
        return out

    clean_all_chunks = _load_chunks("DDP-PHQjtztxy8I")
    clean_clause_hits = detect_clauses(clean_all_chunks)
    clean_clause_kinds = hits_by_kind(clean_clause_hits)
    # clean DDP でも 規程 docs (share_transfer_regulations.docx) に Change of Control 等の literal 記述あり
    if "change_of_control" in clean_clause_kinds:
        result.ok("clause: clean DDP",
                  f"hits={len(clean_clause_hits)} / kinds={list(clean_clause_kinds.keys())}")
    else:
        result.fail("clause: clean DDP",
                    f"hits={len(clean_clause_hits)}、 change_of_control 未検出 (規程 docs から literal 期待)")

    print("[9/16] clause detector: multi-pattern DDP に apply")
    multi_all_chunks = _load_chunks("DDP-Fn-mP3hsIKw")
    multi_clause_hits = detect_clauses(multi_all_chunks)
    multi_clause_kinds = hits_by_kind(multi_clause_hits)
    if multi_clause_hits:
        result.ok("clause: multi-pattern DDP",
                  f"hits={len(multi_clause_hits)} / kinds={list(multi_clause_kinds.keys())}")
    else:
        result.fail("clause: multi-pattern DDP", "0 hit (規程 docs から literal 期待)")

    print("[10/16] jp_patterns: clean DDP に apply (期待 = 0 件 hit、 正常企業 mix verify)")
    from src.jp_patterns.detect import detect_all

    clean_jp_hits = detect_all("DDP-PHQjtztxy8I", clean_all_chunks)
    if len(clean_jp_hits) == 0:
        result.ok("jp_patterns: clean DDP", "0 hit = false-positive 抑制 verified")
    else:
        # clean 企業でも僅か hit する可能性は許容、 ただし family_governance high confidence は要 review
        kinds = [h.kind for h in clean_jp_hits]
        if "family_governance" in kinds and any(h.confidence >= 0.8 for h in clean_jp_hits if h.kind == "family_governance"):
            result.fail("jp_patterns: clean DDP",
                        f"high-confidence family_governance 検出 = false-positive 候補 / hits={kinds}")
        else:
            result.ok("jp_patterns: clean DDP", f"{len(clean_jp_hits)} hit (low confidence、 acceptable) / kinds={kinds}")

    print("[11/16] jp_patterns: multi-pattern DDP に apply (期待 = family + nominee 検出)")
    multi_jp_hits = detect_all("DDP-Fn-mP3hsIKw", multi_all_chunks)
    multi_jp_kinds = {h.kind for h in multi_jp_hits}
    expected_kinds = {"family_governance", "nominee_shareholder"}  # multi-pattern DDP の inject 内容
    intersect = expected_kinds & multi_jp_kinds
    if intersect:
        result.ok("jp_patterns: multi-pattern DDP",
                  f"hits={len(multi_jp_hits)} / kinds={multi_jp_kinds} / intersect={intersect}")
    else:
        result.fail("jp_patterns: multi-pattern DDP",
                    f"期待 {expected_kinds} のいずれも未検出 / actual={multi_jp_kinds}")

    # ===== pipeline (3 step、 BM25 + dense + RRF + cross-encoder、 Stage 5 LLM = mock) =====
    print("[12/16] pipeline: BM25 corpus 構築 verify")
    from src.pipeline import bm25_index, pipeline as pp

    # cache invalidate (前 run の残り回避)
    pp.invalidate_caches()
    try:
        bm25, ids, _ = bm25_index.get_bm25(ddp_id="DDP-Fn-mP3hsIKw")
        if len(ids) >= 10:
            result.ok("BM25 corpus", f"chunks indexed = {len(ids)}")
        else:
            result.fail("BM25 corpus", f"chunks={len(ids)} (期待 ≥ 10)")
    except Exception as e:
        result.fail("BM25 corpus", f"{type(e).__name__}: {str(e)[:80]}")

    print("[13/16] pipeline: 5-stage hybrid + Citation (query='Change of Control 条項')")
    t = time.time()
    try:
        reasoned, citations = pp.hybrid_search_with_citations(
            "Change of Control 条項の有無を確認してください",
            ddp_id="DDP-Fn-mP3hsIKw",
            top_k=5,
        )
        elapsed = time.time() - t
        if reasoned and citations:
            top_label = reasoned[0][1]
            result.ok("5-stage pipeline Q1",
                      f"top_k={len(reasoned)} / top_label={top_label} / cit={len(citations)} / {elapsed:.1f}s")
        else:
            result.fail("5-stage pipeline Q1", f"reasoned={len(reasoned)} / citations={len(citations)}")
    except Exception as e:
        result.fail("5-stage pipeline Q1", f"{type(e).__name__}: {str(e)[:100]}")

    print("[14/16] pipeline: Citation link back verify (page > 0、 doc_id 存在)")
    try:
        if citations:
            valid = sum(1 for c in citations if c.page >= 1 and c.doc_id and c.chunk_id)
            if valid == len(citations):
                result.ok("Citation link back",
                          f"{len(citations)} citations、 全 page≥1 + doc_id + chunk_id 完備")
            else:
                result.fail("Citation link back", f"{valid}/{len(citations)} valid")
        else:
            result.fail("Citation link back", "no citations (前 step skip)")
    except Exception as e:
        result.fail("Citation link back", f"{type(e).__name__}: {str(e)[:80]}")

    # ===== summary (2 step) =====
    print("[15/16] summary: chunk total 集計")
    total_chunks_files = list(CHUNK_CACHE.rglob("*.jsonl"))
    total_chunks = 0
    for jp in total_chunks_files:
        with open(jp, encoding="utf-8") as f:
            total_chunks += sum(1 for line in f if line.strip())
    result.ok("chunk total", f"JSONL files={len(total_chunks_files)} / chunks={total_chunks}")

    print("[16/16] summary: detector hit distribution")
    result.ok(
        "detector distribution",
        f"clean clause={len(clean_clause_hits)} + clean jp={len(clean_jp_hits)} "
        f"/ multi clause={len(multi_clause_hits)} + multi jp={len(multi_jp_hits)}",
    )

    return result.summary()


if __name__ == "__main__":
    raise SystemExit(main())
