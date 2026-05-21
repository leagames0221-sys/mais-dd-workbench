# ADR-0005: Contract clause extraction — CUAD + ACORD taxonomy + JP mid-market pattern detector

## Status

Accepted (2026-05-22)

## Context

The DD workbench extracts specific contract clauses (Change of Control, Limitation of Liability, Most-Favored-Nation, etc.) from VDR documents to surface deal-blocking provisions early in the DD timeline. It also detects Japanese mid-market specific patterns (family ownership, nominee shares, owner personal expenses) that are absent from global PMI templates but recurring in JP mid-market deals.

Four constraints frame the taxonomy + detector choices:

1. **Open, citable clause taxonomy** — the audit conversation with M&A counsel requires that the clause-name vocabulary is from a recognized source, not invented by the cockpit.
2. **JP mid-market patterns are not in global taxonomies** — CUAD / ACORD are English-centric and do not enumerate family-ownership / nominee-shareholder / owner-personal-expense patterns; the workbench must layer a JP-specific detector.
3. **Detector must surface evidence + citation** — each clause / pattern hit must point back to the specific source chunk + citation (page / cell / bbox).
4. **Free + permissive license** — see [Selected under](../../README.md#selected-under) free / OSS only.

## Decision

A two-layer clause + pattern extraction stack ([src/extraction/](../../src/extraction/)):

| Layer | Source | License | Role |
| --- | --- | --- | --- |
| **English clause taxonomy** | CUAD (Atticus Project) — 41 contract clause types annotated by lawyers | CC BY 4.0 | Clause-name vocabulary + training-signal reference for the LLM-driven extractor. |
| **English clause taxonomy (insurance/commercial)** | ACORD forms terminology | open-standard | Supplements CUAD with insurance + commercial-contract terminology. |
| **Benchmark reference** | ContractEval 2026 | open-research | Evaluation set + comparison baseline. |
| **JP mid-market pattern detector** | In-house regex + LLM-checker library | self-built | Detects family ownership, nominee shares, owner personal expenses, related-party transactions, bank-covenant fluency — patterns absent from CUAD / ACORD. |

Concrete commitments:

1. The clause name vocabulary is bounded by CUAD's 41 categories + ACORD's terminology set; no clause name is invented at runtime.
2. JP pattern detector runs as a separate code path with its own pattern library, citing back to source chunks via the same citation metadata as the clause extractor.
3. Both layers feed the `JPFitPattern` Pydantic model that flows downstream to `mais-day1-cockpit` per the [portfolio schema chain](https://github.com/leagames0221-sys/mais-portfolio/blob/main/docs/adr/0002-pydantic-schema-chain-handoff-contract.md).

## Why CUAD + ACORD specifically (not a self-built taxonomy)

### CUAD is the canonical legal-tech reference

CUAD is the standard reference dataset for contract clause extraction in published 2021–2026 papers; using it as the taxonomy source means the workbench's vocabulary matches academic + industry references. A self-built taxonomy would have no external validation.

### ACORD covers insurance + commercial gaps

CUAD focuses on M&A / commercial agreements; ACORD covers insurance and supplementary commercial-contract terminology. Together they cover the contract types found in a typical JP mid-market deal.

### CC BY 4.0 license

Permissive license; compatible with the rest of the dependency graph; allows downstream commercial use with attribution.

## Why a separate JP pattern detector layer

Global clause taxonomies (CUAD / ACORD) do not enumerate JP mid-market specifics. The patterns that recur in JP mid-market deals — and frequently surprise foreign acquirers — include:

- **Family ownership** — controlling shareholder is the founder's family; succession + governance dynamics shape integration.
- **Nominee shares** — shares held by employees / relatives on behalf of the controlling shareholder.
- **Owner personal expenses** — owner family expenses paid through the target company.
- **Related-party transactions** — undisclosed contracts with founder-family-owned entities.
- **Bank-covenant fluency** — JP banking-relationship-driven covenant terms that diverge from US/EU norms.

These patterns are best detected by a regex + LLM-checker library tuned to JP business document phrasing; they are absent from CUAD and ACORD.

## Alternatives considered

### Self-built clause taxonomy (rejected)

- **Pros**: maximum control.
- **Cons**: no external validation; vocabulary becomes idiosyncratic to this repo; M&A counsel would need to learn a new vocabulary.
- **Why rejected**: defeats the audit-conversation claim.

### LegalBERT taxonomy (rejected)

- **Pros**: production-grade legal NLP embeddings.
- **Cons**: not a clause taxonomy per se — it's an embedding model trained on legal text. Would still need a separate clause-name vocabulary; CUAD provides that.
- **Why rejected**: orthogonal to the taxonomy question.

### LexNLP (rejected)

- **Pros**: open-source legal NLP library; includes rule-based clause extractor.
- **Cons**: AGPL-3 licensed (viral copyleft) for the Enterprise modules; OSS tier covers basics but not the recent CUAD-trained extractor. Project maintenance has slowed since 2023.
- **Why rejected**: license risk + maintenance signal.

### LLM-only extraction (no taxonomy) (rejected)

- **Pros**: simplest from a code-structure perspective.
- **Cons**: LLM output drifts on clause names; non-reproducible across runs; vocabulary lacks external grounding.
- **Why rejected**: defeats reproducibility + audit-conversation.

### Skip JP pattern detector (CUAD + ACORD only) (rejected)

- **Pros**: smaller codebase.
- **Cons**: misses the JP mid-market-specific patterns — exactly the differentiation the workbench claims over English-focused enterprise legal-tech.
- **Why rejected**: defeats the value-claim differentiation.

### Use ContractEval 2026 as the taxonomy source (rejected)

- **Pros**: more recent than CUAD.
- **Cons**: ContractEval is a *benchmark* not a taxonomy; clause-name vocabulary is borrowed from CUAD / ACORD. Using ContractEval as the taxonomy would conflate evaluation with vocabulary.
- **Why rejected**: scope confusion. Used as benchmark, not taxonomy.

## Consequences

### Positive

- Clause vocabulary matches a recognized academic + industry reference (CUAD), so M&A counsel can verify the extractor's claims against external grounding.
- ContractEval 2026 provides a published benchmark for evaluating the extractor's recall + precision claims.
- JP mid-market pattern detector closes the differentiation gap vs. CUAD-only / ACORD-only enterprise tools.
- Each clause / pattern hit cites back to the source chunk via the same `CHK-*` citation chain as the DD Q-A pipeline.

### Negative

- CUAD is English-centric; clauses in Japanese contracts use Japanese clause names (e.g., `重大事業承継条項`, `株主間契約`) that the English taxonomy does not enumerate. Mitigated by the multilingual-clause-taxonomy expansion item in [PoC status](../../README.md#poc-status-what-is-live-vs-deferred); deferred to integration phase.
- JP pattern detector is regex + LLM hybrid; the regex layer has high precision but bounded recall on novel phrasings, and the LLM layer is bounded by the chosen `LLMProvider` tier.

### Reversibility

The clause taxonomy is configurable via a Pydantic enum + a mapping module; adding a Japanese clause-name overlay is an enum extension + a translation table. The JP pattern detector library is isolated in [src/extraction/jp_patterns/](../../src/extraction/) — adding patterns is additive.

## References

- [CUAD paper — "CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review"](https://arxiv.org/abs/2103.06268)
- [CUAD project](https://github.com/TheAtticusProject/cuad)
- [ACORD Standards](https://www.acord.org/standards-architecture/acord-standards)
- [Atticus Project](https://www.atticusprojectai.org/)
- [LexNLP project](https://github.com/LexPredict/lexpredict-lexnlp) — alternative considered
- [README — What's inside](../../README.md#whats-inside)
- Code: [src/extraction/](../../src/extraction/)
