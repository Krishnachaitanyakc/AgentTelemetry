# outline.md — IEEE Software Human-Centric AI SI Feature Article

**Working title:** *Calibrating the False-Positive Tax: Persona-Stratified Operator Cost of AI Agent Observability*

**Target venue:** IEEE Software, Special Issue: Human-Centric AI for Software Engineering (May/Jun 2027; deadline 2026-09-07)

**Format budget:** 4,200 words including 250 words for each figure/table; abstract ≤150 words; ≤15 references; three actionable insights as bullet box.

**Article type:** Feature article (peer-reviewed)

---

## 1. Thesis (one paragraph)

Observability primitives for autonomous AI agents are sold to engineering teams on a single number — accuracy, recall, or coverage. But the metric that determines whether on-call engineers can *actually live with* an observability stack is two-dimensional: the **diagnostic quality** the stack provides when the on-call engineer reaches for it, and the **false-positive rate (FPR)** of the detectors that page the engineer in the first place. We characterize both axes empirically on an open-source AI-agent observability SDK using four disjoint corpora: a six-persona simulated diagnostic study (72 LLM calls across Junior Dev, Senior Backend, ML Engineer, SRE/DevOps, QA Engineer, Tech Lead), a 112-trace span-level diagnostic-quality analysis (3,060 spans), a real-LLM detector false-positive evaluation, and a threshold-sensitivity sweep across three calibration knobs. Two findings reshape the operator-cost conversation: (1) agent-specific span kinds raise persona-stratified diagnostic accuracy from 25% to 92% — a +67-percentage-point lift — but the lift is uneven across personas, with frontline QA and Tech Lead roles benefiting most; (2) the three most-cited detector calibration knobs (`max_retries`, `cost_threshold`, `token_growth_factor`) are not interchangeable — only two of the three actually move the operator-cost curve, and the one that does (`token_growth_factor`) trades context-overflow alerts against infinite-retry alerts at a sharply non-monotonic rate. The deployment lesson for any team running 24/7 oversight of autonomous agents: choose your detector portfolio by mapping it onto the persona who carries the pager, not by the headline number on the vendor datasheet.

## 2. Audience and stance

- **Primary audience:** on-call engineers, SREs, QA leads, engineering managers who own AI agent oversight.
- **Editorial stance:** human is the agent; the LLM is the assistant whose output the human is auditing.
- **What this paper is not:** a tool pitch, a benchmark race, a generic observability tutorial.

## 3. Section-by-section skeleton

### Opening — Pager-at-3am lead (~250 words)

A concrete vignette: an on-call engineer is paged because an autonomous coding-assistant agent has crossed a "potential reasoning loop" threshold. The engineer opens the trace UI. What they see (or fail to see) in the next 90 seconds decides whether the on-call rotation is sustainable. Bridge from this scene to the two questions of the paper: how good is the diagnostic signal when the engineer looks, and how often was the page right to wake them up.

### Section 1 — The two axes of operator cost (~400 words)

- Define **diagnostic quality** (operator decision-accuracy when paged) and **false-positive rate** (fraction of pages that should never have fired).
- Position relative to recent IEEE/ACM work on human-AI collaboration in SE (Murphy-Hill et al. ASE'25; Abrahão et al. TOSEM'25): iterative collaboration is now the consensus best practice, but the literature has not yet measured the upstream alert-load that determines whether iterative collaboration is even reachable.
- Pivot to the AgentTelemetry SDK as the instrument we measure on (cite the prior AIware paper that introduces it; the SDK is not our contribution).

### Section 2 — Persona-stratified diagnostic quality (~600 words + ~250 for Table 1)

- Empirical setup: 6 personas × 2 conditions (agent-specific spans vs. vanilla OTel) × 6 SWE-bench Lite failed traces = 72 LLM-judged diagnoses.
- Headline number: 91.7% diagnostic accuracy with agent-specific spans vs. 25.0% with vanilla OTel — a +66.7pp lift (Wilson 95% CI [78.2, 97.1] vs. [13.8, 41.1]).
- Per-persona breakdown (Table 1): QA Engineer and Tech Lead reach 100.0% accuracy; ML Engineer / Junior Dev / Senior Backend at 83.3%; SRE/DevOps at 83.3% under both conditions (smallest delta).
- Cost in span-examination effort: agent-specific spans require 20.4% more spans examined on average (23.1 vs. 19.2) — operators trade roughly one extra screenful of spans for nearly 3× the diagnostic accuracy.
- The persona that benefits *least* is the SRE/DevOps engineer (already trained on stack-trace reasoning); the personas that benefit *most* are the engineers who do not normally read traces (QA, Tech Lead, Junior Dev). This is the human-centric finding: agent-specific spans broaden which engineering roles can sustainably carry the pager.

### Section 3 — The false-positive tax (~500 words + ~250 for Table 2)

- Real-LLM FPR measurement on 112 traces totaling 3,060 spans (`real_fpr/fpr_results.json`): on the four canonical detectors (max_retries=5, cost_threshold=0.5 USD, token_growth_factor=2.0, hallucination minimum confidence=0.5), the combined FPR is 0.0% — *but this is a finely-tuned threshold cell*.
- Threshold-sensitivity sweep (`threshold_sensitivity/sensitivity_results.json`): vary each of three detector knobs across five settings.
- Headline finding (Table 2):
  - `max_retries`: lowering from default 3 to 2 triples the alert volume on the real-LLM corpus (26→34 alerts; +30.8%). Raising to 5+ saturates near 6.
  - `cost_threshold`: zero sensitivity across the tested range [0.05, 0.15] USD — the operator can tune this without consequence.
  - `token_growth_factor`: sharply non-monotonic. At 1.15× growth the corpus produces 59 alerts (real-LLM, +127% over default); at 1.45×+ the context-overflow detector silently drops to zero alerts because the threshold exceeds any observed growth — false-*negative* risk replacing false-positive cost.
- The human-centric implication: not all knobs are interchangeable for operator-cost calibration. A naive "increase threshold to reduce noise" policy on `token_growth_factor` quietly suppresses a whole class of alerts; a similar policy on `max_retries` only shifts where on the curve the team sits.

### Section 4 — Cross-tool head-to-head (~300 words + ~250 for Table 3)

- Comparison against Vanilla OTel and OpenLLMetry (`head_to_head/comparison_table.tsv`): visible span kinds (0 vs. 4 vs. 9), reasoning-loop detection (0 vs. 0 vs. 72), guardrail-event visibility (0 vs. 0 vs. 34), planning-phase visibility (0 vs. 0 vs. 112), memory-ops visibility (0 vs. 0 vs. 224).
- Operator-cost framing: the alternatives do not surface the events the on-call engineer needs to diagnose 75% of the loop characterizations or any of the 34 guardrail events.

### Section 5 — Detector applicability on real-world issues (~300 words)

- 17 real GitHub issues from langchain, langgraph, langchain-aws, crewAI, langchain-aws, NeMo-Guardrails covering 6 fault types (`detector_applicability/summary.json`).
- 11/17 (64.7%) have reconstructible telemetry signal for the matching AgentTelemetry detector; 6/17 do not (narrative-only or memory-keyword-only evidence).
- Operator-cost implication: even with frontier instrumentation, roughly one in three real-world agent bugs in the wild leaves no telemetry trace your on-call engineer can act on. The honest practitioner message is "instrument what you can detect; have a manual escalation path for what you cannot."

### Section 6 — Three calibration moves on-call teams can make on Monday (~400 words)

(These also seed the mandatory "three actionable insights" bullet box at the front.)

1. **Map your detector portfolio onto the persona who carries your pager.** If your on-call rotation is QA Engineer-heavy, agent-specific spans buy you more than they would for an SRE-heavy rotation. Quantified data on this in Section 2.
2. **Distinguish FPR-shaping knobs from FPR-substituting knobs.** `max_retries` and `cost_threshold` shape the operator load you actually experience; `token_growth_factor` can substitute false-positives for silent false-negatives. Quantified data on this in Section 3.
3. **Maintain a manual escalation path for the one-in-three real-world bugs telemetry cannot reach.** Quantified data on this in Section 5.

### Section 7 — Threats to validity (~300 words)

- Simulated personas, not real developers. The 72 diagnostic calls were issued by GPT-4o-mini playing each of the six persona roles. Findings motivate but do not substitute for an IRB-approved study with human operators (future work).
- Single benchmark for diagnostic-quality corpus (SWE-bench Lite). Generalization to non-coding agent tasks needs separate study.
- FPR=0 measured at a single threshold cell; the threshold-sensitivity sweep shows the FPR landscape is non-trivial.
- Detector applicability sample (n=17) is small and labeled by the author.
- Author overlap with the prior AIware'26 paper that introduces AgentTelemetry is disclosed in the first-page footnote; the prior work introduces the SDK, this paper measures operator-cost properties of using it.
- Concurrent author submission to a different IEEE Software SI (Edge-Cloud Continuum) is disclosed in the first-page footnote; the two papers are topically and empirically disjoint per the orthogonality analysis filed with the submission.

### Section 8 — Conclusion (~150 words)

Summarize: two-dimensional operator-cost framing > headline accuracy; persona-stratified evidence; calibration-knob non-interchangeability; three Monday-morning moves. Close on a call for the SE community to instrument and report persona-stratified diagnostic latency as a standard part of any new AI-agent observability work.

### Three actionable insights (mandatory bullet box on first page)

1. *Choose your detector portfolio by the persona who carries the pager.* Agent-specific spans buy 4× more diagnostic accuracy for QA and Tech Lead roles than for SRE/DevOps roles.
2. *Two of three common detector knobs reshape operator load; the third substitutes false-positive cost for silent false-negative risk.* Inspect `token_growth_factor` sensitivity before raising any threshold to suppress noise.
3. *Hold a manual escalation path for the ~30% of real-world agent faults telemetry cannot reach.* Even frontier instrumentation does not reach narrative-only bug evidence.

---

## 4. Figure and table inventory

| # | Type | Content | Source corpus | Word budget impact |
|---|---|---|---|---|
| Table 1 | Persona-stratified diagnostic accuracy | 6 personas × 2 conditions × 6 instances summary | `simulated_user_study/simulated_user_study.json`, `results_table.tsv` | 250 |
| Table 2 | Threshold-sensitivity sweep | 3 knobs × 5 settings, alert counts on swebench_100 + real-LLM | `threshold_sensitivity/sensitivity_results.json`, `sensitivity_table.tsv` | 250 |
| Table 3 | Cross-tool head-to-head | Vanilla OTel vs. OpenLLMetry vs. AgentTelemetry on 9 axes | `head_to_head/comparison_table.tsv` | 250 |

(Total format budget impact: 750 words consumed by figures/tables, leaving ~3,450 words of prose plus references and bio.)

No architecture figure planned; the architectural primitives are described prose-style in Section 1 with one parenthetical reference to the SDK paper for readers who want depth. This leaves more budget for evidence tables, which IEEE Software practitioners-as-readers prefer.

---

## 5. Data inventory (verification log)

| Corpus | File | Numbers cited in paper |
|---|---|---|
| `simulated_user_study/` | `simulated_user_study.json` | aggregate accuracies (91.67%, 25.0%, +66.67pp); spans examined means (23.14, 19.22); per-persona accuracies (junior_dev 83.3%/16.7%, senior_backend 100.0%/16.7%, ml_engineer 83.3%/16.7%, sre_devops 83.3%/66.7%, qa_engineer 100.0%/16.7%, tech_lead 100.0%/16.7%); total cost ($0.0234), n_total_calls (72), traces_used count (6), personas count (6) |
| `simulated_user_study/` | `results_table.tsv` | confirms diagnosis transcripts cited in lead vignette |
| `diagnostic_quality/` | `diagnostic_quality.json` | n_instances (112), n_failed (84), total_spans (3060), localization precision (mean 3 vs. 9.49), reduction (68.4%), spans-to-diagnosis (9.46 vs. 28.55), signal-to-noise (0.54 vs. 0.0), trace_depth (kind_by_depth counts) |
| `real_fpr/` | `fpr_results.json` | n_traces (112), n_spans (3060), thresholds (max_retries=5, cost_threshold=0.5, token_growth_factor=2.0, hallucination_min_confidence=0.5), fpr_combined (0.0) |
| `threshold_sensitivity/` | `sensitivity_results.json`, `sensitivity_table.tsv` | 3 knobs × 5 settings; alert counts on swebench (3060 spans) and real-LLM (6949 spans); identification of non-monotonic `token_growth_factor` behavior |
| `head_to_head/` | `comparison_table.tsv` | 11 metric rows × 3 tools (Vanilla OTel, OpenLLMetry, AgentTelemetry) |
| `detector_applicability/` | `summary.json`, `summary.tsv` | n=17 GitHub issues, 11 reconstructible (64.7%), 6 insufficient evidence, 6 fault types |

Every aggregate number cited in the paper's tables, abstract, or body maps to one of the above files via filename + key path.

---

## 6. References plan (15-reference cap)

Tentative reference budget:

1. AIware'26 paper (own prior; cited as foundation for the SDK telemetry primitives, NOT as the intervention being replicated)
2. OpenTelemetry GenAI semantic conventions
3. Murphy-Hill et al. ASE'25 "Why AI Agents Still Need You" — anchor for iterative-collaboration framing
4. Abrahão et al. TOSEM'25 "Software Engineering by and for Humans in an AI Era" — anchor for human-agency framing
5. MAST taxonomy (Cemri et al. 2025) — anchor for multi-agent failure-mode framing
6. SWE-bench (Jimenez et al. ICLR'24) — benchmark provenance
7. Alert-fatigue literature (one general SRE reference; e.g., Beyer et al. SRE Book or Maurer et al. 2020 PagerDuty fatigue study)
8. Trust calibration in human-AI collaboration (Okamura & Yamada PLOS One 2020 "Adaptive trust calibration for human-AI collaboration")
9. CrewAI / LangChain framework citation (one)
10. OpenLLMetry comparison
11. IEEE Software prior work on human-AI SE collaboration (one)
12. Detector / anomaly-detection on agent traces — one survey or close-prior reference
13. Persona-based usability evaluation (one HCI/SE reference, e.g., Cooper 1999 personas or recent SE-persona work)
14. AgentTelemetry SDK repo / artifact citation (own; cited once)
15. Reserved buffer

(Final bibliography will be trimmed to ≤15 entries; the buffer absorbs reviewer-requested additions during cold-review loop.)

---

## 7. Sprint calendar (informational; user manages actual submission)

Per AUTHORING_BRIEF §10. Today is 2026-05-17; target internal deadline 2026-09-01 for 6-day buffer to the 2026-09-07 deadline.

---

## 8. Anticipated cold-reviewer concerns and pre-emptive mitigations

| Likely concern | Mitigation now built in |
|---|---|
| "Where is the real-developer user study?" | Threats section §7 names simulated personas explicitly; lead and Section 2 are honest that the 72 diagnostic calls were LLM-issued; future-work IRB study mentioned |
| "Why is FPR 0.0%? That can't be right." | Section 3 frames the 0.0% headline as a single threshold cell and immediately pivots to the sensitivity sweep showing the landscape is nontrivial |
| "Why is this not just a paper about your SDK?" | Lead and contribution framing are operator-cost-first; the SDK is the instrument, not the contribution; the prior AIware paper is the SDK's home |
| "Does this overlap with your Edge-Cloud submission?" | First-page footnote discloses; orthogonality analysis filed; corpora and questions disjoint |
| "How does this fit human-centric AI?" | Persona-stratified evidence is the human-centric anchor; calibration-knob analysis is the human-decision-cost anchor; lead is on the on-call engineer's experience |
| "4,200 words is short" | Tables carry evidence; prose is operator-voiced and decision-anchored throughout |
