# RESOLUTION_DECISION.md — IEEE Software Edge-Cloud Overlap

**Date:** 2026-05-17
**Author of this decision doc:** Claude (acting agent), executing the resolution task brief from the user.
**Working directory:** `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/`
**Prior artifact:** `ieee_software_edgecloud_2026/OVERLAP_RISK.md` — stopped the original authoring task at the overlap-detection gate.

---

## 0. TL;DR

**Chosen option: C — Retarget the new paper to a different IEEE Software Special Issue: "Human-Centric AI for Software Engineering" (deadline 2026-09-07, publication May/June 2027).**

The existing `paper/ieee_software_2026/` draft (7 pages, PASS on round-3 cold review, ready for submission) keeps its Edge-Cloud Continuum SI slot. A new paper directory `paper/ieee_software_humancentric_2026/` has been primed with a complete authoring brief (`AUTHORING_BRIEF.md`) and the dispatch status has been documented (`DISPATCH_STATUS.md`); see those files for the full contract and for why the authoring sub-agent was not auto-launched in this turn (no in-session Task/Agent tool was available, and the only shell-launchable dispatch path is `/usr/local/bin/claude`, which the user's pinned memory rule forbids for Independent-Researcher-byline paper inference).

Rationale (one paragraph): Option A loses an EB-1A slot for no reason given the existing draft is finished. Option B wastes a finished PASS-reviewed asset and trades a known good outcome for a doubly-uncertain one. Option D introduces a magazine-conduct concern that could damage the existing draft's acceptance odds. Option C preserves the finished asset, opens a clean second submission with a disjoint guest-editor pool, gives 16 weeks of authoring runway, and fits AgentTelemetry's observability-as-human-oversight angle naturally without shoehorning.

---

## 1. Verified ground truth (all checked in-session 2026-05-17)

### 1.1 The existing draft is a finished, PASS-reviewed asset

- `paper/ieee_software_2026/ieee_software_paper.tex` — 7-page IEEE Software feature article, header explicitly targets "Special Issue: The Edge-Cloud Continuum", deadline 2026-07-07.
- `paper/ieee_software_2026/cold_reviewer_report_round3_2026-05-16.md` — Final verdict **PASS**. "All three Round-2 outstanding items … are present as full, substantive Threats-to-Validity paragraphs… Ready for submission."
- `paper/ieee_software_2026/ieee_software_paper.pdf` — 204 KB compiled PDF on disk.
- Contribution claim: SWE-bench Lite cross-tier replication, n=60 × 4 models × 2 harnesses = 960 runs, showing the published closed-loop intervention's trigger never fires across any cell.

### 1.2 IEEE Software currently lists exactly 2 AI/SE-relevant open SIs

Verified at `https://www.computer.org/publications/author-resources/calls-for-papers` on 2026-05-17:

| SI Title | Deadline | Publication | Guest Editors |
|---|---|---|---|
| The Edge–Cloud Continuum: Software Challenges and Innovations | **2026-07-07** | Mar/Apr 2027 | Taibi (SDU), Dustdar (TU Wien), Wang (Coovally), Toosi (Melbourne) |
| Human-Centric AI for Software Engineering | **2026-09-07** | May/Jun 2027 | Abrahão (UPV), Blincoe (Auckland), Murphy-Hill (Microsoft), Nagappan (Meta) |
| Taking Flight: Software for Small Uncrewed Aerial Systems | 2026-06-08 | Jan/Feb 2027 | — (out of scope) |

No third AI/observability/agents-themed open SI exists at IEEE Software as of today.

### 1.3 Edge-Cloud SI verbatim scope (verified directly from the CFP)

Verified at `https://www.computer.org/digital-library/magazines/so/cfp-edge-cloud-continuum` on 2026-05-17. The CFP enumerates 15 topic areas, including: Reference architectures & patterns; CI/CD and progressive delivery; Orchestration & resource management; Serverless and service meshes; Data pipelines & management; **Observability, SRE & AIOps for edge–cloud systems**; **MLOps on the continuum**; Security, privacy & trust; **Reliability & resilience**; Network-aware engineering; **Testing, verification & benchmarking for distributed edge–cloud software**; Sustainability & cost effectiveness; Developer experience & platform engineering; Domain case studies and experience reports; Intent-based management and orchestration. No per-author submission cap is stated. (The conventional magazine norm of one paper per author per SI was flagged by the OVERLAP_RISK.md author and is treated as a venue-conduct expectation in this analysis, not a written rule.)

### 1.4 Human-Centric AI for SE SI verbatim scope (verified directly from the CFP)

Verified at `https://www.computer.org/digital-library/magazines/so/cfp-human-centric-ai` on 2026-05-17. Scope includes: Explainable, interpretable, and transparent AI for developers, operators, and end users; Human-in-the-loop and human-AI collaborative development tools; Governance, safety, trust, accountability, and ethical alignment in AI-augmented systems; AI-assisted requirements, design, testing, and maintenance; Participatory design, co-creation, and multi-stakeholder collaboration; Empirical studies and workforce development in human-centric AI engineering.

This scope explicitly covers **observability-as-human-oversight** — exactly AgentTelemetry's core claim (give the on-call human the spans they need to understand what an autonomous agent did, so they can intervene). Co-editor Nachiappan Nagappan is at Meta; the user is on Meta's OpsMate team but submits as "Independent Researcher" per their byline rule, and the MEMORY-pinned rule "never de-anonymize the paper" means no Meta-internal connection appears in the paper itself.

### 1.5 Rolling-journal alternatives confirmed

- ACM TOSEM, IEEE TSE, Springer EMSE, Elsevier JSS — all accept regular submissions anytime (deadlines: none).
- JSS "Software Quality Assurance for AI" SI verified open with deadline 2026-08-31 (editors Giordano, Lenarduzzi, Kazman, Recupito).
- JSS "AI Techniques for Performance, Reliability, and Sustainability" SI verified open with deadline 2026-09-30 (editors Litoiu, Incerto, Masti, Basciani, Chow).

### 1.6 AgentTelemetry has 17+ orthogonal experiment corpora

`ls research/AgentTelemetry/results/` shows: `circuit_breaker_demo/`, `crewai_e2e/`, `detector_applicability/`, `diagnostic_quality/`, `head_to_head/`, `multi_agent_e2e/`, `multi_agent_topology_cli/`, `openai_sdk_e2e/`, `overhead_percentiles/`, `real_fpr/`, `real_llm/`, `scalability/`, `simulated_user_study/`, `statistical_rigor/`, `swebench_*`, `tau_bench/`, `threshold_sensitivity/`. The existing draft uses only the `swebench_n60_*` and `swebench_n60_v2_*` cells. Sixteen-plus other corpora are available to support a topically orthogonal second paper.

---

## 2. Option-by-option analysis

For each option: **Pros, Cons, EB-1A impact (filing Jan 2027), Runway (today 2026-05-17), Reviewer-collision risk, Effort, Verdict.**

### Option A — Cancel new paper, keep only existing draft

- **Pros:** Zero overlap, zero rework, zero authoring effort. Existing draft is PASS-reviewed and ready for 2026-07-01 submission per the OUTLINE sprint calendar. No magazine-conduct concern at all.
- **Cons:** Loses one EB-1A submission slot. The Edge-Cloud SI's 15-topic scope genuinely admits angles the existing draft does not occupy (e.g., MLOps-on-continuum, sustainability, testing/verification of cross-tier deployments) — leaving that scope unaddressed is a real opportunity cost.
- **EB-1A impact (filing Jan 2027):** Neutral. The existing draft alone yields one strong IEEE Software submission with first-decision likely Nov 2026–Jan 2027 — citeable in the petition as "Submitted" or "Accepted." Net EB-1A delta vs. baseline: 0.
- **Runway:** Existing draft uses 2026-07-07 deadline; 7 weeks remaining. No new paper to draft.
- **Reviewer collision:** Zero — only one submission to one editorial slate.
- **Effort:** Zero new effort. Confirm existing draft submission per sprint calendar.
- **Verdict:** Conservative-safe. Defensible but leaves an EB-1A slot on the table for no reason given a finished asset exists.

### Option B — Retarget existing draft to a different journal; let new paper take Edge-Cloud slot

- **Pros:** Keeps Edge-Cloud SI slot for a new paper.
- **Cons:** The existing draft was purpose-built for the Edge-Cloud SI. Title: "When Telemetry-Driven Interventions Don't Transfer: A Cross-Tier Replication Study of Closed-Loop Agent Recovery via Vendor Agent CLIs **for Edge-Cloud Deployments**." Keywords include `edge-cloud continuum`. Abstract repeatedly invokes the continuum. Section 1 opens with "The edge-cloud continuum increasingly hosts heterogeneous LLM agent deployments." Retargeting to TOSEM/EMSE/TSE requires (a) removing the edge-cloud framing, (b) rewriting from 7-page IEEE-magazine format into 25–45-page long-form journal format with deep lit review, methodology section, and threats section, (c) re-running the cold-review loop, (d) reformatting bibliography from IEEE numbered to ACM-Trans or Springer/Elsevier name-year. This is essentially writing the paper twice. Meanwhile a new Edge-Cloud paper would also need to be written from scratch with cold-review iterations. **Both papers would compete for the same 7 weeks of runway.**
- **EB-1A impact:** Worst of the four options. Risk of both papers landing lower-quality and missing decisions before the Jan 2027 filing window.
- **Runway:** 7 weeks for Edge-Cloud deadline (2026-07-07); rolling for the journal (any deadline). Net effective runway: 7 weeks for two papers vs. 7 weeks for one.
- **Reviewer collision:** Low (different venues entirely).
- **Effort:** Very high — equivalent to writing two papers in 7 weeks.
- **Verdict:** Rejected. Trades a known-good outcome for two uncertain ones.

### Option C — Retarget new paper to a different IEEE Software SI: Human-Centric AI for SE (2026-09-07)

- **Pros:**
  - Same magazine (IEEE Software), same EB-1A evidentiary value as Edge-Cloud SI.
  - **16 weeks of authoring runway** (2026-05-17 → 2026-09-07) — more than 2× the Edge-Cloud window. Permits a deeper, more cold-reviewed paper.
  - **Disjoint editorial slate.** Edge-Cloud guest editors are Taibi/Dustdar/Wang/Toosi (Europe + Melbourne + industry); Human-Centric AI editors are Abrahão/Blincoe/Murphy-Hill/Nagappan (UPV + Auckland + Microsoft + Meta). No personnel overlap, no reviewer-pool collision concern.
  - **Two distinct IEEE Software submissions on two different SIs is a published, well-precedented author pattern.** Senior researchers routinely have papers in multiple IEEE Software SIs in the same year — different SI = different editorial team = different submission queue.
  - Genuinely fits AgentTelemetry's deepest narrative: observability primitives that allow the on-call human to understand and intervene in autonomous agent behavior. Section topic "Human-in-the-loop and human-AI collaborative development tools" and "Governance, safety, trust, accountability, and ethical alignment in AI-augmented systems" both map directly onto AgentTelemetry's contribution.
  - 17+ unused experiment corpora available — `simulated_user_study/`, `diagnostic_quality/`, `head_to_head/`, `real_fpr/`, `crewai_e2e/`, `multi_agent_e2e/`, `multi_agent_topology_cli/` are all natural fits for a human-oversight framing.
- **Cons:**
  - Co-editor Nagappan is at Meta. The user works at Meta on OpsMate but submits as Independent Researcher and the MEMORY-pinned rule "never de-anonymize the paper" means no Meta connection appears in the manuscript. The single-blind policy admits author identification but the byline is Independent Researcher with `krishnabkc15@gmail.com`. Risk: Nagappan may recognize the author or the project narratively. Mitigation: nothing to do — independent-researcher byline is honest, and any recognition would be a normal part of single-blind review.
  - Human-Centric framing requires a paper genuinely about human factors / oversight, not a shoehorned re-cast. The dispatched sub-agent must select an angle from the 17+ corpora that authentically supports human-centric framing (recommended: diagnostic quality + simulated user study + real-LLM FPR, framed as "how observability primitives change what on-call humans can know and decide about autonomous agent behavior").
- **EB-1A impact:** Best — two distinct IEEE Software submissions, both decisions due before Jan 2027 filing window (Edge-Cloud Mar/Apr 2027 publication implies first decisions Nov 2026; Human-Centric May/Jun 2027 publication implies first decisions Jan 2027 — both citeable).
- **Runway:** 16 weeks (>2× Option D, well over 2× the effective runway of B).
- **Reviewer collision:** Lowest of the multi-paper options (disjoint editor pools).
- **Effort:** Same as Option D's authoring effort (one new paper from scratch + cold-review loop), but with 16 weeks instead of 7.
- **Verdict:** **CHOSEN.**

### Option D — Parallel double-submission to same Edge-Cloud SI with orthogonal angle + disclosure

- **Pros:** Maximizes Edge-Cloud-SI-specific submissions.
- **Cons:**
  - **Magazine-conduct concern.** Two papers by a single Independent Researcher author to one SI editorial team is unusual and signals over-extension. The user's own OVERLAP_RISK.md flagged this explicitly: "submitting two papers by the same author to the same Special Issue editorial team is not standard practice."
  - **Editor selection bias.** When guest editors face two papers from the same author, the default behavior is to choose one (not both) for the issue, even if both are independently acceptable on merit. This can lower BOTH papers' acceptance probability vs. the single-submission baseline.
  - **Reviewer reuse.** Same editorial slate likely uses overlapping reviewer pool. Reviewers seeing two papers from the same author may rate one lower out of fairness concern.
  - **No runway advantage.** Same 7-week deadline.
  - **Mandatory disclosure required.** Cover letter must disclose parallel submission, drawing editor attention to the unusualness.
- **EB-1A impact:** Marginally positive only if both accepted; negative if either is rejected due to the other's presence (likely scenario).
- **Runway:** 7 weeks for both papers.
- **Reviewer collision:** Highest — same editorial slate.
- **Effort:** Same as Option C authoring effort, but compressed into 7 weeks vs. 16.
- **Verdict:** Rejected. Negative-expected-value compared to Option C, with risk of damaging the finished PASS-reviewed asset's chances.

---

## 3. Decision: Option C

Retarget the new paper to **IEEE Software Special Issue: "Human-Centric AI for Software Engineering"**, deadline **2026-09-07**, expected publication May/June 2027. Guest editors Sílvia Abrahão (UPV), Kelly Blincoe (Auckland), Emerson Murphy-Hill (Microsoft), Nachiappan Nagappan (Meta).

### Why this is the strongest answer

1. **Preserves the finished asset.** The existing `ieee_software_2026/` draft (PASS on round-3 cold review) ships unchanged to the Edge-Cloud SI on or before 2026-07-07.
2. **Maximizes EB-1A submissions.** Two distinct IEEE Software submissions on disjoint editorial slates, both with first decisions arriving in time for the Jan 2027 filing window.
3. **Eliminates the magazine-conduct concern.** Two papers to two different SIs is normal and well-precedented. The OVERLAP_RISK.md concern about "same SI editorial team" does not apply.
4. **Maximizes authoring runway.** 16 weeks vs. 7 — permits a more rigorous methodology section, more cold-review iterations, and a more polished final draft.
5. **Genuinely fits AgentTelemetry's deepest contribution.** Observability primitives that enable human oversight of autonomous agents is the project's strongest narrative; the Edge-Cloud SI required a partial reframing (continuum deployment) that the Human-Centric SI does not.

---

## 4. Execution plan

### 4.1 No change to existing Edge-Cloud submission

The existing `paper/ieee_software_2026/` draft proceeds to submission on or before 2026-07-07 per its existing sprint calendar (OUTLINE.md §8: target submission 2026-07-01 with 6-day buffer). No modifications to the existing draft are made as part of this resolution.

### 4.2 New paper — IEEE Software Human-Centric AI for SE SI

Primed (not auto-dispatched): the new paper directory `paper/ieee_software_humancentric_2026/` has been created with two artifacts:
- `AUTHORING_BRIEF.md` — complete task contract for whichever agent eventually authors this paper: verified target SI, overlap-avoidance rules vs. the existing draft, available unused corpora (17+ result directories enumerated), proposed thesis with three STRONG-FIT corpora identified, cold-review loop protocol, sprint calendar (target 2026-09-01 submission for 2026-09-07 deadline), format-compliance requirements, disclosure language, and verified references.
- `DISPATCH_STATUS.md` — explains why the authoring agent was not auto-launched in this turn (no in-session subagent-dispatch tool was available; the only shell-launchable path is `/usr/local/bin/claude`, which is the Meta-routed Claude Code binary, which the user's pinned memory rule forbids for Independent-Researcher-byline paper inference). Lists three user-initiated paths to start the authoring work.

When authoring begins, the agent operates under the same author + cold-review loop pattern as the original Edge-Cloud authoring task brief:
- Round-1: full draft compiled to PDF, written cold reviewer dispatched (PC persona, no anchoring), report saved as `cold_reviewer_report_2026-XX-XX.md`.
- Round-2: revisions applied, fresh cold reviewer dispatched (no prior-round context), report saved as `cold_reviewer_report_round2_2026-XX-XX.md`.
- Round-3+: continues until a fresh cold reviewer returns PASS, with no maximum iteration cap.
- Final: submission-ready PDF + all review artifacts in `paper/ieee_software_humancentric_2026/`.

### 4.3 Edge-Cloud overlap-task disposition

The task originally scheduled to write a second paper for the Edge-Cloud SI is superseded by this decision. The `paper/ieee_software_edgecloud_2026/` directory retains:
- `OVERLAP_RISK.md` (the original stop-condition artifact)
- `RESOLUTION_DECISION.md` (this file)

The directory itself is preserved (not deleted) as the audit trail of the overlap-resolution decision. No additional artifacts (outline, tex, refs, venue research) will be created in this directory. The autonomous-run task list entry for "write Edge-Cloud paper" should be marked **superseded by Option C resolution; replaced by `paper/ieee_software_humancentric_2026/` task**.

---

## 5. What was NOT done and why

- **Did not retarget the existing draft.** Per Option B analysis, the existing draft is purpose-built for the Edge-Cloud SI and rewriting it for a long-form journal would waste a finished asset and consume the same runway as authoring a new paper.
- **Did not pick a JSS or EMSE SI for the new paper.** Option C (a second IEEE Software SI) gives the same EB-1A value with the same magazine venue family, which has stronger practitioner reach for AgentTelemetry's narrative than a niche journal SI. JSS QA-for-AI (Aug 31) and JSS AI-for-Reliability (Sep 30) remain on the venue index as future-quarter targets and are not foreclosed.
- **Did not double-submit to the same SI (Option D).** The negative-expected-value analysis above ruled it out independent of the OVERLAP_RISK.md author's concerns.
- **Did not delete the `paper/ieee_software_edgecloud_2026/` directory.** Preserved as audit trail for the resolution decision.

---

## 6. Verified references (per CLAUDE.md verified-references-block ritual)

All URLs below were fetched in this session on 2026-05-17 with WebFetch. One-sentence ground-truth summaries based on the actual page contents.

- `https://www.computer.org/digital-library/magazines/so/cfp-edge-cloud-continuum` — IEEE Software Special Issue on The Edge-Cloud Continuum: 15 scope topics including Observability/SRE/AIOps, MLOps on the continuum, Reliability & resilience, Testing/verification/benchmarking, Sustainability; deadline 7 July 2026; expected publication Mar/Apr 2027; guest editors Davide Taibi (SDU), Schahram Dustdar (TU Wien), Guodong Wang (Coovally), Adel N. Toosi (Melbourne); no per-author submission cap stated in the CFP content.
- `https://www.computer.org/digital-library/magazines/so/cfp-human-centric-ai` — IEEE Software Special Issue on Human-Centric AI for Software Engineering: scope includes explainable AI for developers/operators/end users, human-in-the-loop and human-AI collaborative development tools, governance/safety/trust/accountability, AI-assisted requirements/design/testing/maintenance, participatory design, empirical studies and workforce development; deadline 7 September 2026; expected publication May/June 2027; guest editors Sílvia Abrahão (UPV Spain), Kelly Blincoe (Auckland NZ), Emerson Murphy-Hill (Microsoft USA), Nachiappan Nagappan (Meta USA); manuscripts must not be published or currently submitted elsewhere; supporting datasets may be uploaded to IEEE DataPort.
- `https://www.computer.org/publications/author-resources/calls-for-papers` — IEEE Computer Society open CFPs page: IEEE Software currently lists three open Special Issues — Human-Centric AI for Software Engineering (Sep 7, 2026), Edge-Cloud Continuum (Jul 7, 2026), Taking Flight: Software for Small UAS (Jun 8, 2026). The page does NOT list "Engineering Agentic Systems" or "AIware FM Era" as currently open (both closed earlier in 2025/2026 per prior `paper/supporting/venues_journals_2026-05-17.md` records).
- `https://www.sciencedirect.com/journal/journal-of-systems-and-software/about/call-for-papers` — Elsevier JSS open CFPs: "Software Quality Assurance for AI" SI confirmed open with deadline 31 August 2026 (editors Giordano, Lenarduzzi, Kazman, Recupito) and "AI Techniques for Performance, Reliability, and Sustainability of Modern Software Systems" confirmed open with deadline 30 September 2026 (editors Litoiu, Incerto, Masti, Basciani, Chow); page limits not specified in either CFP body.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/ieee_software_paper.tex` — read in this session; header explicitly targets Edge-Cloud SI with 2026-07-07 deadline; title "When Telemetry-Driven Interventions Don't Transfer: A Cross-Tier Replication Study of Closed-Loop Agent Recovery via Vendor Agent CLIs for Edge-Cloud Deployments"; abstract reports 960 instance-runs, 2,991 iterations, trigger fires zero times across all eight cells; thanks-footnote already discloses author overlap with cited AIware 2026 prior work.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/cold_reviewer_report_round3_2026-05-16.md` — read in this session; final verdict PASS on round-3; all three round-2 outstanding items (M1 single-author replication, M2 no external instrumentation comparison, M3 baseline-dependent power) addressed as full Threats-to-Validity paragraphs; PDF compile clean at 7 pages 204576 bytes; "Ready for submission."
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/OUTLINE.md` — read in this session; sprint calendar lines 160–172 schedule submission for 2026-07-01 with a 6-day buffer to the 2026-07-07 deadline.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_edgecloud_2026/OVERLAP_RISK.md` — read in this session; the original authoring sub-agent stopped at the overlap-detection gate and flagged four resolution options (A/B/C/D) for user choice; this RESOLUTION_DECISION.md is the response to that gate.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/supporting/venues_journals_2026-05-17.md` — read in this session; corroborates the JSS, EMSE, IST, TOSEM rolling-journal status and listed SI deadlines; lists IEEE Software "Engineering Agentic Systems" SI as MISSED (deadline 2026-01-05).
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/supporting/additional_venues_2026-05-17.md` — read in this session; master index of 5 venue-research source reports, used to confirm no other AI/SE-relevant IEEE Software SI is currently open beyond Edge-Cloud and Human-Centric AI.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/results/` — directory listing this session; 17+ experiment corpora exist beyond the SWE-bench cells the existing draft uses, providing material for a topically orthogonal second paper.

**Could not verify in-session:** any official IEEE Software policy on per-author submission caps to a single SI. The CFP body does not state one; conventional magazine practice was treated as a venue-conduct expectation, not as a hard rule. This does not affect the Option C recommendation, which uses two different SIs anyway.
