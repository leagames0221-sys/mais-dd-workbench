"""Unit tests for src.data_gen."""
from __future__ import annotations

import random

import pytest

from src.data_gen.jp_patterns import (
    JPPatternSeed,
    industry_median_compensation_jpy,
    industry_revenue_jpy,
    make_seed,
    describe_patterns,
)


def test_industry_median_known_value() -> None:
    """既知 industry の median 値が定数通り (regression test)."""
    assert industry_median_compensation_jpy("出版") == 18_000_000
    assert industry_median_compensation_jpy("IT") == 24_000_000
    assert industry_median_compensation_jpy("医療") == 28_000_000


def test_industry_median_unknown_fallback() -> None:
    """未知 industry は 15M fallback (doctrine: waste-zero + KeyError 回避)."""
    assert industry_median_compensation_jpy("未知業界") == 15_000_000


def test_industry_revenue_within_band() -> None:
    """revenue は 15-80 億円 中堅 band 内."""
    rng = random.Random(42)
    revenue = industry_revenue_jpy("出版", rng)
    assert 15 * 100_000_000 <= revenue <= 80 * 100_000_000


def test_make_seed_force_family_governance() -> None:
    """force=family_governance で literal pattern inject + family_surname 非空 + members ≥ 3."""
    rng = random.Random(42)
    seed = make_seed("出版", rng, force={"family_governance": True})
    assert seed.family_governance is True
    assert seed.family_surname # 非空
    assert len(seed.family_members) >= 3
    # members 名 = "{surname} {given}" 形式
    for m in seed.family_members:
        assert m.startswith(seed.family_surname + " ")


def test_make_seed_force_owner_private_expense() -> None:
    """force=owner_private_expense で multiplier ≥ 2.0 + loan ≥ 50M."""
    rng = random.Random(42)
    seed = make_seed("出版", rng, force={"owner_private_expense": True})
    assert seed.owner_private_expense is True
    assert seed.owner_compensation_multiplier >= 2.0
    assert seed.owner_loan_amount_jpy >= 50_000_000


def test_make_seed_reproducibility() -> None:
    """同 seed で同 output (reproducibility test)."""
    rng1 = random.Random(20260512)
    rng2 = random.Random(20260512)
    seed1 = make_seed("IT", rng1)
    seed2 = make_seed("IT", rng2)
    assert seed1.family_governance == seed2.family_governance
    assert seed1.nominee_shareholder == seed2.nominee_shareholder
    assert seed1.owner_private_expense == seed2.owner_private_expense
    assert seed1.family_surname == seed2.family_surname
    assert seed1.owner_compensation_multiplier == seed2.owner_compensation_multiplier


def test_nominee_chain_only_when_inject() -> None:
    """nominee_shareholder False 時は nominee_chain literal empty."""
    rng = random.Random(42)
    seed = make_seed(
        "IT", rng,
        force={"nominee_shareholder": False, "family_governance": False},
    )
    assert seed.nominee_shareholder is False
    assert seed.nominee_chain == []


def test_describe_patterns_empty_for_clean_seed() -> None:
    """全 pattern OFF の seed は describe = empty list."""
    seed = JPPatternSeed()
    assert describe_patterns(seed) == []


def test_describe_patterns_lists_all_active() -> None:
    """active pattern 全件 describe される."""
    rng = random.Random(42)
    seed = make_seed(
        "IT", rng,
        force={
            "family_governance": True,
            "nominee_shareholder": True,
            "owner_private_expense": True,
        },
    )
    desc = describe_patterns(seed)
    assert any("family_governance" in d for d in desc)
    assert any("nominee_shareholder" in d for d in desc)
    assert any("owner_private_expense" in d for d in desc)


@pytest.mark.slow
def test_generate_all_for_ddp_smoke(tmp_path) -> None:
    """generate_all_for_ddp で 8 docs literal 生成 (slow tag、 reportlab + 4 libs 実行)."""
    from src.data_gen.generate_synthetic_vdr import generate_all_for_ddp, make_ddp
    from faker import Faker

    rng = random.Random(20260512)
    faker = Faker("ja_JP")
    Faker.seed(20260512)
    ddp = make_ddp(0, rng, faker)
    n = generate_all_for_ddp(ddp, tmp_path, rng)

    # 8 docs (PDF 2 + DOCX 2 + XLSX 2 + PPTX 2) literal 生成
    assert n == 8

    # 各 kind dir に 2 件
    ddp_dir = tmp_path / ddp.ddp_id
    for kind in ["pdf", "docx", "xlsx", "pptx"]:
        files = list((ddp_dir / kind).glob(f"*.{kind}"))
        assert len(files) == 2, f"{kind} = {len(files)} (expected 2)"
        # 各 file が non-empty (≥ 500 bytes、 最小 sample で literal 確実)
        for f in files:
            assert f.stat().st_size >= 500, f"{f} size = {f.stat().st_size} (expected ≥ 500)"
