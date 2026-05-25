# IEEE Software "Edge-Cloud Continuum" Special Issue — Pre-Submission Compliance Audit

**Date:** 2026-05-18
**Auditor:** sub-agent compliance review
**Paper:** `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/ieee_software_paper.tex`
**Submission deadline:** 2026-07-07 (50 days from today)
**Verdict:** PASS — all binding limits satisfied after fixes applied this session; ready for submission once author confirms.

---

## Verified References (every URL fetched in-session 2026-05-18)

- `https://www.computer.org/digital-library/magazines/so/cfp-edge-cloud-continuum` — IEEE Software Edge-Cloud Continuum special issue CFP. Confirms **submission deadline 7 July 2026**, **publication target Mar/Apr 2027**, **guest editors** Davide Taibi (Univ. of Southern Denmark), Schahram Dustdar (TU Wien), Guodong Wang (Coovally), Adel N. Toosi (Univ. of Melbourne), and the **submission portal** `https://ieee.atyponrex.com/journal/sw-cs`. Page does NOT specify word/figure/page limits, anonymization policy, template, or cover letter requirements — those are deferred to the IEEE Software general author info page.
- `https://www.computer.org/digital-library/magazines/so/cfp-ieee-software` — IEEE Software general author guidelines. Verbatim quotes captured: **"Articles should be no more than 4,200 words, including 250 words for each figure and table"**; **"A maximum of 15 references and author biographies are not included in the word count"**; **"The abstract should be no more than 150 words and should describe the overall focus of your manuscript"**; **"With your submission, provide three actionable insights in bullet-list format that software practitioners will get from your paper"**; **"Please include a photo of each author"**; **"In addition to submitting your paper to IEEE Software, you are also encouraged to upload the data related to your paper to IEEE DataPort"**; submission portal repeated as `https://ieee.atyponrex.com/journal/sw-cs`. Page does NOT mention sidebars, IEEEtran template, anonymization, cover letter, or ORCID.
- `https://ieee.atyponrex.com/journal/sw-cs` — **301 redirect** to `https://ieee.submission.researchexchange.com/journal/sw-cs`. The CFP-listed portal URL is the legacy Atypon endpoint; the live portal is now on ResearchExchange. Both resolve to the IEEE Software (`sw-cs`) submission queue. The redirect is permanent — account creation and submission must be done at the ResearchExchange URL.
- `https://ieee.submission.researchexchange.com/journal/sw-cs` — Live IEEE Software submission portal (returns "Loading…" placeholder over a JavaScript SPA; functional landing page confirmed by HTTP 200 + redirect chain). Use this URL on submission day; account creation requires an IEEE Account ID linkable to an ORCID.
- `https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/` — IEEE submission-policy overview. Does NOT itself state IEEE Software's anonymization choice; **single-blind / non-anonymous is the IEEE Computer Society magazine default and is consistent with the absence of any anonymization instruction in the CFP** (IEEE Software has historically been single-blind with author identities visible to reviewers). No special-issue override was found; treat as single-blind / non-anonymous unless the portal screen indicates otherwise on submission day.
- `https://www.computer.org/publications/author-resources` — IEEE CS author resources page. Confirms **"using an article template is not required but is encouraged"** and points to the IEEE Template Selector. **IEEEtran with the `journal` document-class option is an accepted IEEE Software template.**

---

## Per-item compliance checklist (post-fix state)

| # | Requirement | Limit / required form | Actual (post-fix) | Status |
|---|---|---|---|---|
| 1 | Submission portal | `https://ieee.atyponrex.com/journal/sw-cs` (redirects to ResearchExchange) | n/a | Use `https://ieee.submission.researchexchange.com/journal/sw-cs` on submission day |
| 2 | Deadline | 7 July 2026 (no timezone specified by CFP) | n/a | 50-day buffer; recommend submission by 2026-07-05 to absorb portal hiccups |
| 3 | Total word count | $\leq 4{,}200$ including 250 words per figure/table | 3,944 prose + 250 (1 table) = **4,194** | PASS (6-word margin) |
| 4 | Abstract word count | $\leq 150$ | **150** | PASS (exact) |
| 5 | References | $\leq 15$ | 4 `\bibitem`s | PASS |
| 6 | Figures + tables | counted toward word budget at 250 each | 1 table, 0 figures | PASS |
| 7 | Three actionable insights box | required, bullet list, practitioner-facing | Present at head of article (boxed via `framed`), 3 bullets | PASS |
| 8 | Author photo | required | Not yet embedded in PDF | DEFERRED — supply on submission day via portal upload (separate file) |
| 9 | Author bio | required | Present (Sec. ``Author Biography'', ~60 words) | PASS |
| 10 | Template | encouraged, IEEEtran journal accepted | `\documentclass[journal]{IEEEtran}` | PASS |
| 11 | Anonymization | IEEE Software default single-blind | Non-anonymous (author named on title page) | PASS (matches default) |
| 12 | Citation resolution | no `[?]` markers | 0 undefined citations in log | PASS |
| 13 | Bibliography format | IEEE | `\bibitem` thebibliography environment in IEEE style | PASS |
| 14 | Author affiliation honesty | no internal-employer identifiers (per author MEMORY constraint) | All "Meta Plugboard" / "Claude Code at Meta" references replaced with "enterprise gateway infrastructure" | PASS — see Fix 4 below |
| 15 | Scope alignment | "Observability, SRE & AIOps for edge-cloud systems" | Paper centers AIOps + observability for LLM agents across edge-cloud-continuum tiers | PASS |
| 16 | Plain-English magazine voice | required | Reads as practitioner experience report; preserves technical detail | PASS |
| 17 | Threats to validity in magazine register | required | Section VII condensed to 9 numbered threats; consolidated Limitations section after Conclusion | PASS |
| 18 | Compile clean | pdflatex 3 passes, no warnings | 6-page PDF, no LaTeX warnings, no undefined refs | PASS |

---

## Conflicts with prior notes (FIRST item per the rules)

- **Submission portal URL has moved.** The CFP and the `OUTLINE.md` list `https://ieee.atyponrex.com/journal/sw-cs`, which now returns a permanent (HTTP 301) redirect to `https://ieee.submission.researchexchange.com/journal/sw-cs`. Use the ResearchExchange URL on submission day. Update any submission-day checklist accordingly.
- **Effective word cap is much tighter than the OUTLINE.md "5,000–6,000 word" assumption.** The verified CFP says **4,200 words including 250 per figure/table**. The 5,000–6,000 number in the outline (and the comment `% Target length: ~5,000-6,000 words (IEEE Software feature article convention)` at the top of the .tex) was incorrect. Fixed in this audit; the comment header should be revised at the user's discretion before final submission.
- **Three-Actionable-Insights box is mandatory, not optional.** Outline did not flag this; CFP says **"With your submission, provide three actionable insights in bullet-list format that software practitioners will get from your paper."** Added as a boxed list at the head of the article.
- **Abstract was 321 words pre-fix vs. 150-word cap** — a hard violation. Now trimmed to exactly 150.
- **Anonymization regression risk:** the round-3-PASS .tex contained `Meta Plugboard`, `Claude Code at Meta`, and `Meta's internal Plugboard infrastructure`. These directly de-anonymize the author's employer despite the "Independent Researcher" byline and contradict the explicit `feedback_never_deanonymize_paper.md` MEMORY constraint. Round-3 reviewer did not catch this. All five mentions have been replaced with "enterprise gateway infrastructure" / "enterprise codex CLI" / "enterprise Anthropic gateway" / "enterprise Anthropic quota". Verify no other employer-identifying tokens remain before submission.

---

## Fixes applied this session

1. **Abstract trimmed from 321 → 150 words.** Removed redundant tier descriptions and the parenthetical that restated max-repeat numbers already shown in Table 1.
2. **Three-Actionable-Insights box added** at the head of the article (above the abstract) using a `\begin{framed}` environment. New package: `\usepackage{framed}`. Three bullets directly mapped to Section V's deployment recommendations.
3. **Word count cut from 4,755 → 3,944 prose** (effective total 4,194 incl. 1 table at 250). Cuts taken from:
   - Introduction: condensed central-finding and deployment-implication paragraphs (kept all claims, removed restatements of the abstract).
   - Background: trimmed framework list and overlap-with-GenAI-conventions enumeration.
   - Section "The Vendor Agent CLI as Black-Box Agent": removed paragraph that restated abstract-level absorption claim.
   - Section V "Why this matters": collapsed three numbered recommendations into a reference to the head-of-article insights box plus one paragraph of amplification (so the recommendations appear once, not twice).
   - Threats to Validity: tightened each of the 9 threat paragraphs (kept every methodological caveat; removed throat-clearing).
   - Limitations section (after Conclusion): rewritten as one consolidated paragraph (L1–L4 inline) — saves ~150 words while preserving every L1–L4 substantive point.
   - Reproducibility: condensed two paragraphs into one (kept seeds, hardware, timeout, verification-pass count).
4. **Anonymization sweep.** All 5 instances of `Meta Plugboard`, `Meta's internal Plugboard infrastructure`, `Claude Code at Meta`, and `non-Meta practitioner` replaced with generic enterprise-gateway / external-practitioner phrasing. Independence of the byline is now consistent with the body. No remaining employer-identifying tokens (verified via `grep -n "Plugboard\|Meta\b" ieee_software_paper.tex` → 0 hits).
5. **Compile verification.** `pdflatex` × 3 (no `bibtex` needed — `thebibliography` is inline). Final: 6 pages, 197 KB, no LaTeX warnings, no undefined references, no `[?]` markers. Visual render check via Ghostscript confirms the actionable-insights box, title, byline, abstract, index terms, and footnote disclosure of single-author replication all render on page 1.

---

## Fixes deferred (require user action on submission day)

| # | Item | Action |
|---|---|---|
| D1 | Author photo | Upload via portal during submission flow (the .tex bio is text-only; IEEE Software typically asks for a separate photo file at submission). High-resolution headshot, IEEE-standard 1.5" × 2" or larger. |
| D2 | ORCID linkage | Ensure the IEEE Account used to submit has ORCID `0000-0000-0000-0000` linked (substitute author's actual ORCID). IEEE typically prompts for ORCID at submission. |
| D3 | Cover letter | The CFP does not explicitly require a cover letter; the ResearchExchange portal typically provides a free-text field. Recommended (one paragraph) covering: (a) statement that the paper targets the Edge-Cloud Continuum special issue, (b) one-sentence summary of contribution, (c) disclosure of single-author replication of prior peer-reviewed work (already in title footnote), (d) declaration of no conflicts with any guest editor. Draft below. |
| D4 | Conflict-of-interest declaration | The submission portal will ask the author to identify conflicts with each guest editor. Per public bio search, the author has no co-authorship, advisor/advisee, or current-funding relationship with Taibi, Dustdar, Wang, or Toosi. Confirm and declare "no conflicts" at submission. |
| D5 | IEEE DataPort upload | The CFP **encourages** (does not require) data upload to IEEE DataPort. The 960-trace corpus and per-instance JSONs are already release-ready per `data_inventory_verification_2026-05-16.md`. Recommended: upload to IEEE DataPort and reference the DOI in the Reproducibility section before submission. If not done, the existing release-on-acceptance language is acceptable. |
| D6 | Update `% Target length` comment | The header comment in the .tex says `~5,000-6,000 words`; this is now stale. Recommend changing to `% Target length: 4,200 words effective (incl. 250 per fig/table) per IEEE Software author guide`. Purely cosmetic; does not affect submission. |
| D7 | Replicate IEEEtran template choice with the IEEE Template Selector | The CFP says template usage is "not required but encouraged". Current `\documentclass[journal]{IEEEtran}` is accepted, but the author should run the IEEE Template Selector once on submission day to confirm no newer template is required for this special issue. |

---

## Submission-day step list

1. **2026-07-01 to 2026-07-05** — final author read; confirm no last-minute claim drift.
2. Go to `https://ieee.submission.researchexchange.com/journal/sw-cs`.
3. Sign in with IEEE Account (or create one if needed). Link ORCID.
4. Select "New Submission" → article type: **Feature Article** → topic: **Special Issue: The Edge-Cloud Continuum**.
5. Upload files:
   - `ieee_software_paper.pdf` (final PDF, 6 pages)
   - `ieee_software_paper.tex` (source) plus any required .bib (none — bibliography is inline)
   - **Author photo** (separate file — D1 above)
   - Cover letter (free-text or PDF — draft below)
   - Optional: link to IEEE DataPort dataset (D5) and to the public reproducibility repo
6. Fill in:
   - Authors + affiliations + emails + ORCIDs
   - Abstract (paste from PDF — exactly 150 words)
   - Three actionable insights (paste from PDF — three bullets, also present in the boxed sidebar)
   - Keywords/IEEE index terms (already in paper)
   - Conflict-of-interest declarations with guest editors (D4)
7. Submit. Save the submission confirmation number and the editor-assigned manuscript ID.
8. Tag the submission state in `data_inventory.json` under a new `submission_record` key (date submitted, manuscript ID).

---

## Suggested cover letter (draft for author approval)

> Dear Guest Editors of the IEEE Software Special Issue on the Edge-Cloud Continuum,
>
> I am submitting the enclosed feature article, *"When Telemetry-Driven Interventions Don't Transfer: A Cross-Tier Replication Study of Closed-Loop Agent Recovery via Vendor Agent CLIs for Edge-Cloud Deployments,"* for consideration in your special issue.
>
> The paper directly addresses the CFP topic *"Observability, SRE & AIOps for edge–cloud systems."* It reports a 960-instance-run cross-tier replication of a peer-reviewed closed-loop intervention for LLM agents, deployed across four production-tier models from two vendors (Anthropic and OpenAI) via the vendor agent CLIs that dominate 2026 production. The headline finding is that the published intervention's trigger condition never fires across the deployment regime AIOps practitioners actually face — a result with direct implications for any team selecting or instrumenting agent observability stacks across the edge-cloud continuum.
>
> The paper is a single-author replication of my own previously peer-reviewed prior work (AIware '26), explicitly disclosed in the title footnote and discussed as a methodological caveat in Section VII. I have no co-authorship, advisor/advisee, or current-funding relationships with any of the special-issue guest editors.
>
> The harness, the 960-trace corpus, and the per-instance JSON dataset are release-ready for full reproducibility.
>
> Sincerely,
> Krishna Chaitanya Balusu (Independent Researcher)

---

## Files modified

- `ieee_software_paper.tex` — edited (abstract, body, threats, limitations, anonymization, added insights box + `framed` package).
- `ieee_software_paper.pdf` — recompiled (6 pages, 197 KB).
- `ieee_software_paper.aux`, `.log` — regenerated by pdflatex (no warnings).

## Files created

- This audit report.
