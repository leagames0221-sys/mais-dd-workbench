# ADR-0002: LLMProvider Protocol — 3-tier swap (Mock / Ollama-local / paid API)

## Status

Accepted (2026-05-22)

## Context

The workbench uses an LLM only at the final answer-synthesis step ([README "Configuration (env)"](../../README.md#configuration-env)) — Docling ingestion + chunking + 5-stage retrieval + citation link-back all run without any LLM. The [Selected under](../../README.md#selected-under) constraint set requires:

1. The PoC runs with no API key and no internet.
2. A customer can plug in a paid Claude / Gemini key in one place, no refactor.
3. An intermediate operator can run Ollama locally for self-hosted realism.

## Decision

A single `LLMProvider` Python `Protocol` ([src/llm/provider.py](../../src/llm/provider.py)) carries three concrete implementations behind a single `default_provider()` factory. Callers (`src/api/`, `src/answer_synthesis/`) import only the Protocol — never a concrete SDK.

| Tier | Provider | Env trigger | Cost / surface |
| --- | --- | --- | --- |
| **1 — PoC default** | `MockProvider` (deterministic templated answers) | None (default) | Zero cost, zero credit card, runs offline |
| **2 — Local LLM swap** | `OllamaProvider` | `LLM_PROVIDER=ollama` + `OLLAMA_BASE_URL` + `OLLAMA_MODEL` | Still zero cost, still no credit card |
| **3 — Customer / production swap** | `ClaudeProvider` / `GeminiProvider` | `LLM_PROVIDER=claude` + `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL` | Only tier touching credit-card-backed services |

SDK imports (`import anthropic`, `import ollama`) live inside the concrete provider class.

## Why a Protocol and not an ABC

Python 3.8+ `typing.Protocol` is structural — test fixtures use one-off `class _Stub:` declarations rather than ABC subclasses.

## Why LLM only at the answer-synthesis step

The audit-grade citation surface depends on citations being emitted *before* the LLM is consulted. Stages 1–4 of the retrieval pipeline ([ADR-0004](0004-five-stage-hybrid-retrieval-citation.md)) emit `(chunk, citation)` pairs deterministically; the LLM synthesizes those into a structured answer but cannot fabricate citations because the candidate set is fixed. This is what makes the workbench's claim "the LLM stage cannot fabricate citations" hold structurally, not just by prompt discipline.

## Alternatives considered

### Single hardcoded Claude provider (rejected)

- **Pros**: simplest; production output quality from day one.
- **Cons**: forces PoC reviewers to procure a paid key; violates [Selected under](../../README.md#selected-under).
- **Why rejected**: defeats the constraint.

### LangChain `BaseChatModel` (rejected)

- **Pros**: industry-standard.
- **Cons**: LangChain 1.0 → 2.0 broke chat-model interfaces; heavy transitive dependency tree.
- **Why rejected**: surface area exceeds the need.

### `litellm` (rejected)

- **Pros**: 100+ providers behind one API.
- **Cons**: scope mismatch.
- **Why rejected**: over-engineered.

### LlamaIndex-internal LLM config (rejected)

- **Pros**: LlamaIndex's `CitationQueryEngine` accepts an LLM instance directly.
- **Cons**: that LLM instance would be a LlamaIndex `LLM` subclass, not the workbench's own Protocol — splitting the swap surface between LlamaIndex and the workbench code. Wrapping the workbench's `LLMProvider` Protocol as a thin LlamaIndex `LLM` adapter unifies the surface.
- **Why rejected as primary**: keeping the swap point in one Protocol is simpler; the LlamaIndex adapter is one wrapper class.

## Consequences

### Positive

- PoC reviewer: zero env vars, zero key, full UI + Docling + retrieval + citation surface works.
- Customer: paste `ANTHROPIC_API_KEY=...`, zero refactor.
- Citation surface is producible without any LLM call; PoC reviewer can inspect Stages 1–4 outputs independently of the answer-synthesis quality.

### Negative

- MockProvider answers are deterministic templated; PoC reviewer does not see LLM stochasticity. Disclosed in [PoC status](../../README.md#poc-status-what-is-live-vs-deferred).

### Reversibility

Adding a fourth tier is one new class + one line in `default_provider()`.

## References

- [PEP 544 — Protocols](https://peps.python.org/pep-0544/)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Ollama Python client](https://github.com/ollama/ollama-python)
- [LangChain `BaseChatModel`](https://python.langchain.com/docs/concepts/chat_models/) — heavyweight alternative
- Code: [src/llm/provider.py](../../src/llm/provider.py), [README — Configuration (env)](../../README.md#configuration-env)
