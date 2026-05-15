"""Stage 3: Reciprocal Rank Fusion (T1 ADR-005 literal reuse、 schema 中立)。

BM25 (Stage 1) と dense embedding (Stage 2) の 2 rank list を 1 つに統合。
各 list の rank r (1-based) に対し score = sum(1 / (k + r))、 k = 60 default
(Cormack et al. 2009 standard)。

Reference: mais-deal-matching/src/matching/rrf.py literal copy。
"""
from __future__ import annotations

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    rank_lists: list[list[tuple[str, float]]],
    k: int = DEFAULT_RRF_K,
    top_k: int | None = None,
) -> list[tuple[str, float]]:
    """複数 rank list を fuse、 RRF score 降順の (id, score) を返す."""
    rrf_scores: dict[str, float] = {}
    for rank_list in rank_lists:
        for rank, (item_id, _) in enumerate(rank_list, start=1):
            rrf_scores[item_id] = rrf_scores.get(item_id, 0.0) + 1.0 / (k + rank)

    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    if top_k is not None:
        fused = fused[:top_k]
    return fused
