# Revision Log — IEEE Software Human-Centric AI SI Submission

**Manuscript:** `ieee_sw_humancentric_paper.tex`
**Working title:** *Calibrating the False-Positive Tax: Persona-Stratified Operator Cost of Autonomous AI Agent Observability*
**Target venue:** IEEE Software, Special Issue: Human-Centric AI for Software Engineering (deadline 2026-09-07)

---

## Round 1 (2026-05-17, morning)

**Verdict:** WEAK_ACCEPT with 4 MAJORs (M1--M4) and 7 MINORs (m1--m7).

**Edits applied (per `cold_review_round_1.md`):**

- M1: Moved simulated-persona disclosure into Section III paragraph 1 (was buried in Threats).
- M2: Added body sentence on what the AIware'26 prior paper does not measure.
- M3: Added per-detector decomposition for `token_growth_factor` rows in Table 2 caption (5/26 baseline alerts from context-overflow; drops to 0/21 at threshold 1.45).
- M4: Created `wordcount.md` artifact.
- m1, m2, m4, m5, m7: applied (Junior Dev → Junior SWE relabel; vignette tightened; `cost_threshold` range disclaimer; Poisson CIs added; `django__django-10914` instance ID added).

**Result:** WEAK_ACCEPT → ACCEPT.

---

## Round 2 (2026-05-17, midday)

**Verdict:** ACCEPT — publishable as-is. 7 NIT-level polish items (n1--n7), none conditions for acceptance.

**Edits applied (per `cold_review_round_2.md`):**

- n3: Added illustrative concrete fault examples (`langchain#3354` stale-retrieval, `crewAI#827` short-term memory loss).
- n4: Added `\section*{Acknowledgments}\noindent(Camera-ready only.)` placeholder.
- n7: Added "Author of the AgentTelemetry observability SDK (open-source, 2026)" to the author bio.

**Result:** ACCEPT confirmed.

---

## Round 3 (2026-05-17, afternoon) — Cover-candidate revision

**Verdict (Round-3 reviewer applied STRONG_ACCEPT bar):** ACCEPT (not yet STRONG_ACCEPT). Three blockers (G1--G3), three majors (G4--G6), four minors (G7--G10).

**Edits applied (per `cold_review_round_3.md`):**

### G1 (BLOCKER) — Lead vignette has no resolution

Extended the 3am pager vignette from one paragraph of set-up to two paragraphs of set-up-and-resolution: the engineer sees six failed `search_code` calls in the vanilla trace view, files "tool error — search index stale," silences the page, goes back to bed. Resolution paragraph: "the cost of that misdiagnosis is paid the next shift: the search calls were fine, but the agent was looping through reasoning steps that the vanilla view never rendered as spans. She had triaged the symptom and missed the fault." Closes with the verifiable claim that on this exact instance (`django__django-10914`), all six simulated personas reproduce the misdiagnosis under vanilla telemetry and the correct diagnosis under agent-specific telemetry.

### G2 (BLOCKER) — Insight #3 was generic SRE wisdom

Rewrote bullet #3 from "Hold a manual escalation path for the ~1-in-3 real-world agent faults telemetry cannot reach" to "Triage your real-issue backlog into telemetry-reachable and narrative-only. Tag those tickets at intake so the on-call engineer routes them to the model owner immediately — not after the detector silently fails to fire." Intake-level triage is non-obvious; the alternative (waiting for the detector to fire) is what most teams actually do.

### G3 (BLOCKER) — "Threats to validity" academic heading

Renamed Section VII from "Threats to validity" to "What we don't know yet." Magazine-voiced; content unchanged.

### G4 — Insights box bullet #1 reframed contrarian-first

Rewrote bullet #1 from "Choose your detector portfolio by the persona who carries the pager" (description-first) to "Staff the rotation by who gains, not by seniority" (contrarian operational move-first), with the numerical justification (17%→100% for QA/TL vs 67%→83% for SRE) following.

### G5 — Removed "We make two empirical contributions" academic register

Rewrote the contributions paragraph as "Two findings reshape the operator-cost conversation. First... Second..." Magazine voice; same content.

### G6 — Disclosure footnotes reframed as transparency strength

Consolidated the two `\thanks` footnotes into one, opening with "Transparency disclosures (first page, by author choice)" and numbering items (1) prior author work and (2) concurrent submission. Same content; repositioned framing.

### G7 — Section III now opens with SRE-inversion surprise

Added a one-paragraph lead to Section III: "The least intuitive number in this study is that site-reliability engineers gain the least from agent-specific instrumentation. They are the engineers most often asked to staff agent on-call rotations, and they are the persona for whom the instrumentation lift is smallest. That inversion — and what it implies for who should actually be on the rotation — is the human-centric finding of the persona study." Followed by the methodology + headline-accuracy paragraphs. Concluding paragraph also expanded with the "cheapest sustainable rotation" operational consequence.

### G8 — Conclusion close tightened to single quotable line

Added a one-line close after the iterative-collaboration framing: "Choose the portfolio for the engineer who carries the pager." Echoes the abstract refrain.

### G9 — Defined "false-positive tax" explicitly

In Section II, added the explicit definition: "We call the cumulative withdrawal the *false-positive tax*: the operator-attention cost a deployed detector portfolio imposes per unit time on the engineers carrying its pages."

### G10 — Body said "four frameworks" but data inventory listed five

Section VI now correctly names all five source frameworks (LangChain, LangGraph, langchain-aws, CrewAI, NVIDIA NeMo Guardrails).

### Additional Round-3 edits

- **Abstract** rewritten to lead with the "inverts seniority" hook; trimmed to exactly 150 words (`detex`-measured).
- **Section VI** tightened from two long paragraphs to two short paragraphs with the intake-tagging operational move. Net -90 words.
- **Section IV** `cost_threshold` paragraph tightened. Net -60 words.
- **Threats** section author-overlap paragraph removed (superseded by the reframed first-page disclosure footnote). Net -60 words.
- **Vignette** "next morning the same agent has crashed three more customer pipelines" softened to "the cost of that misdiagnosis is paid the next shift" — removes a fictional consequence-claim that exceeds what the corpus directly supports.

**Net word-count delta:** +30 words of prose growth in load-bearing places (lead resolution, Section III opener, false-positive-tax definition), -180 words of prose trim in lower-leverage places (Section VI, Section IV `cost_threshold`, redundant threats paragraph, conclusion). Net: -150 words. Final effective total: 3,421 prose + 750 tables = 4,171 words (4,200 cap; +29 margin).

---

## Round 4 (2026-05-17, evening) — STRONG_ACCEPT verification

**Verdict:** STRONG_ACCEPT.

Fresh reviewer applied cover-candidate bar checklist (all seven criteria PASS):

1. Lead opens with concrete failure scenario senior engineers at AWS/Google/Meta would recognize: PASS.
2. Three actionable insights non-obvious AND immediately actionable: PASS.
3. Two empirical findings independently surprising: PASS.
4. No academic drift: PASS.
5. First-page disclosure footnotes framed as transparency strength: PASS.
6. 5-page format used efficiently, no wasted space: PASS.
7. Orthogonality vs Edge-Cloud submission bulletproof: PASS.

**Cover-candidacy assessment:** Three independent magazine-cover hooks in five pages (the *false-positive tax* coinage; the SRE inversion; the `token_growth_factor` silent substitution). Reviewer would actively lobby co-editors for cover placement.

**Final verdict from Round 4 reviewer, verbatim:**

> This paper is in the top ~10% I would expect to see for this SI. It is a cover candidate. There are no conditions for acceptance and no revisions required. The author has hit every cover-candidate marker.

---

## Cumulative cap compliance

| Cap | Limit | Final | Status |
|---|---|---|---|
| Effective word budget | 4,200 | 4,171 | PASS |
| Abstract | 150 | 150 | PASS |
| References | 15 | 12 | PASS |
| Figures + tables | 6 | 3 | PASS |
| Pages compiled | (soft) | 5 | PASS |
| Three actionable insights box | required | present | PASS |
| Author bio + photo placeholder | required | present | PASS |
| First-page disclosure footnote | required | present (numbered, transparency-framed) | PASS |
| Orthogonality vs Edge-Cloud SI | required (no double publication) | documented (`overlap_analysis.md`) | PASS |

---

## Files produced this session

- `cold_review_round_3.md` — Round-3 ACCEPT verdict with 10 cover-candidate gaps listed
- `cold_review_round_4.md` — Round-4 STRONG_ACCEPT verdict with cover-candidacy assessment
- `ieee_sw_humancentric_paper.tex` — revised manuscript
- `ieee_sw_humancentric_paper.pdf` — compiled PDF (5 pages, 204,681 bytes)
- `wordcount.md` — updated word-count audit
- `revision_log.md` — this file
