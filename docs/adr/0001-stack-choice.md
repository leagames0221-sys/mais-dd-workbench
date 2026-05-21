# ADR-0001: Stack choice — Python 3.11+ + FastAPI + Docling + Pydantic v2

## Status

Accepted (2026-05-22)

## Context

`mais-dd-workbench` is the due-diligence member of the MAIS suite — ingests Excel / Word / PowerPoint / PDF (incl. OCR + vision) from VDR / shared drives and answers DD questions with page / cell / bbox citation link-backs. Five constraints frame the stack:

1. **Multi-format document parsing with citation metadata preserved end-to-end** — every chunk must carry source coordinates (page number, cell range, bbox) so the citation surface is auditable.
2. **OCR + vision support** — scanned contracts and image-embedded clauses are common in JP mid-market VDRs; the parser must handle these without a separate pipeline.
3. **Type-safe boundary contracts** — `CitationArray`, `QAPair`, `JPFitPattern` flow downstream to `mais-day1-cockpit` per the [portfolio schema chain](https://github.com/leagames0221-sys/mais-portfolio/blob/main/docs/adr/0002-pydantic-schema-chain-handoff-contract.md).
4. **Free + no-CC default** — see [Selected under](../../README.md#selected-under).
5. **Consumer-laptop runtime** — Docling + 5-stage retrieval + faiss index must run on 16 GB RAM CPU.

## Decision

| Layer | Selection | Free + no-CC verified |
| --- | --- | --- |
| Language | Python 3.11+ | ✅ |
| Web framework | FastAPI (MIT) | ✅ |
| ASGI server | uvicorn (BSD-3) | ✅ |
| Templating | Jinja2 (BSD-3) | ✅ |
| Schema | Pydantic v2 (MIT) | ✅ |
| Document parsing | Docling ≥ 2.0 (IBM, MIT) — see [ADR-0003](0003-docling-ingestion.md) | ✅ |
| Citation infra | LlamaIndex `CitationQueryEngine` (MIT) | ✅ |
| Sparse retrieval | rank-bm25 (Apache-2.0) — see [ADR-0004](0004-five-stage-hybrid-retrieval-citation.md) | ✅ |
| Dense embedding | `multilingual-e5-large` via sentence-transformers (MIT) | ✅ |
| Cross-encoder | `cross-encoder/ms-marco-MiniLM-L-12-v2` (Apache-2.0) | ✅ |
| ANN | faiss-cpu (MIT) | ✅ |
| LLM provider | `LLMProvider` Protocol 3-tier swap — see [ADR-0002](0002-llm-provider-protocol-3tier-swap.md) | ✅ |
| Clause taxonomy | CUAD (Atticus Project, CC BY 4.0) + ACORD — see [ADR-0005](0005-cuad-acord-clause-extraction-jp-pattern-detector.md) | ✅ |
| Crypto | cryptography Fernet (Apache-2.0) — contact vault | ✅ |
| Tests | pytest ≥ 9.0.3 (47 collected) | ✅ |

## Rationale

The ML / NLP ecosystem fit argument is shared across the MAIS suite. DD-workbench-specific drivers:

- **Docling (IBM, MIT)** is the only mature OSS document parser that handles PDF + Word + PowerPoint + Excel + OCR + vision in one library *and* preserves page / cell / bbox metadata through chunking — the audit-grade citation surface depends on this. No comparable library outside Python.
- **LlamaIndex `CitationQueryEngine`** is the closest off-the-shelf primitive for `[1]/[2]`-citation-array-shaped answers; Python-only.
- **Pydantic v2 boundary contracts** carry `CitationArray` + `QAPair` downstream — see [`mais-portfolio` ADR-0002](https://github.com/leagames0221-sys/mais-portfolio/blob/main/docs/adr/0002-pydantic-schema-chain-handoff-contract.md).

## Alternatives considered

### Node.js / TypeScript (rejected)

- **Pros**: stack uniformity with security-tool sibling repos.
- **Cons**: no first-class Docling binding (the closest is `pdf-parse` / `mammoth` covering subset of formats without citation metadata preservation); LlamaIndex.ts citation engine is feature-incomplete.
- **Why rejected**: rebinding cost prohibitive.

### Go (rejected)

- **Pros**: single-binary deploy.
- **Cons**: nearly the entire stack would need reimplementation.
- **Why rejected**: ecosystem-fit argument.

### Python without Docling (use multiple per-format parsers) (rejected)

- **Pros**: more granular control per format.
- **Cons**: page / cell / bbox metadata format would differ per parser; chunking + citation infrastructure would have to normalize across formats; OCR + vision would need separate pipelines.
- **Why rejected**: scope discipline — Docling normalizes all formats into a single chunk-with-metadata representation, which is exactly what the citation surface needs.

## Consequences

### Positive

- All ingestion + retrieval primitives used as-published; no FFI / subprocess overhead.
- Pydantic v2 boundary contracts flow downstream cleanly.
- Citation metadata (page / cell / bbox) flows from Docling through chunking through retrieval to the final answer without coordinate-system translation.

### Negative

- Not single-binary distribution; customer deploy uses containers.
- Docling adds ~500 MB of model weights on first ingestion (OCR + vision models); amortized after first run.

### Reversibility

The Pydantic schemas and citation-array boundary contract are stable; the parser swap surface (Docling → alternative) is isolated to [src/ingestion/](../../src/ingestion/) if a customer's environment cannot pull IBM-maintained model weights.

## References

- [Docling project](https://github.com/docling-project/docling)
- [LlamaIndex `CitationQueryEngine`](https://docs.llamaindex.ai/en/stable/examples/query_engine/citation_query_engine/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Pydantic v2 documentation](https://docs.pydantic.dev/latest/)
- [`mais-portfolio` ADR-0002 — schema chain contract](https://github.com/leagames0221-sys/mais-portfolio/blob/main/docs/adr/0002-pydantic-schema-chain-handoff-contract.md)
- [README — Tech stack](../../README.md#tech-stack)
