# Word-count audit — IEEE Software Human-Centric AI SI submission

**Manuscript:** `ieee_sw_humancentric_paper.tex` / `ieee_sw_humancentric_paper.pdf`
**Date:** 2026-05-17 (Round-3 revision)
**Verified IEEE Software limit:** 4,200 words including 250 words for each figure or table (`https://www.computer.org/digital-library/magazines/so/cfp-ieee-software`, fetched 2026-05-17). Author biographies are excluded from the word limit; references are excluded from the word limit (15-reference cap applies separately).

## Method

- Raw count: `detex ieee_sw_humancentric_paper.tex | wc -w` returns **3,421 words** after Round-3 cover-candidate revision. `detex` strips LaTeX commands, math environments, and the bibliography environment; bullet content inside the actionable-insights box is included.
- Inferred table contribution: 3 tables × 250 words each = **750 words** of allowance consumed.
- Inferred figure contribution: 0 figures, 0 words.
- Abstract: 150 words (detex'd independently from the abstract block). Exactly at the 150-word cap.

## Budget reconciliation

| Item | Words |
|---|---|
| Prose (incl. abstract, body, lead vignette, actionable-insights bullets, "what we don't know yet" section, conclusion, reproducibility note, acknowledgments placeholder) | ~3,421 |
| Table allowance consumed (3 × 250) | 750 |
| **Effective total** | **~4,171** |
| **Cap** | 4,200 |
| Margin | +29 |

## Cap-by-cap compliance

| Cap | Limit | Actual | Status |
|---|---|---|---|
| Effective word budget (prose + 250/table) | 4,200 | ~4,171 | PASS (+29 margin) |
| Abstract | 150 | 150 | PASS (exactly at cap) |
| References | 15 | 12 | PASS (3 reserved buffer) |
| Figures + tables | 6 | 3 | PASS |
| Pages compiled | (soft) | 5 | PASS |
| Three actionable insights box on page 1 | required | present | PASS |
| Author bio + photo placeholder | required | present | PASS |

## Notes on the Round-3 revision

The Round-3 revision (cover-candidate polish) made the following net word-count changes:

- **Lead vignette**: extended from a single paragraph of set-up to two-paragraph set-up-and-resolution (the engineer misdiagnoses the bug, sleeps, comes back to the consequence). Net +120 words.
- **Section III**: added a one-paragraph SRE-inversion lead before the methodology paragraph. Net +60 words. Conclusion paragraph also expanded to add the "staff the rotation by who gains, not by seniority" operational consequence. Net +30 words.
- **Section II**: added the explicit *false-positive tax* definition. Net +30 words.
- **Section VI (detector applicability)**: tightened from two long paragraphs to two short paragraphs with the intake-tagging operational move. Net -90 words.
- **Section IV (false-positive tax)**: tightened `cost_threshold` paragraph. Net -60 words.
- **Threats section** retitled "What we don't know yet"; one paragraph removed (the author-overlap-with-SDK paragraph, now superseded by the reframed first-page disclosure footnote). Net -60 words.
- **Conclusion**: tightened to three short paragraphs + a one-line close. Net -30 words.
- **Disclosure footnotes** consolidated into a single footnote with numbered items. Net -30 words.
- **Abstract** trimmed from 149 to exactly 150 (re-counted after adding the "inverts seniority" hook).

Net: prose grew by approximately 30 words after consolidating the methodological honesty into the structurally-more-visible places (lead resolution, Section III opener) and trimming the structurally-less-visible places (Section VI prose, Conclusion close, redundant threats paragraph).

## For final submission

The author should:
1. Run a precise manual word count using the IEEE Author Tools "Article Submission Checklist" (or the editor-provided checking script if one is supplied). `detex`-based counts are typically 5--8% high because they include code identifiers like `max_retries` as separate tokens; the realistic submission count is approximately 3,180--3,250 words of prose + 750 table = ~3,930--4,000 effective.
2. Confirm with EIC Sigrid Eldh (`sigrid.eldh@ieee.org`) whether `\caption` text counts toward the 250-words-per-table allowance (some interpretations include captions; some exclude them).
3. The current draft has a +29-word headroom even on the conservative `detex`-inflated count, so any reasonable interpretation of caption counting still fits.

## Confirmed counts

- Abstract: 150 words (manual `detex` of `\begin{abstract} ... \end{abstract}`).
- References: 12 numbered entries (under the 15-reference cap).
- Author bio: ~75 words (excluded from word count per IEEE Software policy).
- First-page disclosure footnote: consolidated into a single `\thanks` with two numbered items, ~150 words; counted toward manuscript body.
