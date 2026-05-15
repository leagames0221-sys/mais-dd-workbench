"""Contract clause extraction。

CUAD 41 clause category の subset を regex first pass で literal 検出。
Stage 1 = regex (高 precision、 false-positive 低)、 Stage 2 = LLM (recall 補完、 Week 3+)。

source: CUAD (Atticus Project、 CC BY 4.0) + ACORD (academic、 arxiv 2501.06582)
本 PoC で priority な 7 cat を literal cover、 残 34 cat は Week 3 で literal expand:
  1. Change of Control
  2. Limitation of Liability
  3. Indemnification
  4. Most Favored Nation (MFN)
  5. Non-Compete / Non-Solicitation
  6. Termination for Convenience
  7. Governing Law / Jurisdiction
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Literal

ClauseKind = Literal[
    "change_of_control",
    "limitation_of_liability",
    "indemnification",
    "mfn",
    "non_compete",
    "termination_for_convenience",
    "governing_law",
]


@dataclass
class ClauseHit:
    """1 chunk に対する clause 検出結果."""

    chunk_id: str
    doc_id: str
    kind: ClauseKind
    matched_phrase: str
    confidence: float # [0.0, 1.0]


# 各 cat の literal pattern (高 precision、 J 言語 + 英語混在、 中堅 M&A 契約書想定)
_PATTERNS: dict[ClauseKind, list[re.Pattern]] = {
    "change_of_control": [
        re.compile(r"Change\s+of\s+Control", re.IGNORECASE),
        re.compile(r"経営権(?:の|移)?(?:異動|変動|変更|移転)"),
        re.compile(r"発行済株式総数の\s*\d+\s*%\s*を超える(?:持分|株式)異動"),
        re.compile(r"持分(?:の)?\s*\d+\s*%\s*(?:超|を超える|以上)?\s*(?:異動|変動)"),
    ],
    "limitation_of_liability": [
        re.compile(r"Limitation\s+of\s+Liability", re.IGNORECASE),
        re.compile(r"責任の\s*(?:上限|制限)"),
        re.compile(r"損害賠償(?:額)?(?:の)?(?:上限|総額制限)"),
    ],
    "indemnification": [
        re.compile(r"Indemnif(?:y|ication)", re.IGNORECASE),
        re.compile(r"補償(?:義務|条項)"),
        re.compile(r"損害(?:を)?(?:補填|補償|填補)"),
    ],
    "mfn": [
        re.compile(r"Most\s+Favored\s+Nation", re.IGNORECASE),
        re.compile(r"MFN(?:\s+条項)?", re.IGNORECASE),
        re.compile(r"最恵国(?:待遇)?(?:条項)?"),
    ],
    "non_compete": [
        re.compile(r"Non[-\s]*Compet(?:e|ition)", re.IGNORECASE),
        re.compile(r"競業避止(?:義務|条項)"),
        re.compile(r"競合事業(?:への)?(?:従事|参加)(?:の)?禁止"),
    ],
    "termination_for_convenience": [
        re.compile(r"Termination\s+for\s+Convenience", re.IGNORECASE),
        re.compile(r"任意解約(?:権|条項)"),
        re.compile(r"理由(?:の)?有無(?:に)?(?:かかわらず|関わらず)?\s*(?:本契約)?(?:を)?解約"),
    ],
    "governing_law": [
        re.compile(r"Governing\s+Law", re.IGNORECASE),
        re.compile(r"準拠法(?:は|を)?\s*(?:日本(?:国)?法|英国法|米国法)"),
        re.compile(r"管轄(?:裁判所)?(?:は|を)?"),
    ],
}


def detect_clauses(chunks: Iterable[dict]) -> list[ClauseHit]:
    """chunk dict list (ChunkMetadata serialized) → ClauseHit list を return.

    confidence:
        1.0 = pattern complete match
        0.85 = ASCII case-insensitive match
        0.70 = 日本語 partial match
    """
    hits: list[ClauseHit] = []
    for chunk in chunks:
        cid = chunk["chunk_id"]
        did = chunk["doc_id"]
        text = chunk["text_redacted"]
        for kind, patterns in _PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    # ASCII-only pattern = higher confidence、 日本語 = やや低 (false-positive risk あり)
                    is_ascii_pat = all(ord(c) < 128 for c in pattern.pattern if c.isalnum())
                    confidence = 0.85 if is_ascii_pat else 0.70
                    hits.append(
                        ClauseHit(
                            chunk_id=cid,
                            doc_id=did,
                            kind=kind,
                            matched_phrase=match.group(0),
                            confidence=confidence,
                        )
                    )
                    break # 1 chunk 1 cat 1 hit (重複検出抑制)
    return hits


def hits_by_kind(hits: list[ClauseHit]) -> dict[ClauseKind, list[ClauseHit]]:
    """ClauseKind → hits list の groupby."""
    out: dict[ClauseKind, list[ClauseHit]] = {}
    for h in hits:
        out.setdefault(h.kind, []).append(h)
    return out
