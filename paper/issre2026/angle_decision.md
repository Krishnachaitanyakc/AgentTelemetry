# Angle Decision: ISSRE 2026 Industry Track

**Date:** 2026-05-17
**Author:** Krishna Chaitanya Balusu

---

## TL;DR

**Chosen framing:** *"Telemetry-Driven Reliability Engineering for LLM Agent Systems: An Industrial Deployment Rubric Derived from 3,780 Fault-Injection Runs"*

The paper recasts the AgentTelemetry benchmark as **the empirical backbone of a deployment-time reliability rubric** for production agent systems — a practitioner-oriented integration pattern that an SRE team can adopt on Monday morning. The benchmark is the evidence base; the contribution is the **reliability-engineering process** built on top of it: alert-threshold derivation, conformance grading of agent frameworks, blast-radius scoring of fault classes, and an error-budget translation layer that converts FDR into SLO-impact terms.

This is fundamentally distinct from the AIware 2026 paper, which presents the same data as a *fault-detection benchmark and toolkit research artifact*. Detailed overlap audit below.

---

## Why this framing wins for ISSRE Industry Track

The Industry Track explicitly values (verbatim from the CFP, see `venue_research_report.md`):

1. "work grounded in real-world systems, operational experience, or industrial practice"
2. "papers with good evaluation, honest data, new insights and practical experiences"
3. "submissions reporting negative results, unexpected outcomes, and lessons learned from real-world practice"
4. Topic: "Reliability in AI-driven and autonomic systems or AI techniques used for Reliability Engineering"

The chair pairing — **Jinyang Liu (ByteDance AIOps)** and **Sigrid Eldh (Ericsson reliability testing)** — signals reviewers steeped in deployed AIOps and industrial reliability practice. Neither will reward a research-artifact reskin. Both will reward a paper that reads like an engineering team's deployment writeup.

The whitespace is real: a scan of ISSRE 2024 Industry Track papers (Liu et al. "Early Bird"; Cusick & Basil "Global Operational Readiness Review"; Sun et al. anomaly detection; Hong et al. NICSDG) shows that **no prior ISSRE Industry Track paper has tackled LLM-agent system reliability as a discipline**. AIware is a separate community (AI-for-software-engineering); ISSRE Industry is the natural home for the deployment-pattern contribution.

---

## Why the other candidate framings were rejected

I considered three alternative framings; here is why the chosen one wins:

**(a) "From 14 fault classes to deployment-ready agent reliability requirements"** — too narrow, reads as a checklist paper. Doesn't surface the framework-conformance finding (the per-framework FDR gap), which is the most interesting deployment lesson and a near-perfect fit for the Industry Track's "lessons learned" framing.

**(b) "An industrial case study in agent fault classification"** — would require a real production deployment we cannot defensibly anchor. The author is Independent Researcher; we have benchmark evidence and SWE-bench traces but no third-party production telemetry. Going this route risks being caught overclaiming, which on the Industry Track is fatal.

**(c) Chosen: "Telemetry-driven reliability evaluation as an engineering process"** — frames the benchmark as the *measurement instrument* underpinning a deployment-time reliability program. The per-framework FDR gap (0.500–0.571 for third-party SDKs vs 1.000 for the conformance-complete reference) becomes a *vendor-grading rubric*. The fault-class matrix becomes a *blast-radius taxonomy*. The detector-threshold sensitivity sweep becomes an *alert-tuning playbook*. Every benchmark output translates into a reliability-engineering artifact.

This framing also lets us lean into the Industry Track's appetite for negative findings: the 3/42 false positives at metadata level, the per-framework conformance gap, and the gap between mock-FDR (controlled) and real-LLM organic-fault rates all become *deployment lessons* rather than weaknesses.

---

## Overlap audit vs AIware 2026 (the critical risk)

This is the single most important section. The reviewer will spend most of their energy here. If we cannot articulate a defensible boundary, the paper is a self-plagiarism reject.

### What AIware 2026 contributes

(Verified by reading `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/aiware2026/aiware_paper.tex` line-by-line.)

AIware 2026 is positioned as a **Benchmark & Dataset Track** paper. Its four explicit contributions are:

1. A fault-detection benchmark (14 faults × 5 conditions × 7 frameworks × 6 mocked LLMs = 490 fault-detection cells, 2,940 raw runs)
2. A 9×14 ablation matrix proving every span kind is necessary
3. A SWE-bench Lite case study (112 instances, +12.5pp telemetry-guided intervention)
4. A 3,700+ LOC open-source toolkit with 78 tests and seven adapters

Its scientific claim is **structural completeness**: that the 9-span-kind taxonomy is the minimal sufficient observability primitive set for the 14 fault classes. Its rhetorical position is "here is a research-grade benchmark to enable a research community."

### What this ISSRE Industry paper contributes

The ISSRE paper does **not** claim a new benchmark, new taxonomy, new toolkit, or new SWE-bench case study. It cites AIware for those.

The ISSRE paper claims four contributions AIware does not have:

1. **A reliability-engineering deployment rubric** that translates benchmark outputs into operational artifacts: (a) per-framework *conformance grades* an SRE team uses to vet vendor SDKs before adoption; (b) per-fault-class *blast-radius scores* an incident-response team uses to triage; (c) per-detector *alert thresholds* with empirically derived false-positive bounds.

2. **A reliability-metric translation layer** that maps benchmark FDR/FPR into operational metrics ISRE reviewers care about: incident-coverage SLO targets, alert-fatigue budgets, error-budget burn from undetected fault classes, and a back-of-envelope MTTR-impact analysis tied to span-kind coverage. AIware reports FDR in academic terms; this paper reports what FDR means for an oncall rotation.

3. **A deployment-integration pattern** describing how a team that already runs OpenTelemetry + Grafana/Datadog/Tempo wires the agent-specific span kinds into their existing reliability stack: instrumentation rollout order (which adapter first, why), alert-policy template, runbook template for each of the 14 fault classes, and a postmortem rubric. None of this is in AIware.

4. **Industrial lessons learned**, including negative findings: (a) the 0.5–0.6 FDR plateau across all third-party SDKs is a *vendor conformance problem* with concrete remediation cost; (b) the 3/42 false-positive rate at metadata level translates into a specific alert-fatigue cost we quantify; (c) the gap between controlled-benchmark FDR (1.000 ceiling) and organic real-LLM fault rates means production teams need *both* fault-injection drills (chaos engineering) and passive monitoring; (d) the framework-conformance gap is fixable with adapter improvements but is currently a deployment blocker for vendors that ship pre-integrated agent SDKs. These are deployment lessons. AIware does not address any of them.

### Side-by-side comparison

| Dimension | AIware 2026 | ISSRE 2026 (this paper) |
|-----------|-------------|--------------------------|
| Venue community | AI-for-software-engineering researchers | Reliability engineers / SREs |
| Primary contribution | A fault-detection benchmark | A reliability-engineering rubric |
| Centerpiece artifact | 9-span taxonomy + 14-fault benchmark + toolkit | Deployment rubric + conformance grades + alert thresholds + runbook templates |
| Use of benchmark data | Demonstrate structural completeness, ablation, SWE-bench validation | Derive operational thresholds, conformance grades, blast-radius scores |
| Page budget | 8 pp (ACM sigconf) | 6 pp (IEEE Computer Society) |
| Key new tables not in AIware | per-framework conformance grade card; per-fault blast-radius taxonomy; alert-threshold table with FPR bounds; runbook template | — |
| Key claims absent in AIware | "if you adopt SDK X, expect FDR Y" deployment guidance; alert-fatigue budget translation; error-budget burn estimation; conformance-fix cost analysis | — |
| Rhetorical posture | "Here is a research artifact for the community" | "Here is what we learned engineering for agent reliability, and a rubric your team can adopt" |

### Honest reuse

The paper **does reuse** the underlying 3,780-row benchmark data and references the toolkit. This is appropriate and disclosed:

- Section 1 (Introduction) explicitly cites AIware 2026 and states: "The benchmark data underlying the analyses in this paper was presented in [AIware 2026] as a research artifact; this paper is a separate contribution that derives a reliability-engineering rubric from that data and describes deployment patterns absent from the original work."
- Section 2 (Background) provides only a compact summary of the span taxonomy and refers readers to AIware for the derivation.
- The reliability-engineering rubric, conformance grading scheme, alert-threshold derivation, blast-radius taxonomy, runbook templates, and deployment patterns are all **new in this paper**.

This is the same data-reuse pattern that ISSRE Industry has accepted in past years for deployment retrospectives that build on prior research-track work.

### Test the reviewer would apply

"Can I, as a senior reliability engineer, point to at least one *new* artifact in this paper that I could adopt next week?"

Yes:
- The conformance grade card (Table in §3)
- The blast-radius taxonomy (Table in §4)
- The alert-threshold derivation with FPR bounds (Table in §5)
- The runbook template (Appendix or §5)

"Could I have learned this from the AIware paper alone?"

No. AIware reports FDR aggregated across frameworks (0.612) without surfacing the per-framework gap as a vendor-grading rubric. AIware reports FPR (0.071) as a benchmark-validity check, not as an alert-fatigue cost. AIware does not provide alert thresholds, runbooks, or deployment integration patterns.

### Worst-case reviewer counterargument and rebuttal

**Counterargument:** "All of this could be in the AIware paper as a 'Practical Implications' section."

**Rebuttal:** AIware is 8 pages on a Benchmark & Dataset Track; it must focus on data-artifact contributions. The deployment-pattern contribution requires its own treatment and is not in AIware. We are not splitting a single contribution to game double-submission rules — we are putting the deployment-pattern paper at the venue whose explicit mandate covers it ("Reliability in AI-driven and autonomic systems"). The two papers cite each other transparently.

---

## What we will not claim

To avoid overclaiming and to maintain trust with industrial reviewers, the paper will explicitly NOT claim:

- A production deployment at a named company (we have no such anchor)
- Real-world MTTR reductions measured in a live oncall rotation (we have no such data; the benchmark's `time_to_root_cause_ms` column is 0 in the released TSV, meaning no real timing was captured — we will not claim MTTR numbers, only span-coverage-based detection-feasibility arguments)
- Field FDR rates above the organic-fault rates documented in the AIware real-LLM appendix
- Statistical significance on the SWE-bench intervention (cited as demonstrative, p=0.53)

What we *will* claim is bounded by what the data supports: the per-framework conformance gap, the per-fault detection ceiling, the false-positive rate, the per-fault blast-radius (qualitative scoring based on which span kinds are required), and the deployment-integration patterns we derive.

---

## Decision

**Proceed** with the chosen framing. The overlap audit defends the boundary with AIware; the venue fit is strong; the reviewer-persona match is good; the contribution is real and operationally meaningful; and the deadline (July 5, 2026 AoE) is comfortably ahead of today (May 17, 2026). Move to outline.
