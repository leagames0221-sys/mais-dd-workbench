# ADR-0003: Document ingestion — Docling (IBM, MIT) for multi-format parsing with citation metadata preservation

## Status

Accepted (2026-05-22)

## Context

The workbench ingests four document formats (PDF / Word / PowerPoint / Excel) plus OCR'd scans and image-embedded clauses, all in the same pipeline. Five constraints frame the parser choice:

1. **Multi-format coverage with one library** — JP mid-market VDRs commonly mix PDF reports, Word agreements, Excel financial schedules, PowerPoint board materials in the same engagement. Per-format parsers would force the chunking + citation layer to handle four different metadata schemas.
2. **Page / cell / bbox citation metadata preserved end-to-end** — the audit-grade citation surface requires that every chunk carries source coordinates that round-trip through retrieval to the final answer.
3. **OCR + vision support** — scanned contracts and image-embedded clauses are common; the parser must handle these natively.
4. **MIT-or-permissive license** — see [Selected under](../../README.md#selected-under) "free / OSS only" constraint.
5. **Active maintenance signal** — DD workbench is a long-lived portfolio piece; a parser on maintenance-only status is a future-stranded dependency.

## Decision

Docling 2.0+ (IBM Research, MIT) as the sole document parser ([src/ingestion/](../../src/ingestion/)). Docling's output is a unified `DoclingDocument` representation carrying per-element source metadata (page, bbox for PDFs / PPTX; cell range for XLSX; paragraph offset for DOCX). The workbench chunks the `DoclingDocument` into citation-bearing units that flow into the [5-stage retrieval pipeline](0004-five-stage-hybrid-retrieval-citation.md).

OCR + vision are integrated in Docling 2.0+ via the same `convert()` call — no separate pipeline branch.

## Why Docling specifically

### Single library, four formats, citation metadata preserved

The alternative landscape splits across multiple libraries:
- PDF: `pdfminer.six`, `PyPDF2`, `pdfplumber`, `pymupdf`
- Word: `python-docx`, `mammoth`
- Excel: `openpyxl`, `xlrd`, `pandas`
- PowerPoint: `python-pptx`
- OCR: `tesseract` + Python bindings, EasyOCR, PaddleOCR
- Vision: separate pipeline using HF Transformers vision models

Each library's citation metadata schema differs; chunking + citation infrastructure would need a normalization layer. Docling provides this normalization out-of-library.

### IBM maintenance signal

Docling is maintained by IBM Research with regular releases through 2026; the project has a clear roadmap and active issue triage. This is the right maintenance signal for a long-lived portfolio piece.

### MIT license

Permissive license; compatible with the rest of the dependency graph.

### CVE-2026-24009 was fixed promptly

The 2026 Docling CVE (model-poisoning via crafted PDF) was patched within 7 days of disclosure — strong responsive-maintenance signal.

## Alternatives considered

### Per-format parsers (pdfminer + python-docx + openpyxl + python-pptx) (rejected)

- **Pros**: each library is narrower and easier to reason about in isolation.
- **Cons**: citation metadata schema differs per library; OCR + vision would need separate pipelines; testing surface multiplies by 4–6×.
- **Why rejected**: scope discipline — Docling normalizes the metadata schema, which is exactly what the citation surface needs.

### Apache Tika (Java, via REST or jpype) (rejected)

- **Pros**: industry-standard multi-format parser; very wide format coverage.
- **Cons**: Java runtime dependency (~200 MB JVM install on user machine) + bridge overhead (REST server or jpype); citation metadata coverage is shallower than Docling's (Tika focuses on text + minimal metadata, not bbox + cell range).
- **Why rejected**: Java runtime install friction + shallower citation metadata.

### Unstructured (`unstructured.io`) (rejected)

- **Pros**: similar scope to Docling — multi-format unified ingestion.
- **Cons**: split-license model (open-source MIT core + paid Unstructured Platform for higher-quality OCR / vision); the OSS tier's OCR quality lags Docling's in published benchmarks. Some downstream users report `unstructured` 0.18+ requiring credit-card-backed managed-service hooks for production-grade extraction.
- **Why rejected**: ambiguous split-license risk + lagging OSS-tier OCR. Documented as alternative if Docling's IBM maintenance changes.

### Azure Document Intelligence / Google Document AI / Amazon Textract (rejected)

- **Pros**: production-grade managed OCR + layout extraction.
- **Cons**: managed cloud service requires credit card; violates [Selected under](../../README.md#selected-under) zero-CC default.
- **Why rejected**: cost constraint. Customer engagements with existing Azure / GCP / AWS contracts can swap to these at the same `src/ingestion/` boundary.

### LlamaParse (LlamaIndex Cloud) (rejected)

- **Pros**: integrates natively with LlamaIndex; high-quality table extraction.
- **Cons**: hosted service requires API key + paid usage at moderate volume; violates the zero-CC default.
- **Why rejected**: cost constraint.

### Hand-rolled parsing (use pdf2text + raw XML extraction for DOCX/PPTX/XLSX) (rejected)

- **Pros**: no external dependency.
- **Cons**: re-implements months of layout + OCR + table extraction work; citation metadata schema would still need designing from scratch.
- **Why rejected**: scope discipline.

## Consequences

### Positive

- One library, four formats, plus OCR + vision — keeps the ingestion-layer surface small.
- Citation metadata (page / bbox / cell range / paragraph offset) flows end-to-end through chunking + retrieval to the final answer; the citation link-back is reproducible from a clean ingestion.
- MIT license + IBM maintenance signal supports long-term dependency stability.
- The CVE-2026-24009 patch within 7 days establishes the responsive-maintenance signal that matters for a production-bound dependency.

### Negative

- Docling adds ~500 MB of OCR + vision model weights on first ingestion; first-run latency is non-trivial. Amortized across the project lifetime.
- The unified `DoclingDocument` representation is opinionated; format-specific edge cases (heavily-merged-cell Excel sheets, animated PowerPoint diagrams) may lose fidelity vs. a per-format parser. Mitigated by the fallback to manual chunk adjustment in the chunking layer.

### Reversibility

The ingestion layer is isolated to [src/ingestion/](../../src/ingestion/) behind a unified `Chunk` Pydantic boundary. Swapping Docling for Unstructured / Azure Document Intelligence / a per-format parser stack is a single-module rewrite; the chunking + retrieval + citation layers do not change.

## References

- [Docling project](https://github.com/docling-project/docling)
- [Docling paper — "Docling Technical Report"](https://arxiv.org/abs/2408.09869)
- [Apache Tika](https://tika.apache.org/) — alternative considered
- [Unstructured](https://github.com/Unstructured-IO/unstructured) — alternative considered
- [Azure Document Intelligence](https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence) — paid alternative
- [LlamaParse](https://docs.llamaindex.ai/en/stable/llama_cloud/llama_parse/) — paid alternative
- [CUAD paper — "CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review"](https://arxiv.org/abs/2103.06268) — downstream clause-taxonomy consumer
- Code: [src/ingestion/](../../src/ingestion/), [README — Architecture](../../README.md#architecture)
