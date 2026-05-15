"""Stage 4: Cross-encoder pair-wise reranker (T1 ADR-005 literal reuse、 schema 中立)。

cross-encoder/ms-marco-MiniLM-L-12-v2 (Apache-2.0、 HuggingFace 公式) で
query + candidate を pair-wise scoring、 RRF (Stage 3) top の listwise を
pair-wise 精度で order し直す。

Reference: mais-deal-matching/src/matching/cross_encoder_rerank.py literal copy。
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from sentence_transformers import CrossEncoder

load_dotenv()

DEFAULT_MODEL = os.environ.get("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-12-v2")


@lru_cache(maxsize=1)
def _get_model(name: str = DEFAULT_MODEL) -> CrossEncoder:
    return CrossEncoder(name)


def rerank(
    query: str,
    candidates: list[tuple[str, str]],
    top_k: int | None = None,
    model_name: str = DEFAULT_MODEL,
) -> list[tuple[str, float]]:
    """candidates = [(id, doc_text), ...] を pair-wise rerank、 (id, score) descending."""
    if not candidates:
        return []
    model = _get_model(model_name)
    pairs = [(query, doc) for _, doc in candidates]
    scores = model.predict(pairs, show_progress_bar=False)
    ranked = sorted(
        [(cid, float(s)) for (cid, _), s in zip(candidates, scores)],
        key=lambda x: x[1],
        reverse=True,
    )
    if top_k is not None:
        ranked = ranked[:top_k]
    return ranked
