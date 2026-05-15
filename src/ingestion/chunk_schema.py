"""Chunk + Citation Pydantic schema (ADR-102 SSoT、 systemPatterns 連動).

Run: 直接 import 経由のみ (no CLI entry)。

ADR-102 順守:
  - 必須 7 field + Optional 4 field
  - Citation link back (Hebbia 商用と literal 同等) の core data structure
  - PII boundary: text_redacted のみ literal 保持 (raw text は ChunkPII vault 側、 必要時のみ)
  - 移植時 = Pydantic → SQLAlchemy ORM mapping 1 file (orm.py) で本番化、 schema 不変
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


def _new_id(prefix: str) -> str:
    """secrets.token_urlsafe(12) ベースの不可推測 ID (PROF/COMP/DOC/CHK/Q/A/CIT/JPP 共通)."""
    return f"{prefix}-{secrets.token_urlsafe(12)}"


class DocKind(str, Enum):
    """source document 種別 (Docling 入力 file type)."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    HTML = "html"
    UNKNOWN = "unknown"


class ChunkMetadata(BaseModel):
    """Docling 抽出 chunk の operational metadata (ADR-102)."""

    model_config = ConfigDict(extra="forbid", frozen=False)

    chunk_id: str = Field(default_factory=lambda: _new_id("CHK"))
    doc_id: str
    ddp_id: str
    page: int = Field(ge=1, description="1-indexed page number")
    text_redacted: str = Field(description="Presidio 相当で PII redact 済")
    text_chars: int = Field(ge=0)
    extracted_at: datetime
    extractor: str = Field(description="例 'docling-2.93.0'")
    language: str = Field(description="例 'ja' / 'en'")
    redaction_applied: bool

    # Optional (doc type 依存)
    doc_kind: DocKind = DocKind.UNKNOWN
    section_header: Optional[str] = None
    bbox: Optional[tuple[float, float, float, float]] = None
    cell: Optional[str] = Field(default=None, description="Excel cell ref 例 'B12'")
    paragraph_offset: Optional[int] = Field(default=None, ge=0)


class Citation(BaseModel):
    """LLM 生成回答 → source chunk link back (ADR-102、 Clarum 仕様)."""

    model_config = ConfigDict(extra="forbid")

    citation_id: str = Field(default_factory=lambda: _new_id("CIT"))
    answer_id: str
    chunk_id: str
    doc_id: str
    page: int = Field(ge=1)
    snippet: str = Field(max_length=200, description="chunk text 抜粋")
    confidence: float = Field(ge=0.0, le=1.0)
    human_verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None


def now_jst() -> datetime:
    """JST tz-aware timestamp (extracted_at default 用)."""
    return datetime.now(timezone.utc)
