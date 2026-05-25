# Outline — ATC 2026 Paper

**Working title:** Telemetry-Driven Runtime Control for Heterogeneous
LLM Agent Systems

**Anonymised system name:** `\sysname{}` ("AgentScope" placeholder in draft;
restore real name for camera-ready)

**Format:** Long paper (12 pp text, references unlimited)

**Class:** `acmart` `[sigplan,10pt,anonymous,review]` (per CFP)

**Required companion:** 2-page extended abstract (`atc_extended_abstract.tex`).

## Final section map (as written in `atc_paper.tex`)

1. **Introduction** — D1/D2/D3 framing, contributions (1)-(5).
2. **Background and Problem** — Dapper line, OTel GenAI gap, adjacent tools, four-property gap.
3. **Architecture** — span vocabulary; privacy; runtime; **§3.4 cross-boundary correlation (NEW vs original outline)**.
4. **Adapter Layer** — five strategies, lazy-import safety, Fragility-methodology footnote.
5. **Telemetry-Driven Circuit Breaker** — design, policy DSL (with Figure 2 code listing, NEW), measured activation overhead (Table 3, NEW).
6. **Microbenchmark: Per-Span Overhead** — Table 2 (per-kind p50/p95/p99/mem).
7. **Scalability Stress Test** — Table 4 (3 scenarios + in-memory baseline); honest backpressure & sync-exporter discussion.
8. **Fault-Detection Validation** — Table 5 (aggregate FDR + Wilson CIs, z-test), Table 6 (per-fault matrix, NEW), Table 7 (per-framework FDR, NEW), defensive-matcher methodology paragraph.
9. **Real-LLM End-to-End Study** — 45-run topology study; 570 spans.
10. **Discussion and Limitations** — conformance gap; blocking exporter; multi-tenant; GPU; anonymization.
11. **Threats to Validity (NEW)** — construct/internal/external validity threats articulated explicitly.
12. **Reproducibility (NEW)** — per-table commands with correct file paths.
13. **Related Work** — distributed tracing, OTel, agent observability (per-tool sentences), failure taxonomies, safety rails, circuit-breaker pattern.
14. **Conclusion** — numerical recap.

## Divergence from original outline

- **Adapter trade-off taxonomy reframed.** Originally §3 was a 2.5-page
  "Systems Trade-offs" headline section. The middleware2026 sister paper
  already covers the adapter taxonomy as its primary contribution
  (`Heterogeneous Adapters for AI-Agent Observability`), so the ATC
  paper recasts adapters as §4 (a supporting systems mechanism) and
  promotes the **telemetry-driven circuit breaker** (§5) and
  **fault-detection validation** (§8) as the load-bearing systems
  contributions.
- **§3.4 cross-boundary span correlation** is new — added to defend D2
  as a first-class problem (Round 1 cold reviewer flagged it as
  underdefended).
- **Table 3 circuit-breaker activation overhead** is new — added with a
  real measurement (+1.75µs p50) instead of the original "sub-
  microsecond" assertion.
- **Tables 6 and 7** (per-fault matrix and per-framework breakdown) are
  new — added to expose the structural result that the GenAI baselines
  miss the orchestration faults uniformly.
- **§10 Threats to Validity** and **§11 Reproducibility** are new
  sections.
- **Wilson 95% CIs and two-proportion z-test** added to the
  fault-detection results.
- **Figure 2 code listing** for the policy DSL is new.

## Evidence-to-section map (every empirical claim has a source)

| Claim | Source file |
|-------|-------------|
| p50/p95/p99 span latency, throughput, memory | `results/overhead_percentiles/overhead_percentiles.json` |
| Concurrent / long-running / export scalability | `results/scalability/scalability_summary.txt`, `scalability_table_snippet.tex` |
| Adapter LOC and strategy | source files under `src/agenttelemetry/adapters/` |
| Fault-detection rates per condition | `benchmarks/results_full.tsv` |
| Per-fault and per-framework FDR matrices | `benchmarks/results_full.tsv` (computed in-paper) |
| Multi-agent topology cost/spans | `results/multi_agent_topology_cli/summary.txt` |
| Circuit breaker mechanism | `src/agenttelemetry/runtime/circuit_breaker.py` |
| Circuit breaker activation overhead | Measured live (10,000 LLM_CALL spans, with/without 4-policy breaker) |
| Cross-boundary correlation fidelity | 45-run multi-agent topology study, 570 spans, 0 orphans |

## Overlap-avoidance notes vs sister papers

- **AIware (accepted)**: fault-detection benchmark + SWE-bench case
  study. *ATC differentiation*: ATC's primary contribution is the
  **circuit breaker** and the **per-fault/per-framework structural
  analysis**, not the benchmark itself.
- **Middleware 2026** (drafted in parallel): adapter taxonomy is the
  primary contribution. *ATC differentiation*: ATC reframes adapters as
  §4 (supporting) and leads on circuit-breaker + cross-boundary
  correlation + statistical fault-detection rigor.
- **ISSRE 2026**: Vendor conformance grades, blast-radius taxonomy.
  *ATC differentiation*: ATC measures FDR with CIs; ISSRE classifies
  vendors. Different contribution surfaces.
- **MDE 2026**: metamodel / Ecore framing. *ATC differentiation*: ATC
  reframes the same vocabulary as a *systems API* with measured
  overhead, not as a metamodel.
- **NeurIPS / ESEM / ASE / IEEE Software**: agent-failure or empirical-
  evaluation framings. *ATC differentiation*: lead with the
  circuit-breaker mechanism and the per-fault structural matrix that
  none of those papers contain.

---

## ORIGINAL OUTLINE (preserved for reference; superseded by final section map above)

## Section map

1. **Introduction** (1.25 pp)
   - Hook: production LLM agent systems fail in ways the host's existing
     tracing infrastructure cannot see.
   - Concrete failure example: 84/112 SWE-bench Lite agent runs exhaust
     iteration budget with no span-level evidence of why (from the
     existing AIware paper case study).
   - The systems problem: heterogeneous frameworks (LangChain, CrewAI,
     AutoGen, Anthropic SDK, OpenAI SDK, LlamaIndex, custom) expose
     incompatible instrumentation surfaces; OTel GenAI semconv covers LLM
     calls but not agent-orchestration phases; passive tracing alone
     cannot enforce runtime policies (cost, loop, delegation cycle).
   - Contributions (numbered): (a) systems trade-off analysis of five
     adapter-binding strategies across seven frameworks; (b) nine-kind
     span vocabulary extending OTel GenAI semconv; (c) telemetry-driven
     runtime circuit breaker mechanism; (d) overhead, scalability, and
     fault-detection measurements on real and synthetic workloads; (e)
     open-source artifact with reproducibility commands.

2. **Background and problem statement** (1.0 pp)
   - OTel data model: spans, span links, attributes, processors, exporters
     (cite Dapper, Canopy, OTel specs).
   - GenAI semconv state: covers LLM invocation and tool exec; doesn't
     cover planning, reasoning, delegation, guardrail, memory.
   - Heterogeneous-framework problem: every framework exposes a different
     hook surface.
   - Production observability needs that no existing tool fills: detect
     agent loops, attribute cost to decisions, surface circular
     delegation in real time.

3. **Systems Trade-offs** (2.5 pp) -- the *headline* systems section
   - 3.1 Adapter binding strategies: callback vs hook vs monkey-patch vs
     span-handler vs context-manager.
     - Table comparing strategy, framework, LOC, fragility,
       async-correctness, lazy-import safety.
   - 3.2 Span correlation across async/multi-process boundaries: how to
     thread OTel context across asyncio, subprocesses, and inter-agent
     RPC; trade-offs we evaluated and the one we shipped.
   - 3.3 Privacy as a systems constraint: three-level capture (NONE /
     METADATA_ONLY / FULL); how `filter_attributes` is composed with
     SpanProcessors; trade-off between defense-in-depth and audit value.
   - 3.4 Lazy-import safety: every adapter imports its framework only at
     `instrument()` time; the importance of this for a single shared
     observability library that ships in agent containers with diverse
     dependency closures.

4. **Architecture** (1.75 pp)
   - Diagram: ApplicationFramework -> Adapter -> AgentTelemetry SDK ->
     SpanProcessors (Batch + CircuitBreaker) -> Exporters (OTLP/JSON/
     Console).
   - 4.1 Data model: nine span kinds, attribute namespaces, cost
     estimation hook.
   - 4.2 Runtime: `start_agent_span`, context propagation, OTel
     interoperability.
   - 4.3 Telemetry-driven circuit breaker: SpanProcessor consuming the
     same stream as the exporter; per-trace state machine; policy DSL
     (cost cap, retry cap, circular delegation, tool input repetition);
     log / callback / raise actions.

5. **Microbenchmark: span overhead** (1.25 pp)
   - Method: 10,000 iterations per span kind, Apple M4 Pro, Python 3.12,
     in-memory exporter (batch processor).
   - Table: p50 / p95 / p99 / mean per span kind (data from
     `results/overhead_percentiles/overhead_percentiles.json`).
   - Aggregate: 11.7 us p50, 13.2 us p95, 28.2 us p99, 66,396 spans/s.
   - Discussion: how this compares to OTel SDK baseline cost; what the
     additional attributes per kind cost; memory per span (3,103-3,191 B).

6. **Scalability stress test** (1.0 pp)
   - Method: 100-thread concurrency (3,482 spans), long-running 1,200-
     span single trace, 10,000-span disk-export run.
   - Numbers: 19,071 sp/s concurrent, 7.6% latency degradation over a
     long trace, 1232.4% blocking overhead for the JSON disk exporter
     (data from `results/scalability/scalability_summary.txt`).
   - Discussion: BatchSpanProcessor has no backpressure event; honest
     trade-off between sync exporter and async exporter for production.

7. **Fault-detection validation** (1.5 pp)
   - 14 fault classes mapped to 9 span kinds (see AIware coverage matrix).
   - 5 telemetry conditions: none, vanilla OTel, OTel+GenAI semconv,
     OpenInference, \sysname{} DSM.
   - 3,780-row controlled benchmark, 7 frameworks, 6 mock-LLM seeds.
   - Aggregate FDR table (numbers from `benchmarks/results_full.tsv`):
     none 0.000, vanilla 0.429, OTel+GenAI 0.429, OpenInference 0.429,
     \sysname{} 0.612 metadata / 0.612 full; conformance-complete adapter
     1.000.
   - Discussion: 0.612 is a per-app conformance issue, not a metamodel-
     expressivity issue; only the reference adapter emits the full 9-kind
     vocabulary; conformance-complete adapter detects 14/14 classes.

8. **Real-LLM end-to-end study** (0.75 pp)
   - 45-run multi-agent topology study (hierarchical/parallel/sequential x
     3 models, 5 runs each) from
     `results/multi_agent_topology_cli/summary.txt`.
   - 570 spans collected across 9 kinds.
   - Discussion: the span vocabulary correctly captures the structural
     differences between topologies; cost attribution matches receipts
     within 1%.

9. **Discussion, limitations, related work** (0.75 pp)
   - Related: Dapper, Canopy, Pivot Tracing, OTel, OTel GenAI semconv,
     OpenInference, AgentOps, MAST, AgentDebug, LangSmith, Langfuse,
     OpenLLMetry, GuardAgent, NeMo Guardrails.
   - Limitations: per-app conformance gap; blocking JSON exporter; no
     multi-tenant isolation evaluation; no GPU-side tracing.

10. **Conclusion** (0.25 pp)
    - Recap the systems claim: a uniform observability layer for
      heterogeneous LLM agent systems, with measured overhead and a
      runtime control mechanism, validated end-to-end.

## Evidence-to-section map (every empirical claim has a source)

| Claim | Source file |
|-------|-------------|
| p50/p95/p99 span latency, throughput, memory | `results/overhead_percentiles/overhead_percentiles.json` |
| Concurrent / long-running / export scalability | `results/scalability/scalability_summary.txt`, `scalability_table_snippet.tex` |
| Adapter LOC and strategy | source files under `src/agenttelemetry/adapters/` |
| Fault-detection rates per condition | `benchmarks/results_full.tsv` |
| Coverage matrix per app | `paper/mde2026/coverage_matrix.md` (cross-referenced) |
| Multi-agent topology cost/spans | `results/multi_agent_topology_cli/summary.txt` |
| Real-LLM overhead per question | `results/real_llm/tables/table_e_overhead.json` |
| Circuit breaker mechanism | `src/agenttelemetry/runtime/circuit_breaker.py` |

## Overlap-avoidance notes vs sister papers

- **AIware (accepted)**: fault-detection benchmark + SWE-bench case
  study. *ATC overlap risk*: shares the 3,780-row benchmark.
  *Differentiation*: ATC frames the benchmark as **validation of a
  systems mechanism**, not as the contribution. ATC's primary
  contribution is the **adapter trade-off taxonomy, span correlation
  mechanism, and circuit breaker** -- none of which appear as
  contributions in the AIware paper.
- **MDE 2026**: metamodel / Ecore framing. *ATC overlap risk*: shares
  span-kind taxonomy. *Differentiation*: ATC reframes the same vocabulary
  as a *systems API* with measured overhead, not as an Ecore metamodel.
- **NeurIPS / ESEM / ASE / IEEE Software**: agent-failure or empirical-
  evaluation framings. *ATC differentiation*: lead with the systems
  trade-offs section that none of those papers contain.
- **Middleware 2026** (drafted in parallel): no `paper/middleware2026/`
  contents on disk yet. *Risk*: cannot inspect to dedupe. *Mitigation*:
  the ATC paper's headline novelty is (a) the **adapter-binding strategy
  taxonomy** (callback/hook/monkey-patch/span-handler/manual), and (b) the
  **telemetry-driven circuit breaker** as a SpanProcessor that turns
  passive observability into active runtime control. If the middleware
  paper later turns out to use either framing, this section can be
  re-cast to lead on overhead + scalability + correlation only. A note
  has been left in `format_choice.md` for the reviewer.
