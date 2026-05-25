# Cold-reviewer report, round 1

**Reviewer persona:** IEEE Software magazine reviewer with 10+ years of experience; member of the Human-Centric AI for SE SI guest-editor team. Has read the CFP scope, the magazine's general feature-article rules (4,200 words including 250 per fig/table, ≤15 refs, 150-word abstract, three actionable insights bullet box), and the author's concurrent Edge-Cloud SI submission for orthogonality check. Skeptical, no anchoring.

**Manuscript reviewed:** `ieee_sw_humancentric_paper.pdf` (5 pages, 192,888 bytes), `ieee_sw_humancentric_paper.tex` (369 lines).

---

## Summary verdict: WEAK_ACCEPT

This is a competent, magazine-voiced feature article with a genuinely human-centric thesis (operator cost, persona-stratified evidence, calibration knobs that affect what the on-call engineer actually experiences). The orthogonality vs. the author's concurrent Edge-Cloud submission is convincing on the corpus dimension and on the research-question dimension. Three actionable insights are present, prominent, and well-mapped to the evidence. The format is within budget.

That said, four MAJOR concerns and several MINOR ones keep this from a clean ACCEPT.

---

## MAJOR issues

### M1. The "simulated personas" framing is the load-bearing structural risk and the manuscript does not work hard enough to defuse it.

The headline finding (+66.7pp lift in persona-averaged diagnostic accuracy) is generated entirely by LLM-played personas, not human developers. The threats section acknowledges this in one paragraph, but a human-centric reviewer will read the lift number first and the methodology second, and will reach the simulated-persona disclosure on page 4. This is the single most likely reject lever a Human-Centric SI editor pulls.

**Fix:** Move the methodological frankness up. The first time the persona finding appears (Section III), state that personas are LLM-simulated *in the same paragraph* as the accuracy number. The threats section can then go deeper. The current opening of Section III says "We ran six engineering personas... each instructed to diagnose..." — it does not say *what* ran the personas until later in the paragraph. Be explicit on first contact.

### M2. Self-citation of the AIware'26 paper is structurally honest but does not yet explain *what this paper does not claim* from it.

The first-page footnote and the threats section both disclose author overlap. Neither says, in body text, "the prior paper measured X and Y; the present paper measures W, which the prior paper did not." A reviewer who reads quickly may not absorb the disclosure-by-footnote and will worry the contribution is a re-skin of the prior work.

**Fix:** Add one sentence to the Section II SDK-introduction paragraph along the lines of: "The prior work introduces the SDK and quantifies its failure-detection coverage on a fixed benchmark; it does not measure the operator cost we characterize here." This makes the orthogonality explicit in the body, not just in the footnote.

### M3. The threshold-sensitivity section's "dangerous knob" framing on `token_growth_factor` is the most novel finding in the paper, but the evidence presentation does not make the false-negative substitution as concrete as it could be.

Table 2 shows alert count dropping from 26 (default) to 21 at `token_growth_factor=1.45`. Section IV says context-overflow alerts "drop to zero." But the table reports total alert counts, not per-detector counts, so a careful reader has to infer that the 5-alert difference is the entire context-overflow class. The supporting prose says it clearly, but the table does not back it visually.

**Fix:** Add a brief inline parenthetical in the table footnote or the prose: "(context-overflow alerts contribute 5 to the default total; raising `token_growth_factor` to 1.45 zeroes that contribution while leaving infinite-retry alerts at 21 unchanged.)" Or — better — add a small per-detector breakdown column to Table 2 for the `token_growth_factor` rows only.

### M4. The 4,200-word budget computation needs to be explicit to the reviewer, because magazine editors will count.

The `detex`-based count came in at 3,315 words of prose plus 3 tables × 250 words = 4,065 effective. That is under budget but only just. The author should ship a `wordcount.txt` file alongside the PDF so the editor does not have to re-compute. Also, IEEE Software counts tables as "table area" not as word-equivalents in some reviewer instructions — confirm the editor's exact rule before relying on the 250-per-table allowance.

**Fix (process):** Add a `wordcount.md` artifact to the submission directory. Pre-check with EIC Sigrid Eldh by email if the budget interpretation is ambiguous.

---

## MINOR issues

### m1. "Three actionable insights" box and Section VI duplicate each other almost verbatim.

The box at the front and the prose in Section VI ("Three calibration moves on-call teams can make on Monday" in the outline, though the section did not survive into the .tex by that title — it was distilled into the Conclusion section and the actionable-insights box) are paraphrases of each other. The CFP requires the box; the prose can be shorter and reference the box.

**Fix:** Either drop a dedicated Section VI in the .tex (currently the actionable-insights content lives only in the front box and the Conclusion), or expand Section VI to provide *additional* operator-decision context per insight that the box does not have room for. Currently the body has Sections I, II, III, IV (cross-tool), V (which is detector applicability), VI (threats), VII (conclusion). The actionable-insights bullets are in the box at the top but not elaborated in body text. This is acceptable but feels thin — consider adding one paragraph of "how to apply this knob" prose to Section IV per insight, so the box is the surface and the body is the depth.

### m2. The lead vignette uses "junior on-call engineer" and the persona table includes "Junior Dev." A reader will conflate these — the persona is a development persona (junior dev writing code), but the vignette is an on-call persona (junior engineer carrying the pager).

**Fix:** Clarify the vignette: "A junior engineer, new to the on-call rotation, is paged…" — or change the persona table's "Junior Dev" label to "Junior SWE" and explicitly note the personas were prompted as developers reviewing failed traces, not as on-call rotators.

### m3. References cap is 15; the paper lists 12 numbered references. Two of the cited entries are URL-only (\cite{atrepo} and the OpenLLMetry/LangChain entries); IEEE numeric style permits these but the editor should confirm.

**Fix:** No structural change required; flag for self-check before submission.

### m4. The threshold-sensitivity sweep's claim that `cost_threshold` is "insensitive" is true in the tested range [0.05, 0.15] USD but a reviewer will ask "what about extreme values, e.g., 0.001 or 5.0?"

**Fix:** Add a brief sentence acknowledging the range tested and stating that outside it (very low values would page on essentially every run; very high values would never page) the knob would matter; the operator-relevant range is the one tested. This pre-empts the reviewer comment.

### m5. The Wilson confidence intervals are stated for accuracy in the abstract and table footnote, but no CIs are reported for the threshold-sensitivity counts.

**Fix:** Acknowledge as a deliberate choice (counts are absolute, not estimates) or report a Poisson CI for the alert counts. The latter is cleaner.

### m6. The Section V detector-applicability finding (35.3% non-reconstructible) is interesting but n=17 is genuinely small. The paper notes this; consider whether the finding warrants a section of its own or could be folded into the threats section to save 100 words.

**Fix (optional):** Either strengthen the section by adding one or two illustrative example issues (which the corpus has) or fold it into the threats section. If kept as a section, add a sentence on why the 17 issues were chosen (sampling method).

### m7. The lead vignette is generic ("a Django backport"). A specific instance from the persona-study corpus (e.g., `django__django-10914`, which the persona study uses) would make the vignette concrete and verifiable.

**Fix:** Replace "Django backport" with the specific instance, and ensure that the lead's diagnostic outcome matches what the persona study found.

---

## NIT issues

### n1. Section heading style is inconsistent — Section II is "Two axes of operator cost" (sentence case); Section V is "Detector applicability on real-world issues" (sentence case); but Section IV is "Cross-tool head-to-head" (hyphenated). All fine, but IEEE Software prefers Title Case in section headings — check the latest template.

### n2. The em-dashes between sentences ("--- the kind of false-positive flood that motivates an engineering manager...") are stylistically heavy in places. Magazine voice usually prefers periods or commas; em-dashes work but use fewer of them.

### n3. The actionable-insights box uses `\begin{mdframed}` from the `mdframed` package. IEEE Software's IEEEtran template does not standardize this; safer to use `\begin{tcolorbox}` (or a simple `\fbox` with `\parbox`) if the editor's submission system has restrictive package whitelists.

### n4. The data inventory artifact promised in the outline (`data_inventory.json`) is not yet present in the submission directory. Reviewer cannot independently verify every number in the tables against a corpus file.

---

## Orthogonality vs. Edge-Cloud submission: PASS

The orthogonality claim is convincing on inspection. The Edge-Cloud paper uses 960 SWE-bench-Lite outcome runs; this paper uses persona diagnostics + span counts + FPR detector results + threshold sweeps + GitHub issue analysis. The research questions ("does the intervention transfer across model tiers" vs. "what does it cost engineers to use this observability stack") are genuinely disjoint. The first-page footnote disclosure is correct and complete.

If I were the editor, I would not reject either paper on grounds of overlap.

---

## Magazine voice: ACCEPTABLE-TO-STRONG

The lead is concrete (the 3am pager). The prose avoids academic hedging in most places. Tables carry evidence. The "three actionable insights" box is well-mapped to the body. Section II's "two axes of operator cost" framing is the kind of accessible synthesis IEEE Software readers expect.

Areas where the voice could lean more magazine-y:

- Section III's "We chose simulated personas because the design space..." is more academic than magazine. Consider: "We used simulated personas to map the full design space — hundreds of detector-portfolio × persona × trace combinations would be impractical with human subjects."
- Section VII's "The next step for the software-engineering research community..." reads more like an academic call-to-arms than a magazine close. Consider sharpening to a one-line practitioner directive: "The next observability stack you evaluate should publish persona-stratified diagnostic latency, not just headline accuracy."

---

## Page/format compliance: PASS

- 5 pages compiled (well under the implicit 7-8 for IEEE Software feature articles).
- 3 tables, 0 figures, well under the 6-element cap.
- 12 references, under the 15 cap.
- 150-word abstract (149 words counted on first pass — confirm with a final count).
- Three actionable insights bullet box present on page 1.
- Author bio present.
- IEEEtran journal class used.
- First-page thanks-footnote with author-overlap and concurrent-submission disclosures present.

---

## Required for ACCEPT (clean) on next round:

- Fix M1 (move simulated-persona disclosure into Section III's first paragraph)
- Fix M2 (one body sentence on what AIware'26 does not measure)
- Fix M3 (per-detector breakdown for `token_growth_factor` rows in Table 2 or a sentence in the prose making the false-negative substitution unambiguous from the table alone)
- Fix M4 (ship `wordcount.md` artifact)
- Apply m1, m2, m4, m5, m7 (low-cost, high-trust improvements)

Without these, this is WEAK_ACCEPT. With these, ACCEPT.

---

**Reviewer signature:** (single-blind editorial reviewer; cold pass; no prior context from this author)
