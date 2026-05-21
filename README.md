# MAIS — DD Workbench

> **Due Diligence automation** that ingests Excel / Word / PowerPoint / PDF directly from VDR / shared drives and answers hundreds of DD questions with **source-document link-backs** in minutes, not weeks.

[![tests](https://img.shields.io/badge/tests-47%20passing-brightgreen)]()
[![pip-audit](https://github.com/leagames0221-sys/mais-dd-workbench/actions/workflows/pip-audit.yml/badge.svg)](https://github.com/leagames0221-sys/mais-dd-workbench/actions/workflows/pip-audit.yml)
[![python](https://img.shields.io/badge/python-3.11+-blue)]()
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Constraint: zero credit card](https://img.shields.io/badge/Constraint-zero%20credit%20card-blue)](#selected-under)
[![Constraint: local LLM (default)](https://img.shields.io/badge/Constraint-local%20LLM%20%28default%29-blue)](#selected-under)
[![Constraint: free / OSS only](https://img.shields.io/badge/Constraint-free%20%2F%20OSS%20only-blue)](#selected-under)
[![Constraint: security defense-in-depth](https://img.shields.io/badge/Constraint-security%20defense--in--depth-blue)](#selected-under)

---

## Selected under

> **The 4-constraint set** (applied across the full portfolio — verified consistent across all 11 portfolio repos):
>
> 1. **Zero credit card** — no paid API / cloud service required for the default path. A reviewer can clone, install, and run with $0 spend and no payment method on file.
> 2. **Local LLM (default)** — when an LLM is involved, the default path is local (Ollama / similar) or deterministic mock. Paid cloud LLM is opt-in via env var, never default.
> 3. **Free / OSS only** — every runtime dependency is permissively-licensed open source (MIT / Apache-2.0 / BSD-3); no proprietary SDK at build time.
> 4. **Security defense-in-depth** — secrets-scan CI + `.gitignore` hardening, encrypted-at-rest where PII is involved, append-only audit logging where applicable, dep-vuln gating (`pip-audit` / `pnpm audit`), paid-API constructor gate where applicable.

This repo specifically demonstrates: Docling ingestion + chunking + 5-stage retrieval + citation link-back, all running without an LLM. The LLM tier is consulted only at the final answer-synthesis step. The [Configuration (env)](#configuration-env) section's 3-tier swap shows the single point where paid APIs enter the system (tier 3 only).

---

## 🎬 Demo walkthrough (~2-minute narrated video)

End-to-end demo of the DD Q-A flow — landing → sign-in → DD project list (5 synthetic cases) → 映像制作 case → Docling ingestion (71 chunks extracted) → JP patterns hit (family ownership / nominee shareholder) → legal questionnaire (300+ items) → 1-question AI answer with citation link-back → audit log → landing 本番 scale. Japanese narration by [AivisSpeech](https://aivis-project.com/) (まお おちついた, Style-Bert-VITS2), 1920×1080 H.264.

> [▶️ **mais_dd_workbench_demo.mp4**](out_video/mais_dd_workbench_demo.mp4) — 111.07 s · 6.8 MB · 16 scenes with burned-in SRT subtitles.

<video src="out_video/mais_dd_workbench_demo.mp4" controls width="100%"></video>

**Reproducible pipeline** ([scripts/produce_video.py](scripts/produce_video.py), [requirements-video.txt](requirements-video.txt)) — action-then-narration timing model: each scene measures Playwright action elapsed time then plays narration on the settled destination page. All synthetic VDR data, zero real PII, zero paid API.

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

The workbench ships with a **3-tier LLM swap path** for the DD Q-A engine. Pick the tier that matches your environment — no env edits are needed for tier 1 (PoC default).

### Tier 1 — PoC default (zero cost, zero credit card, runs offline)

```bash
# No LLM env vars required. MockProvider is the default; Docling ingestion +
# 5-stage retrieval + citation link-back all work on deterministic templated
# answers without any external API call.
VAULT_KEY=<fernet key>                  # contact info vault (always required)
SYNTHETIC_SEED=20260513
DATA_DIR=./data
```

### Tier 2 — Local LLM swap (still zero cost, zero credit card; uses your own GPU/CPU)

For developers / customers who want real LLM-driven answers without paid APIs. Requires [Ollama](https://ollama.com/) running locally with a model pulled (e.g. `ollama pull qwen2.5:7b`).

```bash
LLM_PROVIDER=ollama                     # switches default_provider() to Ollama (1-file swap point in src/api/)
OLLAMA_BASE_URL=http://localhost:11434  # Ollama default
OLLAMA_MODEL=qwen2.5:7b                 # any local model the Q-A prompt format supports
# ... plus the always-required vars from tier 1
```

### Tier 3 — Customer / production swap (paid API; the only tier that touches credit-card-backed services)

For customer deployments where higher answer quality or hosted-model SLA is required. **This is the only place credit-card-backed services enter the system** — paste the customer's key here and nothing else changes.

```bash
LLM_PROVIDER=claude                     # or "gemini" / future provider
ANTHROPIC_API_KEY=sk-ant-...            # paste customer's key here (tier 1 + tier 2 never read this var)
ANTHROPIC_MODEL=claude-sonnet-4-6       # whichever model the engagement contract specifies
# ... plus the always-required vars from tier 1
```

Docling ingestion + chunking + 5-stage retrieval + citation link-back all run on tier 1 alone. The LLM tier is only consulted at the final answer-synthesis step — every prior stage (chunk → embed → retrieve → cite) ships even when the LLM tier is offline.

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
