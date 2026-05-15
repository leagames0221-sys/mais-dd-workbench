"""Stage 5: LLM listwise rerank with DD CoT prompt (T1 ADR-005 + DD context 調整)。

MDPI 2024 paper の structured prompting pattern を DD 文書 QA に適用。
real LLM 投入時用 prompt template、 mock は heuristic で短絡 (LLM API call ZERO)。
"""
from __future__ import annotations

from src.pipeline.llm_provider import LLMProvider, get_provider


MAIS_DD_COT_PROMPT_TEMPLATE = """以下は M&A デューデリジェンス (DD) の質問項目です。 質問 (query) に対し source 文書 chunks (candidates) の relevance を Chain-of-Thought で評価し、 listwise rerank してください。

[DD 質問]
{query}

[source chunks]
{candidates_block}

各 chunk について:
1. 質問が問う axis (財務 / 法務 / 事業 / 中堅 fit pattern) を identify (CoT)
2. chunk が answer 含むか / source 根拠として使えるか literal 評価
3. fit_label を high / medium / low で判定
4. 1-2 文の reasoning を日本語で記述 (中堅日本企業固有 pattern 検出時は具体明示)

最後に top_k = {top_k} を relevance 降順で返してください。"""


def listwise_rerank(
    query: str,
    candidates: list[tuple[str, str]],
    top_k: int = 5,
    provider: LLMProvider | None = None,
) -> list[tuple[str, str, str]]:
    """Stage 5 LLM listwise rerank entry point (PoC = MockProvider、 移植時 real LLM swap)."""
    if provider is None:
        provider = get_provider()
    return provider.listwise_rerank(query, candidates, top_k=top_k)


def build_cot_prompt(query: str, candidates: list[tuple[str, str]], top_k: int = 5) -> str:
    """real LLM 投入時の MDPI CoT prompt 構築 (mock は internal heuristic で短絡)."""
    block = "\n".join(
        f"  {i+1}. [{cid}] {doc[:300]}..." for i, (cid, doc) in enumerate(candidates)
    )
    return MAIS_DD_COT_PROMPT_TEMPLATE.format(query=query, candidates_block=block, top_k=top_k)
