# CFP Compliance Audit — IEEE Software "Human-Centric AI for Software Engineering" Special Issue

**Manuscript:** `ieee_sw_humancentric_paper.tex` / `ieee_sw_humancentric_paper.pdf`
**Working title:** *Calibrating the False-Positive Tax: Persona-Stratified Operator Cost of Autonomous AI Agent Observability*
**Audit date:** 2026-05-18
**Submission deadline:** 2026-09-07 (T-112 days)
**Expected publication:** May/June 2027

---

## Verdict: READY TO SUBMIT — submission gate cleared after low-risk fixes applied

All format caps satisfied with margin. All citations resolve. PDF compiles cleanly in 3 passes with zero undefined references. Round-4 cold reviewer signed off STRONG_ACCEPT / cover-candidate. Three low-risk fixes were applied during this audit (uncited bibitems, misleading "single-blind" phrasing on the repository reference). One open item (author photo) is documented below as a submission-day requirement that does not affect the LaTeX source.

---

## Verified References (CFP ground truth, fetched 2026-05-18)

```
Verified references:
- https://www.computer.org/digital-library/magazines/so/cfp-human-centric-ai
  — Official CFP for the SI. Confirms: deadline 7 September 2026; expected publication May/June 2027; submission portal https://ieee.atyponrex.com/journal/sw-cs; guest editors Silvia Abrahão (Universitat Politècnica de València, Spain), Kelly Blincoe (University of Auckland, New Zealand), Emerson Murphy-Hill (Microsoft, USA — NOT Google), Nachiappan Nagappan (Meta Inc., USA); scope spans human-centered AI and AI for developers/end-users; concurrent-submission policy: "Manuscripts should not be published or currently submitted for publication elsewhere"; IEEE DataPort upload encouraged.
- https://www.computer.org/digital-library/magazines/so/cfp-ieee-software
  — General IEEE Software author guidelines. Confirms verbatim: "Articles should be no more than 4,200 words, including 250 words for each figure and table"; "The abstract should be no more than 150 words and should describe the overall focus of your manuscript"; "A maximum of 15 references and author biographies are not included in the word count"; "Please include a photo of each author"; "With your submission, provide three actionable insights in bullet-list format that software practitioners will get from your paper"; submission portal https://ieee.atyponrex.com/journal/sw-cs; EIC email sigrid.eldh@ieee.org accepts presubmission abstract triage.
- https://github.com/traceloop/openllmetry
  — Official OpenLLMetry repository (Traceloop). 7.1k stars, Apache 2.0. Confirms the bibitem URL is current and valid.
```

**Discrepancy flag (Murphy-Hill affiliation):** The user's briefing said Murphy-Hill is at Google; the official CFP lists him at **Microsoft**. The manuscript does not name the guest editors anywhere in the body (correctly), so no manuscript edit is required. Cover-letter authors should write "Microsoft," not "Google."

---

## Per-item compliance checklist

### Format caps (verified 2026-05-18 against `cfp-ieee-software`)

| Cap | Limit | Actual (post-fix) | Status |
|---|---|---|---|
| Effective word budget (prose + 250/figure-or-table) | 4,200 | 3,424 prose + 750 (3 tables × 250) = **4,174** | PASS (+26 margin) |
| Abstract length | 150 | **150** (detex'd from `\begin{abstract}` block) | PASS (exactly at cap) |
| References | 15 | **12** | PASS (3 slot buffer) |
| Figures + tables | (no explicit cap; 250-word allowance) | 0 figures + 3 tables | PASS |
| Three actionable insights box on page 1 | required | present (`mdframed` box, three bullets, page 1) | PASS |
| Author photo | required ("Please include a photo of each author") | **NOT in LaTeX source** — provide separately at portal upload | OPEN — submission-day step |
| Author bio | required (excluded from word count) | present (~75 words, page 5) | PASS |
| IEEE manuscript-prep template | author choice (IEEEtran journal class is widely accepted at IEEE Software) | `\documentclass[journal]{IEEEtran}` v1.8b (2015) | PASS |
| Compilation | clean | 3 pdflatex passes, 0 errors, 0 undefined refs, 0 rerun warnings | PASS |
| Pages compiled | (no hard cap; magazine target ~5--7) | **5 pages** | PASS |

### Citations / bibliography

| Item | Status |
|---|---|
| All `\cite{}` keys resolve to a `\bibitem{}` | PASS (12/12) |
| All `\bibitem{}` keys cited at least once in body | PASS (12/12) **after audit fix** — pre-fix, `openllmetry`, `langchain`, `crewai` were defined but uncited |
| OpenLLMetry GitHub URL valid | PASS (verified 2026-05-18) |
| Single-blind / non-anonymous appropriateness | PASS — author named on title page, in bio, and in two `\bibitem`s; the AgentTelemetry repo identifier `\bibitem{atrepo}` is the only reference held back for camera-ready |

### Magazine voice (Round-4 reviewer cover-candidate bar)

| Criterion | Status |
|---|---|
| Lead opens with concrete 3am-pager failure scenario | PASS |
| Three actionable insights non-obvious AND Monday-actionable | PASS |
| Two empirical findings independently surprising (SRE inversion; `token_growth_factor` substitution) | PASS |
| No academic drift (no "Threats to validity" heading; no academic-passive in lead/findings/conclusion) | PASS |
| First-page transparency footnote framed as strength, not apology | PASS |
| 5-page format efficient; no padding | PASS |

### Concurrent-submission disclosure

| Item | Status |
|---|---|
| Edge-Cloud SI overlap analysis on file (`overlap_analysis.md`) | PASS — disjoint corpora, disjoint research questions, disjoint editorial pools |
| First-page footnote item (2) declares concurrent submission and orthogonality artifact | PASS — language is transparency-positive, names the other SI by name |
| Compliance with "not currently submitted for publication elsewhere" policy | NUANCE — this clause is about prior or pending publication of the same manuscript. Submitting two genuinely orthogonal manuscripts to two different IEEE Software SIs is permitted provided the manuscripts do not overlap. The author's footnote disclosure + on-file `overlap_analysis.md` discharge the disclosure duty. Editors who flag this should be pointed at the disjoint-corpora table in `overlap_analysis.md`. |

### Required SI-specific elements

| Element | Required? | Present? |
|---|---|---|
| Actionable insights box (3 bullets) | Yes (general IEEE Software CFP) | PASS — boxed `mdframed` on page 1 |
| Sidebar | Not required by CFP | N/A |
| IEEE DataPort archive | Encouraged | Reproducibility section commits to post-acceptance DataPort upload — PASS |
| Author photo | Yes (general IEEE Software CFP) | **OPEN — upload via Atypon portal at submission time** |
| Cover letter | Not strictly required, but recommended | DRAFT-AT-SUBMISSION — see "Submission-day steps" below |

---

## Fixes applied during this audit (2026-05-18)

1. **Added missing `\cite{openllmetry}`, `\cite{langchain}`, `\cite{crewai}` to first textual mention.** Pre-audit, these three bibitems were defined in the bibliography but never `\cite{}`d in the body — a quality issue that an attentive copy editor or reviewer would flag. Now cited at first mention in Section V (head-to-head) and Section VI (detector applicability). Word count delta: +3 words (still 4,174 effective vs 4,200 cap, +26 margin).

2. **Corrected the `\bibitem{atrepo}` parenthetical** from "Repository identifier withheld for single-blind review" to "Repository URL withheld pending peer review." The original phrasing was technically incorrect: single-blind review hides the reviewer identity, not the author identity, so "for single-blind review" is not a coherent reason to withhold an author-disclosed repository URL. The corrected phrasing is neutral and accurate.

3. **Recompiled (3 pdflatex passes).** Final PDF: 5 pages, 204,677 bytes, 0 errors, 0 undefined references, 0 multiply-defined labels, 0 rerun warnings. Only cosmetic underfull-hbox warnings remain (typical for IEEEtran two-column layout with `\texttt{}` tokens like `max_retries`).

---

## Open items requiring action before submission

| # | Item | Action |
|---|---|---|
| 1 | **Author photo** | Required by general IEEE Software CFP. Not embedded in LaTeX. Upload a professional headshot (JPEG, $\geq$300 dpi, $\geq$1.5"$\times$2") to the Atypon submission portal when prompted. The portal handles this as a separate asset; no LaTeX edit needed. |
| 2 | **Cover letter** | Draft a one-page cover letter naming the SI, stating the concurrent Edge-Cloud SI submission with on-file orthogonality analysis, and offering to provide `overlap_analysis.md` if requested. Address to "Dear Guest Editors of the Human-Centric AI for SE Special Issue." |
| 3 | **Presubmission abstract triage (optional but recommended)** | Email the abstract to `sigrid.eldh@ieee.org` (EIC) to confirm topical fit for the SI before full submission. Two-week response window is typical; do this by 2026-08-15 if pursued. |
| 4 | **IEEE DataPort archive (post-acceptance, but prepare now)** | Pre-package the four corpora referenced in Reproducibility section (persona-study transcripts, threshold-sensitivity sweep, head-to-head TSV, detector-applicability annotations) as a single DataPort-ready archive. The DataPort DOI will be inserted into the camera-ready Reproducibility paragraph after acceptance. |
| 5 | **Atypon-vs-ResearchExchange portal redirect** | The CFP-listed URL `https://ieee.atyponrex.com/journal/sw-cs` 301-redirects to `https://ieee.submission.researchexchange.com/journal/sw-cs`. Both URLs should work. Use the CFP URL first; if it fails, follow the redirect. |

---

## Submission-day step-by-step

1. **Final LaTeX rebuild** — run `pdflatex` three times in the paper directory; verify `Output written ... (5 pages, ~204,677 bytes)` and 0 undefined references.
2. **Re-verify word count** — `detex ieee_sw_humancentric_paper.tex | wc -w` should return $\leq$3,450 (current: 3,424). Effective total = words + 750 (3 tables) must remain $\leq$4,200.
3. **Re-verify abstract** — `awk '/\\begin\{abstract\}/,/\\end\{abstract\}/' ... | detex | wc -w` should return $\leq$150 (current: 150).
4. **Navigate to portal** — https://ieee.atyponrex.com/journal/sw-cs — log in / create author account; select "Human-Centric AI for Software Engineering" special issue from the dropdown.
5. **Upload assets** in this order:
   - Main manuscript PDF (`ieee_sw_humancentric_paper.pdf`)
   - LaTeX source bundle (`ieee_sw_humancentric_paper.tex` + `refs.bib` if used externally — currently bibliography is in-line, so `.tex` alone suffices)
   - Author photo (JPEG, headshot)
   - Cover letter (PDF)
   - Supplementary materials checkbox — point to AgentTelemetry repository post-acceptance + planned IEEE DataPort archive
6. **Declare** in the portal's submission form:
   - Manuscript type: Feature article
   - Special issue: Human-Centric AI for Software Engineering
   - Concurrent submissions: Yes — one orthogonal submission to IEEE Software Edge-Cloud Continuum SI (orthogonality artifact on file with corresponding author)
   - Conflicts of interest: none with the four guest editors
7. **Final disclosure block check** — confirm the first-page `\thanks{...}` footnote on the compiled PDF still renders both numbered transparency items (prior AIware'26 work; concurrent Edge-Cloud submission).
8. **Submit; record submission ID** in `revision_log.md` § Submission.
9. **Backup** — push the as-submitted `.tex` and `.pdf` to a tagged git ref (`tag: ieee-sw-hc-2026-submission`).

---

## Final compliance summary

| Dimension | Verdict |
|---|---|
| Word/abstract/reference caps | PASS with margin |
| All bibitems cited; all citations resolve | PASS (post-audit fix) |
| LaTeX compiles cleanly | PASS (3 passes, 0 errors, 0 undefined refs) |
| Required first-page elements (actionable insights box, transparency footnote) | PASS |
| Magazine voice / cover-candidate bar | PASS (Round-4 STRONG_ACCEPT) |
| Concurrent submission disclosed and orthogonal | PASS |
| Author photo embedded in LaTeX | **OPEN** — upload at portal; no LaTeX edit needed |
| Cover letter drafted | OPEN — draft at submission time |
| EIC presubmission triage (optional) | OPTIONAL — recommended by 2026-08-15 if pursued |

**Submission gate: CLEARED.** The manuscript is submission-ready pending the photo upload and cover-letter draft, both of which are portal-side artifacts that do not require LaTeX edits.

**Submission URL:** https://ieee.atyponrex.com/journal/sw-cs (301-redirects to https://ieee.submission.researchexchange.com/journal/sw-cs)
**Deadline:** 2026-09-07
**EIC:** Sigrid Eldh (sigrid.eldh@ieee.org)
**Guest editors:** Silvia Abrahão (UPV Valencia), Kelly Blincoe (U. Auckland), Emerson Murphy-Hill (**Microsoft**, not Google — correct in the official CFP), Nachiappan Nagappan (Meta)
