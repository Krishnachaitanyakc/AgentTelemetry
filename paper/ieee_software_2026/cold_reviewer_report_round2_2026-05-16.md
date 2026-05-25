# Cold Reviewer Re-Review (Round 2) — IEEE Software Edge-Cloud Continuum Submission

**Reviewer role:** Same skeptical cold reviewer from Round 1.
**Paper:** `ieee_software_paper.tex` (Krishna Chaitanya Balusu, Independent Researcher)
**Date:** 2026-05-16
**Round:** 2 (post-revision verification)

---

## Per-Category Verdicts (at-a-glance)

| # | Fix Category | Verdict |
|---|---|---|
| 1 | CFP fit (edge-cloud framing in §I + Threats item on edge-scope) | **FIXED** |
| 2 | Self-overlap disclosure | **FIXED** |
| 3 | Citation fixes ([mast] downgrade, [aiware2026] URL, [otel] version) | **FIXED** |
| 4 | "~8,000 spans" claim struck or replaced | **FIXED** |
| 5 | Missing limitations M1–M5 | **PARTIAL** (M1 disclosed in author footnote not Threats; M2 not added; M3 not added; M4 added; M5 added) |

**Final verdict: REVISE-AGAIN.** The five Round-1 categories are mostly addressed and the fixes that were made are substantive, not cosmetic. However, the limitations category has two gaps — M2 (no external-instrumentation comparison) and M3 (baseline-dependent power) — that any careful reviewer will still hit. These are small, targeted edits (one bullet each in §VII Threats), not structural rewrites. After those two bullets are added, the paper is PASS.

---

## Category 1 — CFP Fit: **FIXED**

**Round-1 ask:** (a) move the edge-cloud framing to §I (not just §V), (b) add a Threats item on edge-scope, (c) tie the tier-coverage finding to a concrete operational mechanism justifying the tier coverage.

**What changed:**

- Title now reads: "...Closed-Loop Agent Recovery via Vendor Agent CLIs **for Edge-Cloud Deployments**." The phrase "edge-cloud" is in the title itself, not just buried in §V. This is the single most important framing fix and it was made.
- §I (Introduction) opens with: *"The edge-cloud continuum increasingly hosts heterogeneous LLM agent deployments. Latency-constrained edge inference at the network perimeter runs budget-tier models like Haiku 4.5 inside vendor CLI containers; high-capability cloud serving runs frontier-tier models like Opus 4.6 or GPT-5.5..."* This is no longer buried at §V — it leads the paper and ties the tier-coverage design (Haiku/Sonnet/Opus/GPT-5.5) directly to edge-vs-cloud tier separation. This is the most substantive Round-1 fix and it was made well.
- Abstract sentence 1 now reads "Production deployments of LLM-based autonomous agents at the edge-cloud continuum..." — the edge-cloud framing is in the abstract's first sentence, not the penultimate sentence as it was in Round 1.
- §VII Threats now contains a new bullet: **"Edge-scope is operational, not experimental."** This bullet explicitly acknowledges that all 960 runs are on cloud-tier compute (Apple M-series), and explicitly identifies the edge-specific phenomena not measured (constrained bandwidth, intermittent connectivity, edge-side resource contention). It even adds a forward-looking inference: *"A practitioner running Haiku 4.5 on a network-edge appliance is more likely to see the patch-rate collapse we observed in v2-Haiku..."* This satisfies the Round-1 ask precisely.

**Verdict:** FIXED. The CFP fit is no longer cosmetic. A skeptical reviewer can still ding the paper for not running on actual edge hardware, but the framing now treats edge-cloud as a load-bearing operational dimension rather than a bolt-on word. The Threats bullet preempts the "this isn't an edge paper" critique with a fair acknowledgement.

---

## Category 2 — Self-Overlap Disclosure: **FIXED**

**Round-1 ask:** Add a one-sentence disclosure footnote at the first [aiware2026] cite or in Acknowledgments stating the cited work is by the same author.

**What changed:** The author block now contains a `\thanks` footnote (line 25):

> *"The cited prior work \cite{aiware2026} is by the same author; this paper deliberately replicates and stress-tests that prior work in a different deployment regime (multi-tier vendor agent CLIs spanning the edge-cloud continuum). All citations are written in third-person form for academic register; the author overlap is disclosed here."*

This is exactly the wording recommended in Round 1, plus an explicit note that the third-person form is a stylistic choice (not deception). It appears on the title page where every reviewer sees it. The third-person citation register is preserved throughout the body, which was also Round 1's recommendation.

**Verdict:** FIXED. This was the most reputationally sensitive fix and it is handled cleanly. The disclosure is unambiguous, on the first page, and converts the self-overlap from a credibility risk into a credibility feature.

---

## Category 3 — Citation Fixes: **FIXED** (all three sub-items)

**Round-1 asks:** (a) [mast] downgraded from "NeurIPS 2025" to "arXiv preprint"; (b) URL added to [aiware2026]; (c) [otel] version pin softened.

**What changed (verified against bibliography, lines 247–272):**

- **[mast]:** Now reads `\emph{arXiv preprint arXiv:2503.13657}, 2025.` The unverified "Proc. NeurIPS, 2025" claim is gone. A reviewer who checks the arXiv ID will find the paper exactly as described. **FIXED.**
- **[aiware2026]:** Now includes the AIware 2026 Benchmark & Dataset Track URL: `\url{https://2026.aiwareconf.org/track/aiware-2026-benchmark---dataset-track}`. The DOI is still present (DOI: 10.1145/3805760.3814931) but the URL gives a reviewer a working verification path even before ACM DL indexing completes. **FIXED.**
- **[otel]:** Now reads "*OpenTelemetry Specification*, 2026. [Online; accessed 2026-05-16]." The brittle "v1.30, 2024" version pin is gone, replaced with an accessed-date format that does not promise a version that the live page does not display. **FIXED.**

**Verdict:** FIXED on all three. None of these citations will trip up a reviewer who does a citation-check pass.

---

## Category 4 — "~8,000 spans" Claim: **FIXED**

**Round-1 ask:** Strike "~8,000 spans" from the abstract OR compute and back it with a verified number.

**What changed:** The abstract now reads:

> *"Across all eight (model × harness) cells we ran --- 960 instance-runs totalling **2,991 LLM-call iterations** ---"*

I independently verified this against `data_inventory.json`. Summing avg_iterations × 60 across the 16 cells:

- v1 cells (×60 each): 1.03+1.03+1.0+1.02+1.02+1.0+1.0+1.0 = 8.10 → 486 iterations
- v2 cells (×60 each): 4.03+4.03+5.30+5.70+6.45+7.10+4.47+4.67 = 41.75 → 2,505 iterations
- **Total: 486 + 2,505 = 2,991 iterations.** Exact match.

The replacement claim is verifiable, modest, and accurate. The "~8,000 spans" claim (which was the only data-section claim that failed verification in Round 1) is gone.

**Verdict:** FIXED. The arithmetic checks out. This is exactly the right fix — strike the unverifiable claim, replace with a precise count grounded in the inventory.

---

## Category 5 — Missing Limitations: **PARTIAL**

**Round-1 asks (5 items):** M1 (same-author replication); M2 (no external instrumentation comparison); M3 (baseline-dependent power); M4 (narrow trigger generalization); M5 (multiple-comparisons).

**Per-item verification:**

### M1 (same-author replication): **PARTIAL — addressed in author footnote, not in Threats**

The author footnote (line 25, see Category 2) discloses that the replication is by the same author and explicitly frames it as a "same-author cross-tier stress test." This addresses the substance of M1 — a reviewer cannot claim the same-author overlap was hidden. However, Round 1 specifically asked for this in the **Limitations** section as a methodological caveat, not just as a disclosure footnote on the title page. The current placement covers the ethics/transparency angle but not the methodological-weakness angle (i.e., "same-author replication cannot detect shared bugs in the trigger definition or harness, which is a recognized limitation of single-lab replication studies"). A picky reviewer will still ding the paper for not naming this as a methodological limitation in §VII or the Limitations section.

**Status:** Substantively addressed via the author footnote, but the methodological framing (vs. the disclosure framing) is missing. **PARTIAL.**

### M2 (no external instrumentation comparison): **NOT FIXED**

Round 1 asked: *"The paper argues that vendor CLIs 'absorb' the agentic loop, but does not compare against any practitioner-instrumented stack (e.g., OpenTelemetry GenAI conventions applied directly to raw API calls, or LangChain with the LangSmith tracer). Without this comparison, the claim that 'the practitioner cannot observe' is asserted but not measured."*

I searched §V, §VII (Threats), and the Limitations section. **There is no acknowledgement that the practitioner-observability claim is asserted rather than measured against an alternative instrumented stack.** The closest §V comes is "the wrapper-level signals about whether the agent is using your provided tools at all are the practitioner-accessible proxy" — but this restates the claim, it does not flag the comparison-not-done limitation.

L2 ("We did not test raw-API access") is adjacent but addresses a different concern: raw-API access changes model *behavior* (because the loop runs in the practitioner process), not the *observability comparison*. M2 is about whether existing OTel GenAI conventions / LangSmith / similar stacks could have observed *more* than this paper claims they can — that is genuinely not in the paper.

**Status:** NOT FIXED. A skeptical reviewer will ask: "did you compare against any actually-deployed practitioner observability stack, or just assert the limitation?" The paper does not preempt this.

### M3 (baseline-dependent power): **NOT FIXED**

Round 1 asked the paper to acknowledge that the "powered to detect a true +25pp effect" claim is misleading for cells with baseline rates of 85%+ (Opus, GPT-5.5, Haiku v1) where the +25pp would require >100% rates (ceiling effect).

The §VII "Sample size" bullet reads:
> *"At n=60 per arm we are powered to detect a true +25pp effect at α=0.05 with β=0.2 but not the published +12.5pp effect. The original work was at n=24 and reported p=0.53; our n=60 extends the statistical power but does not approach the ~214 instances per arm needed..."*

This is unchanged in substance from Round 1. There is no acknowledgement of the ceiling-effect / baseline-dependent power issue. A reviewer with statistics training will catch this — Opus baseline is 85–88%, so the "powered to detect +25pp" claim is mathematically impossible for that cell. The wording would be saved by adding a single sentence: *"Note that for cells with baseline patch rates above 75% (Opus, GPT-5.5, Haiku v1), this power calculation is constrained by the ceiling effect; a true +25pp effect would require patch rates exceeding 100% in those cells, so our effective sensitivity to a +25pp effect is concentrated on the lower-baseline cells (Sonnet v1, all v2 cells)."*

**Status:** NOT FIXED. One missing sentence in §VII Sample size.

### M4 (narrow trigger generalization): **FIXED**

§V recommendation (3) now reads:
> *"We tested one such trigger (the exact-string-repeat trigger of the cited prior work \cite{aiware2026}); we do not have direct data on related trigger classes such as fixed-argument-match or specific-tool-invocation-pattern triggers, and our finding does not directly refute those."*

This is exactly the scope-narrowing that Round 1 asked for. The generalization is no longer asserted as universal; it is properly scoped to "this specific trigger class," with sibling trigger classes flagged as untested.

**Status:** FIXED.

### M5 (multiple-comparisons): **FIXED**

§IV.D Finding 4 now closes with:
> *"Given the lowest observed p-value is 0.17 and the headline finding is null, multiple-comparison correction would not change the verdict."*

This is exactly the preemptive line Round 1 asked for. A reviewer who raises multiple-comparisons concerns is met head-on, with the correct argument (none significant uncorrected → none significant corrected).

**Status:** FIXED.

### Category 5 summary

| Sub-item | Verdict |
|---|---|
| M1 same-author replication | PARTIAL (in author footnote; not in Threats/Limitations as methodological limit) |
| M2 no external instrumentation comparison | NOT FIXED |
| M3 baseline-dependent power | NOT FIXED |
| M4 narrow trigger generalization | FIXED |
| M5 multiple-comparisons | FIXED |

**Category 5 overall verdict:** PARTIAL. 2 of 5 (M2, M3) are not addressed; M1 is addressed via disclosure but not via methodological-limitation framing.

---

## Fresh Pass — Any New Issues Introduced?

I re-read the revised paper end-to-end checking for new issues that the edits may have created. Findings:

**New issue 1 (minor, cosmetic):** The Author Biography (line 279) still contains the awkward phrase *"His research interests include 3 very brief topics: agent observability..."* — the literal phrase "3 very brief topics" reads as leftover instruction text from a template, not a researcher bio. This was present in Round 1 but not flagged then; it should be edited to *"His research interests include agent observability, deployment-experience studies of telemetry-derived interventions, and reproducibility methodology for systems research."* before submission. Not a Round-2 regression; flagging now because it is below the threshold IEEE Software copy-editing will catch.

**New issue 2 (minor, factual):** §IV.D mentions *"with seven of eight ≥ 0.79 and six of eight at exactly 1.00"*. Counting from the inventory the Fisher p-values are: 0.79, 0.17, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00 — that's 7 cells ≥ 0.79 and **six** at exactly 1.00. Verified correct (matches Round 1 audit row 22). No regression.

**New issue 3 (minor, internal consistency):** The abstract now claims "2,991 LLM-call iterations" but the body never references this aggregate count. A reader who checks the abstract figure against the body will not find a confirming sentence in §IV or §III. Minor — the count is verifiable from Table I averages × 60, but a single recap sentence in §III.D or §IV intro ("across the 960 runs, the harness logged 2,991 LLM-call iterations in total") would tighten the consistency. Not a regression; an opportunity to remove a reviewer follow-up.

**New issue 4 (minor, abstract count claim):** The abstract still says "*max repeat = 1 across all 960 runs*" referring to query repeats. This is *only literally true for the v2 cells* (the 480 v2 runs); the 480 v1 cells have max_repeats = 0 (no searches at all). The Table I caption disambiguates ("max_repeats=0 across all v1 runs; max_repeats=1 across all v2 runs") but the abstract elides this. A pedantic reviewer could call this misleading. Not a regression — this was in Round 1's text — but a candidate for tightening: *"max repeat = 1 across the 480 v2 runs that exercised the search path; zero searches in the 480 v1 runs."*

**No structural / consistency regressions.** All Round-1 numerical claims still trace correctly to the inventory. The trace iterations count is new and was independently verified. The edits did not break any internal cross-references, did not introduce a citation that contradicts another, did not produce overlap between the new Threats bullet and the existing L-items, and did not break the page budget (PDF compiles to 6 pages, within IEEE Software feature-article convention).

---

## Final Verdict: **REVISE-AGAIN**

The four cleanly-fixable categories (CFP fit, self-overlap disclosure, citation fixes, ~8,000-spans claim) are all **substantively fixed**. The fixes are not cosmetic — the edge-cloud framing in §I is real, the disclosure footnote is unambiguous, the citation downgrades are correct, and the iteration count is exact.

But the limitations category has two gaps:
- **M2 (no external instrumentation comparison)** — not addressed anywhere in the paper.
- **M3 (baseline-dependent power)** — not addressed; the "powered to detect +25pp" claim still ignores the ceiling effect at high-baseline cells.

Plus M1 is addressed via disclosure (Category 2 fix) but not via Threats/Limitations framing as a methodological weakness — a borderline call, but a careful methods reviewer will still flag it.

These are 3 short bullets to add to §VII (Threats to Validity) or to the post-Conclusion Limitations section. Estimated effort: 30 minutes of writing.

**What to add to reach PASS:**

1. A new §VII bullet — *"External instrumentation comparison not performed."* — acknowledging that the practitioner-cannot-observe claim is asserted relative to wrapper-level CLI subprocess observation and is not measured against alternative observability stacks (OTel GenAI applied to raw API calls; LangSmith / LangFuse traces; vendor-provided telemetry endpoints), and naming this comparison as future work.

2. One sentence in the existing §VII "Sample size" bullet — *"For cells with baseline patch rates above 75% (Opus, GPT-5.5, Haiku v1), this power calculation is constrained by the ceiling effect; effective sensitivity to a +25pp effect is concentrated on the lower-baseline cells."*

3. One sentence in the post-Conclusion Limitations section — a new "L5: Same-author replication" item naming the methodological caveat (cannot detect shared bugs in trigger definition or harness; same-lab replication is weaker than independent-lab replication on certain failure modes; cross-tier scope partially compensates by testing 4 model classes from 2 vendors).

Plus the cosmetic fix to the bio line "3 very brief topics" (one-line edit).

With those three additions and the bio cleanup, this paper is PASS and submittable to IEEE Software's Edge-Cloud Continuum special issue with high confidence of clearing desk review and entering substantive peer review.

**Round-2 verdict: REVISE-AGAIN (small, targeted, ~30 minutes of edits).**
