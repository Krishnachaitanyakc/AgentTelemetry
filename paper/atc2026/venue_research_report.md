# Venue Research Report — ATC 2026

> Compiled 2026-05-17 for the AgentTelemetry ATC submission effort.

## CRITICAL VENUE CORRECTION

The user's prompt named the target venue as "USENIX ATC 2026 (Hong Kong, Nov
16-18 2026)". Web verification shows that **USENIX has discontinued the
Annual Technical Conference**; LWN's coverage ("The end of the USENIX Annual
Technical Conference", lwn.net/Articles/1020306/) confirms ATC has been wound
down by USENIX. The conference that now matches every concrete detail the
user listed (Hong Kong, mid-November 2026, June 10 2026 paper deadline) is
the **ACM SIGOPS Annual Technical Conference (ATC 2026)**, a newly
reconstituted ATC under ACM SIGOPS sponsorship. The deadline, location, and
dates the user supplied all match the SIGOPS page exactly. This paper is
written for the SIGOPS ATC 2026 venue. If the user actually meant a
different venue, work must be re-targeted; flagging here per the workflow
rule.

References:
- https://sigops.org/s/conferences/atc/2026/index.html
- https://sigops.org/s/conferences/atc/2026/cfp.html
- https://lwn.net/Articles/1020306/ (end of USENIX ATC)
- https://en.wikipedia.org/wiki/ACM_SIGOPS_Annual_Technical_Conference (history; ATC moved from USENIX to ACM SIGOPS in 2025)

## Verified Facts

| Item | Value |
|------|-------|
| Conference | ATC 2026 (ACM SIGOPS Annual Technical Conference) |
| Location | Hyatt Hotel, Shatin, Hong Kong |
| Dates | November 15-18, 2026 (technical program 16-18) |
| Submission deadline | **June 10, 2026** (no extensions) |
| Early-rejection notifications | August 1, 2026 |
| Author-response window | August 29 -- September 2, 2026 |
| Author notification | September 18, 2026 |
| Camera-ready due | October 16, 2026 |
| Long paper page limit | **12 pages** (text/figures/tables), references and appendices excluded |
| Short paper page limit | **6 pages** (text/figures/tables), references and appendices excluded |
| Template | Official SIGPLAN LaTeX or MS Word ACM templates (acmart, sigplan option) |
| Font | 10-point Times Roman or similar on 12-point leading |
| Paper size | A4 or US letter |
| Review model | **Double-blind** |
| Submission portal | HotCRP at atc26.hotcrp.com (TBD per CFP) |
| Artifact evaluation | "Authors of accepted papers will be expected to supply electronic versions of their papers and encouraged to supply source code and raw data to help others replicate and understand their results." (encouraged, not currently described as mandatory in the CFP text) |

## Scope (verbatim from CFP)

ATC covers "all practical aspects related to computer systems" and explicitly
lists: operating systems; runtime systems; parallel and distributed systems;
storage; networking; **ML for systems and systems for ML**; security and
privacy; virtualization; software-hardware interactions; performance
evaluation and workload characterization; reliability, availability, and
scalability; energy and power management; and **bug-finding, tracing,
analyzing, and troubleshooting**. Judging criteria: novelty, significance,
interest, clarity, relevance, correctness.

The "tracing, analyzing, and troubleshooting" axis is the natural home for
AgentTelemetry; the "systems for ML" axis is the secondary fit.

## Submission Volume / Competitiveness

Per the SIGOPS history page: submissions to ATC grew from "more than 350 in
2023, nearly 490 in 2024, and over 630 in 2025". The 2026 round is therefore
expected to be a high-volume, low-acceptance venue. Acceptance rates are
not published on the 2026 site; historical USENIX ATC ran 15-25%, and the
SIGOPS-era acceptance rate is unknown. **The paper must compete against
heavy systems work.**

## What Will Get Dismissed at ATC

A senior systems PC member will dismiss the paper as "not a systems paper"
if it reads as:

1. **An application paper** about LLM agents that happens to instrument
   them. Mitigation: lead with the systems trade-offs (adapter strategies,
   span correlation across async/multi-process topologies, overhead budget,
   privacy enforcement, runtime control).
2. **A benchmark/dataset paper.** ATC has a benchmark/measurement track
   but the bar for "we measured X" is high; pure measurement papers must
   surface a counter-intuitive finding. Mitigation: keep the controlled
   benchmark as evidence, not as the contribution; frame the contribution
   as systems mechanisms validated by the benchmark.
3. **An OSS announcement.** ATC publishes systems with insight, not
   "here is our library". Mitigation: every claim is grounded in a
   measurement, and there is a clear novel mechanism (telemetry-driven
   circuit breaker) that is not present in adjacent tools (LangSmith,
   Langfuse, OpenLLMetry, OTel GenAI).
4. **Anything that hides numbers.** Mitigation: report p50/p95/p99,
   throughput, memory per span, export blocking overhead, scalability under
   concurrency, with reproducibility commands.
5. **AI-related work without a systems mechanism.** Mitigation: frame as
   tracing infrastructure that happens to target a new workload class
   (heterogeneous LLM agent frameworks), in the line of Dapper / Canopy /
   Pivot Tracing rather than in the line of agent-debugging tools.

## Representative Recent Related Work to Cite

- **Dapper** (Sigelman et al., Google TR 2010) -- canonical large-scale
  tracing system; will set the reviewer's mental model.
- **Canopy** (Kaldor et al., SOSP'17) -- end-to-end performance tracing at
  Facebook; the relevant prior art on schema-based tracing.
- **Pivot Tracing** (Mace et al., SOSP'15) -- dynamic instrumentation /
  causal aggregation; relevant for span-attribute extensibility.
- **AgentOps** (Dong et al., arXiv 2024) -- conceptual taxonomy of agent
  observability; lacks implementation/measurements.
- **MAST / AgentDebug / AgentRx** -- agent failure taxonomies; complementary
  to the span vocabulary.
- **OpenTelemetry GenAI Semantic Conventions** (in stabilisation) -- the
  status-quo baseline that AgentTelemetry's DSM extends.
- **LangSmith / Langfuse / OpenLLMetry / OpenInference** -- adjacent
  commercial/OSS tooling with closed-source schemas.

## PC-Persona Synthesis

A representative ATC 2026 PC reviewer is a senior systems researcher who
reviews 8-12 ATC submissions a year, has built or operated a large-scale
distributed system, and treats measurement quality as a first-class
acceptance gate. They will look for:

1. **Concrete systems trade-offs**, articulated in their own section, with
   evidence. (Adapter strategy taxonomy belongs here.)
2. **Performance numbers with percentiles**, not means; reported per-
   operation and at scale; with sample size, hardware spec, and
   reproducibility instructions.
3. **A figure that shows the architecture** at a level a peer could
   re-implement.
4. **A failure-mode discussion** -- what does the system do under
   backpressure, exporter outage, very long traces.
5. **A real workload** end-to-end (here: real-LLM agent topologies),
   not only synthetic micro-benchmarks.
6. **A baseline comparison** against the closest production system
   (OTel + GenAI semconv, OpenInference, OpenLLMetry).
7. **Honest limitations**: per-app coverage, blocking exporter behaviour,
   what is not yet generalised.
8. **Double-blind correctness**: no author names, no project URL that
   identifies the author, no self-citation that breaks blinding.

## Operational Notes for the Submission

- **Anonymise**: replace "AgentTelemetry" with a pseudonym (we use
  `\sysname` mapping to "AgentScope" in this draft, with a comment to
  restore the real name post-acceptance). Strip GitHub URLs and the
  authors' Zenodo DOIs; replace with "[redacted for double-blind review]".
- **Hardware disclosure**: every measurement table notes the machine
  (Apple M4 Pro, Python 3.12, OTel SDK pinned in `requirements.lock`).
- **Reproducibility**: every claim in the eval section maps to a script
  under `benchmarks/` or `results/` that produced the underlying JSON.
- **Page count**: target the long-paper limit (12 pages text). The systems
  story has enough depth to justify long-paper.
