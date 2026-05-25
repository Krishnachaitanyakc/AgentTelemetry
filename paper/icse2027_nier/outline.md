# ICSE 2027 NIER — Outline

**Working title:** *Agent Observability is Not Microservice Observability:
A Research Agenda for Telemetry That Models Open-Ended Reasoning*

**Format:** IEEE 2-column, 10pt, conference. **4 pp main + 1 pp refs.**
**Mode:** Double-anonymous; no author identification anywhere.

**Mandatory section:** "Future Plans" (per CFP).

---

## Page 1 — Title, Abstract, Introduction, Vignette

### Abstract (~180 words)
- One sentence: production LLM agents are failing in ways microservice
  observability cannot represent.
- Concrete vignette teaser: 84 of 112 coding-agent runs on SWE-bench Lite
  silently looped through reasoning steps that vanilla OpenTelemetry encoded
  as 28 undifferentiated `INTERNAL` spans.
- Vision statement: agent observability is a *cognitive-state* problem, not
  a *request/response* problem; this reframing implies a new SE research
  agenda.
- Five research questions the SE community must own.
- Emerging result hint: pilot evidence from a 9-span-kind prototype.

### Section I — Introduction (~600 words; 1 col)
- Opens with the **vignette**: a coding agent on `django__django-10914`
  issues four near-identical `search_code('FilePathField')` calls; the
  trace contains eight `INTERNAL` OTel spans with no signal that the agent
  is stuck. Maintainer sees nothing.
- The hypothesis: this is not a missing-attribute problem; it is a
  *missing-model-of-execution* problem. Microservice OTel models a server
  receiving a request and returning a response. Agents do not look like that.
- Three structural mismatches:
  1. **Open-ended action space.** A microservice has a fixed RPC surface;
     an agent's "next action" is sampled from a learned distribution over
     tools, sub-agents, internal reasoning, and memory operations.
  2. **Model-of-the-world reasoning.** A microservice has no internal
     state worth tracing; an agent maintains a (lossy, drifting) world
     model whose corruption is the *primary* failure mode.
  3. **Emergent multi-agent coordination.** Microservice tracing assumes
     a single causal call graph; agent populations exhibit cycles,
     re-entrancy, and Byzantine failure within a single application.
- Thesis: SE needs new telemetry abstractions, new fault classes, new
  conformance gates, and new failure-mode taxonomies — none of which fit
  cleanly into a `SpanKind` enum that was designed in 2010 for RPC.
- Roadmap of the paper.

---

## Page 2 — Why Microservice Observability is Insufficient + Emerging Result

### Section II — Why Microservice Observability is Insufficient (~700 words)

**A. The microservice telemetry model.** Dapper, Jaeger, Zipkin, and the
OpenTelemetry consensus model an execution as a DAG of typed spans
(`SERVER`/`CLIENT`/`INTERNAL`/`PRODUCER`/`CONSUMER`) attached to fixed
semantic-convention namespaces (HTTP, DB, RPC, messaging). The graph
structure is closed: every node corresponds to a deployed binary's RPC
boundary.

**B. The agent telemetry mismatch.** Three concrete mismatches:

1. *Span kinds are typed by transport, not by cognition.* An LLM
   reasoning step, a planning decomposition, and a guardrail decision are
   all `INTERNAL`. The vocabulary cannot express the question "where in
   the reasoning chain did the hallucination originate?"
2. *Causal edges are RPC parent/child, not state propagation.* When an
   agent updates its memory and a later step retrieves a corrupted value,
   no span edge encodes that dataflow.
3. *Aggregations are per-endpoint, not per-decision.* SLOs are
   formulated over (endpoint, status, latency) tuples; an agent fleet's
   SLO is over (task, recovery rate, cost-per-task) tuples with no
   pre-defined endpoint.

**C. The current state of "LLM observability."** A survey of the leading
GenAI observability stacks (Langfuse, LangSmith, AgentOps [Dong et al.
2024], OpenLLMetry) shows they *intercept API calls* but inherit the
microservice metamodel beneath. None defines typed cognitive span kinds.
Recent work on agent-failure taxonomies (MAST [Cemri et al. 2025],
AgentDebug [Zhu et al. 2025], Aegis [Song et al. 2025], AgentRx [Barke
et al. 2026]) characterizes *what* fails but provides no runtime telemetry
primitives for fault detection.

**D. The OTel community's response.** The OpenTelemetry GenAI SIG has
been iterating on `gen_ai.*` attributes since 2024, but the agent
orchestration phases (planning, reasoning, guardrails, delegation,
memory) remain absent from accepted semantic conventions. The
community has explicitly identified standardization fragmentation as a
gap.

### Section III — Emerging Result (~300 words)

A pilot from a recently-released open-source agent-telemetry SDK
[Anon-1, under review]:

- Deploy the SDK across 7 agent frameworks on 112 SWE-bench Lite
  instances.
- **Finding:** 84 of 112 failed runs (75%) exhibit a structural pattern —
  three or more consecutive `REASONING -> LLM_CALL -> TOOL_CALL` cycles
  with identical tool arguments — that is *only visible* once the trace
  carries a typed `REASONING` span kind. Vanilla OTel encodes the same
  84 traces as 28 undifferentiated `INTERNAL` spans each (3,060 total
  spans, no signal).
- A controlled benchmark across 14 fault classes confirms: vanilla OTel
  + OTel GenAI conventions both saturate at FDR 0.429 (6/14 detectable
  faults); the eight undetectable faults all require an agent-specific
  span kind that no existing telemetry standard provides [Anon-1].
- This finding is the *minimum viable evidence* for the vision: the gap
  is structural, not threshold-tunable, and a NIER paper cannot ignore
  it. The full benchmark is reserved for the main-track ICSE
  submission; here we use one number to motivate the agenda.

---

## Page 3 — Research Agenda (the core)

### Section IV — A Research Agenda (~900 words)

Each of five open questions names a *concrete artifact* the SE community
can build.

**RQ-1: What is the right span-kind vocabulary for agent execution?**
- Artifact: a community-curated, empirically-saturated taxonomy of
  cognitive span kinds, accepted into OTel semantic conventions.
- Sub-questions: How many kinds before saturation? Are reasoning and
  planning distinguishable in trace data? Should memory operations have a
  unified span kind or one per backend?
- Tractable starting point: open-coding study across ≥10 production
  agent frameworks; release the taxonomy as a versioned semantic
  convention proposal.

**RQ-2: How do we specify, at design time, what a correct agent trace
should look like?**
- Artifact: an expected-trace specification language analogous to
  OCL/temporal logic, but typed over cognitive span kinds.
- Why SE: this is software contracts re-imagined for stochastic
  executors.
- Sub-questions: What is the right granularity (must-contain, must-not-
  contain, must-precede)? Can specifications be inferred from successful
  traces?

**RQ-3: How do we detect agent faults that are emergent — invisible in
any single span but visible only in the trace as a whole?**
- Artifact: a benchmark of trace-level fault detectors, with ground-
  truth labels for failure modes that no single-span detector can catch
  (e.g., circular delegation, reasoning loops, planning regression,
  Byzantine sub-agent).
- Tractable starting point: extend MAST's behavioral taxonomy with
  trace-level detection signals.

**RQ-4: What are the SLOs for an autonomous agent fleet, and how do we
formulate them from telemetry?**
- Artifact: a catalog of agent-SLO patterns (recovery rate, cost-per-
  successful-task, intervention-trigger-rate, plan-regression-rate) with
  PromQL/OTel-compatible queries.
- Why this matters: production teams currently set SLOs by analogy to
  microservices, producing meaningless thresholds (mean latency, error
  rate) on a stochastic executor.

**RQ-5: How do we close the loop — from observability to runtime
intervention — without violating the principle of telemetry as side-
effect-free?**
- Artifact: a research agenda for *intervention-aware* tracing, in which
  span processors are first-class actuators (cost cutoff, model
  downgrade, plan simplification) and the trace records both the
  observation and the intervention as causally-linked events.
- Sub-questions: How do we evaluate the *counterfactual* — what would
  the agent have done without the intervention? How do we prevent
  intervention loops?

A small horizontal box: these five questions cut across at least four
ICSE-relevant areas (observability, testing, formal methods, debugging).

---

## Page 4 — Related Vision Work, Threats, Future Plans, Conclusion

### Section V — Related Vision Work (~250 words)
- Position papers on AI for SE (Devanbu, Menzies, etc.) and SE for AI
  (multiple) have laid groundwork on *quality assurance* for ML systems;
  we extend that frame to *runtime observability* of stateful agents.
- Tool/system papers (Langfuse, LangSmith, AgentOps, OpenLLMetry) ship
  point solutions but no position on what the field's *abstractions*
  should be.
- The closest prior NIER vision: position papers on observability for
  microservices in the 2010s (which themselves preceded Dapper as a
  research artifact). The agent moment is analogous; the field needs the
  same maturation arc.

### Section VI — Threats to the Vision (~150 words)
- Risk 1: the field converges on a different vocabulary (e.g., LLM-only,
  collapsing agent semantics into tool-call sequences). We argue the
  emerging result already shows this is structurally insufficient.
- Risk 2: agent frameworks consolidate to a single dominant API, making
  cross-framework abstractions unnecessary. Even one framework's traces
  exhibit all the structural mismatches.
- Risk 3: production telemetry shifts toward proprietary single-vendor
  platforms (Datadog LLM, NewRelic AI) that absorb the standard. SE
  research should pre-empt this by establishing open, typed semantics now.

### Section VII — Future Plans (~250 words, MANDATORY per CFP)
- Full ICSE Research-Track submission: a 14-fault benchmark with
  cross-framework reproduction (already partially executed in [Anon-1]).
- A multi-year community effort: propose an OTel `gen_ai.agent.*`
  semantic convention covering the five novel span kinds; coordinate
  with the OTel GenAI SIG.
- An expected-trace specification language and reference checker — a
  follow-up paper.
- A controlled human study (n ≈ 30 SE practitioners) measuring
  time-to-diagnose with vs. without typed cognitive spans.
- Release of all artifacts (anonymized for the review period) including
  the SWE-bench trace corpus, fault-injection harness, and the
  semantic-convention specification.

### Section VIII — Conclusion (~100 words)
- Microservice observability is the wrong frame for agent execution.
- The emerging result shows the gap is structural, not parameter-tunable.
- Five tractable research questions, each anchored to a concrete
  artifact, define the agenda.
- The SE community is uniquely positioned to do this work because the
  problem is fundamentally about *abstractions, conformance, and
  contracts* — not about training better models.

### Page 5 — References only (≤ 1 page, no body text)
- ~25-30 references max; will heavy-edit for fit.
- Categories: OTel/Dapper/Jaeger; agent failure taxonomies; agent
  observability tools; SE position papers on AI; OTel GenAI SIG.

---

## Anonymization plan
- Author block: `Anonymous Author(s)` (IEEEtran style).
- No GitHub URL, no Zenodo DOI, no PR number, no acknowledgements.
- Self-citation: "[Anon-1]" / "[Anon-2]" with bib entries marked
  "Anonymous, under review" or "[author elided for double-anonymous
  review]"; replace AIware citation with anonymized placeholder.
- No "we previously showed" phrasing — third-person ("Recent work [Anon-1]
  showed...").

## Length budget (4 pp IEEE 2-column 10pt)
Approximate, target ≤ 4 columns × 4 pp = 16 column-equivalents:
- Abstract: 0.4
- I Intro + vignette: 1.6
- II Why microservice OTel insufficient: 2.6
- III Emerging result: 1.2
- IV Research agenda (5 RQs): 3.6
- V Related vision work: 1.0
- VI Threats: 0.6
- VII Future Plans: 1.0
- VIII Conclusion: 0.4
- Headers, figures, tables: ~2.0
- Buffer: 1.6

Will trim aggressively after first compile.
