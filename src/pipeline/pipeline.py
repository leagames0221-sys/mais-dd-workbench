"""5-stage hybrid pipeline over chunk corpus (T2 Week 2、 T1 ADR-005 literal reuse + Citation 機能)。

[query] → BM25 (Stage 1) + dense embedding (Stage 2) → RRF (Stage 3) →
cross-encoder (Stage 4) → LLM listwise rerank (Stage 5) → Citation array (ADR-102 schema)

T1 との差: chunk-based + Citation 生成 + 移植時に real LLM (Gemini/Claude/Ollama) swap path
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from src.ingestion.chunk_schema import Citation, _new_id
from src.pipeline import bm25_index, cross_encoder_rerank, llm_rerank, rrf

load_dotenv()

DENSE_MODEL = os.environ.get("DENSE_MODEL", "intfloat/multilingual-e5-large")
DENSE_TOP_K = int(os.environ.get("DENSE_TOP_K", "50"))
BM25_TOP_K = int(os.environ.get("BM25_TOP_K", "50"))
RRF_TOP_K = int(os.environ.get("RRF_TOP_K", "25"))
CROSS_TOP_K = int(os.environ.get("CROSS_TOP_K", "15"))
LLM_TOP_K = int(os.environ.get("LLM_TOP_K", "5"))


@lru_cache(maxsize=1)
def _dense_model() -> SentenceTransformer:
    return SentenceTransformer(DENSE_MODEL)


_DENSE_INDEX: dict[str | None, tuple[np.ndarray, list[str], list[str]]] = {}


def _build_dense_index(ddp_id: str | None = None) -> tuple[np.ndarray, list[str], list[str]]:
    """chunk corpus を dense encode、 (matrix, ids, texts) を return + cache."""
    if ddp_id in _DENSE_INDEX:
        return _DENSE_INDEX[ddp_id]
    ids: list[str] = []
    texts: list[str] = []
    for chunk in bm25_index.iter_chunks(ddp_id):
        ids.append(chunk["chunk_id"])
        texts.append(chunk["text_redacted"])
    if not texts:
        empty = (np.zeros((0, 1024), dtype=np.float32), [], [])
        _DENSE_INDEX[ddp_id] = empty
        return empty
    model = _dense_model()
    # e5 系 prefix convention: passage 側に "passage: " 付与
    encoded = model.encode(
        [f"passage: {t}" for t in texts],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    out = (encoded.astype(np.float32), ids, texts)
    _DENSE_INDEX[ddp_id] = out
    return out


def _dense_search(query: str, ddp_id: str | None, top_k: int) -> list[tuple[str, float]]:
    matrix, ids, _texts = _build_dense_index(ddp_id)
    if matrix.shape[0] == 0:
        return []
    model = _dense_model()
    q_emb = model.encode(
        [f"query: {query}"],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0]
    scores = matrix @ q_emb
    ranked = sorted(zip(ids, scores), key=lambda x: x[1], reverse=True)
    return [(cid, float(s)) for cid, s in ranked[:top_k]]


def _chunk_text_lookup(ddp_id: str | None = None) -> dict[str, dict]:
    """chunk_id → chunk dict lookup (text / doc_id / page 等)."""
    return {c["chunk_id"]: c for c in bm25_index.iter_chunks(ddp_id)}


def hybrid_search(
    query: str,
    ddp_id: str | None = None,
    top_k: int = LLM_TOP_K,
) -> list[tuple[str, float]]:
    """5-stage hybrid (LLM 除く 4 stage) で top_k chunk を return (id, cross_score)."""
    # Stage 1: BM25
    bm25_results = bm25_index.search(query, top_k=BM25_TOP_K, ddp_id=ddp_id)
    # Stage 2: dense
    dense_results = _dense_search(query, ddp_id, top_k=DENSE_TOP_K)
    # Stage 3: RRF
    fused = rrf.reciprocal_rank_fusion([bm25_results, dense_results], top_k=RRF_TOP_K)
    if not fused:
        return []
    # Stage 4: cross-encoder
    lookup = _chunk_text_lookup(ddp_id)
    candidates = [(cid, lookup[cid]["text_redacted"]) for cid, _ in fused if cid in lookup]
    reranked = cross_encoder_rerank.rerank(query, candidates, top_k=CROSS_TOP_K)
    return reranked[:top_k]


def hybrid_search_with_citations(
    query: str,
    ddp_id: str | None = None,
    top_k: int = LLM_TOP_K,
    answer_id: str | None = None,
) -> tuple[list[tuple[str, str, str]], list[Citation]]:
    """5-stage full pipeline + Citation array 生成 (ADR-102 schema)。

    Returns:
        (reasoned_results, citations):
          reasoned_results = [(chunk_id, fit_label, reasoning), ...] (Stage 5 LLM 出力)
          citations = [Citation(...), ...] (ADR-102 Pydantic、 answer link back)
    """
    answer_id = answer_id or _new_id("A")
    # Stage 1-4
    bm25_results = bm25_index.search(query, top_k=BM25_TOP_K, ddp_id=ddp_id)
    dense_results = _dense_search(query, ddp_id, top_k=DENSE_TOP_K)
    fused = rrf.reciprocal_rank_fusion([bm25_results, dense_results], top_k=RRF_TOP_K)
    lookup = _chunk_text_lookup(ddp_id)
    candidates = [(cid, lookup[cid]["text_redacted"]) for cid, _ in fused if cid in lookup]
    reranked = cross_encoder_rerank.rerank(query, candidates, top_k=CROSS_TOP_K)
    if not reranked:
        return [], []

    # Stage 5: LLM listwise rerank
    stage5_input = [(cid, lookup[cid]["text_redacted"]) for cid, _ in reranked]
    reasoned = llm_rerank.listwise_rerank(query, stage5_input, top_k=top_k)

    # Citation 生成 (ADR-102)
    score_map = {cid: s for cid, s in reranked}
    citations: list[Citation] = []
    for cid, fit_label, _reasoning in reasoned:
        ch = lookup.get(cid)
        if ch is None:
            continue
        snippet = ch["text_redacted"][:200]
        # cross-encoder score を [0,1] にざっくり map (sigmoid 風)
        raw = score_map.get(cid, 0.0)
        confidence = float(1.0 / (1.0 + np.exp(-raw)))
        citations.append(
            Citation(
                answer_id=answer_id,
                chunk_id=cid,
                doc_id=ch["doc_id"],
                page=ch["page"],
                snippet=snippet,
                confidence=confidence,
            )
        )
    return reasoned, citations


def invalidate_caches(ddp_id: str | None = None) -> None:
    """全 corpus cache (BM25 + dense) を invalidate."""
    bm25_index.invalidate_cache(ddp_id)
    if ddp_id is None:
        _DENSE_INDEX.clear()
    else:
        _DENSE_INDEX.pop(ddp_id, None)
