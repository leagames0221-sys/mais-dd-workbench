"""Docling DocumentConverter wrapper.

Run:
  python -m src.ingestion.parse_vdr_docs --ddp-id DDP-XXXXXX
  python -m src.ingestion.parse_vdr_docs --all

Output (data/cache/chunks/<DDP-id>/<doc-id>.jsonl):
  - 各 chunk = ChunkMetadata Pydantic instance
  - text_redacted は本 wrapper で literal redact (Presidio 相当 = src/redaction で実装、 Week 1 = 簡易 regex で placeholder)

 PII boundary 順守:
  - ingestion layer は vault DB に literal 書き込まない (operational のみ literal 出力)
  - raw text が PII 含む場合は redact 後 operational 保存、 raw text 自体は 本 wrapper で discard
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from docling.document_converter import DocumentConverter

from src.ingestion.chunk_schema import ChunkMetadata, DocKind, _new_id

# Docling package version (pip 経由 install 時の actual version)。
# import 時には docling.__version__ が literal 公開されないため、
# pip metadata から 読む path で本 PoC では const string 維持 (移植時 importlib.metadata に置換)。
DOCLING_VERSION_STR = "docling-2.93.0"

# Week 1 簡易 PII redact (Presidio 相当の placeholder、 Week 4 で本格化)
PII_PATTERNS = [
    (re.compile(r"[\w\.\-]+@[\w\.\-]+"), "[EMAIL]"),
    (re.compile(r"0\d{1,4}-?\d{1,4}-?\d{3,4}"), "[PHONE]"),
    (re.compile(r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}"), "[CARD]"),
    (re.compile(r"\d{3}-?\d{4}\s*[都道府県]"), "[ZIP_ADDR]"),
]


def _redact(text: str) -> tuple[str, bool]:
    """簡易 PII redact、 (redacted_text, applied_flag) を返却."""
    redacted = text
    applied = False
    for pattern, placeholder in PII_PATTERNS:
        new = pattern.sub(placeholder, redacted)
        if new != redacted:
            applied = True
        redacted = new
    return redacted, applied


def _detect_doc_kind(path: Path) -> DocKind:
    """file 拡張子から DocKind enum 推定."""
    suffix = path.suffix.lower().lstrip(".")
    mapping = {
        "pdf": DocKind.PDF,
        "docx": DocKind.DOCX,
        "xlsx": DocKind.XLSX,
        "pptx": DocKind.PPTX,
        "htm": DocKind.HTML,
        "html": DocKind.HTML,
    }
    return mapping.get(suffix, DocKind.UNKNOWN)


def parse_document(
    path: Path,
    *,
    doc_id: str,
    ddp_id: str,
    converter: DocumentConverter | None = None,
) -> list[ChunkMetadata]:
    """1 ファイルを Docling で convert + chunk metadata list 返却."""
    converter = converter or DocumentConverter()
    result = converter.convert(str(path))
    doc = result.document
    doc_kind = _detect_doc_kind(path)
    extracted_at = datetime.now(timezone.utc)

    chunks: list[ChunkMetadata] = []
    # Docling document の text items を iterate、 1 text item = 1 chunk (PoC 簡易方針)。
    # production 時はsemantic chunking (semchunk 等) で chunk size 制御。
    for idx, (item, _level) in enumerate(doc.iterate_items()):
        text = getattr(item, "text", "") or ""
        text = text.strip()
        if not text:
            continue
        text_redacted, redaction_applied = _redact(text)

        # page 番号取得 (Docling item の prov から、 absent なら 1 fallback)
        page_no = 1
        prov = getattr(item, "prov", None) or []
        if prov:
            first = prov[0]
            page_no = int(getattr(first, "page_no", 1) or 1)

        chunk = ChunkMetadata(
            chunk_id=_new_id("CHK"),
            doc_id=doc_id,
            ddp_id=ddp_id,
            page=page_no,
            text_redacted=text_redacted,
            text_chars=len(text_redacted),
            extracted_at=extracted_at,
            extractor=DOCLING_VERSION_STR,
            language="ja",
            redaction_applied=redaction_applied,
            doc_kind=doc_kind,
            paragraph_offset=idx,
        )
        chunks.append(chunk)
    return chunks


def write_chunks(chunks: Iterable[ChunkMetadata], out_path: Path) -> int:
    """chunks を JSONL に literal write、 書き込み件数を返す."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(chunk.model_dump_json() + "\n")
            count += 1
    return count


def parse_ddp(ddp_dir: Path, *, output_root: Path) -> dict[str, int]:
    """1 DDP の全 docs を ingestion、 doc_id → chunk count の dict 返却."""
    ddp_id = ddp_dir.name
    converter = DocumentConverter()
    stats: dict[str, int] = {}
    for doc_path in sorted(ddp_dir.rglob("*")):
        if not doc_path.is_file():
            continue
        kind = _detect_doc_kind(doc_path)
        if kind == DocKind.UNKNOWN:
            continue
        doc_id = _new_id("DOC")
        chunks = parse_document(doc_path, doc_id=doc_id, ddp_id=ddp_id, converter=converter)
        out_path = output_root / ddp_id / f"{doc_id}.jsonl"
        count = write_chunks(chunks, out_path)
        stats[f"{doc_path.relative_to(ddp_dir)}#{doc_id}"] = count
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Docling ingestion wrapper")
    parser.add_argument("--ddp-id", help="単一 DDP 処理 (例 DDP-abc123)")
    parser.add_argument("--all", action="store_true", help="全 DDP 処理")
    parser.add_argument("--vdr-root", default="data/vdr_synthetic")
    parser.add_argument("--cache-root", default="data/cache/chunks")
    args = parser.parse_args()

    vdr_root = Path(args.vdr_root)
    cache_root = Path(args.cache_root)

    if not vdr_root.exists():
        print(f"[err] vdr_root {vdr_root} 不在、 まず src.data_gen.generate_synthetic_vdr を実行")
        return 1

    targets: list[Path] = []
    if args.all:
        targets = [p for p in vdr_root.iterdir() if p.is_dir()]
    elif args.ddp_id:
        target = vdr_root / args.ddp_id
        if not target.exists():
            print(f"[err] DDP {args.ddp_id} 不在")
            return 1
        targets = [target]
    else:
        parser.error("--all or --ddp-id 必要")

    total_docs = 0
    total_chunks = 0
    for ddp_dir in targets:
        stats = parse_ddp(ddp_dir, output_root=cache_root)
        n_docs = len(stats)
        n_chunks = sum(stats.values())
        total_docs += n_docs
        total_chunks += n_chunks
        print(f"[{ddp_dir.name}] docs={n_docs} / chunks={n_chunks}")

    print(f"[total] docs={total_docs} / chunks={total_chunks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
