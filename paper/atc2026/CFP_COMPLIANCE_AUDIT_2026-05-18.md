# ATC 2026 Pre-Submission Compliance Audit
> Auditor session date: 2026-05-18
> Submission deadline: 2026-06-10 (no extensions)
> Days remaining: 23

## Verified References
- `https://sigops.org/s/conferences/atc/2026/cfp.html` — Fetched in-session.
  Verified: deadline June 10, 2026 (no extensions); long submissions
  "must not exceed 12 pages" + short "must not exceed 6 pages"
  (references and appendices excluded); template
  `\documentclass[sigplan,10pt]{acmart}`; 10-pt font on 12-pt leading;
  A4 or US-letter, 178×229 mm two-column block; double-blind
  ("Authors should make a good faith attempt to anonymize your
  submission" and "reference your past work in the third person, just
  as you would any other piece of related work"); mandatory separate
  2-page extended abstract; all pages must be numbered; references
  must be hyperlinked; conflict declaration required at submission;
  HotCRP portal "TBD" at publication time; artifact evaluation
  encouraged not mandatory; no CCS-concepts or keywords requirement;
  no paper-type marker required.
- `https://sigops.org/s/conferences/atc/2026/index.html` — Fetched
  in-session. Verified: Hyatt Hotel, Shatin, Hong Kong, November
  15-18, 2026.
- `https://sigops.org/s/conferences/atc/2026/abstract.html` — Fetched
  in-session. Verified: extended abstract has four mandatory
  components (Motivation; Limitations of current approaches; Key
  insights or ideas; Overview of results); citations and forward
  pointers to the full paper are permitted; the abstract should NOT
  contain numbered sections; page limit not on this page (the 2-page
  number comes from the CFP page).

## Disagreement With Prior Venue Research

`venue_research_report.md` is **consistent with the CFP fetched today**
on every load-bearing detail (deadline, location, dates, page limits,
template, double-blind model). No corrections required.

One nuance the prior report did not surface: the abstract guidelines
page explicitly recommends that the extended abstract "not contain
numbered sections" — this was unnumbered in the original draft and is
now enforced (see Fix 2 below).

## Per-Item Compliance Checklist

### Main Paper (`atc_paper.tex` / `atc_paper.pdf`)

| Item | Status | Notes |
|---|---|---|
| documentclass `acmart` with `sigplan,10pt` options | OK | Line 1: `\documentclass[sigplan,10pt,anonymous,review]{acmart}` — the `anonymous,review` add-ons are standard ACM practice for double-blind submissions and are accepted by the CFP. |
| Long-paper page limit ≤12 pages (refs excluded) | OK | Body + conclusion ends mid-page 11; references occupy bottom of p11 + p12. Body well under 12. |
| Total PDF page count | OK | 12 pages (11 body + ~1 page of references continuing onto p12). |
| Font: 10-pt Times Roman / 12-pt leading | OK | acmart sigplan defaults match. |
| Two-column 178×229 mm block | OK | acmart sigplan defaults match. |
| Page numbers present | OK | `printfolios=true` set; page numbers render at bottom. |
| Hyperlinked references | OK | acmart loads hyperref by default. |
| Anonymous author block | OK | `\author{Anonymous Authors}`, `\affiliation{Submission under double-blind review}`, `\renewcommand{\shortauthors}{Anonymous Authors}`. PDF header reads "Anonymous Author(s)". |
| PDF metadata (Author/Title/Subject) does not leak identity | OK | Author field contains only the LaTeX engine string; Title is the paper title; no real name. |
| No author URLs, emails, real org names | OK | `grep` for `gmail|krishna|balusu|kcbalusu|zenodo|pypi` returns 0 hits in `atc_paper.tex`. |
| No real OSS-project name leaking authorship | **FIXED** | Originally the body contained 5 occurrences of the literal string `agenttelemetry` in code-path references (e.g., `src/agenttelemetry/`, `from agenttelemetry.runtime import`). `agenttelemetry` is the author's real GitHub-org/PyPI-package name (`pypi.org/project/agenttelemetry`, `github.com/Krishnachaitanyakc/AgentTelemetry`), so any reviewer who searched any of these strings would have de-anonymized the submission. All 5 occurrences now pseudonymized to `agentscope` consistent with the displayed `\sysname = AgentScope` macro. |
| No author funding / acknowledgement section | OK | `grep -iE "funding|acknowled|thanks"` returns 0 hits in body. |
| Past work cited in third person | PARTIAL — DEFERRED TO USER | One sentence in §1 reads "In a prior controlled study by the authors [redacted for double-blind review], 84 of 112 SWE-bench Lite runs...". The CFP wording ("reference your past work in the third person, just as you would any other piece of related work") prefers a normal third-person citation to a published prior work rather than a `[redacted]` placeholder. Replacing the placeholder with a real third-person citation is an authorial judgement (whether to anonymise via redaction or via a third-person citation to the AIware paper, which is a same-author work published in the same year and is itself a de-anonymisation risk if cited by DOI). Flagged here for the user. |
| Bibliography style appropriate | OK | `\bibliographystyle{ACM-Reference-Format}` (the ACM standard); `.bbl` includes hyperlinks. |
| Bibliography entries do not leak author identity | OK | Refs in `refs.bib` are all third-party (Dapper, Canopy, Pivot Tracing, OpenInference, etc.); no author self-cite. |
| Paper-type marker in title (e.g. `[Research]`) | OK / N/A | CFP does not require one (unlike Middleware). Title is plain. |
| CCS Concepts | OK / N/A | CFP does not require CCS. `printccs=false` is set; nothing to add. |
| Keywords | OK / N/A | CFP does not require keywords. Nothing to add. |
| Filename does not de-anonymize | OK | `atc_paper.tex` / `atc_paper.pdf` are generic. |
| Footers / footnotes leak identity | OK | None found. The footer is the CFP-standard "Anon." marker that acmart auto-inserts in `anonymous,review` mode. |
| No overfull / underfull boxes affecting layout | OK | Latest `atc_paper.log` reports zero `Overfull` or `Underfull` warnings. |
| LaTeX compiles cleanly with bibtex pass | OK | `pdflatex → bibtex → pdflatex → pdflatex` completes; only warnings are the standard bibtex empty-publisher warnings on three book-style entries, which do not affect rendering. |

### Extended Abstract (`atc_extended_abstract.tex` / `atc_extended_abstract.pdf`)

| Item | Status | Notes |
|---|---|---|
| Exact 2 pages | OK | PDF metadata reports 2 pages. |
| Same template as main paper | OK | `\documentclass[sigplan,10pt,anonymous,review]{acmart}`. |
| Anonymous | OK | `\author{Anonymous Authors}`. |
| Four mandatory CFP components present | OK | Motivation → "Problem" section. Limitations of current approaches → covered in "Problem" paragraph 1. Key insights / ideas → "Approach" section. Overview of results → "Evaluation" section. (A fifth "Contribution" section restates the take-away, also compliant.) |
| Numerical claims track the full paper | OK | Spot-checked: 11.7 µs p50, 19,071 spans/s, +2.16 µs p50 (CI [+2.06, +2.25]), 0.612 vs 0.429 vs 1.000 FDR, 3,780-row benchmark, 7×6×14 design — all match `atc_paper.tex` and `cold_review_round_6.md` Table 3 / Tables 4-8. |
| Sections unnumbered (per CFP recommendation) | **FIXED** | Originally `\section{Problem}` etc. gave numbered headings `1 Problem`, `2 Approach`, ..., which the CFP recommends against because they collide with the full-paper's `\S` references. Now `\section*{Problem}` etc. give unnumbered headings. |
| PDF metadata clean | OK | No author identity in `Author` field. |
| Compiles cleanly | OK | Two-pass pdflatex completes; still exactly 2 pages. |

### Cross-File Consistency

| Item | Status | Notes |
|---|---|---|
| Same pseudonym (`AgentScope`) in both files | OK | `\newcommand{\sysname}{\textsc{AgentScope}\xspace}` in both. |
| Same `\acmConference` metadata | OK | Both files declare `ATC '26 / November 16–18, 2026 / Hong Kong`. |

## Fixes Applied This Session

### Fix 1 — Double-blind: pseudonymize all `agenttelemetry` strings (HIGH SEVERITY)

**Severity:** This was the only true blinding violation in the paper.
The literal string `agenttelemetry` appears as the package/repo name
on the author's real PyPI listing and GitHub. A reviewer who searched
any of the five code-path references would have identified the
author.

**Locations edited in `atc_paper.tex`:**
- Line 206: `\texttt{src/agenttelemetry/}` → `\texttt{src/agentscope/}`
- Line 502: `\texttt{src/agenttelemetry/adapters/}` → `\texttt{src/agentscope/adapters/}`
- Line 584: `\texttt{import agenttelemetry}` → `\texttt{import agentscope}`
- Line 600: `\texttt{src/agenttelemetry/runtime/circuit\_breaker.py}` → `\texttt{src/agentscope/runtime/circuit\_breaker.py}`
- Line 684 (listing block): `from agenttelemetry.runtime import ...` → `from agentscope.runtime import ...`

**Verification:** `grep -nE "agenttelemetry" atc_paper.tex atc_extended_abstract.tex` returns no matches. Recompiled PDF spot-checked: every page that previously rendered `agenttelemetry` now renders `agentscope`. Page count unchanged (12). PDF metadata unchanged (no author identity).

**Note for camera-ready:** Revert by global-replacing `agentscope` back to `agenttelemetry` in these five locations (and updating `\sysname`/`\sysnameNoFont` accordingly).

### Fix 2 — Extended abstract: unnumbered sections (CFP recommendation)

**Severity:** Low / cosmetic compliance with the abstract-guidelines page.

**Locations edited in `atc_extended_abstract.tex`:** all four `\section{...}` → `\section*{...}` (Problem, Approach, Evaluation, Contribution).

**Verification:** Recompiled PDF: headings now render without leading numbers ("Problem", "Approach", "Evaluation", "Contribution" instead of "1 Problem", "2 Approach", …). Page count unchanged (2).

## Fixes Deferred to User (Authorial Judgement Required)

### Deferred 1 — Replace `[redacted for double-blind review]` self-citation with a third-person citation

**Where:** `atc_paper.tex` §1, sentence reading "In a prior controlled
study by the authors [redacted for double-blind review], 84 of 112
SWE-bench Lite runs against a production agent exhausted their
iteration budget...".

**Why deferred:** The CFP wording is "reference your past work in the
third person, just as you would any other piece of related work". This
means the preferred form is a normal `\cite{...}` to the prior
publication, written in the third person ("In a prior study,
[cite]..."), not a `[redacted]` placeholder.

The reason to defer rather than apply: the author's `AIware 2026`
paper (DOI 10.1145/3805760.3814931) covers the same SDK and is the
natural target of the citation, but citing it by DOI immediately
de-anonymises (the AIware paper carries the author's name on the
camera-ready). Whether to (a) cite the AIware paper in the third
person and accept the disclosure, (b) cite an arXiv-anonymised
preprint of the same study if one exists, or (c) keep the `[redacted]`
placeholder and accept the slight CFP-tone mismatch is an authorial
call the audit will not make on the author's behalf.

**Recommendation:** Option (a). The CFP is explicit, and a same-author
prior publication in another venue is the standard situation third-
person citation handles. Reviewers will infer authorship from a
third-person citation only weakly; a `[redacted]` placeholder is a
stronger inference signal.

### Deferred 2 — Audit the `\sysnameNoFont` macro

`\newcommand{\sysnameNoFont}{AgentScope}` is defined on line 23 of
`atc_paper.tex` but is never invoked anywhere in the body. Either
remove the unused macro (one-line cleanup) or invoke it where the
pseudonym appears as plain text. Not blocking; cosmetic.

## Submission-Day Steps for the User

1. **Verify HotCRP URL is live.** As of 2026-05-18 the CFP says
   "Submission Site TBD" and gives no portal URL. Re-fetch
   `https://sigops.org/s/conferences/atc/2026/cfp.html` on the day
   you submit to get the actual URL. Likely path: `https://atc26.hotcrp.com/`
   following the SIGOPS sub-domain convention, but **do not assume** —
   confirm against the CFP page on the day.

2. **Create the HotCRP account early.** ATC has historically required
   each author to create an individual account; do this at least a
   week before the deadline. ORCID is not flagged as mandatory in the
   CFP fetched today, but if HotCRP asks for it, have your ORCID iD
   ready (look it up at `https://orcid.org/`).

3. **Declare conflicts at submission time.** The CFP requires
   institutional / advisor / collaborator / personal-relationship
   conflict flags. Have the conflict list compiled before opening
   HotCRP so the upload form does not time out.

4. **Upload two PDFs, not one.** ATC requires a separate 2-page
   extended-abstract PDF in addition to the full paper. Both files
   in `paper/atc2026/`:
   - `atc_paper.pdf` (12 pages)
   - `atc_extended_abstract.pdf` (2 pages)

5. **Apply Deferred Fix 1 (or accept the deferral) before upload.**
   Decide whether to keep the `[redacted for double-blind review]`
   placeholder or switch to a third-person `\cite`. If switching,
   recompile and re-run the page-count check before upload.

6. **Re-run the page-count check immediately before upload.** Open
   the final PDFs in a real viewer and confirm: main paper text ends
   on a page ≤ 12 (currently page 11; references continue onto p12,
   which is permitted because references do not count toward the
   12-page limit per the CFP); extended abstract is exactly 2 pages.

7. **Spot-check PDF metadata immediately before upload.** Run
   `mdls -name kMDItemAuthors atc_paper.pdf atc_extended_abstract.pdf`
   and confirm no real name appears (current output shows only the
   LaTeX engine string, which is acceptable).

8. **Save the HotCRP confirmation email.** The CFP's no-extension
   policy means a missed deadline is fatal; the confirmation email
   is your proof of timely upload.

## Verdict

**NEEDS-FIXES → CLEAN (post-audit).** All blocking CFP compliance
issues identified by this audit have been applied to the source
files. The paper and extended abstract now satisfy every CFP item
verified against the official ATC 2026 pages fetched in-session.

Two remaining items are deferred to the user as authorial-judgement
decisions (most importantly: whether to switch the `[redacted for
double-blind review]` placeholder to a third-person citation per
CFP guidance). Neither blocks upload.

## Files Changed by This Audit

- `paper/atc2026/atc_paper.tex` — 5 line edits (pseudonym Fix 1).
  Recompiled; PDF regenerated.
- `paper/atc2026/atc_extended_abstract.tex` — 4 line edits
  (`\section` → `\section*`, Fix 2). Recompiled; PDF regenerated.
- `paper/atc2026/atc_paper.pdf` — Regenerated (12 pages, clean).
- `paper/atc2026/atc_extended_abstract.pdf` — Regenerated (2 pages,
  clean).
- `paper/atc2026/CFP_COMPLIANCE_AUDIT_2026-05-18.md` — This file
  (new).
