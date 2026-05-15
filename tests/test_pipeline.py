"""Unit tests for src.pipeline + src.data_gen.questionnaire (T2 Week 2、 ADR-105/106)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.pipeline import bm25_index, rrf
from src.pipeline.llm_provider import LLMProvider, MockProvider, get_provider
from src.pipeline.llm_rerank import build_cot_prompt, listwise_rerank
from src.data_gen.questionnaire import build_questions, FINANCIAL_TEMPLATES, LEGAL_TEMPLATES, BUSINESS_TEMPLATES


# ===== rrf unit tests =====


def test_rrf_basic_fusion() -> None:
    """2 rank list の同 id が両方 top1 で最高 score."""
    bm25 = [("CHK-A", 1.0), ("CHK-B", 0.5)]
    dense = [("CHK-A", 0.9), ("CHK-C", 0.8)]
    fused = rrf.reciprocal_rank_fusion([bm25, dense])
    assert fused[0][0] == "CHK-A"


def test_rrf_top_k_truncate() -> None:
    """top_k で literal 切詰."""
    bm25 = [("CHK-A", 1.0), ("CHK-B", 0.5), ("CHK-C", 0.3)]
    fused = rrf.reciprocal_rank_fusion([bm25], top_k=2)
    assert len(fused) == 2


def test_rrf_empty_input() -> None:
    """空 input で空 output."""
    assert rrf.reciprocal_rank_fusion([]) == []


# ===== bm25 tokenize unit tests =====


def test_bm25_tokenize_japanese() -> None:
    """日本語 + ASCII の literal split."""
    tokens = bm25_index.tokenize("本契約は Change of Control 条項に従う。")
    assert "本契約は" in tokens
    assert "Change" in tokens
    assert "of" in tokens
    assert "Control" in tokens
    assert "条項に従う" in tokens


def test_bm25_tokenize_empty() -> None:
    """空 text で空 tokens."""
    assert bm25_index.tokenize("") == []
    assert bm25_index.tokenize("   、。 ") == []


# ===== LLMProvider unit tests =====


def test_mock_provider_returns_labeled_results() -> None:
    """MockProvider が (id, label, reasoning) tuple を top_k 件返却."""
    provider = MockProvider()
    candidates = [
        ("CHK-1", "本契約の第 3 条 Change of Control 条項に基づき、 取締役会承認を要する。"),
        ("CHK-2", "役員報酬は業界中央値 の 2.5 倍 とする。"),
        ("CHK-3", "本日の天気は晴れです。"),
    ]
    results = provider.listwise_rerank("Change of Control 条項の有無", candidates, top_k=3)
    assert len(results) == 3
    for cid, label, reasoning in results:
        assert label in ("high", "medium", "low")
        assert isinstance(reasoning, str)


def test_mock_provider_high_for_relevant() -> None:
    """keyword 多数 match で 'high' label."""
    provider = MockProvider()
    candidates = [
        ("CHK-1", "第 3 条 Change of Control 条項により 持分譲渡時 取締役会承認を要する。 株主 名義変更も同様。"),
    ]
    results = provider.listwise_rerank("第 3 条 持分 譲渡 承認", candidates, top_k=1)
    cid, label, _ = results[0]
    assert label == "high"


def test_get_provider_default_mock() -> None:
    """env LLM_PROVIDER default = 'mock' で MockProvider."""
    provider = get_provider()
    assert isinstance(provider, MockProvider)


def test_build_cot_prompt_contains_query_and_candidates() -> None:
    """CoT prompt に query + candidates が literal 含まれる."""
    candidates = [("CHK-1", "test text")]
    prompt = build_cot_prompt("Change of Control", candidates, top_k=1)
    assert "Change of Control" in prompt
    assert "CHK-1" in prompt
    assert "top_k = 1" in prompt


def test_listwise_rerank_with_mock() -> None:
    """listwise_rerank が MockProvider 経由で動作."""
    candidates = [("CHK-1", "Change of Control 条項 株主 名義変更")]
    results = listwise_rerank("Change of Control", candidates, top_k=1)
    assert len(results) == 1
    assert results[0][1] in ("high", "medium", "low")


# ===== questionnaire unit tests =====


def test_questionnaire_template_count() -> None:
    """各 category 100 項目、 計 300 項目 literal."""
    assert len(FINANCIAL_TEMPLATES) == 100
    assert len(LEGAL_TEMPLATES) == 100
    assert len(BUSINESS_TEMPLATES) == 100


def test_questionnaire_build_returns_300_dicts() -> None:
    """build_questions で 300 件 dict、 各 q_id + category + question_text + expected_evidence_kind 含."""
    qs = build_questions()
    assert len(qs) == 300
    for q in qs:
        assert q["q_id"].startswith("Q-")
        assert q["category"] in ("financial", "legal", "business")
        assert isinstance(q["question_text"], str) and len(q["question_text"]) > 0
        assert isinstance(q["expected_evidence_kind"], str)


def test_questionnaire_evidence_kind_inference() -> None:
    """'Change of Control' 含 質問 = clause:change_of_control の expected_evidence_kind."""
    qs = build_questions()
    coc_qs = [q for q in qs if "Change of Control" in q["question_text"]]
    assert len(coc_qs) >= 1
    for q in coc_qs:
        assert q["expected_evidence_kind"] == "clause:change_of_control"


def test_questionnaire_categories_each_100() -> None:
    """各 category が literal 100 件、 重複 q_id なし."""
    qs = build_questions()
    cats: dict[str, int] = {}
    q_ids: set[str] = set()
    for q in qs:
        cats[q["category"]] = cats.get(q["category"], 0) + 1
        q_ids.add(q["q_id"])
    assert cats == {"financial": 100, "legal": 100, "business": 100}
    assert len(q_ids) == 300  # 重複 ZERO
