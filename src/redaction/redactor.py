"""PII redaction (T1 inherit、 ADR-007 layer 4 = 仮名加工情報化).

試作 = regex base、 移植 = Microsoft Presidio + spaCy ja_core_news_md。
"""
from __future__ import annotations

import re

PII_PATTERNS = [
    (re.compile(r"[\w\.\-]+@[\w\.\-]+"), "[EMAIL]"),
    (re.compile(r"0\d{1,4}-?\d{1,4}-?\d{3,4}"), "[PHONE]"),
    (re.compile(r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}"), "[CARD]"),
    (re.compile(r"\d{3}-?\d{4}"), "[ZIP]"),
]


def redact_text(text: str) -> tuple[str, bool]:
    """text の PII を placeholder 化、 (redacted, applied) 返却."""
    redacted = text
    applied = False
    for pat, ph in PII_PATTERNS:
        new = pat.sub(ph, redacted)
        if new != redacted:
            applied = True
        redacted = new
    return redacted, applied
