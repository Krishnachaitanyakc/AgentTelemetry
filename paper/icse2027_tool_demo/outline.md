# Outline — AgentTelemetry, ICSE 2027 Tool Demo (4 pages, IEEEtran 10pt)

**Title**: AgentTelemetry: An OpenTelemetry-Native Observability SDK for AI Agent Systems

**Author**: Krishna Chaitanya Balusu (Independent Researcher), single-anonymous so name appears.

**Target**: 4 pages with references. Tight. Every section must earn its inches.

## Sectioning (estimated column-inches)

### I. Introduction (≈ 0.6 page) — concrete scenario lead
- One-paragraph hook: a developer instruments a LangChain ReAct agent in 5 lines and immediately sees a `PLANNING → DELEGATION → DELEGATION → DELEGATION → PLANNING` loop in Jaeger that vanilla OTel spans could not have revealed.
- Why agents need new span semantics: OTel GenAI v1.x models `gen_ai.completion` but leaves planning, reasoning, delegation, memory, guardrails un-typed.
- Contribution list (4 bullets): (i) pip-installable SDK, (ii) 9 agent span kinds + 7 framework adapters + 4 analysis modules, (iii) 3,780-row public benchmark, (iv) screencast demonstrating end-to-end use.

### II. Tool Overview (≈ 0.9 page)
- Architecture diagram (Fig. 1): caller → adapter → SDK (spans/privacy/exporter) → OTLP → backend → analysis modules.
- Brief description of each subsystem in one paragraph each: spans, adapters, privacy, analysis.
- Three short tables condensed:
  - Table I: Adapters (framework, class, strategy, LOC).
  - Table II: Analysis modules (module, faults detected).
- (Span-kinds enum listed inline, not in a table, to save space.)

### III. Usage (≈ 0.6 page) — show, don't tell
- Listing 1: Manual instrumentation (≤ 10 LOC).
- Listing 2: Auto-instrumentation with `LangChainInstrumentor` (≤ 6 LOC).
- Screenshot (Fig. 2): Jaeger trace showing the nine span kinds for a real ReAct agent run, faults highlighted.

### IV. Comparison with Existing Tools (≈ 0.6 page)
- Table III: AgentTelemetry vs LangSmith vs Langfuse vs AgentOps vs Phoenix vs OpenLIT.
  - Rows: OSS license, OTel-native, agent-specific span kinds count, framework adapters count, analysis modules, semantic-convention contribution (OTEP), self-hostable.
- One paragraph explaining the novelty: typed coordination/cognition spans + open semantic conventions proposal, not a SaaS dashboard.

### V. Evaluation Evidence (≈ 0.4 page)
- One paragraph + one tiny inline table summarising the benchmark: FDR by telemetry condition (numbers from README — vanilla OTel 0.429, full vocabulary 1.000 upper bound).
- One sentence on overhead: cite `tests/benchmarks/test_overhead.py` measured median per-span overhead.
- One sentence: "Full benchmark, methodology, and statistical analysis are reported separately [AIware'26 citation]; we reference the artifact here as evidence that the tool produces a detectable signal."

### VI. Availability and Reproducibility (≈ 0.3 page)
- PyPI URL, GitHub URL, Zenodo DOI (concept + pinned version).
- Apache-2.0 license, 78 tests, pinned `requirements.lock`.
- Screencast URL (3–5 min).
- Roadmap pointer: OTel semantic convention proposal under discussion (cite the OTEP folder in the repo).

### VII. Conclusion (≈ 0.15 page)
- Two sentences. The tool exists, it's installable, here's where to go.

## Figures

- **Fig. 1**: Architecture (single column, ~2.5 in tall): boxes for User Code → Adapter → AgentTelemetry SDK (Spans, Privacy, Exporter) → OTLP → Backend → Analysis Modules; dashed arrow from Backend back to Analysis showing it pulls completed traces.
- **Fig. 2**: Jaeger UI screenshot of a multi-agent ReAct trace with nine span kinds visible. [REQUEST_FOR_USER if not capturable from existing fixtures.]

## Listings

- **Listing 1**: Manual instrumentation — exact code from README Quickstart, ≤ 10 lines.
- **Listing 2**: LangChain auto-instrumentation — 5 lines from `examples/langchain_example.py`.

## Comparison table rows (Table III — verified facts only)

| Tool | OSS | OTel-native | Agent span kinds | Adapters | Analysis modules | OTEP/semconv | Self-host |
|---|---|---|---|---|---|---|---|
| LangSmith | No (SaaS) | No | n/a | many | proprietary | No | No |
| Langfuse | Yes | Yes | generic LLM | 50+ | dashboards | No | Yes |
| AgentOps | Yes | Not documented | generic | many | dashboards | No | Yes |
| Phoenix | Yes | Yes (OpenInference) | generic LLM/tool | many | evals | No (OpenInference) | Yes |
| OpenLIT | Yes | Yes | generic LLM | 20+ providers | dashboards | No | Yes |
| **AgentTelemetry** | Yes (Apache) | Yes | **9 typed** | 7 | 4 (anomaly, cost, attribution, hallucination) | Yes (OTEP draft in repo) | Yes |

## Anti-overlap with sister papers

- AIware'26 (already accepted, cite as reference): full benchmark + statistical methodology.
- ASE 2026 (sister): semantic-convention discussion at depth.
- ISSRE 2026 (sister): fault taxonomy + reliability framing.
- Middleware 2026 / ATC 2026 / IEEE SW EdgeCloud 2026 (sister): systems-level framings.
- ICSE 2027 NIER (sister): forward-looking research vision.
- **This paper (ICSE 2027 Tool Demo)**: pitches the installable SDK as a usable engineering tool. Empirical claims kept short, deferred to AIware'26 citation. Comparison table + listings + screenshot are the load-bearing content.

## Mandatory pre-submission checks

1. Page count exactly 4 (compile and verify).
2. IEEEtran 10pt conference (no compsoc).
3. Author name on title page (single-anonymous).
4. YouTube URL in paper.
5. PyPI + GitHub + Zenodo links live.
6. No AI/Claude/assistant mentions anywhere.
7. Every bibliography entry verified (no hallucinated DOIs/URLs).
