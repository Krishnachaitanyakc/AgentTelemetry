# Format Choice — ATC 2026

## Decision: LONG (12 pages, references and appendices excluded)

## Reasoning

ATC 2026 accepts either Long (12p) or Short (6p) papers. We choose **Long**.

### Why not Short?

A short paper would force one sharp claim and a single experimental result.
We have multiple load-bearing systems claims that each require their own
evidence section:

1. The **adapter-strategy taxonomy** (callback vs hook vs monkey-patch vs
   span-handler vs manual context-manager) is a systems contribution with
   trade-offs that must be shown across all seven framework adapters; this
   alone needs roughly 2 pages.
2. The **micro-benchmark** (p50/p95/p99 per span kind, throughput, memory
   per span) needs its own table and discussion; cutting it makes the
   "production-scale" claim unfalsifiable.
3. The **scalability stress test** (100-thread concurrency, long-running
   trace stability, blocking exporter overhead) is the strongest systems
   evidence and must be reported in full.
4. The **fault-detection benchmark** (3,780-row controlled study across 5
   telemetry conditions, 14 fault classes, 7 frameworks, 6 mock LLMs) is
   the validation that the systems mechanism actually surfaces real failure
   modes; compressing it to a single number would forfeit the comparison
   against OTel GenAI, OpenInference, and OpenLLMetry.
5. The **telemetry-driven circuit breaker** is the runtime mechanism that
   distinguishes the system from passive tracing tools and from
   schema-only proposals; it needs its own section with the policy model
   and a measurement of activation overhead.
6. The **real-LLM end-to-end study** (13 models, multi-agent topologies)
   provides the external-validity bridge ATC reviewers expect.

Compressing any of these to fit 6 pages would push the paper into the
"interesting idea, evidence too thin" reject zone — the most common ATC
short-paper failure mode.

### Why Long is the right call (not over-reach)

ATC's Long format is specifically for systems papers with multiple
mechanisms, multiple workloads, and a measurement suite that justifies the
page count. AgentTelemetry has all three. The repo backs the page count
with hard data: 3,780-row benchmark TSV, 90,000-iteration span-latency
microbenchmark, 13,000-row real-LLM run set, scalability stress tests,
seven adapter implementations with documented strategy choices, and a
runtime circuit-breaker module. There is no padding required to reach 12
pages and no overflow risk past it.

### Anticipated PC objection: "this is an application paper"

A short paper makes this objection more likely, not less. The Long format
gives room for a dedicated **Systems Trade-offs** section (§3) that
foregrounds the adapter design choices and the cross-framework span
correlation problem as systems problems — exactly the framing ATC
reviewers reward. Cutting that section to fit a 6-page budget is the
fastest path to a reject.

## Page Budget (target)

| Section | Pages |
|---------|-------|
| Abstract + Introduction | 1.25 |
| Background and problem statement | 1.0 |
| Systems trade-offs (adapter strategies, span correlation, privacy) | 2.5 |
| Architecture (data model, runtime, exporter, circuit breaker) | 1.75 |
| Microbenchmark (overhead, memory, throughput) | 1.25 |
| Scalability stress test | 1.0 |
| Fault-detection validation | 1.5 |
| Real-LLM end-to-end study | 0.75 |
| Discussion, limitations, related work | 0.75 |
| Conclusion | 0.25 |
| **Total (text)** | **12.0** |
| References | (excluded from limit) |

Conference template: `acmart` class with `[sigconf,anonymous,review]` for
double-blind submission. Switch to `[sigconf]` (drop anonymous/review) for
camera-ready.
