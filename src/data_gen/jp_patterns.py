"""中堅日本企業 fit pattern injectors (T2 MAIS literal 競合優位 core).

PoC scope = 合成 VDR data に 3 種の中堅 pattern を意図的 inject:
  1. 同族経営 (family governance): 役員姓と社長姓一致、 同姓家族構成員株主
  2. 名義株 (nominee shareholder): 株主譲渡履歴の連続家族間移動
  3. オーナー私的経費 (owner private expense): 役員報酬 industry 中央値の 2-3 倍、 役員貸付金

参照: original proposal § T2 line 389 「中堅日本企業の財務・法務には固有のパターン (同族経営 / 名義株 /
オーナー私的経費 等) があり、 海外発の generic DD AI は補足しづらい領域」
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal

JPPatternKind = Literal["family_governance", "nominee_shareholder", "owner_private_expense"]


@dataclass
class JPPatternSeed:
    """1 案件 (DDP) に inject される中堅 fit pattern seed."""

    family_governance: bool = False # 同族経営
    nominee_shareholder: bool = False # 名義株
    owner_private_expense: bool = False # オーナー私的経費
    family_surname: str = "" # 同族経営 / 名義株時の共通姓 (Faker 由来)
    family_members: list[str] = field(default_factory=list) # 名前 list (姓は family_surname)
    nominee_chain: list[tuple[str, str, str]] = field(default_factory=list)
    # nominee_chain = [(from_name, to_name, date_iso), ...]
    owner_compensation_multiplier: float = 1.0 # industry 中央値の何倍 (≥ 2.0 で red flag)
    owner_loan_amount_jpy: int = 0 # 役員貸付金 (円、 ≥ 50M で red flag)


def industry_median_compensation_jpy(industry: str) -> int:
    """中堅日本企業 industry median 役員報酬 (年間、 単位 = 円、 おおよその合成基準)."""
    medians = {
        "出版": 18_000_000,
        "映像制作": 16_000_000,
        "広告": 22_000_000,
        "印刷": 14_000_000,
        "アパレル": 15_000_000,
        "食品製造": 17_000_000,
        "外食": 12_000_000,
        "小売": 16_000_000,
        "卸売": 18_000_000,
        "物流": 14_000_000,
        "建設": 20_000_000,
        "不動産": 25_000_000,
        "ホテル": 14_000_000,
        "観光": 13_000_000,
        "教育": 12_000_000,
        "医療": 28_000_000,
        "介護": 11_000_000,
        "農業": 9_000_000,
        "IT": 24_000_000,
        "コンサルティング": 26_000_000,
    }
    return medians.get(industry, 15_000_000)


def industry_revenue_jpy(industry: str, rng: random.Random) -> int:
    """中堅 (10-100 億円 band) revenue 合成値."""
    base = rng.randint(15, 80) # 15-80 億円
    return base * 100_000_000


def make_seed(industry: str, rng: random.Random, force: dict[str, bool] | None = None) -> JPPatternSeed:
    """1 DDP 用 fit pattern seed を生成。

    force = {"family_governance": True, ...} で literal 指定可 (試験用)。
    default = ~60% で何かしらの pattern inject、 残 40% は clean (DD 質問票で literal pass する企業)。
    """
    force = force or {}
    seed = JPPatternSeed()

    # 同族経営: 全企業の 35% で inject
    seed.family_governance = force.get("family_governance", rng.random() < 0.35)
    # 名義株: 全企業の 20% で inject (同族経営と相関)
    seed.nominee_shareholder = force.get(
        "nominee_shareholder",
        rng.random() < (0.45 if seed.family_governance else 0.10),
    )
    # オーナー私的経費: 全企業の 25% で inject
    seed.owner_private_expense = force.get("owner_private_expense", rng.random() < 0.25)

    # family_surname (同族経営 / 名義株時のみ実値、 それ以外 empty)
    if seed.family_governance or seed.nominee_shareholder:
        seed.family_surname = rng.choice(["山田", "佐藤", "鈴木", "高橋", "田中", "渡辺", "伊藤", "中村"])
        seed.family_members = [
            f"{seed.family_surname} {given}"
            for given in rng.sample(
                ["太郎", "次郎", "三郎", "花子", "美咲", "健一", "明", "誠", "幸子", "和子"],
                k=rng.randint(3, 5),
            )
        ]

    # nominee_chain (名義株 inject 時のみ)
    if seed.nominee_shareholder and len(seed.family_members) >= 2:
        chain_len = rng.randint(2, 3)
        for _ in range(chain_len):
            frm, to = rng.sample(seed.family_members, 2)
            year = rng.randint(2008, 2024)
            seed.nominee_chain.append((frm, to, f"{year}-{rng.randint(1, 12):02d}-15"))

    # 役員報酬 multiplier (private_expense inject 時 = 2-3 倍、 それ以外 0.8-1.4 normal)
    if seed.owner_private_expense:
        seed.owner_compensation_multiplier = round(rng.uniform(2.0, 3.2), 2)
        seed.owner_loan_amount_jpy = rng.randint(50, 200) * 1_000_000 # 5000万-2億円
    else:
        seed.owner_compensation_multiplier = round(rng.uniform(0.8, 1.4), 2)
        seed.owner_loan_amount_jpy = 0

    return seed


def describe_patterns(seed: JPPatternSeed) -> list[str]:
    """seed から literal 検出可能な pattern 文字列 (test / docs 用)."""
    out: list[str] = []
    if seed.family_governance:
        out.append(f"family_governance ({seed.family_surname}家、 family_members={len(seed.family_members)})")
    if seed.nominee_shareholder:
        out.append(f"nominee_shareholder (chain={len(seed.nominee_chain)} 件)")
    if seed.owner_private_expense:
        out.append(
            f"owner_private_expense (compensation_x{seed.owner_compensation_multiplier},"
            f" loan_¥{seed.owner_loan_amount_jpy:,})"
        )
    return out
