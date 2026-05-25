# Middleware 2026 Paper Outline

## Title (working)
**Heterogeneous Adapters for AI-Agent Observability: A Middleware Architecture for Span Correlation Across Callback, Hook, and Monkey-Patch Instrumentation**

Backup title: *AgentMW: A Middleware Architecture for Cross-Framework AI-Agent Observability*.

## Distinct Angle (vs. sibling papers)
- AIware paper = benchmark + toolkit; ESEM = empirical SDK survey; ASE = open-source toolkit demo; MDE = metamodel; NeurIPS = primitives taxonomy; IEEE Software = closed-loop intervention case study.
- **Middleware angle = architecture and engineering of the instrumentation layer itself.** The contribution is the heterogeneous-adapter middleware design, not the span vocabulary, not the fault-detection rates, not the metamodel.

## One-paragraph thesis
Cross-framework observability for AI agents requires reconciling three structurally incompatible instrumentation strategies — callback registration (LangChain, LlamaIndex), hook subscription (CrewAI), and monkey-patching (OpenAI SDK, Anthropic SDK, AutoGen) — under a single semantic-convention overlay on top of OpenTelemetry. We present a middleware architecture that does this with lazy-imported adapters, a shared semantic-convention substrate, W3C-baggage-extended cross-agent context propagation, and a pluggable analysis pipeline. We evaluate it on six framework adapters across six telemetry conditions, measure p50/p95/p99 span-creation overhead at sub-30 μs per span, stress-test to 78,000 spans/s in-memory and 19,000 spans/s under 100-thread concurrency, and demonstrate that the architecture correlates spans across async multi-agent topologies (hierarchical, parallel, sequential) without modification to host frameworks.

## Sections (target: 12 pp at 9pt SIGCONF)

### 1. Introduction (1.0 pp)
- Problem: AI agent systems use heterogeneous frameworks (LangChain, CrewAI, AutoGen, ...). Each ships its own observability hooks (or none). Operations teams running multi-framework agent fleets cannot get a single coherent trace.
- Why this is a middleware problem (not a tool problem):
  - It is **cross-cutting** (multiple frameworks, multiple processes, multiple languages of LLM providers)
  - It requires **abstraction-level reconciliation** between incompatible instrumentation paradigms
  - It must **scale** to production workloads (low-overhead, concurrent, long-running)
  - It must **interoperate** with existing observability infrastructure (OTel collectors, Jaeger, Tempo, Datadog)
- Contributions (4 bullets):
  1. A heterogeneous-adapter middleware architecture reconciling callback/hook/monkey-patch instrumentation under one semantic-convention overlay
  2. A formal characterisation of cross-agent context propagation extending W3C trace context with agent-baggage
  3. An evaluation across six frameworks × six telemetry conditions (3,780 measured cells) showing per-adapter overhead and span-emission discipline
  4. A scalability study at production-relevant rates (10^4-10^5 spans/s) with backpressure characterisation

### 2. Background and Motivation (1.0 pp)
- 2.1 OpenTelemetry SDK architecture (tracer provider → sampler → processor → exporter)
- 2.2 The AI-agent framework landscape (LangChain, CrewAI, AutoGen, LlamaIndex, OpenAI SDK, Anthropic SDK)
- 2.3 The three instrumentation paradigms a middleware must support:
  - **Callback** (LangChain, LlamaIndex): framework calls user-registered handlers at well-defined lifecycle events.
  - **Hook** (CrewAI): framework exposes typed subscription points (pre-task, post-task, pre-llm, post-llm).
  - **Monkey-patch** (OpenAI SDK, Anthropic SDK, AutoGen): no first-class extensibility; the middleware wraps imported classes at instrument time.
- 2.4 Why OTel GenAI semconv is insufficient: it covers LLM invocations only. Five orchestration phases (planning, reasoning, guard-rail, delegation, memory) have no span-level representation.

### 3. Architecture (2.5 pp)
- 3.1 System overview figure (Fig. 1): host process → framework → adapter → core SDK (spans/context/privacy) → OTel SDK → exporter(s) → backend (Jaeger/Tempo/Datadog).
- 3.2 Three-tier abstraction:
  - **Tier 1 — Semantic substrate** (`core/spans.py`, 191 LOC): 9 agent-span kinds as semantic attributes on OTel INTERNAL spans (rationale: OTel's SpanKind enum is fixed at 5; we overlay).
  - **Tier 2 — Instrumentation adapters** (`adapters/`, 7 modules, 2,123 LOC): one per framework, each implementing the OTel `BaseInstrumentor` contract.
  - **Tier 3 — Analysis pipeline** (`analysis/`, 4 modules, 872 LOC): consumes exported spans for anomaly detection, cost aggregation, decision attribution, hallucination tracing.
- 3.3 Adapter strategy table (Table 1):
  | Framework | Strategy | LOC | Lazy-import | First-class extensibility? |
  |---|---|---|---|---|
  | LangChain | Callback handler | 406 | yes | yes |
  | LlamaIndex | Hook (BaseSpanHandler) | 280 | yes | yes |
  | CrewAI | Hook subscription | 278 | yes | yes |
  | OpenAI SDK | Monkey-patch | 245 | yes | no |
  | Anthropic SDK | Monkey-patch | 294 | yes | no |
  | AutoGen | Monkey-patch | 256 | yes | no |
  | Custom (manual API) | Direct | 315 | n/a | n/a |
- 3.4 **Lazy-import discipline.** Each adapter imports its host framework only inside `_instrument()`. Rationale: a single SDK installation must not force users to install all six framework deps. We show the import-graph in Fig. 2.
- 3.5 **Span context propagation across agents.** `core/context.py` (106 LOC) wraps W3C trace context + baggage with an agent-baggage extension (`agenttelemetry.agent_id`, `agenttelemetry.parent_agent_id`). Discuss propagation across:
  - Synchronous in-process delegation
  - Async coroutines (asyncio task boundaries — context-var semantics)
  - Multi-process delegation (carrier-based extract/inject)
- 3.6 **Privacy controller** (`core/privacy.py`, 116 LOC): three-level policy (NONE / METADATA_ONLY / FULL) applied as a span-attribute filter at emit time. Important for middleware deployment in regulated environments.
- 3.7 **Analysis pipeline as a downstream consumer**: pluggable. Detectors consume the OTel span stream via the exporter, not by instrumenting the SDK. This keeps the middleware unidirectional and lets operators swap detectors without redeploying the agents.

### 4. Implementation (1.0 pp)
- Implementation language: Python 3.10+.
- Total SDK LOC: 3,762 across core (734), adapters (2,123), analysis (872), runtime (33). (counted from `wc -l`)
- OTel version: 1.30 (semconv-compatible).
- Dependency model: `opentelemetry-api`, `opentelemetry-sdk` required; framework deps optional (extras-style).
- Test suite: 78 unit + integration tests under `tests/`.
- Packaging: PyPI-distributable wheel; semantic-convention proposal materials under `otep/` for upstream contribution to OpenTelemetry.

### 5. Evaluation (4.5 pp) — THE HEART OF THE PAPER
- 5.1 **Research questions** (rigour signal for systems reviewers):
  - RQ1 (overhead): What is the per-span instrumentation overhead at p50/p95/p99 across the 9 agent span kinds?
  - RQ2 (scalability): What is the steady-state throughput and backpressure behaviour under concurrent and long-running loads?
  - RQ3 (per-adapter cost): How does end-to-end agent run-time vary across adapters and telemetry conditions?
  - RQ4 (span coverage): How does the heterogeneous-adapter middleware compare to vanilla OTel and OTel-GenAI semantic conventions on span coverage of agent lifecycle events?
  - RQ5 (correlation): Does the context-propagation layer correctly correlate spans across hierarchical, parallel, and sequential multi-agent topologies?
- 5.2 **Setup**: Apple M4 Pro (24-core), Python 3.12, OTel 1.30. 6 frameworks × 6 telemetry conditions × 14 fault classes × 6 LLM configurations = 3,780 cells (`benchmarks/results_full.tsv`). Repeat for each. Repeat counts: 90 cells per (framework, condition) pair.
- 5.3 **RQ1 — Span-creation overhead** (Table 2):
  Reproduce overhead table from `results/overhead_percentiles/overhead_table_snippet.tex`. p50 11-13 μs, p95 12-15 μs, p99 27-43 μs across the 9 span kinds. Memory: ~3.1 KB per span. Throughput per kind: 58-66 K spans/s. Discuss the DELEGATION outlier (p99 42 μs vs 27 μs baseline — attributable to baggage propagation cost).
- 5.4 **RQ2 — Scalability stress test** (Table 3):
  Reproduce from `results/scalability/scalability_table_snippet.tex`. 100-thread concurrent: 19,071 sp/s. 1,200-span long-running trace: 5,335 sp/s with 7.6% latency degradation first-decile-to-last-decile. JSON export to disk: 6,187 sp/s (1232% overhead vs in-memory). BatchProcessor: no backpressure observed (exported 1251/1200 spans). Concurrent memory growth: 10.78 MB for 3,482 spans.
- 5.5 **RQ3 — End-to-end agent overhead by adapter** (Table 4):
  Aggregate `results_full.tsv` by (framework, condition) over 90 cells each. Show that:
  - LangChain (callback strategy) adds ~+0.6 ms per agent run (8.09 ms metadata_only vs 7.45 ms no_telemetry)
  - CrewAI (hook strategy) shows ~+1.8 ms (23.35 vs 21.52, higher absolute baseline)
  - OpenAI SDK (monkey-patch) adds ~+0.5 ms (7.94 vs 7.43)
  - Anthropic SDK (monkey-patch) adds ~+0.4 ms (7.71 vs 7.30)
  - AutoGen (monkey-patch) adds ~+1.6 ms (9.17 vs 7.55)
  - LlamaIndex (hook) adds ~+1.4 ms (9.05 vs 7.64)
  Conclusion: monkey-patch is consistently the lowest-overhead strategy when the host framework lacks first-class hooks; callback/hook is competitive when supported; CrewAI's higher absolute baseline is a property of the framework, not the adapter.
- 5.6 **RQ4 — Span coverage comparison** (Table 5):
  Compare AgentTelemetry vs vanilla_otel vs otel_genai vs openinference on span-kind coverage. Use 14 fault classes × span-emission counts (already in `results_full.tsv`). Show that vanilla OTel and OTel GenAI emit ~15-16 spans per run but capture only LLM_CALL / TOOL_CALL kinds; AgentTelemetry emits fewer spans (often 4-19) but covers all 9 kinds. Frame as **"span-kind coverage breadth, not raw span count"** — a middleware-relevant concern.
- 5.7 **RQ5 — Multi-agent topology correlation** (Table 6):
  Reproduce from `results/multi_agent_topology_cli/summary.txt`: 45 runs across 3 topologies (hierarchical, parallel, sequential) × 3 LLM configs × 5 reps. All 9 span kinds emitted across the 570 collected spans. Trace correlation rate: report from `results/multi_agent_e2e/summary.json` ("all_9_present": true, 16 spans, 1 cost-summary anomaly check passing).
- 5.8 **Comparison to baselines** (Section 5.8): vanilla OTel, OTel GenAI, OpenInference span counts vs ours; argue the middleware contribution is the **abstraction**, not the span count.

### 6. Discussion (0.5 pp)
- Adapter-strategy trade-offs (when to monkey-patch, when to use callbacks)
- Lazy-import as a design principle for cross-framework middleware
- Limitations: Python-only; six frameworks (not exhaustive); offline LLM mocks used for benchmark reproducibility (real-LLM corpus exists but used for sibling work)
- Threats to validity: M4 Pro single-machine measurements; OTel SDK version-locked at 1.30; framework versions pinned (versions noted in `pyproject.toml`)

### 7. Related Work (1.0 pp)
- 7.1 Distributed tracing middleware: Dapper, Jaeger, Zipkin, Tempo, Pinpoint — emphasise that AI-agent observability inherits but extends these
- 7.2 OpenTelemetry SDK and semantic conventions — and the GenAI subgroup
- 7.3 LLM observability vendors: LangSmith, Langfuse, OpenLLMetry, Helicone, Arize Phoenix, OpenInference
- 7.4 Agent-specific observability: AgentOps, AgentRx, agent-debug, MAST, AgDebugger — most are post-hoc analysis, not middleware
- 7.5 Cross-framework instrumentation middleware in adjacent domains: ASM bytecode rewriters (DynaTrace, NewRelic Java agent), Python `wrapt`-based instrumentors

### 8. Conclusion (0.5 pp)
Recap contributions. Future work: adding Rust/TypeScript-language adapters; integrating with OTel collector processors; upstream OTEP submission for the 9 agent-span semantic conventions.

## Figures & Tables

| # | Type | Content | Source |
|---|---|---|---|
| Fig. 1 | Architecture diagram | Tier 1/2/3 layered architecture | TikZ from scratch |
| Fig. 2 | Import graph | Lazy-import dependency edges | TikZ from scratch |
| Fig. 3 | Span correlation diagram | Multi-agent topology trace tree | TikZ from scratch |
| Tab. 1 | Adapter strategies | Per-framework strategy + LOC | This outline |
| Tab. 2 | Span-creation overhead | p50/p95/p99 per kind | `results/overhead_percentiles/` |
| Tab. 3 | Scalability stress test | Concurrent / long / export | `results/scalability/` |
| Tab. 4 | End-to-end per-adapter overhead | (framework, condition) × run_time_ms | `benchmarks/results_full.tsv` |
| Tab. 5 | Span-kind coverage | AgentTelemetry vs OTel vs GenAI vs OpenInference | `results_full.tsv` |
| Tab. 6 | Multi-agent topology | (topology, model) × wall / spans / kinds | `results/multi_agent_topology_cli/` |

## Honest gaps (use "—" in tables)
- No Rust/TypeScript adapter (mark in Sec 4, again in Sec 6)
- No formal verification of context-propagation invariants
- No production-deployment metrics from a third party (only first-party benchmarks)
- LLM-mock based fault-injection (real-LLM corpus referenced but reported in sibling AIware paper)

## Pages-to-content sanity check
- Intro 1.0 + Background 1.0 + Architecture 2.5 + Impl 1.0 + Eval 4.5 + Discussion 0.5 + Related 1.0 + Conclusion 0.5 = **12.0 pp**. References overflow allowed.

## Anonymization checklist
- No author name anywhere; "Anonymous Authors" affiliation
- No reference to PyPI URL, GitHub URL, Krishna's email, or prior accepted papers in author voice
- Cite sibling work via arXiv preprints rather than venue (if any are arXiv-public) or as `\todo{verify-not-self-revealing}`
- No funder acknowledgement
- Use `\settopmatter{printacmref=false}` and `\acmConference` set to placeholder
