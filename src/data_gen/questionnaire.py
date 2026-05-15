"""DD 質問票テンプレート 300 項目 generator (T2 Week 2、 original proposal § T2 line 372 = 「数百項目」)。

財務 100 + 法務 100 + 事業 100 = 計 300 項目、 industry 別 variation の場 sample 生成。
output: data/questionnaire/questions.jsonl (各 line = {q_id, category, question_text, expected_evidence_kind})

source: CUAD/ACORD 41 cat + M&A PMI 過去案件 reference (parent proposal § T2 inherit)。
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()

OUTPUT_PATH = Path(os.environ.get("QUESTIONNAIRE_PATH", "./data/questionnaire/questions.jsonl"))


# ===== 財務 100 項目 (P&L / BS / CF / 税務 / 私的経費 / 関連会社取引) =====

FINANCIAL_TEMPLATES: list[tuple[str, str]] = [
    # P&L 項目 (25)
    ("financial", "売上高の年次推移 (過去 5 年) を提示してください"),
    ("financial", "売上原価率の業界比較と異常値の有無を説明してください"),
    ("financial", "粗利率の年次推移と低下要因を説明してください"),
    ("financial", "販管費の主要内訳と前年比増減理由を説明してください"),
    ("financial", "役員報酬の総額と業界中央値との乖離を説明してください"),
    ("financial", "営業利益率の年次推移を提示してください"),
    ("financial", "経常利益と営業利益の乖離要因を説明してください"),
    ("financial", "税引前利益から純利益への調整項目を説明してください"),
    ("financial", "EBITDA の算定根拠と一過性項目を説明してください"),
    ("financial", "減価償却費の方法 (定額 / 定率) と耐用年数を説明してください"),
    ("financial", "売上計上基準 (出荷 / 検収 / 進行) を説明してください"),
    ("financial", "売掛金回収サイトの平均日数を提示してください"),
    ("financial", "貸倒引当金の算定根拠を説明してください"),
    ("financial", "棚卸資産の評価方法と滞留在庫の有無を説明してください"),
    ("financial", "買掛金支払サイトの平均日数を提示してください"),
    ("financial", "為替差損益の発生状況を説明してください"),
    ("financial", "受取利息 / 支払利息の年次推移を提示してください"),
    ("financial", "投資有価証券の含み損益を説明してください"),
    ("financial", "持分法投資損益の発生状況を説明してください"),
    ("financial", "特別損益の主要内訳を説明してください"),
    ("financial", "法人税等調整額の発生原因を説明してください"),
    ("financial", "繰延税金資産 / 負債の内訳を説明してください"),
    ("financial", "1 株あたり当期純利益 (EPS) の年次推移を提示してください"),
    ("financial", "配当性向の方針と過去配当履歴を説明してください"),
    ("financial", "自己資本利益率 (ROE) の年次推移を提示してください"),
    # BS 項目 (25)
    ("financial", "現金及び預金の月末残高推移を提示してください"),
    ("financial", "売掛金の主要相手先と金額を説明してください"),
    ("financial", "棚卸資産の主要品目と数量を提示してください"),
    ("financial", "有形固定資産の主要内訳 (建物 / 機械 / 土地) を説明してください"),
    ("financial", "無形固定資産 (のれん / ソフトウェア) の内訳を説明してください"),
    ("financial", "投資不動産の所在地と評価額を説明してください"),
    ("financial", "敷金保証金の差入先と金額を説明してください"),
    ("financial", "買掛金の主要相手先と金額を説明してください"),
    ("financial", "未払金 / 未払費用の主要内訳を説明してください"),
    ("financial", "短期借入金の借入先と利率を説明してください"),
    ("financial", "長期借入金の借入先 / 利率 / 返済期日を説明してください"),
    ("financial", "社債の発行条件 (利率 / 償還期日 / 担保) を説明してください"),
    ("financial", "リース債務の主要対象と残期間を説明してください"),
    ("financial", "退職給付債務の算定根拠を説明してください"),
    ("financial", "資産除去債務の対象資産を説明してください"),
    ("financial", "繰延税金負債の発生原因を説明してください"),
    ("financial", "資本金 / 資本剰余金の異動履歴を説明してください"),
    ("financial", "利益剰余金の異動 (配当 / 自己株式取得) を説明してください"),
    ("financial", "自己株式の取得状況と保有目的を説明してください"),
    ("financial", "その他有価証券評価差額金の内訳を説明してください"),
    ("financial", "役員貸付金の有無 / 金額 / 利率を説明してください"),
    ("financial", "役員借入金の有無 / 金額 / 利率を説明してください"),
    ("financial", "関連当事者取引の一覧を提示してください"),
    ("financial", "オフバランス取引 (保証 / リース) の有無を説明してください"),
    ("financial", "簿外債務の有無を確認してください"),
    # CF / 税務 / 関連会社 (25)
    ("financial", "営業 CF と当期純利益の乖離要因を説明してください"),
    ("financial", "投資 CF の主要内訳 (設備投資 / 売却) を説明してください"),
    ("financial", "財務 CF の主要内訳 (借入 / 返済 / 配当) を説明してください"),
    ("financial", "フリーキャッシュフローの年次推移を提示してください"),
    ("financial", "現金及び現金同等物の月次推移を提示してください"),
    ("financial", "運転資本 (CCC) の年次推移を提示してください"),
    ("financial", "法人税 / 住民税 / 事業税の確定申告書を提示してください"),
    ("financial", "過去 5 年の税務調査履歴と指摘事項を説明してください"),
    ("financial", "繰越欠損金の残高と期限を説明してください"),
    ("financial", "消費税の課税方式 (本則 / 簡易) を説明してください"),
    ("financial", "源泉所得税の納付状況を確認してください"),
    ("financial", "印紙税の納付漏れの有無を確認してください"),
    ("financial", "移転価格税制への対応状況を説明してください"),
    ("financial", "タックスヘイブン対策税制への該当の有無を説明してください"),
    ("financial", "関連会社との取引価格の妥当性を説明してください"),
    ("financial", "親会社からの資金調達状況を説明してください"),
    ("financial", "子会社への貸付金の有無 / 金額を説明してください"),
    ("financial", "関連会社株式の評価方法を説明してください"),
    ("financial", "連結対象会社の範囲を説明してください"),
    ("financial", "持分法適用会社の範囲を説明してください"),
    ("financial", "海外子会社の所在地 / 業種 / 業績を提示してください"),
    ("financial", "外貨建取引の換算方法を説明してください"),
    ("financial", "デリバティブ取引の利用状況を説明してください"),
    ("financial", "ヘッジ会計の適用範囲を説明してください"),
    ("financial", "セグメント別業績の開示状況を説明してください"),
    # 私的経費 / オーナー関連 (25)
    ("financial", "役員報酬の決定プロセスを説明してください"),
    ("financial", "役員退職慰労金の引当状況を説明してください"),
    ("financial", "役員社宅の賃料水準と税務上の取扱いを説明してください"),
    ("financial", "役員専用車両の有無と使用実態を説明してください"),
    ("financial", "役員旅費交通費の水準と業務関連性を説明してください"),
    ("financial", "役員接待交際費の水準と相手先を説明してください"),
    ("financial", "オーナー個人への福利厚生費の有無を説明してください"),
    ("financial", "オーナー名義の資産の会社利用の有無を説明してください"),
    ("financial", "オーナー個人保証の融資先と金額を提示してください"),
    ("financial", "創業家関連会社との取引一覧を提示してください"),
    ("financial", "創業家保有不動産の賃借状況を説明してください"),
    ("financial", "創業家への支払 (役員報酬以外) の有無を説明してください"),
    ("financial", "創業家の資金貸付 / 借入の有無を説明してください"),
    ("financial", "創業家保有株式の評価額を説明してください"),
    ("financial", "創業家個人事業との関連性を説明してください"),
    ("financial", "創業家関連の経費精算ルールを説明してください"),
    ("financial", "役員社用クレジットカードの利用ルールを説明してください"),
    ("financial", "役員出張規程の整備状況を説明してください"),
    ("financial", "役員配偶者 / 親族の従業員雇用状況を説明してください"),
    ("financial", "役員配偶者 / 親族への業務委託の有無を説明してください"),
    ("financial", "創業家保有株式の譲渡履歴を提示してください"),
    ("financial", "創業家からの資金援助 / 補助の有無を説明してください"),
    ("financial", "創業家への保証提供の有無を確認してください"),
    ("financial", "創業家関連の私的支出が経費計上されていないか確認してください"),
    ("financial", "創業家関連の不動産取引価格の妥当性を説明してください"),
]


# ===== 法務 100 項目 =====

LEGAL_TEMPLATES: list[tuple[str, str]] = [
    # 会社組織 / 株式 (20)
    ("legal", "定款の最新版を提示してください"),
    ("legal", "登記簿謄本 (履歴事項全部証明書) を提示してください"),
    ("legal", "株主名簿の最新版を提示してください"),
    ("legal", "発行可能株式総数と発行済株式総数を説明してください"),
    ("legal", "株式の種類 (普通株 / 種類株) を説明してください"),
    ("legal", "株式譲渡制限の有無と承認機関を説明してください"),
    ("legal", "過去 10 年の株主名義変更履歴を提示してください"),
    ("legal", "名義株 (実質所有者と名義人の乖離) の有無を確認してください"),
    ("legal", "自己株式の保有状況と取得経緯を説明してください"),
    ("legal", "新株予約権 / ストックオプションの発行状況を説明してください"),
    ("legal", "株主間契約の有無と内容を説明してください"),
    ("legal", "創業者株主の持分比率と議決権を説明してください"),
    ("legal", "創業者家族の保有株式合計を提示してください"),
    ("legal", "外部株主 (VC / PE / 個人) の持分比率を説明してください"),
    ("legal", "取締役会 / 監査役会の構成を説明してください"),
    ("legal", "取締役の任期と再任手続きを説明してください"),
    ("legal", "代表取締役の専決事項と取締役会決議事項を区別してください"),
    ("legal", "過去 5 年の取締役会議事録を提示してください"),
    ("legal", "過去 5 年の株主総会議事録を提示してください"),
    ("legal", "監査法人 / 会計監査人の変更履歴を説明してください"),
    # 主要契約 (30)
    ("legal", "主要取引先との基本契約書を提示してください"),
    ("legal", "主要取引先との Change of Control 条項の有無を確認してください"),
    ("legal", "主要取引先契約の解約条項を説明してください"),
    ("legal", "主要取引先との独占的取引条項の有無を確認してください"),
    ("legal", "主要金融機関との融資契約書を提示してください"),
    ("legal", "融資契約の財務制限条項 (コベナンツ) を説明してください"),
    ("legal", "融資契約の Change of Control 条項を確認してください"),
    ("legal", "金融機関への担保提供状況を説明してください"),
    ("legal", "個人保証の有無と保証人を説明してください"),
    ("legal", "保証協会保証の利用状況を説明してください"),
    ("legal", "リース契約の主要対象と残期間を説明してください"),
    ("legal", "リース契約の Change of Control 条項を確認してください"),
    ("legal", "不動産賃貸借契約の主要内容を説明してください"),
    ("legal", "賃貸借契約の解約条項と更新条件を説明してください"),
    ("legal", "代理店契約 / 販売店契約の主要内容を説明してください"),
    ("legal", "代理店契約の独占権 / 非独占の区分を説明してください"),
    ("legal", "ライセンス契約 (供与 / 受領) を一覧化してください"),
    ("legal", "ライセンス契約の Change of Control 条項を確認してください"),
    ("legal", "業務委託契約の主要相手先を提示してください"),
    ("legal", "業務委託契約の競業避止条項を確認してください"),
    ("legal", "保守契約の主要対象と期間を説明してください"),
    ("legal", "保険契約 (損害 / PL / D&O) を一覧化してください"),
    ("legal", "Most Favored Nation (MFN) 条項の有無を確認してください"),
    ("legal", "Limitation of Liability 条項の上限額を説明してください"),
    ("legal", "Indemnification 条項の対象範囲を説明してください"),
    ("legal", "Non-Compete / Non-Solicitation 条項の有効期間を説明してください"),
    ("legal", "Termination for Convenience 条項の有無を確認してください"),
    ("legal", "Governing Law / Jurisdiction を確認してください"),
    ("legal", "仲裁条項の有無と仲裁地を説明してください"),
    ("legal", "国際取引契約の準拠法を説明してください"),
    # 知財 / 訴訟 / 規制 (30)
    ("legal", "特許権の出願状況と保有件数を説明してください"),
    ("legal", "特許権の Change of Control 通知義務を確認してください"),
    ("legal", "商標権の保有状況を説明してください"),
    ("legal", "意匠権の保有状況を説明してください"),
    ("legal", "著作権の管理状況を説明してください"),
    ("legal", "営業秘密の管理規程を提示してください"),
    ("legal", "技術ライセンス受領の現況と Change of Control 影響を説明してください"),
    ("legal", "知財帰属 (会社 / 個人) の整理状況を説明してください"),
    ("legal", "係属中の訴訟一覧と請求額を提示してください"),
    ("legal", "過去 5 年の判決 / 和解履歴を提示してください"),
    ("legal", "労働紛争の有無と内容を説明してください"),
    ("legal", "公正取引委員会からの指導 / 処分の有無を説明してください"),
    ("legal", "消費者庁 / 関連省庁からの行政処分の有無を説明してください"),
    ("legal", "個人情報保護法上の漏洩事案の有無を説明してください"),
    ("legal", "個人情報保護委員会からの指導の有無を確認してください"),
    ("legal", "GDPR 対応状況を説明してください"),
    ("legal", "金融商品取引法上の規制対応を説明してください"),
    ("legal", "業界規制 (許認可) の取得状況を説明してください"),
    ("legal", "許認可の Change of Control 影響を説明してください"),
    ("legal", "輸出規制 (安全保障輸出管理) への対応を説明してください"),
    ("legal", "下請法遵守状況を説明してください"),
    ("legal", "労働基準法遵守状況を説明してください"),
    ("legal", "労働時間管理 / 36 協定の整備状況を説明してください"),
    ("legal", "ハラスメント防止規程の整備状況を説明してください"),
    ("legal", "コンプライアンス通報窓口の整備状況を説明してください"),
    ("legal", "反社会的勢力との関係遮断状況を説明してください"),
    ("legal", "AML / KYC 体制を説明してください"),
    ("legal", "贈収賄禁止規程の整備状況を説明してください"),
    ("legal", "競争法 (独禁法) 遵守体制を説明してください"),
    ("legal", "ESG / SDGs 対応方針を説明してください"),
    # 紛争 / 株主間 (20)
    ("legal", "過去 5 年の株主総会 / 取締役会の決議無効訴訟の有無を確認してください"),
    ("legal", "株主代表訴訟の有無を確認してください"),
    ("legal", "少数株主との紛争の有無を説明してください"),
    ("legal", "少数株主の買取請求の発生可能性を説明してください"),
    ("legal", "種類株主間契約の Change of Control 条項を説明してください"),
    ("legal", "ストックオプション保有者との合意の有無を説明してください"),
    ("legal", "従業員持株会の規約と Change of Control 影響を説明してください"),
    ("legal", "従業員持株会の保有比率を説明してください"),
    ("legal", "取引先からの差止請求 / 損害賠償請求の有無を確認してください"),
    ("legal", "金融機関からの期限の利益喪失通告の有無を確認してください"),
    ("legal", "民事再生 / 会社更生申立の有無を確認してください"),
    ("legal", "営業譲渡 / 会社分割の過去履歴を説明してください"),
    ("legal", "合併 / 株式交換 / 株式移転の過去履歴を説明してください"),
    ("legal", "TOB (公開買付) の対象 / 主体となった履歴を確認してください"),
    ("legal", "MBO / EBO の検討履歴を説明してください"),
    ("legal", "創業家との株式譲渡合意の有無を説明してください"),
    ("legal", "創業家との顧問契約 / 業務委託契約の有無を説明してください"),
    ("legal", "創業家の経営関与の今後の方針を説明してください"),
    ("legal", "創業家関連の競業 / 競合会社の有無を確認してください"),
    ("legal", "Change of Control に伴う契約相手方への通知義務一覧を提示してください"),
]


# ===== 事業 100 項目 =====

BUSINESS_TEMPLATES: list[tuple[str, str]] = [
    # 事業概要 / 顧客 (25)
    ("business", "主要事業ラインと売上構成比を説明してください"),
    ("business", "過去 5 年の事業別売上推移を提示してください"),
    ("business", "主要顧客 (売上上位 10 社) と取引年数を説明してください"),
    ("business", "顧客別売上集中度 (上位 5 / 10 社占有率) を説明してください"),
    ("business", "主要顧客との取引継続性 (契約有効期間 / 更新条件) を説明してください"),
    ("business", "新規顧客獲得数の年次推移を提示してください"),
    ("business", "既存顧客のリピート率 / 解約率を説明してください"),
    ("business", "顧客満足度 (NPS / CSAT) の測定状況を説明してください"),
    ("business", "顧客クレーム件数の年次推移を提示してください"),
    ("business", "主要顧客との価格交渉履歴を説明してください"),
    ("business", "主要顧客への依存度低減策を説明してください"),
    ("business", "公共セクター顧客の割合を説明してください"),
    ("business", "海外顧客の地域構成を説明してください"),
    ("business", "B2B / B2C / B2G 比率を説明してください"),
    ("business", "サブスクリプション収入の比率を説明してください"),
    ("business", "ストック収入 / フロー収入の比率を説明してください"),
    ("business", "解約率 (Churn) の年次推移を提示してください"),
    ("business", "LTV / CAC 比率を説明してください"),
    ("business", "顧客獲得経路 (営業 / マーケ / 紹介) を説明してください"),
    ("business", "顧客 segment 別 ARPU を説明してください"),
    ("business", "顧客リード creation の channel mix を説明してください"),
    ("business", "顧客 onboarding プロセスを説明してください"),
    ("business", "アップセル / クロスセル戦略を説明してください"),
    ("business", "顧客 churn の主要理由を説明してください"),
    ("business", "顧客 NPS Promoter 比率を説明してください"),
    # 製品 / サービス (25)
    ("business", "主要製品 / サービスのラインナップを説明してください"),
    ("business", "新商品 / 新サービスの過去 3 年投入実績を提示してください"),
    ("business", "製品 / サービス別粗利率を説明してください"),
    ("business", "製品ライフサイクル管理を説明してください"),
    ("business", "R&D 投資の年次推移と GDP 比率を説明してください"),
    ("business", "知財ポートフォリオの戦略を説明してください"),
    ("business", "競合製品との差別化要因を説明してください"),
    ("business", "価格戦略 (プレミアム / 中位 / ローエンド) を説明してください"),
    ("business", "価格改定の過去履歴と顧客反応を説明してください"),
    ("business", "OEM / ODM 比率を説明してください"),
    ("business", "原材料 / 部品の主要調達先を説明してください"),
    ("business", "サプライチェーンの集中度 / 分散度を説明してください"),
    ("business", "在庫管理方式 (JIT / 安全在庫) を説明してください"),
    ("business", "品質管理体制 (ISO / HACCP 等) を説明してください"),
    ("business", "製品事故 / リコール履歴を説明してください"),
    ("business", "PL (製造物責任) 保険の付保状況を説明してください"),
    ("business", "サービス SLA の遵守状況を説明してください"),
    ("business", "保守 / アフターサービス体制を説明してください"),
    ("business", "デジタル化 / オンライン化の進捗を説明してください"),
    ("business", "DX 投資の戦略を説明してください"),
    ("business", "AI 活用の取組状況を説明してください"),
    ("business", "サブスクリプション化への移行戦略を説明してください"),
    ("business", "プラットフォーム化 / ネットワーク効果の有無を説明してください"),
    ("business", "海外展開の方針と進捗を説明してください"),
    ("business", "クロスボーダー商流の規模を説明してください"),
    # 組織 / 人材 (25)
    ("business", "従業員数の年次推移を提示してください"),
    ("business", "正社員 / 契約社員 / パート比率を説明してください"),
    ("business", "従業員平均年齢 / 平均勤続年数を説明してください"),
    ("business", "離職率の年次推移を提示してください"),
    ("business", "主要 key person (CTO / CFO 等) の引き継ぎ計画を説明してください"),
    ("business", "経営陣の Change of Control 後の継続意向を説明してください"),
    ("business", "幹部社員のリテンション施策を説明してください"),
    ("business", "従業員エンゲージメントの測定状況を説明してください"),
    ("business", "新卒 / 中途採用の比率を説明してください"),
    ("business", "採用難易度 / 採用コストを説明してください"),
    ("business", "人事制度 (等級 / 評価 / 報酬) を説明してください"),
    ("business", "業績連動賞与の設計を説明してください"),
    ("business", "ストックオプション付与状況を説明してください"),
    ("business", "労働組合の有無と関係性を説明してください"),
    ("business", "労働協約の主要内容を説明してください"),
    ("business", "ダイバーシティ指標 (女性管理職比率 等) を説明してください"),
    ("business", "教育研修への投資額を説明してください"),
    ("business", "リスキリング / アップスキリングの取組状況を説明してください"),
    ("business", "テレワーク制度の運用状況を説明してください"),
    ("business", "オフィス / 事業所の所在地一覧を提示してください"),
    ("business", "本社機能の主要内訳を説明してください"),
    ("business", "地方拠点 / 海外拠点の状況を説明してください"),
    ("business", "BCP (事業継続計画) の整備状況を説明してください"),
    ("business", "情報セキュリティ体制を説明してください"),
    ("business", "サイバーインシデント履歴を確認してください"),
    # 市場 / 競合 / 戦略 (25)
    ("business", "対象市場の規模と成長率を説明してください"),
    ("business", "市場シェアと競合上位 5 社を説明してください"),
    ("business", "主要競合との優位性 / 劣位性を説明してください"),
    ("business", "市場の参入障壁を説明してください"),
    ("business", "規制環境の変化リスクを説明してください"),
    ("business", "技術トレンドの影響を説明してください"),
    ("business", "顧客ニーズ変化の影響を説明してください"),
    ("business", "代替品 / 代替サービスの脅威を説明してください"),
    ("business", "サプライヤー交渉力の状況を説明してください"),
    ("business", "顧客交渉力の状況を説明してください"),
    ("business", "3 年事業計画 (KPI / 投資 / 損益) を提示してください"),
    ("business", "中期成長戦略 (新市場 / 新製品 / M&A) を説明してください"),
    ("business", "海外展開計画と現地パートナー戦略を説明してください"),
    ("business", "ESG 戦略 (環境 / 社会 / ガバナンス) を説明してください"),
    ("business", "気候変動関連リスク (TCFD) を説明してください"),
    ("business", "サプライチェーン脱炭素化の取組を説明してください"),
    ("business", "サステナビリティ報告書の発行状況を説明してください"),
    ("business", "DX 推進ロードマップを説明してください"),
    ("business", "AI 戦略 (社内活用 / 製品組込) を説明してください"),
    ("business", "デジタルマーケティング戦略を説明してください"),
    ("business", "アライアンス / 業務提携の状況を説明してください"),
    ("business", "M&A 戦略 (買収 / 売却) の方針を説明してください"),
    ("business", "事業ポートフォリオの再編方針を説明してください"),
    ("business", "IPO 検討の有無を説明してください"),
    ("business", "事業承継後のシナジー想定を説明してください"),
]


def _evidence_kind(category: str, text: str) -> str:
    """質問 text から expected evidence chunk kind を inference (heuristic)."""
    if "Change of Control" in text or "Change of Control" in text:
        return "clause:change_of_control"
    if "Limitation of Liability" in text:
        return "clause:limitation_of_liability"
    if "Indemnif" in text:
        return "clause:indemnification"
    if "Non-Compete" in text or "競業避止" in text:
        return "clause:non_compete"
    if "Termination" in text:
        return "clause:termination_for_convenience"
    if "Most Favored" in text or "MFN" in text:
        return "clause:mfn"
    if "Governing Law" in text or "準拠法" in text:
        return "clause:governing_law"
    if "創業家" in text or "創業者家族" in text or "名義変更" in text:
        return "jp_pattern:family_or_nominee"
    if "役員報酬" in text or "役員貸付金" in text or "私的経費" in text or "オーナー" in text:
        return "jp_pattern:owner_private_expense"
    return f"general:{category}"


def build_questions() -> list[dict]:
    """財務 100 + 法務 100 + 事業 100 = 300 項目 を Pydantic-friendly dict list で構築."""
    out: list[dict] = []
    for category, text in FINANCIAL_TEMPLATES + LEGAL_TEMPLATES + BUSINESS_TEMPLATES:
        q_id = f"Q-{secrets.token_urlsafe(10)}"
        out.append(
            {
                "q_id": q_id,
                "category": category,
                "question_text": text,
                "expected_evidence_kind": _evidence_kind(category, text),
            }
        )
    return out


def main() -> int:
    questions = build_questions()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")

    by_cat: dict[str, int] = {}
    for q in questions:
        by_cat[q["category"]] = by_cat.get(q["category"], 0) + 1
    print(f"[questionnaire] total = {len(questions)}、 path = {OUTPUT_PATH}")
    for cat, n in by_cat.items():
        print(f"  - {cat}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
