"""Stage 1: BM25 sparse lexical retrieval over chunk corpus (T2、 T1 ADR-005 pattern reuse)。

T1 (profile/company JSONL) から T2 (chunk JSONL) への schema adaptation。
chunk corpus = data/cache/chunks/<DDP-id>/<doc-id>.jsonl (ChunkMetadata Pydantic、 ADR-102)。
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

load_dotenv()

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))
CHUNK_CACHE_DIR = DATA_DIR / "cache" / "chunks"

# 日本語 + ASCII の単純 tokenizer (T1 と同 pattern、 将来 sudachi 等で本格化)
_TOKEN_SPLIT_RE = re.compile(r"[\s　、。「」『』【】\[\]()()！？!?:;・,\.]+")


def tokenize(text: str) -> list[str]:
    """text を 単純 split で tokens list 化 (空 token 除外)."""
    return [t for t in _TOKEN_SPLIT_RE.split(text) if t]


def iter_chunks(ddp_id: str | None = None) -> Iterable[dict]:
    """chunk cache JSONL を iterate、 ddp_id 指定なしで全 DDP iterate."""
    base = CHUNK_CACHE_DIR / ddp_id if ddp_id else CHUNK_CACHE_DIR
    if not base.exists():
        return
    for jsonl in sorted(base.rglob("*.jsonl")):
        with open(jsonl, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)


def build_bm25_corpus(ddp_id: str | None = None) -> tuple[BM25Okapi, list[str], list[str]]:
    """chunk corpus を tokenize + BM25 index 構築、 (bm25, ids, texts) を返却."""
    ids: list[str] = []
    texts: list[str] = []
    tokenized: list[list[str]] = []
    for chunk in iter_chunks(ddp_id):
        cid = chunk["chunk_id"]
        text = chunk["text_redacted"]
        ids.append(cid)
        texts.append(text)
        tokenized.append(tokenize(text))
    if not tokenized:
        # 空 corpus = 1 token dummy で BM25Okapi の zero-division 防御
        tokenized = [["__empty__"]]
    bm25 = BM25Okapi(tokenized)
    return bm25, ids, texts


_BM25_CACHE: dict[str | None, tuple[BM25Okapi, list[str], list[str]]] = {}


def get_bm25(ddp_id: str | None = None) -> tuple[BM25Okapi, list[str], list[str]]:
    """BM25 index を build + cache (T1 a34d27f literal 学び inherit、 query 毎 rebuild 回避)."""
    if ddp_id not in _BM25_CACHE:
        _BM25_CACHE[ddp_id] = build_bm25_corpus(ddp_id)
    return _BM25_CACHE[ddp_id]


def invalidate_cache(ddp_id: str | None = None) -> None:
    """ddp_id (or all) BM25 cache を invalidate."""
    if ddp_id is None:
        _BM25_CACHE.clear()
    else:
        _BM25_CACHE.pop(ddp_id, None)


def search(query: str, top_k: int = 50, ddp_id: str | None = None) -> list[tuple[str, float]]:
    """BM25 score 降順 (chunk_id, score) top_k を返却."""
    bm25, ids, _texts = get_bm25(ddp_id)
    if not ids:
        return []
    q_tokens = tokenize(query) or ["__empty__"]
    scores = bm25.get_scores(q_tokens)
    ranked = sorted(zip(ids, scores), key=lambda x: x[1], reverse=True)
    return [(cid, float(s)) for cid, s in ranked[:top_k]]
