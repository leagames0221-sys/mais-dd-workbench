"""Unit tests for src.clause + src.jp_patterns."""
from __future__ import annotations

from src.clause.extract_clauses import detect_clauses, hits_by_kind, ClauseHit
from src.jp_patterns.detect import (
    detect_family_governance,
    detect_nominee_shareholder,
    detect_owner_private_expense,
    detect_all,
)


# ===== clause detector unit tests =====


def _chunk(cid: str, text: str, doc_id: str = "DOC-test", ddp_id: str = "DDP-test") -> dict:
    return {
        "chunk_id": cid,
        "doc_id": doc_id,
        "ddp_id": ddp_id,
        "text_redacted": text,
    }


def test_clause_change_of_control_ascii() -> None:
    """ASCII 'Change of Control' literal 検出 + confidence ≥ 0.85."""
    chunks = [_chunk("CHK-1", "本契約は Change of Control 条項に従う。")]
    hits = detect_clauses(chunks)
    assert any(h.kind == "change_of_control" for h in hits)
    h = next(h for h in hits if h.kind == "change_of_control")
    assert h.confidence >= 0.85


def test_clause_change_of_control_japanese() -> None:
    """日本語 '経営権異動' literal 検出 + confidence ≥ 0.70."""
    chunks = [_chunk("CHK-1", "発行済株式総数の 50% を超える持分異動が生じた場合")]
    hits = detect_clauses(chunks)
    assert any(h.kind == "change_of_control" for h in hits)


def test_clause_indemnification() -> None:
    """補償義務 / Indemnification literal 検出."""
    chunks = [_chunk("CHK-1", "本契約に基づく Indemnification 条項を適用する。")]
    hits = detect_clauses(chunks)
    assert any(h.kind == "indemnification" for h in hits)


def test_clause_no_false_positive_on_clean_text() -> None:
    """clause keyword 含まない text で 0 hit (false-positive 抑制)."""
    chunks = [_chunk("CHK-1", "本日の天気は晴れです。 売上は好調でした。")]
    hits = detect_clauses(chunks)
    assert hits == []


def test_hits_by_kind_groupby() -> None:
    """ClauseHit list を kind で groupby."""
    h1 = ClauseHit("CHK-1", "DOC-1", "change_of_control", "Change of Control", 0.85)
    h2 = ClauseHit("CHK-2", "DOC-1", "change_of_control", "経営権異動", 0.70)
    h3 = ClauseHit("CHK-3", "DOC-2", "indemnification", "Indemnification", 0.85)
    grouped = hits_by_kind([h1, h2, h3])
    assert len(grouped["change_of_control"]) == 2
    assert len(grouped["indemnification"]) == 1


# ===== jp_patterns detector unit tests =====


def test_jp_family_governance_surname_concentration() -> None:
    """同姓 token 高比率 + 明示 signal で family_governance detect."""
    chunks = [
        _chunk("CHK-1", "創業者家族 山田家 合計持分: 75.5%"),
        _chunk("CHK-2", "出席役員: 山田 太郎、 山田 次郎、 山田 花子、 山田 健一"),
        _chunk("CHK-3", "代表取締役 山田 太郎 より来期計画の説明あり。 全員一致で承認。"),
    ]
    hit = detect_family_governance("DDP-test", chunks)
    assert hit is not None
    assert hit.kind == "family_governance"
    assert hit.confidence >= 0.5


def test_jp_family_governance_no_concentration() -> None:
    """姓 分散 + 明示 signal なし = None (false-positive 抑制)."""
    chunks = [
        _chunk("CHK-1", "出席役員: 田中 太郎、 鈴木 花子、 佐藤 健一、 高橋 誠"),
        _chunk("CHK-2", "本日の議題は来期の事業計画について討議した。"),
    ]
    hit = detect_family_governance("DDP-test", chunks)
    assert hit is None


def test_jp_nominee_shareholder_surname_chain() -> None:
    """同姓間 → 譲渡 chain で nominee_shareholder detect."""
    chunks = [
        _chunk("CHK-1", "名義変更履歴"),
        _chunk("CHK-2", "株主 山田 太郎 → 山田 次郎 に名義変更 (家族間譲渡)"),
        _chunk("CHK-3", "株主 山田 次郎 → 山田 花子 に名義変更"),
    ]
    hit = detect_nominee_shareholder("DDP-test", chunks)
    assert hit is not None
    assert hit.kind == "nominee_shareholder"



def test_jp_owner_private_expense_multiplier() -> None:
    """multiplier ≥ 2.0 + 役員貸付金 phrase で detect."""
    chunks = [
        _chunk("CHK-1", "役員報酬は業界中央値 の 2.5 倍"),
        _chunk("CHK-2", "役員貸付金 残高 1 億 5 千万円"),
    ]
    hit = detect_owner_private_expense("DDP-test", chunks)
    assert hit is not None
    assert hit.kind == "owner_private_expense"
    assert hit.confidence >= 0.7 # multiplier ≥ 2.0 で +0.15 boost


def test_jp_detect_all_multi_pattern() -> None:
    """同 DDP 内に 3 pattern 全 inject、 detect_all で全件 hit."""
    chunks = [
        # family_governance
        _chunk("CHK-1", "創業者家族 山田家"),
        _chunk("CHK-2", "山田 太郎、 山田 次郎、 山田 花子、 山田 健一、 山田 明"),
        _chunk("CHK-3", "全員一致で承認"),
        # nominee_shareholder
        _chunk("CHK-4", "株主 山田 太郎 → 山田 次郎 に名義変更"),
        _chunk("CHK-5", "家族間譲渡 (山田家内)"),
        # owner_private_expense
        _chunk("CHK-6", "役員報酬は業界中央値 の 2.8 倍"),
        _chunk("CHK-7", "役員貸付金 1 億 円"),
    ]
    hits = detect_all("DDP-test", chunks)
    kinds = {h.kind for h in hits}
    assert "family_governance" in kinds
    assert "nominee_shareholder" in kinds
    assert "owner_private_expense" in kinds


def test_jp_detect_all_clean_company() -> None:
    """clean 企業 (pattern なし) で detect_all は empty list を return."""
    chunks = [
        _chunk("CHK-1", "本日の取締役会では新規市場参入の議論を実施した。"),
        _chunk("CHK-2", "各取締役より sensitivity 分析の依頼があり、 修正提案を反映。"),
        _chunk("CHK-3", "業界中央値 の 1.0 倍 の役員報酬を維持する方針。"),
    ]
    hits = detect_all("DDP-test", chunks)
    assert hits == []
