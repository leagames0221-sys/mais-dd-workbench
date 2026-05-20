# MAIS — DD Workbench

> **Due Diligence automation** that ingests Excel / Word / PowerPoint / PDF directly from VDR / shared drives and answers hundreds of DD questions with **source-document link-backs** in minutes, not weeks.

[![tests](https://img.shields.io/badge/tests-47%20passing-brightgreen)]()
[![pip-audit](https://github.com/leagames0221-sys/mais-dd-workbench/actions/workflows/pip-audit.yml/badge.svg)](https://github.com/leagames0221-sys/mais-dd-workbench/actions/workflows/pip-audit.yml)
[![python](https://img.shields.io/badge/python-3.11+-blue)]()
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 30-second pitch

DD on a mid-market Japanese deal typically touches dozens of documents and a wide-ranging question list under a tight clock. Most of that time is humans hunting for which clause in which file answers which question.

**MAIS DD Workbench** automates the hunt:
- Ingests Excel / Word / PowerPoint / PDF (incl. OCR + vision) via Docling
- Answers DD questions with citations linked back to page / cell / bbox in source files
- Extracts contract clauses (Change of Control, Limitation of Liability, MFN) using CUAD/ACORD pattern library
- Surfaces Japanese mid-market specific patterns: family ownership, nominee shares, owner personal expenses

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  VDR / shared drive                             │
│  • Excel  • Word  • PowerPoint  • PDF (OCR)     │
└────────────────────────┬────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Docling (IBM, MIT)  │   parse → chunk → metadata
              │  • page / cell /     │   (source link-back data)
              │    bbox preserved    │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  5-stage hybrid      │   BM25 + dense + RRF
              │  retrieval pipeline  │   + cross-encoder + LLM rerank
              └──────────┬───────────┘
                         │
   ┌─────────────────────┼─────────────────────┐
   │                     │                     │
   ▼                     ▼                     ▼
┌──────────┐  ┌────────────────┐  ┌────────────────────┐
│ DD Q-A   │  │  Contract      │  │  JP mid-market     │
│ pipeline │  │  clause        │  │  fit pattern       │
│          │  │  extraction    │  │  detector          │
│ + cite   │  │  (CUAD/ACORD)  │  │  (regex + LLM)     │
└────┬─────┘  └────────┬───────┘  └─────────┬──────────┘
     │                 │                    │
     └─────────────────┴────────────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │  Web UI (FastAPI +  │
            │  Jinja2)            │
            │  • DD project view  │
            │  • chunk viewer     │
            │  • Q-A pairs        │
            │  • clause panel     │
            └─────────────────────┘
```

---

## What's inside

| Capability | Implementation |
|---|---|
| **Multi-format ingestion** | Docling (IBM, MIT) handles PDF/DOCX/PPTX/XLSX/HTML + OCR + vision |
| **Source link-back** | LlamaIndex CitationQueryEngine + Docling chunk metadata (page / cell / bbox) preserved end-to-end |
| **DD Q-A pipeline** | 5-stage hybrid retrieval applied to chunks, then LLM rewrites top-K into structured answers with `[1]` / `[2]` citation refs |
| **Contract clause extraction** | CUAD (Atticus Project, CC BY 4.0) + ACORD pattern library + ContractEval 2026 benchmark |
| **JP mid-market fit detector** | Regex + LLM detector for family ownership, nominee shares, owner personal expenses (patterns absent from global PMI templates) |
| **Vault Pattern** | Contact information vaulted (Fernet); chunks PII-redacted before embedding |

---

## Tech stack

| Layer | Choice |
|---|---|
| Document parsing | Docling >= 2.0 (MIT, IBM-maintained) — CVE-2026-24009 fixed |
| Citation infra | LlamaIndex core (MIT) |
| Sparse / Dense | rank-bm25 + sentence-transformers (multilingual-e5-large) + cross-encoder/ms-marco-MiniLM-L-12-v2 |
| ANN | faiss-cpu (MIT) |
| LLM | Anthropic SDK (MIT) — Claude Sonnet 4.6 with MockProvider swap |
| Web | FastAPI + uvicorn + Jinja2 (MIT) |
| Schema | Pydantic v2 (MIT) |
| Crypto | cryptography (Fernet, Apache-2.0) |
| Tests | pytest >= 9.0.3 (47 collected) — CVE-2025-71176 fixed |
| Synthetic data | Faker (MIT) ja_JP locale |

---

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-week4.txt

# generate synthetic VDR (5 DD projects × ~8 docs = 40 documents)
python -m src.data_gen.generate_synthetic_vdr

# launch UI
uvicorn src.api.app:app --reload --port 8000
```

---

## ID conventions

| Prefix | Entity |
|---|---|
| `DDP-` | DD Project (one M&A engagement) |
| `DOC-` | Source Document (PDF / Word / PPT / Excel) |
| `CHK-` | Chunk (Docling extraction unit, page/cell/bbox) |
| `Q-` | DD Question |
| `A-` | Answer (LLM-generated + citation array) |
| `CIT-` | Citation (link-back to chunk with offsets) |

---

## Configuration (env)

```bash
ANTHROPIC_API_KEY=sk-ant-...           # required for LLM-driven answers
VAULT_KEY=<fernet key>                  # contact info vault
SYNTHETIC_SEED=20260513
DATA_DIR=./data
```

---

## Production deployment notes

- Real M&A documents → run inside sandbox (Docker / WSL2 / Codespaces)
- Customer sandbox dry-run + 1-week stability before cutover
- Sweep 2026 advisories for Docling, LlamaIndex
- External penetration test recommended for large engagements

---

## Sibling tools (M&A Intelligence Suite)

- [mais-deal-matching](https://github.com/leagames0221-sys/mais-deal-matching) — sourcing
- **[mais-dd-workbench](https://github.com/leagames0221-sys/mais-dd-workbench)** ← this repo (DD)
- [mais-day1-cockpit](https://github.com/leagames0221-sys/mais-day1-cockpit) — Day-1 readiness
- [mais-pmi-cockpit](https://github.com/leagames0221-sys/mais-pmi-cockpit) — 100-day PMI dashboard
- [mais-pmi-knowledge-base](https://github.com/leagames0221-sys/mais-pmi-knowledge-base) — knowledge layer
- [mais-portfolio](https://github.com/leagames0221-sys/mais-portfolio) — overview

---

## License

MIT. See [LICENSE](LICENSE).
