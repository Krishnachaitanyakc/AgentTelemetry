# overlap_analysis.md — Orthogonality vs. Existing Edge-Cloud SI Draft

**Date:** 2026-05-17
**Purpose:** Convince a magazine editor (and a possibly-shared reviewer pool) that the present paper and `paper/ieee_software_2026/ieee_software_paper.tex` (the concurrent Edge-Cloud SI submission) are topically and empirically distinct, with no double-publication risk.

---

## Side-by-side comparison

| Axis | Edge-Cloud SI paper (existing, ready) | Human-Centric SI paper (this new draft) |
|---|---|---|
| **SI** | The Edge-Cloud Continuum (Mar/Apr 2027) | Human-Centric AI for Software Engineering (May/Jun 2027) |
| **Guest editors** | Taibi, Dustdar, Wang, Toosi | Abrahão, Blincoe, Murphy-Hill, Nagappan |
| **Title (working)** | When Telemetry-Driven Interventions Don't Transfer: A Cross-Tier Replication Study of Closed-Loop Agent Recovery via Vendor Agent CLIs for Edge-Cloud Deployments | Calibrating the False-Positive Tax: How Detector-Portfolio Calibration Shapes the Cost of Human Oversight for Autonomous AI Agents |
| **Audience** | AIOps practitioners selecting models across the edge-cloud continuum | On-call engineers, SREs, QA leads, engineering managers responsible for human oversight of autonomous agents |
| **Research question** | Does a published telemetry-derived intervention reproduce across model tiers and vendor CLIs? | What does it cost engineers to oversee an autonomous agent, and which detector-portfolio knobs change that cost? |
| **Headline contribution** | Cross-tier replication of one specific intervention; documents structural reasons (vendor CLI absorption) the intervention's trigger no longer fires | Persona-stratified empirical characterization of the diagnostic-quality / false-positive-rate Pareto, plus the threshold-sensitivity calibration knobs that move an on-call team along it |
| **Empirical corpora** | `swebench_n60_opus/`, `swebench_n60_sonnet/`, `swebench_n60_haiku/`, `swebench_n60_gpt55/`, `swebench_n60_v2_*/` — 960 cross-tier SWE-bench Lite runs | `simulated_user_study/` (six personas × two conditions × six instances), `diagnostic_quality/` (112 traces, 3,060 spans), `real_fpr/` (112 traces, FPR analysis), `threshold_sensitivity/` (3 knobs × 5 settings sweep on 10,009 spans across two corpora), `head_to_head/` (cross-tool comparison), `detector_applicability/` (17 real-world GitHub issues) |
| **Number of instance-runs cited** | 960 SWE-bench Lite runs | 72 simulated-persona diagnostic calls + 112 SWE-bench instances reused only for the diagnostic-quality span data (no SWE-bench Lite outcomes cited) |
| **Models named** | Opus 4.6, Sonnet 4.6, Haiku 4.5, GPT-5.5 | GPT-4o-mini (only as the persona-simulation backend; no claim about the model is the contribution) |
| **Framing** | Edge-cloud deployment tiers; vendor-CLI absorption of the agentic loop; intervention-trigger transferability | Operator decision cost; alert-fatigue tax; detector-portfolio calibration; persona-stratified diagnostic accuracy |
| **Lesson for practitioners** | Validate published interventions against your model class before adopting; expect syntactic-repetition triggers to fail | Calibrate detector thresholds against the operator-cost curve your team can sustain; track the diagnostic-quality / false-positive-rate Pareto over time; instrument persona-stratified diagnostic latency |
| **Section structure** | Replication-study form (Intro → Background → Method → Results → Vendor-CLI Black-Box → AIOps lessons → Threats → Conclusion) | Magazine form (Operator lead → Calibration-tax framing → Empirical pillars → Calibration knobs → Three operator recommendations → Threats → Conclusion) |
| **Word count** | ~6,000 (existing template) | ≤4,200 (verified IEEE Software cap) |
| **Cited prior work overlap** | AIware'26 paper (same author, cited as foundational prior) | AIware'26 paper (same author, cited only as motivating telemetry primitives, NOT as the intervention being replicated); Murphy-Hill ASE'25 (cited as motivating iterative collaboration) |
| **Reproducibility artifact** | Per-instance JSONs, harness, parser scripts for 960 runs | TSVs, JSONs, persona diagnostics, threshold sweep table, head-to-head comparison table |

---

## Why a magazine editor will be convinced

1. **Disjoint primary corpora.** The Edge-Cloud paper's entire empirical foundation is `swebench_n60_*` (960 runs). This paper does not use any `swebench_n60_*` cell results. The corpus this paper uses (simulated user study, diagnostic quality span counts, real-FPR detection runs, threshold-sensitivity sweeps, head-to-head detector comparison, detector applicability against real GitHub issues) is wholly distinct.
2. **Disjoint research questions.** "Does intervention X transfer across model tiers?" (Edge-Cloud) vs. "What does observability cost the human operator and how do calibration knobs change that cost?" (this paper). A reviewer holding both papers side-by-side will not see two views of the same finding; they will see two views of the same SDK from two different deployment perspectives — which is exactly what magazine special issues invite.
3. **Disjoint audiences.** Edge-Cloud paper speaks to AIOps engineers deciding on model selection across deployment tiers; this paper speaks to on-call engineers, QA leads, and engineering managers responsible for sustaining 24/7 oversight of autonomous agents. The "Who reads this" answer differs.
4. **Disjoint framing keywords.** Edge-Cloud paper says: continuum, replication, intervention, vendor CLI absorption, model selection. This paper says: calibration, false-positive tax, persona, diagnostic latency, alert fatigue, threshold sensitivity. Search-engine and reviewer keyword recall do not collide.
5. **Disjoint editorial pools.** Verified at `https://www.computer.org/digital-library/magazines/so/cfp-edge-cloud-continuum` and `https://www.computer.org/digital-library/magazines/so/cfp-human-centric-ai` on 2026-05-17. No personnel overlap between the two guest-editor teams.
6. **Author-overlap disclosure included in this paper's first-page footnote** (AUTHORING_BRIEF §9): magazine values author candor; the two-SI parallel-submission pattern is well precedented in IEEE Software when papers are genuinely orthogonal.

---

## Defensive language patterns

When a reviewer asks "isn't this the same as the author's Edge-Cloud paper?":

- Point to the corpus difference: 960 SWE-bench-Lite cross-tier runs (theirs) vs. simulated-user-study + diagnostic-quality + threshold-sensitivity span data (ours).
- Point to the question difference: intervention transferability (theirs) vs. operator decision cost (ours).
- Point to the lesson difference: validate before adopting (theirs) vs. calibrate to sustain (ours).
- Note that the same SDK can support both deployment-tier and operator-cost research questions; the AgentTelemetry corpus was always intended to underwrite both, and the existence of two non-overlapping result directories per topic is direct evidence of that planning.

---

## What both papers explicitly share (and how that overlap is bounded)

| Shared element | How the overlap is bounded |
|---|---|
| Cited prior work AIware'26 (same author) | Both papers cite the prior in third-person form and disclose author overlap in a first-page footnote. The Edge-Cloud paper *replicates* the intervention from the AIware paper; this paper *uses the telemetry primitives* the AIware paper introduces, but does not replicate the intervention. |
| The AgentTelemetry SDK | Both papers reference the SDK by name. Neither paper's contribution is the SDK; both papers' contributions are *empirical findings produced using the SDK*. |
| The SWE-bench benchmark | The Edge-Cloud paper uses SWE-bench Lite for outcome measurement (patch rates). This paper uses SWE-bench instances only as the source of the failed-agent traces that the diagnostic-quality and FPR corpora analyze. No SWE-bench Lite outcome (patch / no-patch) is reported in this paper. |
| The OpenTelemetry standard | Both papers cite the GenAI semantic conventions as a baseline. Neither paper's contribution is the conventions; both papers' contributions are findings about what happens when the conventions are extended (or not). |
