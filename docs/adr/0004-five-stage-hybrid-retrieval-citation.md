# ADR-0004: Five-stage hybrid retrieval with citation link-back — BM25 + dense e5 + RRF + cross-encoder + LLM rerank

## Status

Accepted (2026-05-22)

## Context

The workbench's value claim ([README "30-second pitch"](../../README.md#30-second-pitch)) is that DD questions are answered with **citation link-back to page / cell / bbox in source documents**, in minutes. Five constraints frame the retrieval composition:

1. **Citation link-back is the audit-grade artifact** — every retrieved chunk must carry the source coordinates that flow through the answer-synthesis step to the final `[1]/[2]` citation marker.
2. **Japanese + English bilingual** — JP mid-market VDRs contain mixed-language documents; the retrieval pipeline must handle both.
3. **Stages 1–4 must run without an LLM** — see [Selected under](../../README.md#selected-under) "zero credit card" + "local LLM (default)" constraints. The citation surface is producible deterministically from chunks alone; the LLM is consulted only at the final answer-synthesis step.
4. **High precision at K=5** — DD analysts surface a small candidate set per question for manual review; noise drowns the signal.
5. **JP business writing rewards sparse + dense complementarity** — short kanji-heavy clause titles reward BM25; long context paragraphs reward dense embeddings.

## Decision

A five-stage retrieval pipeline ([src/retrieval/](../../src/retrieval/)) shared between DD Q-A, contract clause extraction, and JP fit pattern detection:

| Stage | Component | License | Role |
| --- | --- | --- | --- |
| 1 — sparse recall | `rank-bm25` | Apache-2.0 | Tokenized BM25 on Docling chunks; recovers exact-term anchors (clause titles, defined terms). |
| 2 — dense recall | `multilingual-e5-large` via sentence-transformers, served from `faiss-cpu` | MIT + MIT | Bilingual semantic recall; handles JP ↔ EN paraphrase. |
| 3 — RRF fusion | Reciprocal Rank Fusion (in-tree, ~20 LOC) | self-built | Combines stage 1 + 2 rankings without weight tuning. |
| 4 — cross-encoder rerank | `cross-encoder/ms-marco-MiniLM-L-12-v2` | Apache-2.0 | Pairwise (question, chunk) scoring; filters RRF output by domain-textual relevance. |
| 5 — LLM listwise answer synthesis | [`LLMProvider` Protocol](0002-llm-provider-protocol-3tier-swap.md) + LlamaIndex `CitationQueryEngine` | MIT | Synthesizes answer with `[1]/[2]` citation markers from top-K chunks of stage 4. |

The candidate set passed to stage 5 is fixed by stage 4 — **the LLM cannot fabricate citations because the candidate chunks (and their citations) are determined before the LLM is consulted**. This is the structural reason the workbench's claim "the LLM stage cannot fabricate citations" holds.

## Why this composition

### Stages 1 + 2 together

BM25 alone misses paraphrase + JP↔EN cross-language matching; dense alone misses clause-title and defined-term anchors. The complementarity is acute for Japanese business contracts; the fusion step is correspondingly load-bearing.

### Stage 3 RRF

[Cormack et al., 2009](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) showed RRF outperforms weighted-sum fusion across IR benchmarks without per-domain weight tuning. RRF's `k` parameter (typically 60) is corpus-insensitive.

### Stage 4 cross-encoder before stage 5 LLM

Cross-encoder rerank is ~100× cheaper per (query, candidate) pair than an LLM call. Reserving the LLM for the final answer-synthesis step over the cross-encoder top-K is the cost / quality balance.

### Stage 5 last (and only at this stage)

The LLM is consulted only at answer synthesis; the candidate set + citations are already determined by stages 1–4. This is what structurally prevents citation fabrication.

## Alternatives considered

### Dense only (rejected)

- **Pros**: simplest pipeline.
- **Cons**: misses clause-title anchors; dense-only top-K on the JP VDR corpus included off-domain chunks BM25 anchored correctly.
- **Why rejected**: stage 1 BM25 anchor is load-bearing.

### BM25 only (rejected)

- **Pros**: deterministic, no model load.
- **Cons**: misses paraphrase + JP↔EN matching.
- **Why rejected**: stage 2 dense recall is load-bearing for the bilingual case.

### Weighted-sum fusion instead of RRF (rejected)

- **Pros**: per-corpus tuning may eke out a few precision points.
- **Cons**: requires per-deployment weight tuning; brittle when corpus shifts.
- **Why rejected**: customer-corpus shift is the norm.

### LlamaIndex single-stage retrieval (rejected)

- **Pros**: simpler integration with `CitationQueryEngine`.
- **Cons**: LlamaIndex's default retriever is single-stage; missing the sparse / dense / RRF / cross-encoder discipline that the JP mid-market corpus needs.
- **Why rejected**: defaults to lower precision than the 5-stage composition.

### Direct LLM scoring (no statistical retrieval) (rejected)

- **Pros**: simplest from a code-structure perspective.
- **Cons**: blows context window beyond a few hundred chunks; no offline / zero-CC path; LLM could fabricate citations because the chunk set is not pre-fixed.
- **Why rejected**: violates citation-fabrication-prevention + zero-CC constraints simultaneously.

### Cohere Rerank (paid managed rerank) (rejected)

- **Pros**: high reranking quality without local model overhead.
- **Cons**: paid managed service violates the zero-CC default.
- **Why rejected**: incompatible with the default path.

## Consequences

### Positive

- Citation surface is producible from stages 1–4 deterministically; the audit-grade replayability anchor holds even when MockProvider is active at stage 5.
- RRF makes the fusion step corpus-insensitive; the pipeline ports from synthetic VDR to a customer's real VDR without weight retuning.
- The LLM stage cannot fabricate citations — the candidate set is fixed by stage 4 before the LLM is consulted. This is a structural guarantee, not a prompt-discipline plea.
- Citation chunk IDs (`CHK-*` with page / cell / bbox metadata) flow through every stage to the final answer.

### Negative

- Cold start loads two model sets (e5-large + MS-MARCO cross-encoder); amortized by long-running uvicorn process.
- Stage 5 answer-synthesis quality is bounded by the chosen `LLMProvider` tier; MockProvider returns templated answers with stage-4 top-K citations attached.

### Reversibility

Each stage is behind an interface in [src/retrieval/](../../src/retrieval/). Component swaps inside a stage are local edits.

## References

- [Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond"](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf)
- [Wang et al., "Multilingual E5 Text Embeddings"](https://arxiv.org/abs/2402.05672)
- [Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods" (SIGIR 2009)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [MS MARCO Cross-Encoders](https://www.sbert.net/docs/cross_encoder/pretrained_models.html)
- [LlamaIndex `CitationQueryEngine`](https://docs.llamaindex.ai/en/stable/examples/query_engine/citation_query_engine/)
- [`rank-bm25` project](https://github.com/dorianbrown/rank_bm25)
- [`faiss` project](https://github.com/facebookresearch/faiss)
- Code: [src/retrieval/](../../src/retrieval/), [README — Architecture](../../README.md#architecture)
