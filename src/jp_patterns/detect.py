"""中堅日本企業 fit pattern detector (T2 MAIS literal 競合優位 core、 ADR-104 SSoT 実装)。

3 種 detector (chunk text + structured signal hybrid):
  1. family_governance: 同姓役員 + 同姓株主 高比率 + 取締役会議事録の議論欠如表現
  2. nominee_shareholder: 株主名簿の連続家族間譲渡履歴 + 同姓間譲渡
  3. owner_private_expense: 役員報酬の業界中央値超過記述 + 役員貸付金 + 私的経費異常値

regex (高速 first pass) + structured field 解析 + (移植時) LLM 確信度判定。
"""
from __future__ import annotations

import re
import secrets
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Iterable, Literal

JPPatternKind = Literal["family_governance", "nominee_shareholder", "owner_private_expense"]


@dataclass
class JPPatternHit:
    """1 DDP に対する中堅 fit pattern 検出結果."""

    jpp_id: str
    ddp_id: str
    kind: JPPatternKind
    evidence_chunk_ids: list[str]
    evidence_phrases: list[str]
    confidence: float  # [0.0, 1.0]
    notes: str


# 同族経営 phrase patterns (議事録 / 規程 / マニュアル 内)
_FG_PHRASES = [
    re.compile(r"創業者家族"),
    re.compile(r"同族(?:支配|経営)"),
    re.compile(r"\w{1,3}家\s*(?:合計)?持分"),
    re.compile(r"(?:全員|満場)一致(?:で)?承認"),
    re.compile(r"\(\s*議論記録\s*なし\s*\)"),
]
# 名義変更 phrase patterns (literal 譲渡記述を broad に catch)
_NS_PHRASES = [
    re.compile(r"名義変更履歴"),
    re.compile(r"家族間譲渡"),
    # 「→」 を含む譲渡記述 (例: 「株主 山田 太郎 → 山田 次郎 に名義変更」 / 「山田 太郎 → 次郎」)
    re.compile(r"[一-龯]+\s+\S+\s*→\s*[一-龯]"),
    # literal 「に名義変更」 直前に 「→」 含む chunk
    re.compile(r"→\s*\S+\s+\S+\s*に名義変更"),
]
# 役員報酬 / 私的経費 phrase patterns
_PE_PHRASES = [
    re.compile(r"業界中央値\s*の\s*[\d\.]+\s*倍"),
    re.compile(r"役員貸付金"),
    re.compile(r"役員報酬(?:が)?(?:業界)?中央値"),
    re.compile(r"私的経費"),
    re.compile(r"オーナー(?:私的)?(?:経費|支出)"),
]

# 同姓 token 検出用 (日本姓 1-3 char + space + given)
_NAME_RE = re.compile(r"([一-龯]{1,3})\s+[一-龯]{1,3}")


def _surname_distribution(text: str) -> Counter[str]:
    """text 内の 「姓 名」 形式から 姓 token を抽出、 Counter で frequency 計上."""
    surnames = _NAME_RE.findall(text)
    return Counter(surnames)


def detect_family_governance(
    ddp_id: str, chunks: list[dict]
) -> JPPatternHit | None:
    """family_governance 検出 (chunk 集合 = 1 DDP 全 docs)."""
    evidence_cids: list[str] = []
    evidence_phrases: list[str] = []
    surname_counter: Counter[str] = Counter()
    explicit_signal_count = 0

    for chunk in chunks:
        text = chunk["text_redacted"]
        cid = chunk["chunk_id"]
        # phrase 検出
        for pat in _FG_PHRASES:
            m = pat.search(text)
            if m:
                evidence_cids.append(cid)
                evidence_phrases.append(m.group(0))
                explicit_signal_count += 1
                break
        # 姓 distribution 集計
        for surname, freq in _surname_distribution(text).items():
            surname_counter[surname] += freq

    if not surname_counter:
        return None

    # most common surname が 全 姓 frequency の 40% 超 = 同姓集中 signal
    most_common_surname, most_common_count = surname_counter.most_common(1)[0]
    total = sum(surname_counter.values())
    surname_ratio = most_common_count / total

    if surname_ratio >= 0.40 or explicit_signal_count >= 2:
        confidence = min(0.95, 0.5 + surname_ratio + 0.1 * explicit_signal_count)
        return JPPatternHit(
            jpp_id=f"JPP-{secrets.token_urlsafe(8)}",
            ddp_id=ddp_id,
            kind="family_governance",
            evidence_chunk_ids=list(dict.fromkeys(evidence_cids))[:10],
            evidence_phrases=list(dict.fromkeys(evidence_phrases))[:5],
            confidence=round(min(confidence, 0.99), 3),
            notes=(
                f"同姓 '{most_common_surname}' = {most_common_count}/{total}"
                f" ({surname_ratio:.1%}) + 明示 signal {explicit_signal_count} 件"
            ),
        )
    return None


def detect_nominee_shareholder(
    ddp_id: str, chunks: list[dict]
) -> JPPatternHit | None:
    """nominee_shareholder 検出 (株主名簿名義変更履歴 + 同姓間譲渡)."""
    evidence_cids: list[str] = []
    evidence_phrases: list[str] = []
    surname_chain_hits = 0

    for chunk in chunks:
        text = chunk["text_redacted"]
        cid = chunk["chunk_id"]
        for pat in _NS_PHRASES:
            m = pat.search(text)
            if m:
                evidence_cids.append(cid)
                evidence_phrases.append(m.group(0))
                # 同姓間譲渡判定: 「→」 直前 last token を 姓 として extract、
                # greedy 回避のため finditer で last match を採用 (例: 「株主 山田 太郎 → 山田 次郎」)
                all_arrows = list(
                    re.finditer(
                        r"([一-龯]{1,3})\s+[一-龯]+\s*→\s*([一-龯]{1,3})\s+",
                        text,
                    )
                )
                if all_arrows:
                    last = all_arrows[-1]
                    if last.group(1) == last.group(2):
                        surname_chain_hits += 1
                break

    if surname_chain_hits >= 1 or len(evidence_cids) >= 2:
        confidence = 0.6 + 0.1 * surname_chain_hits + 0.05 * len(evidence_cids)
        return JPPatternHit(
            jpp_id=f"JPP-{secrets.token_urlsafe(8)}",
            ddp_id=ddp_id,
            kind="nominee_shareholder",
            evidence_chunk_ids=list(dict.fromkeys(evidence_cids))[:10],
            evidence_phrases=list(dict.fromkeys(evidence_phrases))[:5],
            confidence=round(min(confidence, 0.99), 3),
            notes=f"同姓間譲渡 chain {surname_chain_hits} 件 + 名義変更記述 {len(evidence_cids)} chunk",
        )
    return None


def detect_owner_private_expense(
    ddp_id: str, chunks: list[dict]
) -> JPPatternHit | None:
    """owner_private_expense 検出 (役員報酬異常値 + 役員貸付金 + 私的経費)."""
    evidence_cids: list[str] = []
    evidence_phrases: list[str] = []
    multiplier_hits: list[float] = []

    for chunk in chunks:
        text = chunk["text_redacted"]
        cid = chunk["chunk_id"]
        for pat in _PE_PHRASES:
            m = pat.search(text)
            if m:
                evidence_cids.append(cid)
                evidence_phrases.append(m.group(0))
                break
        # multiplier の literal 数字抽出 (例 "業界中央値 の 2.5 倍")
        mult_match = re.search(r"業界中央値\s*の\s*([\d\.]+)\s*倍", text)
        if mult_match:
            try:
                multiplier_hits.append(float(mult_match.group(1)))
            except ValueError:
                pass

    if len(evidence_cids) >= 2 or any(m >= 2.0 for m in multiplier_hits):
        confidence = 0.55 + 0.08 * len(evidence_cids)
        if multiplier_hits and max(multiplier_hits) >= 2.0:
            confidence += 0.15
        return JPPatternHit(
            jpp_id=f"JPP-{secrets.token_urlsafe(8)}",
            ddp_id=ddp_id,
            kind="owner_private_expense",
            evidence_chunk_ids=list(dict.fromkeys(evidence_cids))[:10],
            evidence_phrases=list(dict.fromkeys(evidence_phrases))[:5],
            confidence=round(min(confidence, 0.99), 3),
            notes=(
                f"phrase hit {len(evidence_cids)} chunk"
                + (f", 役員報酬 multiplier max={max(multiplier_hits):.2f}" if multiplier_hits else "")
            ),
        )
    return None


def detect_all(ddp_id: str, chunks: Iterable[dict]) -> list[JPPatternHit]:
    """1 DDP の全 chunks に対し 3 detector を literal 走らせる."""
    chunk_list = list(chunks)
    hits: list[JPPatternHit] = []
    for detector in (
        detect_family_governance,
        detect_nominee_shareholder,
        detect_owner_private_expense,
    ):
        hit = detector(ddp_id, chunk_list)
        if hit:
            hits.append(hit)
    return hits
