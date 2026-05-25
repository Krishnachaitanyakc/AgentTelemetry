# EMNLP 2026 Industry Track — Hostile Cold-Reviewer Stress Test of the Forced-Protocol-Degradation Plan

**Date:** 2026-05-17 (30 days to EMNLP submission deadline 2026-06-16)
**Plan under review:** "When Protocol Forcing Backfires: How Tool-Use Prompt Scaffolds Degrade Mid- and Budget-Tier LLMs in Production Agent Harnesses." Centered on the v2 forced-harness Sonnet/Haiku collapse, with min_searches ∈ {1, 2, 3, 5} sweeps planned across 4 tiers + an optional NLP task.
**Reviewer posture:** Hostile. Evidence-first. No hedging.

---

## Verdict: **ABANDON** (defer to EMNLP Industry 2027 or pivot to an actually-clean EMNLP submission)

The plan as stated has at least four critical, independently disqualifying flaws. The single most damaging fact is that **the entire central finding — including the exact numeric quotes, the deployment lesson, the "Sonnet and Haiku resist the forced protocol" framing, the patch-suppression mechanism, and the syntactic-vs-semantic trigger analysis — is already written, in full, into the IEEE Software paper that will be submitted to IEEE Software (July 7 deadline) and will be visible to EMNLP reviewers via arXiv preprint by the EMNLP review window.** Submitting the same headline finding to EMNLP, even reframed, is a textbook redundant-publication risk that the user's own prior cold-reviewer audit already concluded warrants Option E (defer). The new plan re-litigates that decision without adding evidence that changes the conclusion.

The 14-day-ago decision memo (`EMNLP_DECISION_2026-05-16.md`, lines 77-85) and the round-2 verification (`EMNLP_DECISION_REVIEW_round2_2026-05-16.md`, lines 38-48) both reached PASS on Option E. The current plan is Option D under a different name with an experiment sweep bolted on. The audit findings that ruled D as "Medium risk" still hold, and several have gotten worse since then because the IEEE Software draft has been updated to be even more explicit about the Sonnet/Haiku collapse.

---

## 1. Cross-paper overlap risk audit

### 1a. IEEE Software "Edge-Cloud Continuum" — **FATAL OVERLAP**

File: `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/ieee_software_paper.tex` (last modified 2026-05-16, 15:22, after the prior EMNLP decision memo).

**Data overlap: 100%.** Both the proposed EMNLP paper and IEEE Software use the v2 forced-harness `swebench_n60_v2_*` corpus (480 instance-runs across Sonnet/Haiku/Opus/GPT-5.5 × control/intervention × n=60). The proposed EMNLP min_searches sweep would extend the same harness on the same SWE-bench Lite instance set, on the same vendor CLIs.

**Framing overlap: not "orthogonal" — directly duplicative.** The plan claims the EMNLP angle (forced-protocol degradation) is "orthogonal" to IEEE Software's framing ("interventions don't transfer"). The IEEE Software draft refutes this directly:

- IEEE Software §IV-C "Finding 3: Sonnet and Haiku resist the forced protocol" (lines 161-165 of the .tex). Verbatim quote: *"The remaining two v2 cells — Sonnet 4.6 and Haiku 4.5 — present a different failure mode. Patch rates collapse to 3.3% (Sonnet) and 11.7%-13.3% (Haiku), with high \texttt{patch\_suppressions} averages (4.67-5.75 per run): the model attempts to emit a patch every iteration without searching, and our v2 harness rejects each attempt and demands the model search first. The model never satisfies the search-first protocol, the iteration cap is exhausted, and the run terminates with no patch."*
- The exact deployment lesson the proposed EMNLP paper would put in its abstract — that forced scaffolds break mid/budget tiers — is already IEEE Software's headline #3 of 4 findings.
- The IEEE Software abstract (line 33) already states: *"Anthropic's Sonnet 4.6 and Haiku 4.5 cannot be coerced into the protocol even under the forced harness, collapsing patch rates to 3.3%-13.3%."*

**Headline finding overlap: 100%.** Both papers report Sonnet 3.3%/3.3%, Haiku 13.3%/11.7%, patch_suppressions 4.67-5.75, derived from the same `data_inventory.json` cells (v2-sonnet, v2-haiku — lines 197-273 of the JSON). The min_searches sweep does not *add* a new finding; it *parameterizes* the existing finding. The plan calls this a "monotonic gradient" but the underlying claim (forced protocol degrades non-frontier tiers) is the IEEE Software claim with a slope estimate attached.

**arXiv visibility:** EMNLP allows arXiv preprints with no anonymity period. IEEE Software submission is July 7 (after EMNLP submission June 16, but well before EMNLP rebuttal July 22 and review release). An IEEE Software preprint posted any time between July 7 and August 20 (acceptance notification) would be Googleable by EMNLP reviewers during their review. Reviewers WILL find it. The author is identifiable on both papers (same author, same data, same `data_inventory.json`, same harness code, same `EMNLP_DECISION_*` artifacts visible in the open-source repo unless deliberately scrubbed).

**Even if the EMNLP version is rewritten to focus only on min_searches sweep and not on the 4-tier table, the sweep is parameterized on top of v2 forced harness — which IS the IEEE Software experiment.** There is no clean separation.

### 1b. AIware 2026 (ACCEPTED) — **moderate overlap, partial protection**

File: `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/aiware2026/aiware_paper.tex`. The AIware paper introduces the AgentTelemetry taxonomy and the closed-loop intervention. It uses Haiku 4.5 on real-LLM trace structure (line 591) and includes the n=60 Opus replication (lines 285-376, the §RQ5 SWE-bench section). It does NOT include the forced-harness v2 collapse on Sonnet/Haiku. The forced-protocol Sonnet/Haiku collapse is genuinely not in AIware.

But: the AIware paper IS the prior work the proposed EMNLP paper would cite (`\citep{aiware2026}`). And the proposed EMNLP paper's "forced-scaffold degrades mid/budget tiers" claim conceptually generalizes from AIware's "telemetry-derived interventions don't transfer across tiers" (AIware §RQ5 conclusion, line 364: *"do not assume telemetry-derived interventions developed against budget-tier models will transfer to frontier-tier deployments without re-validation"* — exact inverse-tier framing of the EMNLP plan). Reviewers familiar with AIware (which the field will be by the EMNLP review window — AIware was accepted, conference is July 6-7, 2026, ~6 weeks before EMNLP reviews release) may see the EMNLP claim as a contrapositive of the AIware claim with new data, not as an independent contribution.

### 1c. NeurIPS 2026 (submitted) — **moderate overlap, different scope**

File: `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/neurips2026/neurips_2026.tex`. NeurIPS uses the 159-run real-LLM corpus across 13 models (lines 1067-1071) including Haiku 4.5, Sonnet 4.6, Opus 4.6 (line 421, line 688-689). It does NOT include the SWE-bench v2 forced-harness corpus. The proposed EMNLP min_searches sweep is on a different data slice. Direct corpus overlap with NeurIPS is low.

But: NeurIPS already covers the same 6-model cross-tier story (line 398-399: *"Six LLMs across three capability tiers and two providers"*) for a different telemetry purpose. The proposed EMNLP paper would be the 4th in-flight paper from the same author using the cross-tier comparison framing across the same Anthropic/OpenAI model families.

### 1d. ESEM 2026 (submitted) — **low overlap**

File: `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/esem2026/esem_paper.tex`. Uses "two commercial provider families, three tiers each" (line 578) for a fault-detection protocol, not SWE-bench. Different research question; minimal direct overlap with the proposed EMNLP plan.

### 1e. MDE 2026 (submitted) — **no overlap**

File: `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/mde2026/mde_paper.tex`. Mocked LLMs on coverage matrix. Grep returned zero hits on Sonnet/Haiku/forced/min_searches/protocol. Not in scope.

### 1f. ICML AgenticUQ Determinism (submitted) — **low overlap**

File: `/Users/kcbalusu/Desktop/Project/research/Determinism/paper_v4_anon.tex`. The Determinism paper measures `D(k)` on GSM8K — a math/NLP task — across 9 frontier models. It includes Haiku 4.5 and Sonnet 4.6 (line 230-231) and reports Haiku's non-monotone rebound. Completely different research question (per-position determinism on isomorphic chains), completely different data, completely different harness. Low overlap on data but the cross-tier model lineup is the same; the proposed EMNLP paper would be the 5th cross-tier paper from the same author.

### 1g. Cross-paper portfolio summary

| Paper | Data overlap | Framing overlap | Headline overlap |
|---|---|---|---|
| IEEE Software 2026 | **100%** | **100%** | **100%** |
| AIware 2026 (accepted) | Low (different harness) | Moderate (inverse-tier transfer) | Moderate (same theme, opposite direction) |
| NeurIPS 2026 (submitted) | None | Moderate (cross-tier observability) | Low |
| ESEM 2026 (submitted) | None | Low | Low |
| MDE 2026 (submitted) | None | None | None |
| ICML AgenticUQ (submitted) | None | Low (same model lineup) | None |

**The IEEE Software row is disqualifying.** The plan's claim that EMNLP is "cleanly orthogonal to IEEE Software's 'interventions don't transfer' framing" is wrong as a matter of fact: the Sonnet/Haiku v2 collapse IS one of IEEE Software's four headline findings, with specific patch-suppression numbers identical to what the EMNLP plan proposes to feature.

---

## 2. EMNLP scope-fit audit

EMNLP 2026 Industry Track CFP (https://2026.emnlp.org/calls/industry_track/) verified by WebFetch. Key scope language quoted:

> "real-world implementations of NLP systems, the development of such systems, or provide insights based on real-world datasets"

> "innovations and implementations in all areas of speech and language technologies for real-world applications"

> "meaningful use of NLP and/or speech technologies in practice"

The proposed EMNLP paper's primary data is **SWE-bench Lite — a code-patch benchmark**. SWE-bench is a software engineering benchmark, not a speech-or-language-technology benchmark in the EMNLP/ACL operational sense. Yes, code is sequences and LLMs generate code, but EMNLP's core community (parsers, NER, MT, dialog, IR, QA, summarization, evaluation methodology, speech) does not generally treat code-patch generation on SWE-bench as in-scope for ACL/EMNLP. SWE-bench papers appear at ICLR, NeurIPS, ICML, ICSE, FSE, ASE — not at ACL/EMNLP main or industry tracks.

The CFP does explicitly invite "deployment of language processing and generation systems, including those based on large language models." That is the slot the plan is gambling on. It is a real slot — but the in-scope examples the CFP lists ("System combination and orchestration", "Interactive and user-facing systems") are oriented toward language tasks, not toward "does this LLM patch django/astropy code under SWE-bench harness conditions."

**Experiment C (non-coding NLP task) is the plan's defense.** But:

1. Experiment C is listed as **"optional"** in the plan. If it's optional, the paper would be SWE-bench-only — which is the worst scope fit. Optionality on the load-bearing scope-defense experiment is a red flag.
2. Experiment C adds ~480 runs + ~4h of harness writing for a brand-new NLP task. The plan does not specify which NLP task. Without a specific task choice (HotpotQA? τ-bench? MMLU? OpenAI's evals? something else?), Experiment C is a placeholder, not a planned experiment. A real Experiment C would require: dataset selection, task prompt engineering, scoring pipeline, ground-truth labels, baseline calibration. 4 hours is grossly optimistic — the existing v2 harness took the author months to build, and that was on a benchmark they already had infrastructure for.
3. Even with Experiment C, the SWE-bench data would carry the bulk of the empirical weight (240 runs vs 480 runs on NLP, but the SWE-bench data has the patch_suppressions mechanism story; the NLP task would be a confirmation slot, not the centerpiece). The paper would still read as primarily a SWE-bench paper.
4. EMNLP Industry reviewers can and do triage on scope. A SWE-bench paper with a tacked-on NLP confirmation experiment is a familiar pattern reviewers reject for being a software-engineering paper trying to retrofit into an NLP venue.

**Scope verdict: questionable as-stated; defensible only with a serious (not 4-hour) Experiment C anchored on a recognized NLP task with prior literature.**

---

## 3. Statistical adequacy audit

**Design:** 4 tiers × 4 min_searches settings × 2 conditions (control only per the plan, so actually 1 condition) × n=30 = 480 SWE-bench runs (Experiments A + B). The 4×4 matrix has 30 obs/cell.

**Minimum detectable effect (MDE) at n=30, two-sample binomial, α=0.05 two-sided, β=0.20, baseline near 50%:** ~36 percentage points. At baseline 90%, MDE ≈ 20pp. At baseline 13% (Haiku v2), MDE ≈ 23pp.

**Minimum detectable effect at n=60:** ~25pp at 50% baseline, ~14pp at 90% baseline. The IEEE Software paper already uses n=60 because n=30 is underpowered for this regime — see IEEE Software §VII "Threats to Validity" (line 209): *"At n=60 per arm the experiment is powered (at α=0.05, β=0.2) to detect a true +25pp effect on cells with intermediate baseline rates, but the test loses sensitivity sharply in cells where baseline rates approach the ceiling."*

**Dropping from n=60 (used in IEEE Software) to n=30 (proposed EMNLP) cuts the effective sample in half and pushes MDE from ~25pp to ~36pp.** This is the wrong direction. The whole point of the EMNLP paper would be a finer-grained measurement (a sweep) than IEEE Software's 4-cell snapshot — but the proposed sample size is *coarser*, not finer, per cell.

**Monotonicity claim across min_searches ∈ {1, 2, 3, 5}:** to claim "patch rate degrades monotonically as min_searches increases from 1 to 5", you need to reject the null that the slope is zero across 4 settings on each tier. With n=30 per setting, the standard error on a single patch-rate estimate at 50% baseline is √(0.5·0.5/30) ≈ 9.1pp. A linear-regression slope test across 4 settings with this per-point SE would only declare significance if the per-step change exceeds ~5pp consistently. The IEEE Software data shows v2-Sonnet at 3.3% / v2-Haiku at 13.3%; if the budget-tier collapse is already complete at min_searches=3 (the v2 default), pushing higher to min_searches=5 may show floor effects, and dropping to min_searches=1 may show no effect at all — leaving no monotone gradient to detect.

**Realistic p-value range:** with n=30 per cell and the existing v2 data showing Fisher exact p=1.00 across all 8 cells (every cell already statistically null), the natural prior is that pairwise within-tier comparisons will return p > 0.1 at n=30 unless the slope is unusually steep. The plan does not state what effect size constitutes a positive result.

**Verdict: n=30 per cell is statistically inadequate to support a "monotonic gradient" claim on 4-point sweeps. The plan needs n=60 minimum (~960 runs total for A+B, double the planned scope) to be in the same statistical regime as IEEE Software — which doubles the compute time and tightens the 30-day timeline even further (see §4).**

---

## 4. Timeline feasibility audit

**Hard deadline: 2026-06-16 (30 days from today).**

| Step | Plan estimate | Realistic estimate | Notes |
|---|---|---|---|
| Experiment A (Sonnet+Haiku sweep) | 15-30h overnight | 30-60h | The v2 Sonnet runs hit gateway exit-1 errors on 22-25 of 60 instances (data_inventory.json lines 216, 230). Reruns or partial completions are likely. At n=30 this gets noisy. |
| Experiment B (Opus+GPT-5.5 sweep) | 10-15h overnight | 15-25h | Opus runs cleanly but Plugboard quota is the binding constraint (IEEE Software draft acknowledges peak parallelism of three claude tracks; min_searches=5 may push iteration counts up and lengthen per-run wall-clock). |
| Experiment C (new NLP task, optional) | +4h harness writing | +20-40h | New benchmark requires dataset selection, task design, scoring pipeline, baselines, calibration. The plan's "4h" estimate is unsupported. |
| Draft writing (6-page ACL) | not specified | 15-25h | Cannot reuse much from existing EMNLP draft (which is built on the now-falsified ceiling-effect interpretation). Effectively new write. |
| Anonymization sweep | not specified | 3-5h | Author has six in-flight venues; self-reference scrubbing across `\citep{aiware2026}`, repo links, data inventories, etc., is non-trivial. EMNLP review is double-blind. |
| Cold-reviewer rounds | "at least 2" | 8-12h per round × 2 = 16-24h | Per the project CLAUDE.md, the loop is iterative until PASS. Two rounds is the minimum; three or four is realistic. |
| Buffer | not specified | 10-20% slack minimum on a 30-day plan | Real life: travel, day job, the drive-to-office pattern the user has, sleep. |

**Sum of realistic estimates (excluding C):** 30+15+15+3+16+(10% buffer of ~10h) = ~89 hours minimum, ≈ 3 hours/day every day for 30 days with zero misses.

**With Experiment C:** add ~25h, total ~114 hours ≈ 3.8 hours/day every day.

**User has a day job.** The CLAUDE.md describes a drive-to-office pattern, OpsMate team work, and concurrent work on IEEE Software (July 7), ICSE 2027 SEIP (Oct 23), monitoring of ESEM/MDE/ICML decisions. There is no reasonable model under which 3.8 hours of focused paper-writing-and-experiment-running every single day for 30 days fits alongside that.

**Compounding factor: harness might not converge on first run.** The v2 harness was built by hand and required parser fixes (`swebench_n60_v2_forced_tooluse.py` has multiple parser styles — regex + JSON + markdown-fenced — to handle each model's output format). Adding min_searches=1 (essentially passive harness) and min_searches=5 (more stringent than current default 3) will create new edge cases. Expect 1-3 debug iterations.

**Verdict: timeline is unrealistic at 30 days. Even at the optimistic end of the plan's estimates (240+240 = 480 runs, "overnight" both), the writing+anonymization+cold-review+buffer alone consume 40-60h, and that is on top of full-time day work plus the IEEE Software push.**

---

## 5. Harness risk audit

### 5a. What if min_searches=1 looks identical to min_searches=3?

This is plausible. The v2 default is min_searches=3 (IEEE Software §III-B paragraph 2). The collapse on Sonnet/Haiku occurs because the harness *requires* searches before accepting a patch. At min_searches=1, Sonnet/Haiku just need to issue one search call before being allowed to patch. The IEEE Software data shows v2-Sonnet `avg_searches=0.28` and v2-Haiku `avg_searches=1.02-1.15` — i.e., Haiku already averages ~1 search per run. At min_searches=1, Haiku may largely succeed (close to v1 passive performance, 91.7%); Sonnet might still struggle but recover substantially.

If `min_searches=1` outcome ≈ `min_searches=2` outcome, the "monotone gradient" narrative collapses into "any forcing breaks Sonnet, Haiku partially tolerates min_searches=1 but not 2+". That's a step function, not a gradient. The plan's framing requires a gradient.

**Plan B for this case:** the paper would need to be reframed as a "threshold effect" paper, not a "monotone gradient" paper. The IEEE Software draft already gestures at this. There would be no novel EMNLP angle left.

### 5b. What if min_searches=5 causes all tiers to collapse?

Also plausible. At min_searches=5, even Opus has to issue 5 search calls before patching — but Opus's `avg_searches` at min_searches=3 is 3.23-3.42, just barely above threshold. Pushing to 5 may cause Opus to exhaust the 8-iteration cap. If Opus and GPT-5.5 also collapse at min_searches=5, the four-tier contrast disappears.

**Plan B for this case:** the paper would have to argue that *all* tiers degrade with sufficient protocol forcing, which is a less interesting finding (it's almost tautological — make the protocol hard enough and even frontier models fail). The "mid/budget specifically" framing dies.

### 5c. What if Gateway throws exit-1 errors at high min_searches values?

IEEE Software §VII (line 207): *"the Plugboard gateway returns exit-1 errors after repeated patch-suppression cycles on a substantial fraction of Sonnet/Haiku v2 runs (22-25 errors per 60 runs for Sonnet, 10-12 for Haiku)."* At min_searches=5 the patch-suppression cycle count goes up, and the error rate may compound — possibly to the point where 30/30 runs error out on Sonnet at min_searches=5. The data would then be uninterpretable.

**Plan B for this case:** would need to switch to direct vendor APIs (bypassing Plugboard) or wait for Plugboard-side fixes. Direct vendor APIs would void the "vendor CLI deployment" framing the proposed paper depends on, AND would burn the user's personal API budget.

### 5d. What if the harness's "forced-protocol" reading is itself the artifact?

This is the deepest risk and the plan doesn't address it. The v2 harness uses a synthetic stub for `search_code` that returns hard-coded fake results (`swebench_n60_v2_forced_tooluse.py:351`). The patch-rate degradation on Sonnet/Haiku may partly reflect the synthetic search tool returning useless content, not "scaffold resistance" per se. A reviewer who reads the harness code will see this. The "forced-protocol degrades model" finding may not generalize beyond this specific synthetic-search harness.

**Plan B for this case:** none. The harness is what it is. A reviewer who flags this would be correct.

---

## 6. Hidden alternative: is there a better EMNLP submission?

### 6a. Proposed alternative in prompt: AgentTelemetry GitHub-mining table (14/14 fault types from real issues)

**Verdict: NOT clean. Already published in AIware.**

File evidence:
- `aiware_paper.tex:870-911` includes the full GitHub-issue-mining section ("RQ6: Real-World GitHub Issue Validation") with the 33-issue, 14/14-fault-type table. Verbatim quote: *"All 14 fault types have direct user reports."*
- `aiware_paper.tex:1050` references "the 33-issue GitHub mining" in the conclusion.
- `neurips_2026.tex:735` independently cites the same finding: *"GitHub issue mining confirming all 14 fault types correspond to..."*.
- `mlsys_paper.tex:1449` (older mlsys paper) has the same table.
- The existing EMNLP draft also already cites it (`emnlp_paper.tex:446-447`).

The 14/14 GitHub mining is the SAME asset that AIware was accepted on. Re-centering EMNLP on it would be straightforward self-plagiarism against AIware (accepted), worse than the forced-protocol overlap with IEEE Software (which is at least both unpublished). AIware proceedings will be in ACM Digital Library by July 2026; EMNLP reviewers will trivially find it.

This alternative does not work.

### 6b. Other possible alternatives — none are clean

Surveying the asset list visible in this session:

- **Multi-agent topology data:** 45 runs, 9 cells, anomaly detector broken (per `EMNLP_DECISION_REVIEW_2026-05-16.md` Task 3). Underpowered for any standalone paper.
- **Determinism cross-vendor non-monotone rebound:** already the headline of ICML AgenticUQ submission (`paper_v4_anon.tex:72`).
- **OTel semantic conventions PR #3594:** an engineering artifact, not an empirical paper.
- **τ-bench smoke tests:** smoke-test scale only (`tau_smoke`, `tau_smoke_v2` directories); insufficient for a 6-page paper.
- **Threshold sensitivity / real_fpr / scalability:** all referenced as supporting analyses in AIware, not novel headline content.

There is no clean EMNLP asset in the current portfolio that has not already been claimed by another in-flight or accepted paper.

### 6c. Honest alternatives

1. **Option E (defer to EMNLP 2027).** Was the prior cold-reviewer's recommendation 14 days ago (`EMNLP_DECISION_2026-05-16.md` lines 77-85). Still correct. EMNLP runs annually; a clean submission on genuinely new data in 2027 is achievable.
2. **Option A (kill the EMNLP plan, redirect energy to IEEE Software).** Polishing IEEE Software for July 7 has higher EB-1A marginal value than risking a redundant-publication EMNLP rejection.
3. **Option F (genuinely new experiment, genuinely NLP, before EMNLP 2027).** If the author wants an EMNLP-shaped contribution, design from scratch for the NLP venue: e.g., a multi-tier evaluation of dialog agents on τ-bench's airline/retail tasks (already EMNLP-flavored), with new data not in any current in-flight paper. Not feasible in 30 days.

---

## 7. Critical flaws specific to the new plan (not covered above)

### 7a. The "control only" decision

The plan says "control only" for Experiments A and B (no intervention arm). But the entire IEEE Software/AIware lineage of work is matched-pair (control vs intervention). Dropping the intervention arm means:

- Cannot compare against the closed-loop-intervention literature the AIware/IEEE Software papers are built on.
- Loses one of the core methodological hooks the prior work used to argue rigor.
- A reviewer who knows the prior work will ask "why not intervention?" and the honest answer ("we already showed the intervention never fires") implies the paper is a follow-up on a known-null result.

This makes the EMNLP paper read as an addendum to IEEE Software, not as a standalone contribution.

### 7b. Experiment C's task selection is unspecified

"a new non-coding NLP task" is not a research plan. Which task? With what scoring? What's the baseline? What does "patch suppression" even mean on an NLP task — does the harness reject the output if the model didn't search first? The forced-protocol mechanism is fundamentally a code-tool-use mechanism (search_code calls). Porting it to an NLP task requires a meaningful tool surface (e.g., document retrieval, lookup APIs), which means HotpotQA or similar — which means competing with existing literature where reviewers will ask "how does this compare to {12 prior HotpotQA tool-use papers}?"

The plan does not address any of this. "Optional, +4h" is a placeholder, not a plan.

### 7c. The plan re-litigates a recently-decided question

The prior cold-reviewer audit reached PASS on Option E 1 day ago. The current plan is Option D under a fresh title with a sweep added. The audit's reasoning (5 venues already in flight; rejected EMNLP submission consumes reviewer goodwill; 6-10h Option D costs are not justified by EB-1A marginal value) has not changed. The sweep does not address any of the prior audit's concerns — it adds compute, not novelty.

### 7d. The user's task system shows #16 EMNLP submission as "in_progress" but #25 and #26 as pending sub-tasks that haven't started

This is a planning discrepancy that suggests the plan is being formed in real time, not executed against an approved spec.

---

## 8. Final verdict and recommendation

### Verdict: **ABANDON**

The plan is structurally unworkable:

1. The headline finding is already in IEEE Software (100% data, 100% framing, 100% headline overlap). A reviewer with Google access will find it.
2. The EMNLP scope fit is weak; the proposed defense (Experiment C) is unspecified and underbudgeted.
3. n=30 is statistically inadequate for the "monotone gradient" claim.
4. 30 days is unrealistic for the proposed workload alongside the user's day job and other in-flight obligations.
5. The harness has plausible failure modes (saturation at min_searches=1, collapse at min_searches=5, gateway error compounding, synthetic-search artifact) for which the plan has no contingency.
6. The proposed Hidden Alternative (GitHub mining) is itself already in AIware.
7. The prior cold-reviewer audit reached the same conclusion 1 day ago, and the evidence has only strengthened (IEEE Software draft has been further updated to make the Sonnet/Haiku collapse explicit since the prior audit).

### Recommendation: **Option E (defer to EMNLP Industry 2027) + Option A (redirect to IEEE Software polish for July 7)**

Specifically:

1. **Now (today):** Mark task #16 as `completed-deferred` with a 1-line rationale ("redundant with IEEE Software; defer to EMNLP 2027 on new data"). Strike tasks #25 and #26.
2. **Now → July 7:** Polish IEEE Software submission. The IEEE Software paper carries the actual headline finding (the 4-tier × 2-harness 8-cell story with the Sonnet/Haiku collapse). It is the right venue for this work.
3. **Q3 2026:** If author still wants EMNLP, design a genuinely new study on a genuinely NLP task (τ-bench dialog agents, HotpotQA tool-use, dialog-state tracking — pick one with a real literature) on data that doesn't exist yet. Aim for EMNLP 2027 Industry (June 2027 deadline) or ACL Rolling Review (rolling).
4. **Document this decision** in a single short memo so the same plan doesn't get re-litigated in 14 days.

### Conditional fallback: if the user insists on submitting

The minimum-viable salvage is **NOT** the proposed plan. It is:

- Drop SWE-bench entirely. Build Experiment C from scratch on a recognized NLP benchmark with prior literature (τ-bench airline, HotpotQA tool-use, or MultiWOZ dialog-state). Use min_searches sweep on that benchmark only.
- Use n=60 not n=30.
- Explicitly cite IEEE Software in a "concurrent work" footnote (visible to reviewers as a non-anonymized companion).
- Reframe headline finding around the NLP-task contrast, not the SWE-bench Sonnet/Haiku collapse.

This is essentially a different paper than the one in the plan. It would take ~80-120 hours, not 30. It would not be ready in 30 days. It would be ready for EMNLP 2027.

**The 30-day, SWE-bench-centered plan as written should not proceed.**

---

## Evidence index (file:line citations used in this audit)

- IEEE Software headline overlap: `paper/ieee_software_2026/ieee_software_paper.tex:33, 52, 137-138 (table), 161-165 (Finding 3), 207-209 (validity)`
- IEEE Software last modified: 2026-05-16 15:22:38 (`stat`)
- Data inventory: `paper/ieee_software_2026/data_inventory.json:197-273` (v2-sonnet, v2-haiku cells)
- AIware GitHub mining: `paper/aiware2026/aiware_paper.tex:870-911`
- AIware inverse-tier transfer claim: `paper/aiware2026/aiware_paper.tex:362-366`
- NeurIPS 159-run corpus: `paper/neurips2026/neurips_2026.tex:1067-1071`
- NeurIPS 6-LLM cross-tier: `paper/neurips2026/neurips_2026.tex:398-399`
- ESEM dual-provider three-tier: `paper/esem2026/esem_paper.tex:578`
- Determinism cross-vendor: `research/Determinism/paper_v4_anon.tex:72, 230-231, 248`
- Prior EMNLP decision memo (Option E PASS): `paper/emnlp2026/EMNLP_DECISION_2026-05-16.md:77-85`
- Prior cold-reviewer PASS on Option E: `paper/emnlp2026/EMNLP_DECISION_REVIEW_round2_2026-05-16.md:38-48`
- Existing EMNLP draft (frozen, falsified ceiling-effect framing): `paper/emnlp2026/emnlp_paper.tex:46-53, 335-353`
- Harness with min_searches plumbing already in place: `experiments/swebench_n60_v2_forced_tooluse.py:316-339, 411-418`
- Synthetic search-tool stub (potential artifact): `experiments/swebench_n60_v2_forced_tooluse.py:351`
- EMNLP CFP scope language: https://2026.emnlp.org/calls/industry_track/ (WebFetch verified 2026-05-17)
