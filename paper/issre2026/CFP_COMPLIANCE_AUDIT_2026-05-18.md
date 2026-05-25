# ISSRE 2026 Industry Track — Pre-Submission CFP Compliance Audit

**Audit date:** 2026-05-18
**Paper:** `issre_paper.tex` / `issre_paper.pdf` (Full Paper, Industry Track)
**Auditor scope:** verbatim CFP compliance, IEEE format, page/length limits, mandatory metadata, submission logistics.

---

## Verified references

Every URL below was fetched in this audit session; ground-truth summaries reflect what the pages actually say.

- https://cyprusconferences.org/issre2026/industry-track/ — Authoritative Industry Track CFP. States submissions are **NOT anonymous**; lists three submission types (1-2p enlightening talk/tool demo, 4p short, **6p full including references**); requires **abstract ≤150 words and ≤4 keywords**; requires "IEEE Computer Society Format Guidelines" with provided LaTeX/Word templates; submission portal `https://easychair.org/conferences/?conf=issre2026`; Best Industry Paper Award eligibility requires "at least one author whose primary affiliation is in Industry"; lists dual deadline cycles (abstracts June 28 & July 3, 2026 AoE; full/short papers July 5 & July 12, 2026 AoE; notification August 12; camera-ready August 19); plagiarism screening via IEEE CrossCheck.
- https://cyprusconferences.org/issre2026/ — Master ISSRE 2026 page. Confirms Industry Track abstract/paper/notification/camera-ready dates above; lists Research Track (12p), RENE Track, Fast Abstracts/Project Highlights (2p), Workshops, Doctoral Symposium, J1/C2.
- https://easychair.org/cfp/ISSRE2026 — EasyChair CFP. Confirms dual-cycle Industry Track deadlines, chairs (Jinyang Liu, ByteDance; Sigrid Eldh, Ericsson), and submission types.

Not verifiable in-session (flagged but not blocking):
- Exact LaTeX template `.cls` version — CFP says "provided LaTeX templates" but the Industry Track page does not link a specific template download in the fetched markup; the standard IEEE conference template (`\documentclass[conference]{IEEEtran}`) is the accepted default for IEEE Computer Society conferences and is what the paper uses.
- Whether "July 5 & July 12" is original+extension, or two genuine independent submission cycles: the page provides both dates with no clarifying qualifier. **Recommendation: target July 5 (cycle 1) as the safe deadline and treat July 12 as a fallback.**

---

## CFP-versus-paper compliance matrix

### Page, format, and structural requirements

| Requirement | CFP source | Paper state | Verdict |
|-------------|------------|-------------|---------|
| Page limit ≤ 6 pages including references | Industry Track CFP, "Full paper: 6-pages (including references)" | 6 pages (verified `mdls`, `pdflatex` final log) | OK |
| IEEE Computer Society LaTeX template | "IEEE Computer Society Format Guidelines" | `\documentclass[conference]{IEEEtran}` — IEEE conference style | OK |
| Two-column layout | IEEE conference standard | Two-column (verified PDF) | OK |
| 10pt body | IEEE conference standard | IEEEtran default (10pt) | OK |
| Letter paper | IEEE conference standard | IEEEtran conference default | OK |
| Fonts embedded | CFP: "All fonts must be embedded" | IEEEtran uses Type 1 fonts; verify at submission via EasyChair's PDF check | OK (pending portal check) |
| File size < 15 MB | CFP | 178,955 bytes (~180 KB) | OK |

### Anonymity, authorship, and metadata

| Requirement | CFP source | Paper state | Verdict |
|-------------|------------|-------------|---------|
| Non-anonymous submission | Industry Track CFP: "submissions are **not** anonymous" | Author block: "Krishna Chaitanya Balusu, Independent Researcher, San Francisco, CA, USA, krishnabkc15@gmail.com" | OK |
| Title, author, affiliation, email | CFP: "title, the name and affiliation of each author" | All present | OK |
| Abstract ≤ 150 words | CFP: "an abstract of up to 150 words" | **124 words** after fix (was 227 words — would have been desk-checked) | OK after fix |
| Keywords ≤ 4 | CFP: "up to 4 keywords" | **4 keywords** after fix: "LLM agents, reliability engineering, observability, AIOps" (was 8 keywords) | OK after fix |
| ORCID | Not required by CFP | Not present in paper; nothing to add | N/A |
| IEEE copyright footer | Not required for submission per IEEE Computer Society (added at camera-ready) | Not present; correct for submission | OK |

### Bibliography and citations

| Item | State | Verdict |
|------|-------|---------|
| All `\cite{}` keys resolve in bibliography | `pdflatex` final log shows no "undefined" or "[?]" warnings; `bibtex` log clean | OK |
| BibTeX style matches IEEE | `\bibliographystyle{IEEEtran}` | OK |
| `refs.bib` entries are externally verifiable | AIware paper, MAST paper, ISSRE 2024 Industry Track papers, SRE books, OTel docs, Zenodo DOI all real | OK |
| `agentdebug` and `aegis` entries marked "Anonymous" | Not cited in the body — they are unused; safe to leave but consider removing | Minor |

### Mandatory content (per CFP topic guidance)

| CFP signal | Paper state | Verdict |
|-----------|-------------|---------|
| "Use cases, practical experiences, lessons learned" | Section "Lessons Learned and Negative Findings" with 5 explicit lessons | OK |
| "submissions reporting negative results, unexpected outcomes" | Honest negative findings retained (TTR=0 disclosure, no live deployment, 43% blind spot, mock-vs-real gap) | OK |
| "Reliability in AI-driven and autonomic systems" | Core topic alignment | OK |
| Industrial relevance | Vendor grade card, alert-fatigue budget, runbook templates — all practitioner artifacts | OK |
| AIware overlap defense | Table 1 (boundary table) retained, artifact-by-artifact | OK |
| Data availability statement | Section "Data Availability" with concept DOI `10.5281/zenodo.20129005` | OK |
| Ethics / IRB | Not required (no human subjects, mock LLM clients, public artifacts) | N/A |
| Replication package | Linked via Zenodo concept DOI and PyPI | OK |

### Best Industry Paper Award eligibility

| Rule | Paper state | Verdict |
|------|-------------|---------|
| "at least one author whose primary affiliation is in Industry" | Sole author affiliation is **Independent Researcher** | **INELIGIBLE for Best Industry Paper Award** (paper itself is fully eligible for the track — this only affects award candidacy). Documented in `venue_research_report.md` §6 and accepted. |

### Compilation hygiene

| Item | State | Verdict |
|------|-------|---------|
| `pdflatex` 3x + `bibtex` succeeds (exit 0) | Verified this session | OK |
| Final page count exactly 6 | Verified (`Output written on issre_paper.pdf (6 pages, 178955 bytes)`) | OK |
| Overfull/Underfull hboxes affecting layout | One overfull hbox (13.6pt) in boundary-table caption row eliminated by header shortening; one harmless underfull vbox (column-balance artifact) remains, no visual impact | OK |
| Missing fonts | One benign `LaTeX Font Warning: Font shape TS1/ptm/m/sc undefined` — affects nothing rendered (no small-caps in TS1 encoding used); default substituted; no impact on PDF | OK |
| Undefined references / citations | None | OK |

---

## Discrepancies vs `venue_research_report.md`

Per audit rules, contradictions with the existing venue research are flagged first:

1. **None material.** `venue_research_report.md` correctly identified: 6-page Industry Track full-paper limit (§3), IEEE Computer Society format (§4), non-anonymous (§4), Independent Researcher → no Best Industry Paper Award (§6), dual-cycle deadlines (§2). The report did NOT explicitly call out the **≤150 word abstract** or the **≤4 keyword** cap; those are noted only in passing on the CFP page itself, and the paper violated both before this audit. The compliance matrix above now closes that gap.

---

## Fixes applied this session

All low-risk, no authorial-judgment changes; page count preserved at 6.

1. **Abstract trimmed from 227 → 124 words** to satisfy the CFP's 150-word cap. Every quantitative claim retained (3,780-row corpus, 14×6×7×6 factorial, 0.500–1.000 detection range, 7.1% FPR, 43% blind spot, Grade C/D ceiling, guardrail_bypass blind spot, MTTR gap, open-source release). Removed: redundant restatement that AIware was a "research artifact," the prose explanation of "three converging bodies of SRE practice" (preserved in body §V), and the SRE-practice citation chain (already cited in body).
2. **Keywords trimmed from 8 → 4** to satisfy the CFP cap: kept "LLM agents, reliability engineering, observability, AIOps"; dropped "OpenTelemetry, fault detection, deployment patterns, site reliability engineering" (all present as topic words in the body).
3. **Overfull hbox in Table 1 (boundary table)** eliminated by shortening the last column header from "Why it requires its own treatment" to "Why a separate treatment." Semantics preserved.
4. **Header comment updated** to record both deadline cycles (cycle 1: abstract 2026-06-28, paper 2026-07-05; cycle 2: abstract 2026-07-03, paper 2026-07-12) instead of the single-deadline note. Targeting cycle 1.
5. **Recompiled** `pdflatex 3x` + `bibtex`. Final: 6 pages, 178,955 bytes, exit 0, no `Overfull`/`Underfull` warnings affecting layout, no undefined references, no `[?]` citations.

## Fixes deferred (not blocking submission)

| Item | Why deferred |
|------|-------------|
| Remove unused `agentdebug` and `aegis` bib entries | They are not cited in the body; BibTeX silently drops uncited entries. No compliance issue. Leaving for now lets future revisions add them if needed. |
| Drop the `Anonymous` author tokens from `refs.bib` for `agentdebug` and `aegis` | Not blocking since they are uncited. If they are cited in any future revision, rewrite with real authors first. |
| ORCID for author | CFP does not require it for the Industry Track. If desired, can be added at camera-ready alongside the IEEE copyright footer. |
| IEEE copyright footer / `\IEEEpubid` | IEEE Computer Society convention: copyright notice is added at **camera-ready**, not at submission. CFP does not require it for review. |
| Resolve harmless `TS1/ptm/m/sc undefined` font warning | No visible rendering impact (small-caps in TS1 encoding is not used in the paper). Suppress only if reviewer flags. |

---

## Submission-day checklist

### Cycle 1 (target)
- **Abstract registration:** **2026-06-28 AoE** — register title, authors, affiliations, abstract (use the 124-word abstract from the current PDF), and keywords on EasyChair.
- **Full paper upload:** **2026-07-05 AoE** — upload `issre_paper.pdf`.

### Cycle 2 (fallback if cycle 1 is missed)
- Abstract: **2026-07-03 AoE**
- Full paper: **2026-07-12 AoE**

### Submission portal
- **EasyChair:** https://easychair.org/conferences/?conf=issre2026
- Track: Industry Track → Full Paper
- Submission type to select: "Full paper (6 pages, including references)"

### EasyChair metadata to prepare
- Title: `Telemetry-Driven Reliability Engineering for LLM Agent Systems: A Deployment Rubric from 3,780 Fault-Injection Runs`
- Author: Krishna Chaitanya Balusu, Independent Researcher, San Francisco, CA, USA, krishnabkc15@gmail.com
- Abstract (paste current 124-word version verbatim)
- Keywords: `LLM agents`, `reliability engineering`, `observability`, `AIOps`
- Topic categories: select "Reliability in AI-driven and autonomic systems" plus "Use cases, practical experiences, lessons learned" (or closest equivalents in EasyChair's topic list).
- Author bio (if EasyChair prompts): one-paragraph independent-researcher bio focused on agent observability and SRE practice.

### Submission-day verification (run on the cycle-1 morning)
1. Recompile from a clean state: `latexmk -C && pdflatex -interaction=nonstopmode issre_paper.tex && bibtex issre_paper && pdflatex issre_paper && pdflatex issre_paper`.
2. Confirm `Output written on issre_paper.pdf (6 pages, ...)`.
3. Confirm zero `[?]` markers in the PDF (`/usr/bin/mdfind -onlyin . "kMDItemTextContent == '*[?]*'"` or visual inspection).
4. Verify abstract is still ≤150 words and keywords ≤4 (they have not been touched).
5. Verify fonts are embedded: `pdffonts issre_paper.pdf` — every line should show `yes` under `emb` (or run EasyChair's PDF checker once uploaded).
6. Upload to EasyChair; download the EasyChair-rendered PDF and visually compare to the local PDF.
7. Take a screenshot of the EasyChair confirmation; save under `paper/issre2026/`.

### Post-submission
- Track Best Industry Paper Award status: paper is **not eligible** because author is Independent Researcher; do not select the award flag if EasyChair prompts.
- Wait for notification on **2026-08-12 AoE**.
- Camera-ready: **2026-08-19 AoE** — at that point, add IEEE copyright footer (`\IEEEpubid{...}`), final author block formatting, ORCID if desired.

---

## Overall verdict

**PASS — paper is submission-ready for ISSRE 2026 Industry Track Full Paper, cycle 1 (2026-07-05 AoE).**

Two CFP violations that would have triggered desk-check or reviewer friction (abstract length, keyword count) were caught and fixed in this audit. Page count, format, anonymity, bibliography, data availability, and topic alignment all comply. Author affiliation status (Independent Researcher) makes the paper ineligible for the Best Industry Paper Award but does not affect track eligibility or review priority — this was already an accepted constraint per `venue_research_report.md` §6.
