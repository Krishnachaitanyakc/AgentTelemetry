# Outline: ISSRE 2026 Industry Track

**Title (working):** *Telemetry-Driven Reliability Engineering for LLM Agent Systems: A Deployment Rubric from 3,780 Fault-Injection Runs*

**Target:** ISSRE 2026 Industry Track Full Paper, **6 pages including references**, IEEE Computer Society format.

**Stance:** This is a deployment-pattern paper, not a benchmark paper. The benchmark is the evidence base behind the rubric. AIware 2026 is cited as the source of the benchmark and toolkit; this paper's contribution is the *reliability-engineering rubric* layered on top.

---

## Page Budget (target)

| Section | Approx pages |
|---|---|
| Abstract + Introduction | 0.75 |
| §2 Background & relation to AIware | 0.5 |
| §3 Vendor conformance grades for agent SDKs | 1.0 |
| §4 Blast-radius taxonomy for the 14 fault classes | 0.75 |
| §5 Alert-threshold derivation + alert-fatigue budget | 1.0 |
| §6 Deployment integration pattern + runbook templates | 0.75 |
| §7 Lessons learned (incl. negative findings) | 0.5 |
| §8 Threats to validity | 0.25 |
| §9 Related work | 0.25 |
| §10 Conclusion | 0.15 |
| References (~25 refs, dense IEEE format) | ~0.6 |
| **Total** | **~6.0** |

Headers will be tight. Tables will be `\scriptsize` or `\footnotesize`. No CCS taxonomy (IEEE format). Single column probably required by IEEE Computer Society format — will adapt to whatever the actual template is.

---

## Detailed Section-by-Section Outline

### Abstract (~180 words)

- LLM agents fail in ways generic observability cannot detect; existing benchmarks document the *what* but not the *how to deploy*.
- We present a reliability-engineering rubric for deploying agent observability in production, derived from a 3,780-run fault-injection benchmark (14 fault classes × 6 telemetry conditions × 7 frameworks × 6 LLMs).
- Three operational artifacts: (1) per-framework conformance grades for seven SDKs (FDR range 0.500–1.000 at metadata-level instrumentation); (2) a blast-radius taxonomy of the 14 fault classes for incident triage; (3) alert-threshold tables with empirically derived false-positive bounds (3/42 false-positive rate on no-fault runs).
- Practitioner-facing: integration pattern for existing OTel+Grafana/Tempo/Datadog stacks; runbook templates; error-budget translation.
- Honest negative findings: the framework-conformance gap means production teams using off-the-shelf SDKs operate at ~57% fault coverage today.
- Open-source: rubric, conformance card, runbook templates, raw benchmark data all archived.

### §1 Introduction (~3/4 page)

- Hook: A team deploys a CrewAI-based pricing agent into production. It enters a reasoning loop, burns $400 of API credit before oncall is paged, and the postmortem reveals the telemetry stack had no concept of "reasoning step." This is not hypothetical — it is the modal failure mode our benchmark documents.
- Problem: SREs adopting LLM agents inherit a four-way reliability deficit: (a) generic OTel doesn't speak agent-language; (b) framework SDKs vary widely in observability conformance; (c) traditional fault taxonomies don't cover coordination/cognitive faults; (d) the existing observability research community has produced benchmarks but no deployment rubric.
- Prior work: AIware 2026 paper presented the AgentTelemetry benchmark and toolkit as research artifacts establishing that nine span kinds are necessary and sufficient for detecting fourteen agent fault classes [cite AIware]. This paper does not duplicate that contribution.
- Contribution of this paper:
  1. **Vendor conformance grades** — turning the per-framework FDR into a deployable SDK-selection rubric
  2. **Blast-radius taxonomy** — a triage scoring of the 14 fault classes by incident impact and detector reliability
  3. **Alert-threshold playbook** — empirical thresholds with FPR bounds an SRE can paste into their alert stack
  4. **Deployment pattern** — runbook templates and integration sequencing for adopting agent observability inside an existing reliability program
  5. **Lessons & negative findings** — including the framework-conformance gap and the alert-fatigue cost of metadata-only capture
- Audience: cloud-platform reliability teams, AIOps practitioners adopting LLM agents, vendors of agent SDKs deciding what to instrument.

### §2 Background & Relation to AIware 2026 (~1/2 page)

- One-paragraph recap of the nine agent-specific span kinds (AGENT, LLM_CALL, TOOL_CALL, PLANNING, REASONING, RETRIEVAL, GUARD_RAIL, DELEGATION, MEMORY) — cite AIware for derivation
- One-paragraph recap of the 14 fault classes and the 6 telemetry conditions (no_telemetry, vanilla_otel, otel_genai, openinference, metadata_only, full_capture) — cite AIware for taxonomy
- **Explicit boundary statement** (a short paragraph): "The benchmark data underlying this paper was presented in [AIware] as a research artifact. This paper is a separate contribution: we use the benchmark as a measurement instrument and derive deployment-time engineering artifacts (conformance grades, blast-radius scores, alert thresholds, runbook templates) that are absent from the AIware paper."
- Reliability-engineering vocabulary primer: MTTR, MTBF, error budget, SLO, blast radius, alert fatigue, conformance — establish terms the rest of the paper uses.

### §3 Vendor Conformance Grades for Agent SDKs (~1 page) — *centerpiece 1*

- **The question:** If a team chooses LangChain vs CrewAI vs AutoGen vs LlamaIndex vs OpenAI Agents SDK vs Anthropic SDK vs a hand-rolled custom adapter, how much fault coverage do they get out of the box?
- **The data:** Run the metadata_only condition on each framework × all 14 faults × all 6 LLMs. Average FDR per framework.
- **Table 1: Conformance grade card.** Columns: Framework | LOC of adapter | Span-kind coverage (X/9) | FDR | Conformance grade (A/B/C/D/F) | Remediation cost (LOC to reach A).
- Empirically derived from the TSV:
  - Custom adapter: 9/9 span kinds, FDR=1.000 → Grade A (reference)
  - Anthropic SDK, AutoGen, CrewAI, OpenAI SDK: FDR=0.571 → Grade C
  - LangChain, LlamaIndex: FDR=0.500 → Grade D
- **Why this matters operationally:** A team picking an SDK today inherits a ~43% blind spot for agent-orchestration faults. The grade card lets a vendor or platform team decide whether the remediation cost (adapter improvements) is worth it, or whether to use a hand-rolled adapter for high-reliability workloads.
- **Remediation pathway:** brief discussion — each Grade C/D framework needs N additional span kinds emitted; the missing kinds are PLANNING, REASONING, GUARD_RAIL, DELEGATION, MEMORY. We estimate adapter LOC needed per framework based on the existing AgentTelemetry adapter footprint.
- **Honest finding:** the conformance gap is not algorithmic — every framework *could* emit the missing span kinds. It is an industry-wide instrumentation deficit. This is the "lesson learned" the Industry Track explicitly invites.

### §4 Blast-Radius Taxonomy for the 14 Fault Classes (~3/4 page) — *centerpiece 2*

- **The question:** When triaging an agent incident, which faults are highest priority?
- **Approach:** Score each fault class on three dimensions (qualitative, with empirical anchors):
  - **Blast radius (S/M/L/XL)**: scope of damage if undetected — cost burn, data leakage, user-visible regression
  - **Detection reliability (Grade A/B/C)**: based on which conditions can detect it (vanilla OTel only, metadata-only required, full-capture required, or undetectable in all conditions for some frameworks)
  - **Time-to-detect class (Fast/Medium/Slow)**: based on whether detection is per-span (Fast), per-trace (Medium), or requires cross-trace correlation (Slow). NOTE: we are *not* claiming MTTR numbers from the benchmark — the `time_to_root_cause_ms` column in the released TSV is 0 because real timing was not measured. We will use qualitative classes only and disclose this clearly.
- **Table 2: Blast-radius scoring.** 14 rows × 3 columns + recommended response.
  - cost_explosion: XL blast (direct $ burn), Grade A detection, Fast → **immediate page**
  - hallucination: L blast (user-trust damage), Grade B detection (requires metadata + grounding check), Slow → **ticket, not page**
  - circular_delegation: XL blast (compounds with cost), Grade A detection on conforming frameworks, Fast → **immediate page**
  - reasoning_loop: L blast (iteration exhaustion), Grade C detection (only custom adapter today), Medium → **page only if recurring**
  - planning_failure: M blast, Grade C detection, Medium → ticket
  - guardrail_bypass: XL blast (safety/compliance), Grade C detection, Fast → **page** but only conforming frameworks detect
  - memory_corruption: L blast (silent corruption of state), Grade C detection, Slow → ticket, manual review
  - agent_misroute: M blast, Grade C detection, Fast → ticket
  - stale_retrieval: M blast (factual drift), Grade C detection, Slow → daily digest
  - tool_failure / timeout / context_overflow / wrong_tool / infinite_loop: covered well by vanilla OTel, Grade A detection
- **Operational use:** this is the table a triage runbook authors would copy and paste, modified for their cost thresholds and SLAs.

### §5 Alert-Threshold Derivation and Alert-Fatigue Budget (~1 page) — *centerpiece 3*

- **The question:** What thresholds should each detector use, and what false-positive rate does an SRE team accept?
- **Source data:** the benchmark FPR (3/42 = 0.071 on no-fault runs at metadata level) plus the threshold sensitivity sweep referenced in AIware.
- **Table 3: Alert thresholds.** Columns: Detector | Default threshold | Empirical FPR at default | Stricter threshold (lower FP) | Looser threshold (higher recall) | Recommended pager vs ticket policy.
  - infinite_retry: max_retries=3, FPR ≈ 0 organically, 4 false fires/3 models in 159 real-LLM runs (from AIware appendix) — recommend pager threshold = 4 retries to absorb stochasticity
  - cost_explosion: $0.10/task default, fully insensitive in ±50% range — recommend per-tenant policy
  - context_overflow: 1.3× growth factor default, sensitive in 1.15–1.45 range — recommend per-agent-type calibration
  - reasoning_loop: ≥4 consecutive identical REASONING→LLM_CALL cycles — recommend ticket, not page (false pos under stochastic models)
- **Alert-fatigue budget calculation.** If a team runs 10,000 agent invocations/day and the per-run FPR is 0.071 at metadata-level instrumentation, expected daily false alerts = 710. We translate this into a *cost per false alert* (engineer time, oncall page) and back into the question: *does the marginal fault coverage of metadata-level instrumentation justify the alert volume?* — answer depends on team size and SLO sensitivity; we provide a decision diagram.
- **Honest finding:** the 7.1% FPR at metadata level is a real operational cost. Teams should consider full_capture for sensitive workloads (same FPR — capture level doesn't change FPR in our data) and tier their alert policy by fault class.
- **Note on TTR/MTTR:** we deliberately do *not* report MTTR numbers — the benchmark TSV's `time_to_root_cause_ms` field is unpopulated. We instead provide qualitative time-to-detect classes (per-span, per-trace, per-window) which are structurally derivable and operationally meaningful.

### §6 Deployment Integration Pattern and Runbook Templates (~3/4 page)

- **The integration pattern.** A team with an existing OTel + Grafana Tempo / Datadog / Honeycomb stack adopts agent observability in four rollout phases:
  1. **Week 0 — Inventory:** identify which agent frameworks are in production, score them on the conformance grade card (§3), pick rollout order (highest-blast-radius workloads first)
  2. **Week 1 — Bridge:** install the AgentTelemetry adapter for each framework, route spans through existing OTLP collector, validate no regression in latency budget (overhead is <0.006% per AIware, but team should verify in their stack)
  3. **Week 2–4 — Detectors:** turn on detectors one at a time, starting with cost_explosion (Grade A, XL blast, fast) and infinite_loop (Grade A, L blast, fast); tune thresholds against §5 table; observe FPR in production traffic; gate next detector activation on FPR stability
  4. **Week 4+ — Runbooks & postmortems:** wire each enabled detector to a runbook (template provided); add agent-fault-class section to the postmortem template
- **Runbook template (one-paragraph format example for one fault class, e.g., reasoning_loop):**
  > **Detector:** ≥4 consecutive REASONING→LLM_CALL cycles within a single trace
  > **First action:** check whether the trace is from a known-buggy agent version; if yes, pin to last good version
  > **If not:** inspect REASONING span attributes for repeated patterns in the prompt fragments; if the agent is stuck on a tool that keeps returning empty results, manually inject a strategy-change hint or kill the trace
  > **Postmortem template additions:** record the loop pattern, the tool involved, the prompt fragment, the cost burn, and whether AgentTelemetry adapter conformance grade was A or below at the time of the incident
- We provide condensed templates for all 14 fault classes in the open-source release; the paper shows two as worked examples (reasoning_loop and cost_explosion).
- **Postmortem rubric additions:** one paragraph describing the fields a postmortem should add for agent incidents (fault class, detection latency class, conformance grade of the affected SDK at incident time, blast-radius score, whether alert threshold was at default).

### §7 Lessons Learned and Negative Findings (~1/2 page)

This section is the heart of the Industry Track contribution — explicitly invited by the CFP ("submissions reporting negative results, unexpected outcomes, and lessons learned").

- **Lesson 1 — The conformance gap is industry-wide.** Every off-the-shelf agent SDK we tested ships at Grade C or D today. This is not an algorithm problem; it is an instrumentation deficit. Vendors must ship richer span kinds.
- **Lesson 2 — Metadata-level instrumentation is enough for fault detection but introduces a real alert-fatigue cost.** FDR is identical at metadata and full-capture levels, but FPR is also identical (3/42 in both). Pick metadata for privacy compliance and accept the FPR cost; do not pay full-capture's privacy cost expecting better detection.
- **Lesson 3 — A controlled benchmark over-counts what you'll see in production.** The mock benchmark hits FDR=1.000 because faults are injected at rate 1.0; the AIware real-LLM appendix shows organic fault rates are dominated by missing_guardrail and cost_explosion, with most fault classes rare in production-tier models. *Implication:* fault-injection drills (chaos engineering for agents) remain necessary because passive monitoring alone won't surface rare faults often enough to validate the detection stack.
- **Lesson 4 — Span-kind coverage is the right unit of reliability investment.** Adding a single missing span kind (e.g., REASONING) to a Grade D adapter shifts it to Grade B for a specific fault class — span-kind work yields concrete, measurable coverage gains.
- **Lesson 5 — The benchmark didn't measure latency-to-detection.** The released `time_to_root_cause_ms` column is 0 — we did not instrument that signal in the benchmark harness. This is a real gap for operational deployment and is the highest-priority next benchmark work. We disclose it openly.

### §8 Threats to Validity (~1/4 page)

- **Construct.** "Conformance grade" is a derived rubric, not a vendor-sanctioned standard. The grade reflects coverage on our 14-fault taxonomy, not all possible agent failures.
- **Internal.** The benchmark uses deterministic mock LLM clients; organic rates differ (see §7 lesson 3). False-positive rate (7.1%) is from a controlled corpus; production traffic FPR may be higher or lower.
- **External.** Tested on seven frameworks and six LLM families; conformance grades may shift as vendors update SDKs. We pin against current versions (specified in artifact). No live production deployment is included; the rubric is grounded in benchmark evidence and known SRE practice, not in a measured field rollout.
- **Conclusion.** Operational claims (alert-fatigue budget, runbook applicability) are propositional — they describe *what an SRE team would do* if they adopt the rubric. They are not measured outcomes.

### §9 Related Work (~1/4 page)

- AIware 2026 paper — benchmark and toolkit source [cite]
- ISSRE 2024 Industry Track AIOps papers — Early Bird, NICSDG, Cusick & Basil — adjacent in framing (cloud-system reliability tooling) but pre-LLM-agent era
- AgentDebug, MAST — agent-failure taxonomies that complement our blast-radius scoring
- OpenLLMetry, Langfuse, LangSmith — adjacent observability tools without agent-specific span taxonomy
- Site Reliability Engineering literature [Beyer et al.] — origins of the SLO/error-budget vocabulary we adopt

### §10 Conclusion (~1/8 page)

- Adopting LLM agents in production requires a reliability-engineering rubric, not just a benchmark.
- This paper translates the AgentTelemetry benchmark into deployment-time artifacts: conformance grades, blast-radius taxonomy, alert thresholds, runbook templates.
- The conformance gap across off-the-shelf SDKs is real and remediable; vendors and platform teams have a concrete next step.
- Open-source rubric, templates, and reproduction artifacts released.

### References (~25 entries, IEEE format, ~0.6 pp)

Key references to include:
- AgentTelemetry AIware 2026 paper (DOI 10.1145/3805760.3814931)
- OpenTelemetry GenAI semantic conventions
- MAST (Cemri et al.)
- AgentDebug
- Beyer et al. (Site Reliability Engineering book — for SLO/error-budget vocabulary)
- Treynor et al. (SRE blog posts on alert fatigue / on-call burden)
- AIOps reference: Liu et al. "Roadmap towards Intelligent Operations for Reliable Cloud Computing"
- ISSRE 2024 Industry papers: Early Bird (Liu et al.), Cusick & Basil
- OpenLLMetry, Langfuse, LangSmith
- LangChain, CrewAI, AutoGen, LlamaIndex, OpenAI Agents SDK, Anthropic SDK
- SWE-bench
- AgentOps survey
- Datadog, Honeycomb, Grafana Tempo (vendor refs for the integration story)

---

## What I will NOT do

- Will not claim a production deployment at a named company
- Will not claim measured MTTR reductions (TSV doesn't support it; will use qualitative time-to-detect classes only)
- Will not claim statistical significance on intervention experiments (AIware doesn't have it at n=24)
- Will not duplicate AIware's tables verbatim — derived per-framework conformance card is new analysis, not a republished table
- Will not over-promise on conformance-fix LOC estimates — will hedge with "approximate" and cite the existing adapter LOC as the empirical anchor
