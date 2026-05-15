"""LLM Provider interface (T1 ADR-005 Stage 5 literal reuse、 DD context 調整)。

User constraint 「無料 + クレカ不要」 順守 + doctrine: no-design-compromise:
framework full design、 LLM (Claude / Gemini / Ollama 等) は plug-in。
PoC = MockProvider (template + heuristic)、 移植時に real LLM に literal swap。

Reference: mais-deal-matching/src/matching/llm_provider.py literal copy + DD prompt 調整。
"""
from __future__ import annotations

import os
from typing import Protocol


class LLMProvider(Protocol):
    """LLM listwise rerank の最小 interface."""

    def listwise_rerank(
        self,
        query: str,
        candidates: list[tuple[str, str]],
        top_k: int = 5,
    ) -> list[tuple[str, str, str]]:
        """candidates = [(id, doc_text), ...] を listwise rerank.

        returns: [(id, fit_label, reasoning), ...] descending by relevance,
                 fit_label = "high" / "medium" / "low" (CoT 由来 literal label).
        """
        ...


class MockProvider:
    """Template + heuristic MockProvider (PoC、 LLM API call なし).

    DD context: query = DD 質問項目、 candidate = chunk text。
    keyword overlap で fit_label を割当、 reasoning = simple template。
    本番 (Gemini / Claude / Ollama 等) では LLM の actual reasoning に置換。
    """

    KEYWORDS_HIGH = [
        "第", "条", "Change of Control", "持分", "譲渡", "役員報酬",
        "貸付金", "私的", "代表取締役", "株主", "名義変更", "申告",
    ]

    def listwise_rerank(
        self,
        query: str,
        candidates: list[tuple[str, str]],
        top_k: int = 5,
    ) -> list[tuple[str, str, str]]:
        results: list[tuple[str, str, str]] = []
        q_lower = query.lower()
        for cid, doc in candidates[:top_k]:
            doc_lower = doc.lower()
            # 簡易 keyword overlap heuristic
            hits = sum(1 for kw in self.KEYWORDS_HIGH if kw in doc or kw.lower() in doc_lower)
            query_hits = sum(1 for w in q_lower.split() if w in doc_lower)
            score = hits + query_hits
            if score >= 3:
                label = "high"
                reasoning = f"質問の主要 keyword と chunk の literal 一致 {score} 件、 DD 着眼点 high relevance"
            elif score >= 1:
                label = "medium"
                reasoning = f"部分一致 {score} 件、 補助 chunk としての relevance medium"
            else:
                label = "low"
                reasoning = "keyword 直接一致なし、 周辺 chunk の可能性 low"
            results.append((cid, label, reasoning))
        return results


def get_provider() -> LLMProvider:
    """env LLM_PROVIDER から provider 解決 (試作 = mock default)."""
    name = os.environ.get("LLM_PROVIDER", "mock").lower()
    if name == "mock":
        return MockProvider()
    # 移植時 = gemini / claude / ollama の literal import + return
    raise ValueError(f"Unknown LLM_PROVIDER: {name}")
