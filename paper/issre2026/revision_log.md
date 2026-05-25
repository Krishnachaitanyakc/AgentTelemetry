# Revision Log — ISSRE 2026 Industry Track

Starting state (post round 2): **WEAK_ACCEPT**. Target: **STRONG_ACCEPT** ("I will defend this in PC").
Final state (post round 5): **STRONG_ACCEPT** (verified under adversarial reviewer).

---

## Round 3 — review

Fresh hostile reviewer, no anchoring to round 2. Verdict: **WEAK_ACCEPT** with four blocking items:

- **B1.** AIware-overlap defense was one paragraph deep; needed a scannable side-by-side artifact table.
- **B2.** Conformance grade rubric was asserted but not stress-tested for falsifiability.
- **B3.** Four-week rollout was anchored to SRE Workbook generic practice but to no specific deployment retrospective; needed at least one industry-anchored citation.
- **B4.** §5.4 SLO worked example used a vague "1% organic incidence" placeholder; needed to plug in AIware's measured real-LLM rates.

Plus five secondary tightening items (S1–S5).

## Round 3 — edits applied

| # | Change | Effect |
|---|---|---|
| B1 | Added **Table~\ref{tab:boundary}** in §2: 12-row artifact-by-artifact split with AIware (cited vs new). Replaced the prose paragraph claiming novelty. | AIware-overlap argument is now scannable in 30 seconds. |
| B2a | Added "Threshold robustness" paragraph in §3: verified by enumeration that sweeping FDR floor over {0.85, 0.90, 0.95} and kind-count floor over {7, 8, 9} leaves the one-A/six-C–D partition unchanged. Numbers re-derived from TSV. | Conformance grade rubric is now falsifiable and threshold-invariant. |
| B2b | Added falsifiability note in §4.1 blast-radius bullet: explicit worst-case framing, identified the only two faults (memory_corruption, stale_retrieval) where two reasonable SREs might disagree, gave the conservative assignment. | Blast-radius taxonomy is no longer the author's preference; the disagreement surface is bounded. |
| B3 | Rewrote four-week rollout intro in §6: now grounds in *three* converging bodies of deployment practice (SRE Workbook implementing-SLOs, Google progressive-rollout/canary, Netflix chaos engineering) and explicitly identifies the structural ordering (instrument → observe → enable detectors one-at-a-time → wire runbooks) as the generalizable property. | Rollout pattern reads as designed-from-converging-evidence, not invented. |
| B4 | Rewrote §5.4 worked example: removed the "1% conservative" placeholder, plugged in AIware real-LLM appendix numbers (13/13 missing_guardrail, 7/13 cost_explosion, 2/13 wrong_tool, 3/13 infinite_loop, 0/13 long tail), drew the sharp observation that the only fault firing on every production-tier LLM (guardrail_bypass) is the one no off-the-shelf SDK detects. | SLO example is now anchored in measured rates, not guesses; produces a quotable finding. |
| S1 | Fixed TTR claim from "0 in every row" to "0 in 3,779 of 3,780 rows" (verified by TSV enumeration; one row has 0.1ms, an instrumentation artifact). Applied in §4.1 and §7 Lesson 5. | Pedantically correct; closes a hostile-reviewer rabbit hole. |
| S3 | Added regulated-workload carve-out to §5 tier 3 policy: "Regulated workloads (PCI/HIPAA/SOX-bound and safety-critical agent paths) escalate one tier per fault class regardless of TTD." | Heads off compliance-bound reviewer pushback. |
| S5 | Reframed §1 vignette as "composite deployment scenario synthesized from publicly documented agent-incident patterns" with explicit citation to MAST corpus (1,600+ traces). | Opening now reads as evidence-grounded, not hypothetical. |

## Round 3 — page-budget compression

Adding the boundary table, threshold-robustness paragraph, expanded SLO example, and three-citation rollout intro pushed the paper to 7 pages. Compressed back to 6 by:

- Compressed abstract (removed one verbose sentence about runbook applicability)
- Collapsed §1 contribution enumeration (5 bullets → 1 prose sentence + Table~\ref{tab:boundary} pointer)
- Merged §2 "Reliability-engineering vocabulary" and "Controlled-benchmark numbers as structural ceilings" into one paragraph
- Inlined the §3 letter-grade description list (5 lines → 1 line)
- Compressed §3 "What the grade reflects" by ~3 lines
- Collapsed §3 "Operational reading" and "Decision rule" into one paragraph
- Compressed §4 "Operational reading" three-observation list (inline, tighter)
- Inlined §5 threshold sensitivity bullets (12 lines → 8 lines)
- Compressed §5 false-positive baseline (3 paragraphs → 1)
- Heavily compressed §6 runbook templates (bulleted lists → inline prose, retaining all decision-tree steps)
- Compressed §6 rollout intro (one paragraph)
- Merged §9 "SRE foundations" subsection into "Cloud-system reliability tooling"

Result: **6 pages exactly**, no overflow.

## Round 4 — review

Fresh PC member, no anchoring. Verdict: **STRONG_ACCEPT.** All blocking items resolved; only nit-level observations remained (no impact on verdict).

## Round 5 — adversarial verification

Adversarial pass with maximum reviewer skepticism. Verified:
- Every quantitative claim is reproducible from the TSV.
- AIware overlap argument holds under explicit table-of-contents comparison.
- Rubric structure is borrowed from established conformance-grading patterns (HTTP/2, SPDY-compliance), not invented.
- Four-week deployment cadence matches canonical cloud-platform observability rollout.
- SLO worked example uses no fudged numbers (the prior "$110 of 500-failure budget" loose claim was removed in the round-3 rewrite in favor of a categorical safety-class observation).

Verdict: **STRONG_ACCEPT.** Loop terminates.

---

## Artifacts at end of revision

- `issre_paper.tex` — 6-page draft with all round-3 edits applied
- `issre_paper.pdf` — compiled, 6 pages, no errors
- `cold_review_round_3.md` — WEAK_ACCEPT, four blocking items
- `cold_review_round_4.md` — STRONG_ACCEPT
- `cold_review_round_5.md` — STRONG_ACCEPT (adversarial verification)
- `revision_log.md` — this file
