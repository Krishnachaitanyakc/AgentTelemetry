# Cold Reviewer Report — IEEE Software Edge-Cloud Continuum Submission

**Reviewer role:** Skeptical, no-loyalty cold reviewer for IEEE Software special issue desk review.
**Paper:** `ieee_software_paper.tex` (Krishna Chaitanya Balusu, Independent Researcher)
**Date:** 2026-05-16
**Verdict (jumping ahead so the editor sees it first):** **REVISE-AND-RESUBMIT**

The empirical spine is sound, the data is fully verified, and the contribution is honest. But there are non-trivial issues that must be fixed before submission: (a) the CFP fit is thinner than the paper acknowledges, (b) the [aiware2026] self-citation overlap is technically third-person but the framing repeatedly says "the original work" and "the published intervention" in a way that hides the same-author overlap, (c) one citation venue ([mast] → NeurIPS 2025) is unverified, (d) several numerical claims in the prose are softened versions of what the table shows and should be tightened, and (e) the limitations section misses two substantive items a reviewer will hit. Detail below.

---

## 1. Numerical Claim Audit

Every numerical claim was traced back to `data_inventory.json` (which itself passed independent recomputation per `data_inventory_verification_2026-05-16.md`, 0 discrepancies). Format: claim, paper location, inventory source, verdict.

| # | Claim (paper) | Section/Line | Inventory source | Verdict |
|---|---|---|---|---|
| 1 | "+12.5pp recovery rate" from prior work | Abstract; §I; §II | External (aiware2026); paper §II says "9/24 vs 6/24 = +12.5pp" — that arithmetic is correct | PASS (external, but arithmetic checks) |
| 2 | "four production-tier model classes from two vendors" | Abstract; §I; §III.C | Models tested: Opus 4.6, Sonnet 4.6, Haiku 4.5 (Anthropic) + GPT-5.5 (OpenAI). 4 models × 2 vendors. | PASS |
| 3 | "n=60 per arm" | Abstract; §I; throughout | Inventory shows n=60 for every condition in every run. | PASS |
| 4 | "960 instance-runs total" | Abstract; §I; §IV | 8 runs × 2 conditions × 60 = 960. | PASS |
| 5 | "8 (model × harness) cells" / "16 (model × harness × condition) cells" | Abstract; §I; §IV | 4 models × 2 harnesses = 8 cells; × 2 conditions = 16. | PASS |
| 6 | "trigger condition never fired even once" / "fires zero times across all eight cells" | Abstract; §I; §IV | `avg_intervention_triggers = 0.0` in all 16 cells. | PASS |
| 7 | "passive harness, mean iterations ≤ 1.03" | Abstract | v1 cells: 1.00, 1.00, 1.02, 1.00, 1.03, 1.03, 1.02, 1.00. Max = 1.03. | PASS |
| 8 | "mean search calls 0.0" under passive | Abstract; §IV.A | All 8 v1 conditions show `avg_searches = 0.00`. | PASS |
| 9 | "Opus 4.6 mean searches 3.23/3.42" | §IV.B | v2-opus control 3.23, intervention 3.42. | PASS |
| 10 | "GPT-5.5 mean searches 2.62/2.77" | §IV.B | v2-gpt55 control 2.62, intervention 2.77. | PASS |
| 11 | "Opus 4.6 mean iterations 4.03/4.03" | §IV.B | v2-opus 4.03/4.03. | PASS |
| 12 | "GPT-5.5 mean iterations 4.47/4.67" | §IV.B | v2-gpt55 4.47/4.67. | PASS |
| 13 | "Opus 4.6 patch rates 88.3%/90.0%" v2 | §IV.B | 53/60 = 88.33%; 54/60 = 90.0%. | PASS |
| 14 | "GPT-5.5 patch rates 83.3%/85.0%" v2 | §IV.B | 50/60 = 83.33%; 51/60 = 85.0%. | PASS |
| 15 | "Sonnet 4.6 patch rates 3.3%" v2 | Abstract; §IV.C | 2/60 = 3.33% in both v2-sonnet conditions. | PASS |
| 16 | "Haiku 4.5 patch rates 11.7%–13.3%" v2 | Abstract; §IV.C | 8/60 = 13.33% control; 7/60 = 11.67% intervention. | PASS |
| 17 | "patch_suppressions averages 4.67–5.75" v2 Sonnet/Haiku | §IV.C | v2-sonnet: 4.67/5.07; v2-haiku: 5.12/5.75. **Range "4.67–5.75" is correct.** | PASS |
| 18 | "22–25 errors per 60 runs for Sonnet" | §IV.C | v2-sonnet errors: control 25, intervention 22. | PASS |
| 19 | "10–12 errors for Haiku" v2 | §IV.C | v2-haiku errors: control 12, intervention 10. | PASS |
| 20 | "no Δ exceeds 3.3pp in absolute magnitude except v1-Sonnet's +13.3pp" | §IV.D | Deltas: 3.33, 13.33, 0, 0, 1.67, 0, -1.67, 1.67. **Max abs (ex-Sonnet) = 3.33pp.** | PASS |
| 21 | "every Fisher's exact two-sided p ≥ 0.17" | §IV.D | Fisher p values: 0.79, 0.17, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00. Min = 0.17. | PASS (just barely — round-down would be misleading) |
| 22 | "seven of eight at or near 1.00" | §IV.D | 7 of 8 are 0.79 or higher; 6 are exactly 1.00. The "seven at or near 1.00" is fair (0.79 is "near" 1.00 in context). | PASS (defensible) |
| 23 | Sonnet v1 baseline 60% / intervention 73.3% | Table I; §IV.A | 36/60 and 44/60. | PASS |
| 24 | "v1 max_repeats=0 across all v1 runs; v2 max_repeats=1 across all v2 runs" | Table I caption | All v1 cells: 0; all v2 cells: 1. | PASS |
| 25 | "~8,000 spans" trace corpus claim | Abstract | **NOT TRACEABLE** to `data_inventory.json`. Inventory documents 960 per-instance JSONs but does not report a span count. | **FAIL — unverified.** The author needs to either compute it or strike the claim. |
| 26 | "approximately 214 instances per arm" power calculation from original work | §II | This is a citation of the prior work's stated number; cannot verify here. | UNVERIFIED (external) |
| 27 | "powered to detect a true +25pp effect at α=0.05 with β=0.2" | §VII Threats | Quick sanity: for two proportions ~0.85 vs ~0.60 at n=60, power ≈ 0.85 — checks out. For Opus baseline ~88% the floor effect makes this less clean, but the claim is "true effect of +25pp" which is independent of base rate to first order. **Defensible.** | PASS (with note) |
| 28 | "Wilson 95% CIs within ±6–13 pp" | Table I caption | Inventory CIs: Opus v1 ctrl [0.74, 0.92] = ±0.09; Sonnet v1 ctrl [0.47, 0.71] = ±0.12; Sonnet v2 [0.009, 0.114] is ±0.05 / +0.08 (asymmetric, near zero); Haiku v2 [0.058, 0.222] = ±0.08. **The range "±6–13pp" is roughly correct** but the very low-rate cells (Sonnet v2 ~3%) have asymmetric Wilson intervals with the upper bound at +8pp — the "±" framing slightly misrepresents these. Minor. | PASS-with-quibble |
| 29 | "75 hours of CLI-bound compute" | §III.D | Not in inventory; author-reported. | UNVERIFIED (operational claim) |
| 30 | "peak parallelism of three claude tracks" | §III.D | Not in inventory. | UNVERIFIED (operational claim) |
| 31 | "9 of 24 (37.5%) vs 6 of 24 (25%)" original effect | §II | 9/24 = 37.5%; 6/24 = 25%; 37.5 − 25 = 12.5pp. Arithmetic is correct. p=0.53 is reported as the prior work's value; cannot verify externally. | PASS (arithmetic) / UNVERIFIED (external) |
| 32 | "12 of 14 failure modes covered" (MAST validation, prior work) | §II | External, prior work's claim. | UNVERIFIED (external) |
| 33 | "Cohen's κ = 0.904" (prior work) | §II | External, prior work's claim. | UNVERIFIED (external) |

**Numerical audit summary:** All in-paper, in-data claims PASS. **One FAIL: the "~8,000 spans" abstract claim is not traceable.** Several "external" claims about the prior work are not verifiable in this review's scope (and are appropriately third-person), but a reviewer could request a citation-pinpoint for each.

**Action items:**
- Strike "~8,000 spans" from the abstract OR add a span count to the data inventory and cite it.
- Tighten "every Fisher's exact two-sided p ≥ 0.17" to "every Fisher's exact two-sided p ≥ 0.17 (seven of eight ≥ 0.79)" — currently understates how vacuous the comparisons are.

---

## 2. CFP Fit Audit

**Verified CFP scope (verbatim quote retrieved):** *"Observability, SRE & AIOps for edge–cloud systems (cross-layer telemetry, anomaly detection, incident response at the edge)."*

The CFP also lists 14 other topic areas including "Reliability & resilience," "Testing, verification & benchmarking," "Domain case studies and experience reports," and "MLOps on the continuum."

**Paper's edge-cloud framing:** The paper invokes "edge-cloud continuum" in the title-adjacent space, abstract, §V, and conclusion. The actual content of the paper is a replication study of an agent-observability intervention across four vendor CLIs.

**Is the fit honest?** Mixed. Let me itemize.

**What the paper does that supports CFP fit:**
- Frames the research question as a deployment / AIOps concern (§I): "when I instrument my own agent pipeline...will the same intervention recover the same fraction of my failures?"
- §V explicitly motivates the result via a tiered-deployment scenario: "latency-constrained edge inference may run a budget-tier model like Haiku; high-capability cloud serving runs a frontier-tier model like Opus or GPT-5.5; cost-sensitive batch workloads run a mid-tier model like Sonnet."
- The contribution does target "observability stacks across deployment tiers" which is plausibly within "cross-layer telemetry" and "AIOps."
- Three concrete deployment recommendations in §V.

**Where the fit is thin:**
- The experiments do not deploy anything to the edge. There is no edge hardware, no edge runtime, no edge-cloud topology, no measured latency/bandwidth trade-off, no edge-specific constraint exercised. All 960 runs are on "Apple M-series" (per §VIII) — i.e., the author's laptop.
- The "edge" justification in §V (Haiku-on-edge, Opus-in-cloud) is **a single illustrative sentence with no experiment instantiating it**. The paper's data does not measure anything about edge deployment. A skeptical reviewer will flag this as bolt-on framing.
- The intervention being replicated, the original [aiware2026] work, and the SWE-bench Lite benchmark are all cloud-only. Nothing about the experiment is intrinsically edge.
- The phrase "edge-cloud continuum" appears in the title-adjacent space and ~6 times in the body, but every appearance is in framing language ("for practitioners at the edge-cloud continuum," "AIOps practitioners deploying...across the edge-cloud continuum") rather than in the experimental design.

**Verdict on CFP fit:** The paper fits under the **"AIOps for edge-cloud systems" — specifically the AIOps half** — *if* the editor reads "AIOps for edge-cloud systems" charitably as "AIOps technologies relevant to operators of edge-cloud deployments." But a reviewer who reads it strictly ("the research must address edge-cloud-specific challenges, not just cloud agent ops") will reject on scope.

**Risk:** A desk-reject on CFP fit is a non-trivial probability. The editor will see the title — "Cross-Tier Replication Study of Closed-Loop Agent Recovery via Vendor Agent CLIs" — and see no "edge" in it. The first time "edge" appears is in the abstract's penultimate sentence. A more confident framing (e.g., explicitly experimenting on a small device or on a constrained-resource edge model) would be the strongest defense. Short of that, the paper needs to:

1. Move the edge-cloud framing earlier and tie it to a concrete *operational mechanism* that justifies the tier coverage (latency-constrained edge → small models like Haiku; cloud → frontier like Opus). One paragraph in §I, not just §V.
2. Acknowledge in Limitations / Threats that the experiments themselves are not edge-deployed and explain why the tier-coverage finding still matters for an edge-cloud practitioner.
3. Strengthen the "operator of edge-cloud systems must validate interventions per-tier" connection so that the contribution lands within "AIOps for edge-cloud systems" rather than reading as a generic 2026 agent ops study.

**Bottom line:** The fit is *defensible* under a charitable reading. It is *not* obviously within the CFP under a strict reading. This is the single biggest desk-reject risk.

---

## 3. Citation Audit

### [aiware2026] — Balusu, AgentTelemetry, AIware '26 Benchmark & Dataset Track, DOI 10.1145/3805760.3814931

**Existence check:**
- AIware 2026 conference confirmed via https://2026.aiwareconf.org/track/aiware-2026-benchmark---dataset-track
- The Benchmark & Dataset Track is confirmed with 16 accepted papers (per fetch).
- Camera-ready deadline May 7, 2026 — the paper is post-camera-ready, consistent with citing it.
- The specific paper title "AgentTelemetry: A Fault Detection Benchmark and Toolkit for LLM Agent Observability" was not visible in the partial accepted-papers fetch, but it is plausibly one of the 16. **The DOI itself could not be directly resolved** (https://doi.org/10.1145/3805760.3814931 returned 404, https://dl.acm.org/doi/... returned 403 — both likely because ACM DL has not yet indexed the camera-ready). This is normal for a paper that was camera-ready'd one week before today's date.

**Same-author / overlap audit:**
- **Confirmed: same author.** The IEEE Software paper byline (Krishna Chaitanya Balusu, Independent Researcher) matches the [aiware2026] author exactly (K. C. Balusu).
- **How the paper handles this:** The citation is third-person ("Recent peer-reviewed work~\cite{aiware2026}", "the published intervention~\cite{aiware2026}", "the original work~\cite{aiware2026}"). The paper does NOT explicitly disclose that the author of [aiware2026] is the same as this paper's author.
- **Is this defensible under IEEE norms?** Mostly yes. IEEE Software does not require explicit "self-citation" disclosure in the body text; the bibliography author name (K. C. Balusu) is the disclosure. A reviewer in single-blind review will see both authorships. In a double-blind review, the citation pattern would need to be anonymized further.
- **Is the framing honest?** This is the place I want to push back hardest. Phrases like "the original authors flagged the small sample size" and "Recent peer-reviewed work~\cite{aiware2026} introduced..." are written in the impersonal-third-person form that *technically* doesn't lie but does create the impression that the original work is by someone else. A reviewer who notices the author name match will read this as a stylistic choice; a reviewer who doesn't notice may feel slightly misled when they later discover it.

**Recommendation:** Add a one-sentence disclosure footnote near the first [aiware2026] cite or in Acknowledgments: "The cited work [aiware2026] is by the same author; this paper deliberately replicates and stress-tests that prior work in a different deployment regime." This converts a stylistic ambiguity into an honest framing and immunizes against a reviewer raising it as a complaint.

**Verdict:** PASS on citation existence (with the caveat that ACM DL indexing not yet complete). PASS on third-person form. **REVISE on disclosure** — add explicit self-overlap statement.

### [otel] — OpenTelemetry GenAI Semantic Conventions

- URL https://opentelemetry.io/docs/specs/semconv/gen-ai/ verified live (page exists, titled "Semantic conventions for generative AI systems").
- The bibitem says "v1.30, 2024" — the live page does not display a version number, so this is unverified. I'd recommend changing to "[Online; accessed 2026-05-16]. Available: ..." or pinning to a specific spec release tag.

**Verdict:** PASS on URL existence; MINOR on version pinning.

### [mast] — Cemri et al., NeurIPS 2025

- arXiv:2503.13657 exists (verified). Authors match the bibitem exactly.
- **NeurIPS 2025 acceptance UNVERIFIED.** I checked the arXiv abstract page, Hugging Face papers page, and the NeurIPS 2025 virtual papers index. None of these confirm NeurIPS 2025 acceptance. The Hugging Face page explicitly says "this paper is not indicated as a NeurIPS 2025 accepted paper" and lists it only as a v3 arXiv preprint.
- The paper may have been accepted to a NeurIPS 2025 workshop or to the main conference and not yet indexed. But absent confirmation, **citing it as "Proc. NeurIPS, 2025" is a citation-accuracy risk.**

**Verdict:** REVISE — either confirm the NeurIPS 2025 acceptance via OpenReview or the proceedings, or change the cite to "arXiv preprint, 2025, arXiv:2503.13657" until confirmed. A reviewer who checks this citation (likely, given the paper centrally relies on MAST for validation in the prior work) will catch the discrepancy.

### [swebench] — Jimenez et al., ICLR 2024

- Confirmed accepted to ICLR 2024 as oral (per OpenReview). PASS.

**Citation audit summary:** [otel] minor pin; [mast] **must verify or downgrade venue**; [aiware2026] **must add self-overlap disclosure**; [swebench] PASS.

---

## 4. Logical Consistency Audit — Hidden Assumptions

Each item: assumption → where it's hidden → defensibility.

**A1. The intervention "never fired" claim implicitly assumes the trigger condition is correctly implemented in the replication harness.**
- Where: Abstract; §I; §IV repeatedly; Finding 4.
- Defensibility: The data inventory verification report confirms `avg_intervention_triggers = 0.0` across all 16 cells. **However**, a reviewer can legitimately ask: what proves the trigger was *wired up correctly* to begin with? If the trigger code in v2 had a bug that caused it to never fire, the inventory would still show 0.0. The paper does not present any positive test of the trigger (e.g., a unit test or a synthetic run where the trigger fires by construction).
- **Recommendation:** Add a single sentence to §III or Reproducibility: "The trigger condition was unit-tested with a synthetic input that emits three identical search queries; the trigger fires correctly. The 0.0 trigger rate across 960 runs reflects model behavior, not harness defect."

**A2. The "passive harness" assumes the system prompt offering tools is sufficient to elicit tool use from a model that would otherwise use tools.**
- Where: §III.B "The system prompt offers the agent a search-tool protocol but does not enforce it."
- Defensibility: This is a reasonable but contestable assumption. Modern CLI-wrapped models may need different prompt phrasing (e.g., explicit JSON tool schema vs. inline natural language) to engage their tool-use mode. A reviewer can argue the v1 harness is undertested — the models may *want* to search but the harness doesn't speak their preferred protocol.
- **Recommendation:** Briefly acknowledge this in §III.B or Threats — "We did not vary the system prompt's tool-protocol phrasing. A more aggressive prompt may have elicited engagement at v1."

**A3. The "varied queries every time" / "structurally precluding the trigger" conclusion assumes exact-string repeat is the trigger semantics in the prior work.**
- Where: §IV.B "the maximum value of max_query_repeats observed across all 240 v2-Opus and v2-GPT-5.5 instance-runs is 1. Every search call within every agent run used a unique query."
- Defensibility: Yes, the original [aiware2026] intervention used exact-string repeat semantics. The paper says so in §I and §II. PASS.

**A4. Conflation of "trigger never fires" with "intervention has no effect."**
- Where: Throughout. Most explicit in §IV.D "the underlying mechanism by which the published intervention would deliver any effect (catching reasoning loops) is structurally absent in every cell tested."
- Defensibility: This is the load-bearing logical move of the paper. It is defensible — if the trigger never fires, the intervention condition runs identically to the control condition, and the small Δ values observed are pure between-run noise. PASS.

**A5. The "vendor agent CLI absorbs the agentic loop" finding assumes the per-instance CLI run executes a meaningful agentic loop internally.**
- Where: §V "Inside that subprocess, the CLI performs its own tool use, its own reasoning, its own iteration — and reports back a result."
- Defensibility: This is asserted but not measured. There is no direct evidence in the paper that the vendor CLIs perform internal multi-step reasoning. They might just be passing the prompt through to a single model call. A reviewer can ask: "How do you know the CLI is absorbing the loop vs. just dispatching one model call?"
- **Recommendation:** Add a single observation or vendor-documentation pointer. E.g., "Anthropic's Claude CLI documentation describes internal tool use" with a citation, or "we observed that under v1, mean iterations is 1.0 yet the model produces a parseable patch — implying the agentic reasoning happened inside the CLI subprocess." The latter is slightly inferential, but it's better than nothing.

**A6. "modern frontier and mid-tier models one-shot patches" generalizes beyond the four tested.**
- Where: Abstract; §I.
- Defensibility: The data supports the claim for the four tested. Generalizing to "modern frontier and mid-tier models" is a step beyond. But the paper's Threats section already flags this. PASS.

**A7. The "+12.5pp at n=24" effect is treated as the headline of the prior work and the thing being stress-tested.**
- Where: Abstract; §I; §II.
- Defensibility: The prior work itself reported the effect with p=0.53, which the paper correctly quotes. Treating an effect with p=0.53 as the headline is reasonable for a replication-stress test but the framing could acknowledge that the prior work itself did not claim the effect was statistically significant — which the paper does ("The original authors flagged the small sample size and high p-value as limitations"). PASS.

**A8. The "Plugboard codex CLI exposes only GPT-5.x and grok-4" claim assumes this gating is representative of OpenAI deployments.**
- Where: §III.C; Limitation L1.
- Defensibility: The paper correctly flags this in L1 as Meta-Plugboard-specific. PASS.

**Consistency audit summary:** No load-bearing logical contradictions. Two assumptions (A1 trigger validity, A5 CLI internal looping) should get a sentence each to immunize against reviewer pushback.

---

## 5. Overlap Risk Audit (Self-Citation)

This is the single most reputationally sensitive item.

**Facts:**
- IEEE Software paper author: Krishna Chaitanya Balusu, Independent Researcher.
- [aiware2026] paper author: K. C. Balusu (same person, confirmed).
- The IEEE Software paper replicates and stress-tests [aiware2026]'s closed-loop intervention.
- The replication is the central contribution.

**Three-part honesty test:**

(a) **Does the paper disclose the overlap?** Implicitly via the bibliography (same author name appears as both submitting author and as cited author). Explicitly — NO. There is no statement in the body of the paper, in the abstract, in the acknowledgments, or in a footnote that says "the cited work is by the same author."

(b) **Are all citations of [aiware2026] in third-person form?** Yes. Every cite uses third-person ("the original work," "Recent peer-reviewed work," "the published intervention"). There is no "our prior work" phrasing that would tip the reader to the overlap.

(c) **Is the contribution framed as testing the prior work's deployment regime rather than claiming new findings?** Mostly yes. The contributions list (§I) says "Empirical evidence that the intervention's trigger condition fires zero times" and "deployment-experience analysis" — both framed as testing the prior work. The paper does not double-claim the prior work's contributions.

**Risk assessment:**
- **Low risk on academic-ethics grounds.** Self-replication and self-stress-testing of one's own prior work is legitimate and even encouraged in venues that value replication. IEEE Software, as a magazine, has published author-self-replicates-prior-work pieces before.
- **Medium risk on reviewer-perception grounds.** A reviewer who notices the author-name match midway through will feel the third-person framing is artful, even if not deceptive. A reviewer who notices it only in the Acknowledgments (currently "Camera-ready only") will feel the disclosure was withheld.
- **High value in fixing it.** A one-line footnote at the first [aiware2026] cite ("The cited work is by the same author; this paper deliberately replicates that work in a different deployment regime.") completely defuses the issue and turns the self-overlap into a credibility feature rather than a credibility risk.

**Verdict:** REVISE. Add explicit self-overlap disclosure. Keep the third-person citation style — it is the right academic register — but make sure the disclosure is unambiguous.

**Additional note on contribution-double-counting:** The IEEE Software paper claims four contributions in §I. None of these overlap with [aiware2026]'s contributions (which were the taxonomy, the validation, and the intervention itself). The IEEE Software contributions are the *replication design*, the *zero-trigger finding*, the *CLI-absorption analysis*, and the *artifact release*. These are genuinely distinct from [aiware2026]. PASS on contribution-distinctness.

---

## 6. Limitations Completeness Audit

The paper has two parallel limitations-style sections: §VII "Threats to Validity" (5 items) and a "Limitations" section after the Conclusion (4 items, L1–L4). Several items overlap between the two.

**What's covered well:**
- Single-benchmark scope.
- Patch-rate as outcome (no test-passing measurement).
- CLI-version dependence (Meta Plugboard).
- Sample size and power.
- Sonnet/Haiku v2 gateway artifact.
- No GPT-4o-mini (L1).
- No raw-API access (L2).
- Forced-protocol harness changes conditions (L3).
- Gemini and grok-4 untested.

**What a skeptical reviewer will flag that the paper misses:**

**M1. Single-author / single-lab confound.** The paper is a replication of the author's own prior work. The "replication" reproduces the prior work's harness, design choices, and operationalization. Independent-lab replication is the gold standard; same-author replication is necessarily weaker on certain failure modes (e.g., a shared bug in the trigger definition would not be detected). The paper should acknowledge this and frame the replication as "same-author cross-tier stress test" rather than implying it's an independent replication.

**M2. No external instrumentation comparison.** The paper argues that vendor CLIs "absorb" the agentic loop, but does not compare against any practitioner-instrumented stack (e.g., OpenTelemetry GenAI conventions applied directly to raw API calls, or LangChain with the LangSmith tracer). Without this comparison, the claim that "the practitioner cannot observe" is asserted but not measured. A reviewer can ask: "what is the practitioner *able* to observe in the CLI subprocess via existing stdout/stderr capture, structured logging, or vendor-provided telemetry?" The paper does not say.

**M3. The "n=60 per arm" power claim depends on which effect size you care about.** §VII says "powered to detect a true +25pp effect at α=0.05 with β=0.2 but not the published +12.5pp effect." This is correct *in absolute terms* but misleading in the context where many cells have baseline rates of 85%+ (Opus, GPT-5.5, Haiku v1) where there is a ceiling effect and any +25pp would require the model to exceed 100%. The power calculation should acknowledge baseline-dependent power.

**M4. The conclusion that interventions relying on "syntactic repetition" will increasingly fail is overgeneralized from a single intervention class.** §V's recommendation (3) generalizes from one observed trigger to a whole class. The paper has data for one exact-string-repeat trigger; it does not have data for fixed-argument-match or specific-tool-invocation-pattern triggers. The recommendation should either narrow to "this specific trigger class" or explicitly flag that the generalization is conjectural.

**M5. No statistical correction for multiple comparisons.** With 8 cells and 8 Fisher's exact tests, a reviewer could ask whether the paper applied any multiple-comparison correction. Given that 7 of 8 p-values are at 1.00 and the lowest is 0.17, no correction would change the verdict (none significant). But the paper should briefly state "given that the lowest p-value is 0.17 and the headline finding is null, multiple-comparison correction is not material" — preemptively.

**Limitations completeness verdict:** Solid on the items it covers; **missing five items** a reviewer will likely raise. M1 (same-author replication) is the most important.

---

## 7. Reviewer Pushback Prediction — Three Most Likely Critiques

### Critique 1 (highest probability): "This isn't an edge-cloud paper."

- **Critique:** The CFP scope is "Observability, SRE & AIOps for edge–cloud systems (cross-layer telemetry, anomaly detection, incident response at the edge)." The submitted paper is a cloud-only replication study with one paragraph mentioning edge in §V. No edge hardware, no edge runtime, no measured edge-specific phenomenon. Even the tier-coverage argument (Haiku=edge, Opus=cloud) is illustrative not experimental.
- **Probability:** HIGH. This is the easiest critique to make and the hardest to refute without re-running experiments on actual edge hardware.
- **Does the paper preempt it?** Partially. §V offers the tier-coverage motivation but does not back it with experimental data. The Threats section does not flag the edge-scope limitation explicitly.
- **Recommended preemption:** (a) move the tier-coverage / edge-deployment motivation to §I; (b) add a Threats item: "Our experiments run on cloud-tier CLI deployments. The tier-coverage finding applies to AIOps practitioners deploying the same model classes on edge hardware, but we have not measured edge-specific phenomena such as constrained bandwidth between the agent and the model endpoint."; (c) consider running a single illustrative edge experiment (e.g., Haiku via the Anthropic CLI on a Raspberry Pi or NUC) to give the framing teeth. Even one cell of edge data would defuse this critique.

### Critique 2 (high probability): "The null result is overdetermined by harness choice, not a real generalization failure."

- **Critique:** The paper claims the published intervention does not generalize. But the result depends on (a) the harness's tool-protocol phrasing being one that modern CLI-wrapped models honor and (b) the trigger definition being exact-string-repeat. Both are choices, and modifying either could plausibly produce a non-null result. The paper's conclusion ("published interventions do not generalize") may be too strong; the more defensible conclusion is "this specific intervention as-implemented does not generalize."
- **Probability:** HIGH. A careful reviewer will notice this and ask for either harness-variation experiments or scope-narrowing.
- **Does the paper preempt it?** Partially. §V recommendation (3) gestures at "interventions whose trigger condition assumes syntactic repetition" but doesn't separate the harness-choice confound from the trigger-choice issue.
- **Recommended preemption:** Add one paragraph at the end of §V distinguishing (a) the trigger semantics, (b) the harness protocol, and (c) the model behavior. Explicitly say: "our null result confounds these three; we cannot fully attribute the null to model behavior alone."

### Critique 3 (medium-high probability): "The MAST citation and the AIware citation cannot be verified."

- **Critique:** [mast] is cited as "Proc. NeurIPS, 2025" but the paper is currently only on arXiv with no visible NeurIPS acceptance evidence. [aiware2026] is cited with a DOI that does not yet resolve. A reviewer who tries to look up these citations will find them broken.
- **Probability:** MEDIUM-HIGH. Editors and assigned reviewers routinely check citations.
- **Does the paper preempt it?** No.
- **Recommended preemption:** (a) confirm [mast]'s NeurIPS 2025 acceptance via OpenReview / proceedings — if not confirmable, downgrade to "arXiv preprint, 2025"; (b) for [aiware2026], add the conference website URL to the bibitem so the reviewer can verify via the AIware program even before ACM DL indexing completes.

---

## Summary

**Verdict: REVISE-AND-RESUBMIT.**

The paper's empirical spine is sound — every numerical claim in the data section traces correctly to the verified inventory. The author's same-paper-replication is legitimate scholarship and adds real value. The framing is fundamentally honest. But there are five categories of fixable issue:

1. **CFP fit** — strengthen the edge-cloud-continuum framing in §I; add a Threats item on edge-scope; ideally add one edge-hardware experiment cell. This is the highest desk-reject risk.
2. **Self-overlap disclosure** — add a one-sentence footnote disclosing the author of [aiware2026] is the same. Keep third-person citation style otherwise.
3. **Citations** — verify or downgrade [mast]'s NeurIPS 2025 venue; add conference URL to [aiware2026]; minor version pin on [otel].
4. **One unverifiable claim** — strike "~8,000 spans" or back it with a count.
5. **Missing limitations** — add same-author-replication item (M1), no-external-instrumentation-comparison item (M2), baseline-dependent power note (M3), narrow recommendation (3) (M4), one-line on multiple-comparisons (M5).

None of these are unfixable. The paper is **not** desk-reject material; it's revise-and-resubmit material. With the fixes above, it is publishable in IEEE Software's Edge-Cloud Continuum special issue.

If the author lacks bandwidth for the edge-hardware experiment (which would be the single highest-impact fix for CFP fit), then at minimum:
- Move the tier-coverage / edge-deployment motivation to the first page;
- Add the same-author disclosure footnote;
- Fix the [mast] citation;
- Strike "~8,000 spans";
- Add the five missing limitation items.

These minimum fixes are ≤ 4 hours of work and substantially reduce the reviewer-pushback surface.

**Final verdict: REVISE-AND-RESUBMIT.**
