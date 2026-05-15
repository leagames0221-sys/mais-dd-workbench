"""Unit tests for src.ingestion (T2 Week 1、 ADR-101/102)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.ingestion.chunk_schema import (
    ChunkMetadata,
    Citation,
    DocKind,
    _new_id,
    now_jst,
)
from src.ingestion.parse_vdr_docs import _detect_doc_kind, _redact


# ===== chunk_schema unit tests =====


def test_new_id_prefix_and_length() -> None:
    """_new_id は prefix + secrets.token_urlsafe(12)、 prefix 含 ≤ 30 chars."""
    cid = _new_id("CHK")
    assert cid.startswith("CHK-")
    assert len(cid) <= 30  # token_urlsafe(12) = 16 chars + prefix-4


def test_chunk_metadata_required_fields() -> None:
    """必須 field 全 揃って ChunkMetadata literal construct."""
    chunk = ChunkMetadata(
        chunk_id="CHK-test123",
        doc_id="DOC-test456",
        ddp_id="DDP-test789",
        page=1,
        text_redacted="本契約は当事者間の合意により締結された。",
        text_chars=22,
        extracted_at=now_jst(),
        extractor="docling-2.93.0",
        language="ja",
        redaction_applied=False,
    )
    assert chunk.page == 1
    assert chunk.doc_kind == DocKind.UNKNOWN  # default


def test_chunk_metadata_page_must_be_positive() -> None:
    """page < 1 で ValidationError (ge=1 制約)."""
    with pytest.raises(ValidationError):
        ChunkMetadata(
            chunk_id="CHK-x",
            doc_id="DOC-x",
            ddp_id="DDP-x",
            page=0,  # invalid
            text_redacted="...",
            text_chars=3,
            extracted_at=now_jst(),
            extractor="docling-2.93.0",
            language="ja",
            redaction_applied=False,
        )


def test_chunk_metadata_extra_forbid() -> None:
    """extra field は forbid (ConfigDict extra='forbid')."""
    with pytest.raises(ValidationError):
        ChunkMetadata(
            chunk_id="CHK-x",
            doc_id="DOC-x",
            ddp_id="DDP-x",
            page=1,
            text_redacted="...",
            text_chars=3,
            extracted_at=now_jst(),
            extractor="docling-2.93.0",
            language="ja",
            redaction_applied=False,
            unknown_field="should fail",  # type: ignore[call-arg]
        )


def test_chunk_metadata_optional_bbox() -> None:
    """bbox = 4-tuple float、 ChunkMetadata literal accept."""
    chunk = ChunkMetadata(
        chunk_id="CHK-x",
        doc_id="DOC-x",
        ddp_id="DDP-x",
        page=1,
        text_redacted="...",
        text_chars=3,
        extracted_at=now_jst(),
        extractor="docling-2.93.0",
        language="ja",
        redaction_applied=False,
        bbox=(10.0, 20.0, 100.0, 50.0),
    )
    assert chunk.bbox == (10.0, 20.0, 100.0, 50.0)


def test_citation_confidence_bounds() -> None:
    """confidence は [0.0, 1.0]、 外れ値で ValidationError."""
    with pytest.raises(ValidationError):
        Citation(
            citation_id="CIT-x",
            answer_id="A-x",
            chunk_id="CHK-x",
            doc_id="DOC-x",
            page=1,
            snippet="...",
            confidence=1.5,  # invalid
        )


def test_citation_snippet_max_length() -> None:
    """snippet > 200 chars で ValidationError."""
    with pytest.raises(ValidationError):
        Citation(
            citation_id="CIT-x",
            answer_id="A-x",
            chunk_id="CHK-x",
            doc_id="DOC-x",
            page=1,
            snippet="a" * 250,
            confidence=0.8,
        )


# ===== parse_vdr_docs unit tests =====


def test_detect_doc_kind_known_extensions() -> None:
    """各拡張子 → DocKind 正確 mapping."""
    assert _detect_doc_kind(Path("foo.pdf")) == DocKind.PDF
    assert _detect_doc_kind(Path("foo.docx")) == DocKind.DOCX
    assert _detect_doc_kind(Path("foo.xlsx")) == DocKind.XLSX
    assert _detect_doc_kind(Path("foo.pptx")) == DocKind.PPTX
    assert _detect_doc_kind(Path("foo.html")) == DocKind.HTML
    assert _detect_doc_kind(Path("foo.htm")) == DocKind.HTML
    assert _detect_doc_kind(Path("foo.zip")) == DocKind.UNKNOWN


def test_redact_email() -> None:
    """email を [EMAIL] mask + applied=True."""
    text = "連絡先: yamamoto@example.com まで"
    redacted, applied = _redact(text)
    assert "[EMAIL]" in redacted
    assert "yamamoto" not in redacted
    assert applied is True


def test_redact_phone() -> None:
    """phone を [PHONE] mask + applied=True."""
    text = "Tel: 03-1234-5678"
    redacted, applied = _redact(text)
    assert "[PHONE]" in redacted
    assert "1234-5678" not in redacted
    assert applied is True


def test_redact_no_pii() -> None:
    """PII なし時は applied=False、 text 不変."""
    text = "本契約は当事者間の合意により締結された。"
    redacted, applied = _redact(text)
    assert redacted == text
    assert applied is False


@pytest.mark.slow
def test_parse_document_smoke(tmp_path) -> None:
    """end-to-end smoke: generate 1 PDF → Docling parse → chunks (slow tag)."""
    import random
    from faker import Faker
    from src.data_gen.generate_synthetic_vdr import generate_pdf_tax_return, make_ddp
    from src.ingestion.parse_vdr_docs import parse_document

    rng = random.Random(20260512)
    faker = Faker("ja_JP")
    Faker.seed(20260512)
    ddp = make_ddp(0, rng, faker)

    pdf_path = tmp_path / "tax_return.pdf"
    generate_pdf_tax_return(ddp, pdf_path, rng)
    assert pdf_path.exists() and pdf_path.stat().st_size > 500

    chunks = parse_document(pdf_path, doc_id="DOC-test", ddp_id=ddp.ddp_id)
    assert len(chunks) >= 1, "PDF から chunk が抽出されなかった"
    # 各 chunk は ChunkMetadata schema 順守
    for c in chunks:
        assert c.doc_id == "DOC-test"
        assert c.ddp_id == ddp.ddp_id
        assert c.page >= 1
        assert c.extractor.startswith("docling-")
        assert c.language == "ja"
