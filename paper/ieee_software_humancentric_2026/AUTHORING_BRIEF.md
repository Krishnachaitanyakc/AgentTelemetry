# AUTHORING_BRIEF.md — IEEE Software "Human-Centric AI for Software Engineering" SI

**Date created:** 2026-05-17
**Target directory:** `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_humancentric_2026/`
**Origin:** Dispatched from `paper/ieee_software_edgecloud_2026/RESOLUTION_DECISION.md` (Option C resolution to the IEEE-Software-Edge-Cloud overlap).

This document is the contract for the authoring sub-agent that will write this paper.

---

## 0. Mission

Write a complete, submission-ready IEEE Software feature article for the **Human-Centric AI for Software Engineering** Special Issue (deadline 2026-09-07), distinct from the existing `paper/ieee_software_2026/` draft, using AgentTelemetry's experimental corpora that are NOT used by the existing draft, and iterate it through the cold-review loop until a fresh cold reviewer returns PASS.

---

## 1. Verified target venue (do not re-verify these — they are pinned ground truth)

- **Magazine:** IEEE Software
- **Special Issue:** Human-Centric AI for Software Engineering
- **CFP URL:** `https://www.computer.org/digital-library/magazines/so/cfp-human-centric-ai`
- **Submission deadline:** 2026-09-07 (timezone not stated on CFP; treat as 11:59 PM AoE; confirm with editors before any near-deadline submission)
- **Expected publication:** May/June 2027
- **Guest editors:** Sílvia Abrahão (UPV, Spain), Kelly Blincoe (Auckland, NZ), Emerson Murphy-Hill (Microsoft, USA), Nachiappan Nagappan (Meta, USA)
- **Submission portal:** IEEE Author Portal (link from CFP)
- **Article type:** Feature article
- **Word/page convention:** IEEE Software feature article ≈ 5,000–6,000 words ≈ 6–8 pages in IEEEtran journal class. Verify final formatting against IEEE Software's current author guide before submission. **Do this verification by WebFetch yourself in the first step of the authoring task.**
- **Blind policy:** Single-blind (IEEE Software default; verify in author guide).
- **Author byline:** Krishna Chaitanya Balusu, Independent Researcher, krishnabkc15@gmail.com. NEVER name Meta, OpsMate, or any specific employer in the paper body. Per the user's pinned memory rule "never de-anonymize the paper," no Meta-internal connections, case studies, or system names may appear in the manuscript regardless of single-blind policy.
- **Submission rule from CFP:** "Manuscripts should not be published or currently submitted for publication elsewhere." Compliant by construction since this is a single submission to one SI.

**Verified scope topics (from CFP fetched 2026-05-17):** Explainable, interpretable, and transparent AI for developers, operators, and end users; Human-in-the-loop and human-AI collaborative development tools; Governance, safety, trust, accountability, and ethical alignment in AI-augmented systems; AI-assisted requirements, design, testing, and maintenance; Participatory design, co-creation, and multi-stakeholder collaboration; Empirical studies and workforce development in human-centric AI engineering.

---

## 2. What this paper MUST NOT do — overlap-avoidance rules

The existing `paper/ieee_software_2026/ieee_software_paper.tex` is a separate IEEE Software submission to the Edge-Cloud Continuum SI. **This new paper must be topically and empirically distinct** — different research question, different empirical corpus, different framing, different lessons. The Human-Centric SI editorial team is disjoint from the Edge-Cloud editorial team, so there is no double-submission concern; but reviewer-pool overlap at the magazine level is possible, so the two papers must be defensibly distinct on inspection.

**Forbidden overlap:**
- Do NOT use the `swebench_n60_*` or `swebench_n60_v2_*` corpora as the primary empirical contribution. The existing draft uses all 960 of those runs. You may cite the existing draft's published finding in passing (as prior work) but you may not re-analyze the same SWE-bench data.
- Do NOT frame this paper around the closed-loop intervention replication. That is the existing draft's contribution.
- Do NOT frame this paper around the edge-cloud continuum. That is the existing draft's framing.
- Do NOT use the same headline thesis ("when telemetry-derived interventions don't transfer").
- Do NOT re-use the existing draft's title-style framing about "vendor agent CLI absorption" as the primary contribution; it may appear as a cited prior finding but cannot be the new paper's contribution.

**Required distinctness markers:**
- Different empirical corpus (one or more of the 17+ unused result directories listed below).
- Different research question (about human oversight, diagnostic quality, decision support, or trust calibration — not about intervention transferability).
- Different deployment scenario (not specifically edge-cloud).
- Different audience cut of the practitioner story (developer-facing, on-call-facing, governance-facing, or auditing-facing — not AIOps-deployment-tier-facing).

---

## 3. Available unused experimental corpora

Listed at `research/AgentTelemetry/results/` as of 2026-05-17. The existing draft uses ONLY `swebench_n60_*` and `swebench_n60_v2_*`. Everything else is available.

| Corpus directory | What it contains (verify by reading) | Candidate human-centric framing |
|---|---|---|
| `circuit_breaker_demo/` | Telemetry-driven safeguard activation traces | Failure containment as a human-readable signal |
| `crewai_e2e/` | End-to-end CrewAI multi-agent runs | Multi-agent coordination visibility for human operators |
| `detector_applicability/` | Per-detector applicability across agent configurations | Which detectors actually help operators on which agent types |
| `diagnostic_quality/` | How well telemetry supports root-cause identification | **STRONG FIT** — operator diagnostic quality |
| `head_to_head/` | Compared instrumentations or detectors | Comparative operator decision support |
| `multi_agent_e2e/` | Multi-agent end-to-end traces | Cross-agent visibility for human supervisors |
| `multi_agent_topology_cli/` | Multi-agent runs across topologies | Topology-aware human comprehension |
| `openai_sdk_e2e/` | OpenAI SDK end-to-end runs | Non-CrewAI alternative for diversity |
| `overhead_percentiles/` | SDK overhead at p50/p95/p99 | Cost of human-oversight instrumentation |
| `real_fpr/` | Real-LLM false-positive rates for detectors | False-alarm tax on human attention |
| `real_llm/` | Real-LLM validation runs | Operator decision support under realistic noise |
| `scalability/` | Performance at scale | Sustainability of human-oversight tooling |
| `simulated_user_study/` | Simulated operator behavior under telemetry conditions | **STRONG FIT** — direct human-centric data |
| `statistical_rigor/` | Methodology/replication scaffolding | Supporting evidence |
| `tau_bench/` | Tau-bench task runs | Alternative agent benchmark |
| `threshold_sensitivity/` | Detector threshold sensitivity sweeps | Calibration cost of operator alerts |

The authoring sub-agent's FIRST task (after fetching the CFP and IEEE Author Guide) is to inspect at least the 3 STRONG-FIT corpora (`diagnostic_quality/`, `simulated_user_study/`, `real_fpr/`) by reading the summaries / JSONs on disk, plus one or two supporting corpora, and propose a thesis. Record the thesis in `OUTLINE.md` before drafting.

---

## 4. Recommended thesis (proposal — sub-agent may refine after inspecting the corpora)

**Working title (sub-agent may revise after thesis refinement):** *"Calibrating the False-Positive Tax: How Detector Quality Shapes the On-Call Engineer's Diagnostic Latency for Autonomous AI Agents"*

**Working thesis:** Observability primitives for autonomous AI agents shift human-oversight cost via two compounding axes — (a) detector false-positive rate (FPR), which determines the alert tax the on-call engineer pays per agent-hour, and (b) diagnostic quality, which determines how long root-cause identification takes when an alert fires. We characterize the FPR/diagnostic-quality Pareto frontier across {N} detector configurations on the real-LLM trace corpus, and quantify the implied operator decision-time cost using the simulated user-study data. The deployment lesson for AI-augmented software engineering teams: instrumentation choices that look identical on a single quality metric (precision, recall, or accuracy) can differ by an order of magnitude in actual human decision-latency cost.

**Why this thesis fits the SI:**
- Directly hits "human-in-the-loop and human-AI collaborative development tools" (scope topic 2).
- Directly hits "governance, safety, trust, accountability" (scope topic 3) — false-positive alerts erode operator trust; FPR/diagnostic-quality calibration is a trust-engineering problem.
- Directly hits "empirical studies and workforce development" (scope topic 6) — empirical Pareto-frontier characterization with operator decision-latency implications.

**Why this thesis is NOT overlapping with the existing draft:**
- Different research question (operator decision-latency cost, not intervention transferability).
- Different empirical corpus (`real_fpr/`, `diagnostic_quality/`, `simulated_user_study/`, not the SWE-bench cells).
- Different framing (human-decision-cost calibration, not edge-cloud-deployment-tier behavior).
- Different lesson for practitioners (how to calibrate detector portfolios for operator workload, not how to validate published interventions on your model).

**If the sub-agent finds the proposed corpora do not support the thesis** (e.g., simulated_user_study/ does not actually contain operator-latency data), it must propose an alternate thesis from the available corpora and document the choice in `OUTLINE.md` with the inspected evidence. **Do not force-fit the proposed thesis to data that does not exist.**

---

## 5. Required deliverables in this directory

By submission day (2026-09-07, target internal-deadline 2026-09-01 for 6-day buffer):

1. `AUTHORING_BRIEF.md` — this file (already exists; do not modify).
2. `OUTLINE.md` — the chosen thesis, section-by-section skeleton, figure/table list, data-source verification log (which corpora are used + what is in each), risk/overlap-management section.
3. `ieee_software_humancentric_paper.tex` — full paper in IEEEtran journal class, ≤6,000 words, ≤8 pages.
4. `refs.bib` — bibliography in IEEE Software-compatible format.
5. `ieee_software_humancentric_paper.pdf` — clean compile of the above.
6. `cold_reviewer_report_2026-XX-XX.md` (round 1).
7. `cold_reviewer_report_round2_2026-XX-XX.md` (round 2).
8. `cold_reviewer_report_round3_2026-XX-XX.md` (round 3 — and so on until PASS).
9. `data_inventory.json` — machine-readable record of every corpus directory used, every summary file read, and every aggregate number cited in the paper, with file paths.
10. `data_inventory_verification_2026-XX-XX.md` — cold-reviewer-checked verification that every number in the paper's tables and abstract maps to a specific file in `data_inventory.json`.

---

## 6. Cold-review loop pattern (identical to the existing Edge-Cloud draft's process)

After every full draft revision:

1. **Dispatch a fresh cold-reviewer sub-agent.** Persona: IEEE Software Special Issue Program Committee reviewer for the Human-Centric AI for SE SI. Has read the CFP scope. Skeptical, thorough, no prior-round anchoring. Must read the current PDF in full and produce a written report with concrete line-numbered concerns.
2. **Each round uses a NEW sub-agent.** No memory of prior rounds. This prevents anchoring and produces independent verdicts.
3. **Reviewer report structure:** per-item issues categorized as MAJOR / MINOR / NIT, plus an overall verdict of PASS / REVISE / REJECT.
4. **Author revises** addressing every MAJOR item and as many MINOR items as time allows. Document each fix in the next round's review-loop entry.
5. **No iteration cap.** Continue until a fresh cold reviewer returns PASS. The existing Edge-Cloud draft took 3 rounds; this paper may take more or fewer.
6. **Per-round data-inventory verification.** Dispatch a separate verification sub-agent (read-only, narrow scope) to confirm every numeric claim in the paper maps to a specific corpus file. If any number is unsupported, the round fails and the author must add or remove the claim.

---

## 7. Verification rules (per CLAUDE.md verified-references ritual)

Every external reference in the paper (cited prior work, vendor docs, OTel specs, etc.) must be verified by the authoring agent in this session before being cited. The authoring agent must include a "Verified references:" block in the paper's bibliography section or in a companion file `bibliography_verification.md` that lists every cited URL/DOI with a one-sentence ground-truth summary of what the source actually says.

For prior work that overlaps with AgentTelemetry's author (e.g., `aiware2026` paper, the existing Edge-Cloud draft):
- Cite by third-person form ("the authors of [X] reported…")
- Disclose author overlap in a thanks-footnote, identical in structure to the existing draft's lines 25 thanks-footnote.
- Do NOT present any contribution from the cited work as this paper's own.

---

## 8. Format compliance

- IEEEtran journal class with `[journal]` option (same as existing draft).
- Target page count: 6–8 pages including references and author bio (verify against current IEEE Software author guide; if the guide specifies a different limit, follow the guide).
- Figures/tables: combined cap of 6 per IEEE Software feature article convention; verify against current author guide.
- Bibliography in IEEE numeric citation style (same as existing draft).
- Author bio: ~50 words per IEEE Software template.

**First action of the authoring sub-agent:** fetch `https://www.computer.org/digital-library/magazines/so/author-information` (or current IEEE Software author guide URL) and record verified page-limit, word-limit, and template requirements in `OUTLINE.md` before drafting any prose.

---

## 9. Disclosure to include in the manuscript

A thanks-footnote on the first page must disclose:

> "The author is concurrently submitting a separate paper to a different IEEE Software Special Issue (The Edge-Cloud Continuum, deadline July 7, 2026). The two submissions address topically distinct research questions on disjoint experimental corpora: the present paper characterizes detector-portfolio calibration costs for human operators of autonomous AI agents, while the concurrent submission replicates a previously published closed-loop intervention across model tiers. The author confirms no manuscript overlap and no double publication."

This disclosure is required for editorial transparency even though the two SIs have disjoint editorial slates. Magazines value author candor about parallel submissions.

---

## 10. Sprint calendar (target deadline 2026-09-07; aim for 2026-09-01 submission)

| Week of | Milestone |
|---|---|
| 2026-05-18 | Sub-agent dispatched; CFP + author guide verified; corpora inspected; OUTLINE.md with thesis |
| 2026-05-25 | Section 1–2 drafted; tables 1–2 generated from data |
| 2026-06-01 | Sections 3–4 drafted |
| 2026-06-08 | Sections 5–7 drafted; first full assembly + clean compile |
| 2026-06-15 | Round-1 cold reviewer + data-inventory verification |
| 2026-06-22 | Round-1 revisions; Round-2 cold reviewer |
| 2026-06-29 | Round-2 revisions |
| 2026-07-06 | Round-3 cold reviewer (parallel with user submitting the Edge-Cloud draft on 2026-07-01) |
| 2026-07-13 → 2026-08-15 | Continue cold-review loop until PASS; tighten abstract/intro; verify all cited URLs |
| 2026-08-22 | Bibliography in IEEE Software format; author bio; format-compliance check (page count, figure count, word count) |
| 2026-08-29 | Final read; user approval gate |
| 2026-09-01 | **Submit** to IEEE Author Portal; 6-day buffer to deadline |

---

## 11. What this brief is NOT asking the sub-agent to do

- NOT to write a second Edge-Cloud Continuum paper. That decision was rejected (see `paper/ieee_software_edgecloud_2026/RESOLUTION_DECISION.md`).
- NOT to modify the existing `paper/ieee_software_2026/` draft. That draft is PASS-reviewed and ships to its own SI.
- NOT to make any git commits. The user reviews and approves all commits separately.
- NOT to invent data or extrapolate from corpora not actually inspected. Every claim in the paper must be traceable to a verifiable file.
- NOT to mention Meta, OpsMate, or any employer affiliation. Independent Researcher byline only.

---

## 12. Verified references (for this brief)

- `https://www.computer.org/digital-library/magazines/so/cfp-human-centric-ai` — fetched 2026-05-17. CFP for IEEE Software SI "Human-Centric AI for Software Engineering"; deadline 7 September 2026; publication May/June 2027; guest editors Abrahão, Blincoe, Murphy-Hill, Nagappan; 6 scope topic areas as enumerated in §1; "Manuscripts should not be published or currently submitted for publication elsewhere."
- `https://www.computer.org/publications/author-resources/calls-for-papers` — fetched 2026-05-17. Confirms this is one of two AI/SE-relevant IEEE Software SIs currently open.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/ieee_software_paper.tex` — read in this session. Establishes what the existing draft says (so that this paper can be made distinct from it).
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/OUTLINE.md` — read in this session. Establishes the existing draft's thesis, methodology, corpora, and risk/overlap framework — used as a template for the analogous artifacts this new paper will produce.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/results/` — listed in this session. 17+ corpora available beyond `swebench_n60_*`; this paper draws from `real_fpr/`, `diagnostic_quality/`, `simulated_user_study/` plus supporting corpora.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_edgecloud_2026/RESOLUTION_DECISION.md` — written in this session. Establishes the Option-C decision that authorizes this new paper as a separate-SI submission rather than a same-SI parallel submission.
