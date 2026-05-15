# MAIS — DD Workbench

> **M&A Intelligence Suite (MAIS)** の 2 番目のツール。
> M&A Due Diligence (DD) 段階で **VDR / 共有ドライブの Excel / Word / PowerPoint / PDF を直接 ingestion**、
> DD 質問票数百項目に対し **source 文書 link back 付き で分単位回答** する PoC。

[![pip-audit](https://img.shields.io/badge/pip--audit-0%20CVE-brightgreen)]()
[![python](https://img.shields.io/badge/python-3.11+-blue)]()
[![license](https://img.shields.io/badge/license-PoC%20demo-lightgrey)]()

---

## 何ができるか

| 機能 | 内容 |
|---|---|
| **Multi-format ingestion** | Excel / Word / PowerPoint / PDF / OCR / vision を Docling (IBM 公式) で literal parse、 page/cell/bbox metadata 付き chunk 抽出 |
| **DD 質問票自動回答** | 数百項目の質問に対し RAG + 5-stage hybrid pipeline で回答、 全回答に source 文書 link back |
| **Contract clause extraction** | CUAD/ACORD pattern で Change of Control / Limitation of Liability / MFN 等の抽出 |
| **財務 DD draft 生成** | 申告書 / 財務諸表 / 勘定科目内訳明細書 → 財務 DD レポート draft (decomposed prior art: SEC filings RAG + Equity Research multi-agent) |
| **中堅日本企業 fit pattern** | 同族経営 / 名義株 / オーナー私的経費 detector (regex + LLM)、 グローバル PMI template に未収録の補足 |
| **黒×金 brand UI** | FastAPI + Jinja2、 DD project / chunk viewer / question-answer pairs / contract clause panel |

---

## 想定ユースケース

- **M&A advisory firm** の DD チームが工数 -50% 化
- **PE / VC / 戦略コンサル** の DD サイクル 週 → 日 圧縮
- **コーポレート M&A 部門** の internal DD platform として deploy

---

## tech stack

| 層 | 採用 | source |
|---|---|---|
| Document ingestion | **Docling** (IBM 公式、 PDF/DOCX/PPTX/XLSX/HTML/OCR/vision 全 cover) | https://www.docling.ai/ |
| Citation infra | **LlamaIndex CitationQueryEngine** + Docling chunk metadata | https://docs.llamaindex.ai/ |
| Contract clause | **CUAD** + **ACORD** dataset + **ContractEval 2026** benchmark | https://www.atticusprojectai.org/cuad |
| DD QA pipeline | 5-stage hybrid (BM25 + dense + RRF + cross-encoder + LLM listwise rerank) | (本 suite 共通) |
| Financial DD draft | SEC filings RAG + Equity Research multi-agent + Finance-LLMs reference (decomposed) | (Discovery brief 参照) |
| Embedding | sentence-transformers (multilingual-e5-large + cross-encoder/ms-marco-MiniLM-L-12-v2) | Apache-2.0 |
| Web UI | FastAPI + uvicorn + Jinja2 | MIT |
| Security | python-ml-stack 5-layer 防御 + Vault Pattern (担当者連絡先 vault + chunk redact) | (本 suite 共通) |

---

## 期待効果

- **DD 工数 -50%** ★★★ (Clarum / M's DD 公式実績 benchmark)
- **DD サイクル 週 → 日** ★★★ (PE benchmark)

---

## 4-Week roadmap (PoC scope)

| Week | scope | deliverable |
|---|---|---|
| **Week 0** | Discovery → Requirements → Design → Tasks、 GitHub PRIVATE repo + drift CI install、 採用 OSS audit gate (Layer 5 pre_commit + Dependabot active 化) | scaffold + design doc |
| **Week 1** | 合成 VDR data 生成 (PDF/Word/Excel/PPT 各 2 件 × DDP 5 案件 = 計 40 docs、 中堅 fit pattern inject) + Docling ingestion smoke + chunk metadata schema | 1 commandlet で VDR → chunked text + page/cell/bbox metadata |
| **Week 2** | DD 質問票テンプレート 100 項目 (財務 / 法務 / 事業) + RAG citation pipeline + 5-stage hybrid retrieval を chunk に literal 適用 | 質問 → 回答 + source 文書 link back smoke |
| **Week 3** | Contract clause extraction (CUAD/ACORD pattern) + 中堅日本企業 fit pattern detector | Q-A pair full pipeline + 中堅 fit pattern surface |
| **Week 4** | FastAPI/Jinja UI 5 page + Vault Pattern + e2e_smoke | 実機 demo (Cloudflare quick tunnel) |

---

## 環境設定

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-week0.txt
copy .env.example .env
```

### 必須 env var

```bash
ANTHROPIC_API_KEY=sk-ant-...           # Week 2+ で active
VAULT_KEY=<fernet key>                  # vault PII 暗号化
SYNTHETIC_SEED=20260513
DATA_DIR=./data
```

---

## 制約 (PoC scope)

- **無料 + クレカ不要範囲** で完走
- **consumer laptop** で完走前提
- **合成 VDR data only** — 実 M&A 契約書 / 実財務諸表 一切扱わない (移植時 sandbox 必須)
- **vendor lock-in ZERO** (Anthropic API + OSS only、 Gemini / Claude / Ollama 1 file swap path)

---

## 移植段階の追加要件

- 実 M&A 契約書投入時 = sandbox (Docker / WSL2) + 顧客 sandbox dry-run + 1 週間 stability
- Docling 等 OSS の 2026 advisory 履歴 sweep
- 大型案件 = external pentesting 推奨

---

## related tools (M&A Intelligence Suite)

- **mais-deal-matching** — sourcing stage
- **mais-dd-workbench** ← 本リポジトリ (DD automation)
- **mais-day1-cockpit** — Day-1 readiness
- **mais-pmi-cockpit** — 100-day PMI dashboard
- **mais-pmi-knowledge-base** — knowledge layer (全 tool 共通参照)

---

## license

PoC demo — 設計思想 + コード構造を portfolio 公開、 合成データのみ含む。 商用 deploy は別途相談。
