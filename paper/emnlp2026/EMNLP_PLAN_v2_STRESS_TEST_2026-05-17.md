# EMNLP 2026 Industry Track — Hostile Cold-Reviewer Stress Test v2 (revised plan, post-user-pushback)

**Date:** 2026-05-17 (30 days to EMNLP 2026 Industry deadline 2026-06-16)
**Plan under review:** Revised v2 plan after user override of prior ABANDON verdict.
  - Dual-submit overlapping SWE-bench data to **IEEE Software** (July 7) AND **EMNLP 2026 Industry** (June 16); accept duplication at camera-ready if both accept.
  - n=50 per cell (not n=30).
  - Forced-protocol-degradation framing parameterized by min_searches ∈ {1, 2, 3, 5}.
  - Extend to **HotpotQA** (multi-hop QA, EM + F1) as the non-coding NLP task.
  - Neither paper goes to arXiv until both decisions are in.
  - Total: 1,600 instance-runs (A: 400, B: 400, C: 800).
**Reviewer posture:** Hostile. Evidence-first. Audit the REVISED assumptions only — the user owns the dual-submit decision in principle, but the auditor's job is to surface evidence the user did not have when overriding.

---

## Verdict: **ABANDON-AGAIN**

The user's pushback ("submissions ≠ acceptances; parallel-submit is acceptable; accept camera-ready duplication") is reasonable in the abstract but is refuted in this specific case by **three independent and individually disqualifying pieces of evidence the prior audit did not surface in full**:

1. **EMNLP/ARR policy text explicitly forbids what the plan proposes.** Verbatim from `aclrollingreview.org/cfp`, retrieved 2026-05-17: *"ARR will not consider any paper that is under review in a journal or another conference at the time of submission, and submitted papers must not be submitted elsewhere during the ARR review period."* And: *"we will not consider any paper that overlaps significantly in content or results with papers that will be (or have been) published elsewhere, without exception."* The IEEE Software paper IS a journal submission; it will be under review during the EMNLP review period (July 7 – August 20); the two papers share 100% of the SWE-bench v2 corpus, ~100% of the headline finding text, and the same author. Submitting both is a **direct policy violation that is auto-desk-reject grounds if discovered**. "Submissions ≠ acceptances" does not save the plan when the submission itself is the violation.

2. **Statistical power at n=50 is inadequate for the stated MDE goal.** The user said "want MDE ~10pp" on adjacent-setting comparisons. At n=50 with a Sonnet baseline of ~30%, the actual MDE is **27.5pp**, not 10pp. To get a 10pp MDE at this baseline requires **n=356 per cell**. n=50 buys you n=30's old MDE plus ~8pp — not enough to detect a real monotone gradient unless the per-step slope is huge (≥25pp per step).

3. **The harness uses Meta's internal claude/codex/gemini CLIs through Plugboard.** Verbatim from `experiments/swebench_n60_v2_forced_tooluse.py` and `experiments/cli_subprocess.py`: the system invokes `claude`, `codex exec`, and `gemini` binaries served via Meta's internal gateway. The IEEE Software draft openly discloses this (line 112: *"peak parallelism of three claude tracks sharing the Anthropic Plugboard quota"*; line 165: *"Claude Code at Meta gateway returns 'exit 1' errors"*; line 205: *"installed via Meta's internal Plugboard infrastructure"*; line 245: *"Plugboard gateway returns exit-1 errors"*). The IEEE Software paper is single-blind, so Meta affiliation is fine there. **EMNLP is double-blind.** All Plugboard/Meta references must be anonymized, but the user's own MEMORY rule says: *"No Meta CLI for DataPup paper... never use /usr/local/bin/{claude,gemini} for paper inference"* — exactly because Meta CLI-derived data is not anonymizable and not externally reproducible. The same logic applies here. EMNLP reviewers would correctly flag the harness as either (a) using a non-anonymizable internal infrastructure, or (b) needing rerun on public APIs to be reproducible — and the second option burns the user's personal API budget, voids the timing plan, and creates a data discrepancy with the IEEE Software version.

The 1,600-run experiment plan, the HotpotQA extension, the timeline math, and the camera-ready story are all moot because of items 1, 2, and 3 above. The detailed audit below answers each of the seven stress-test questions in order regardless, because the user asked for it — but the verdict does not turn on those details.

---

## 1. HotpotQA feasibility audit

### 1a. Public accessibility — OK

- HuggingFace: `hotpotqa/hot_qa` (config: `distractor`, `fullwiki`). Distractor: 90,447 train / 7,405 dev. Fullwiki: 90,447 train / 7,405 dev / 7,405 test. **License: CC BY-SA 4.0.** Total download ≈ 1.27 GB. Source: `huggingface.co/datasets/hotpotqa/hot_qa`, retrieved 2026-05-17.
- Question types: **bridge** (multi-hop chained reasoning) and **comparison** (compare two entities). Exact bridge/comparison split is not stated on the HuggingFace card or the HotpotQA homepage; the original Yang et al. 2018 paper reports ~80% bridge / ~20% comparison in dev (commonly cited). The HF data does include the `type` field so a stratified sample is trivial.
- Difficulty levels: easy / medium / hard. Also a field on the HF data.

**Feasibility on access: clean.**

### 1b. Official scoring pipeline — partly OK, with a load-bearing caveat

- Official evaluator: `https://raw.githubusercontent.com/hotpotqa/hot/master/hot_evaluate_v1.py`. Free-standing Python script. Input: prediction JSON `{"answer": {id: str}, "sp": {id: [[title, sent_id], ...]}}`. Output: EM + F1 on answer, EM + F1 on supporting facts, joint EM + F1.
- Answer normalization: lowercase, strip articles (a/an/the), strip punctuation, collapse whitespace. Special handling for yes/no/noanswer (must exact-match).
- **The hard part: the official scorer requires supporting-facts predictions as well as answers.** "Joint F1" multiplies answer F1 by supporting-fact F1. A CLI agent that just emits a free-form answer will get supporting-fact F1 = 0, making the joint score useless. The paper would have to either (a) report only answer EM + answer F1 (foregoing the joint metric and looking incomplete to NLP reviewers), or (b) force the model to emit a structured supporting-fact list (which is itself a tool-use protocol — the very thing the paper is supposed to measure stress on, creating circularity).

**This is a real problem the user's plan does not address.** The "EM + F1 scoring" line in the plan glosses over the fact that the official scorer is built around the joint metric, and NLP reviewers will notice if you cherry-pick only the answer-F1 subset.

### 1c. Per-instance latency on a frontier-tier CLI subprocess — estimable, not measured

The IEEE Software paper reports 480 instance-runs (8 cells × n=60) in 75 hours of CLI-bound compute with peak parallelism of three claude tracks. That averages **~9.4 minutes per instance-run** on SWE-bench Lite, **single-process equivalent**. SWE-bench Lite has a much heavier prompt (repo context, search loop, multiple iterations) than HotpotQA. Reasonable lower bound for HotpotQA on the same harness: 2-4 minutes per instance for distractor (10 paragraphs fed in-context, simple QA), 5-10 minutes for fullwiki (requires retrieval, which the agent has to perform via search tool — but the harness's `search_code` stub returns hard-coded fake results, so fullwiki is **not actually runnable on this harness without writing a real Wikipedia retrieval tool**).

**Realistic wall-clock for Experiment C (800 runs on HotpotQA):**
- Distractor only (no retrieval needed): 800 × 3 min / 3-way parallelism ≈ **13.3 hours** lower bound, **40+ hours** if per-run latency is closer to SWE-bench scale (which it will be because the forced-search-protocol harness wastes iterations on synthetic search calls before answering).
- Fullwiki: not feasible without building a Wikipedia retrieval tool (estimated 20-40 extra engineering hours for a non-toy implementation).

The plan's "~30-40h" estimate for Experiment C is only credible for **distractor-only, no real retrieval, answer-only scoring (no supporting facts)**. That subset is a defensible feasibility envelope, but it is not "HotpotQA" — it is "HotpotQA-easy-mode with three caveats", and the NLP reviewers will see exactly that.

### 1d. The forced-protocol mechanism does not naturally port to HotpotQA

The SWE-bench v2 harness's "forced protocol" is: model must call `search_code` ≥ min_searches times before emitting a patch. On HotpotQA, the analog would be: model must call a retrieval tool ≥ min_searches times before emitting an answer. But:
- HotpotQA-distractor has 10 paragraphs **already in the prompt context**. There is nothing meaningful for the model to "search" — the answer is in the visible context.
- HotpotQA-fullwiki requires real Wikipedia retrieval, which the current harness does not implement.
- Even if you bolt on a fake-search stub, forcing min_searches=5 on a question whose answer is in the visible prompt context will artificially cap answer quality — but this is uninteresting because the forcing is artificial. The reviewer's reaction: "you forced an irrelevant tool call; of course the answer rate drops; this is not a finding."

**Verdict on Experiment C: as specified, it is not a clean port of the forced-protocol mechanism to HotpotQA. To make it clean, the harness needs a real document-retrieval tool surface and HotpotQA-fullwiki, which is 20-40 hours of additional harness engineering on top of the run-time budget.**

---

## 2. Sample size adequacy at n=50

Two-sample binomial MDE, α=0.05 two-sided, β=0.20 (computed via Python/scipy normal-approximation; iteratively verified):

| Baseline | MDE at n=30 | **MDE at n=50** | MDE at n=60 | n needed for 10pp MDE |
|---|---|---|---|---|
| 5% | 27.8 pp | **19.7 pp** | 17.4 pp | n=141 |
| 13% (Haiku v2) | 32.2 pp | **24.0 pp** | 21.6 pp | n=231 |
| 30% (proposed Sonnet adjacent-setting baseline) | 35.4 pp | **27.5 pp** | 25.0 pp | n=356 |
| 50% | 33.4 pp | **26.7 pp** | 24.5 pp | n=388 |
| 85% (Opus / GPT-5.5) | 15.0 pp | **14.7 pp** | 13.8 pp | n=141 |
| 90% (Haiku v1) | 10.0 pp | **10.0 pp** | 10.0 pp | n≈85 |

**Adjacent-setting comparison (min_searches=2 vs 3 within Sonnet, baseline ~30%):** the user said "want MDE ~10pp". At n=50, actual MDE = **27.5pp**. To achieve the user's stated 10pp MDE you need n≈**356 per cell**, which means the design becomes 4 tiers × 4 sweep settings × 356 ≈ **5,700 runs on SWE-bench alone** — ~14× the planned budget, not 1×.

**Tier-by-strictness interaction (Opus vs Sonnet at min_searches=3, ~85pp observed gap):** trivially detectable at any reasonable n. n=50 is overkill for this comparison. But this comparison is also already in IEEE Software at n=60 — no new information.

**HotpotQA generalization (continuous F1 on 0-100 scale):** modeling F1 spread as σ ≈ 0.40 (reasonable for HotpotQA — answers cluster at 0 and 1 with mid-range partial credit), MDE at n=50 ≈ **22 pp F1**. To detect a 10pp F1 difference reliably, need n≈250 per cell.

**Aggregate verdict:** n=50 is barely-an-improvement-over-n=30 for the comparisons that actually carry the paper. The user's intuition that "n=50 buys real power" is wrong by a factor of ~5×. Either:
- (a) re-scope the claim from "monotonic gradient" to "step-function effect at min_searches ≥ 2 vs min_searches = 1" (which n=50 can detect at ~20pp), and accept that the paper now reports a binary effect, not a gradient, which is the same claim IEEE Software already has;
- (b) accept that n=50 cannot statistically distinguish adjacent settings and report a descriptive sweep without significance claims (which weakens the paper's "monotonic gradient" framing to the point of empty).

Neither (a) nor (b) supports the plan's central narrative.

---

## 3. Timeline realism

**Hard deadline:** 2026-06-16 (30 days from 2026-05-17). Plus IEEE Software July 7 (52 days). Plus user's day job.

| Item | Plan claim | Realistic | Notes |
|---|---|---|---|
| Experiment A (Sonnet+Haiku, 400 runs) | ~20h | 25-45h | Per-run ~9.4 min ×400 ÷ 3-way parallelism = 20.9h baseline. Sonnet/Haiku v2 had 22-25 gateway exit errors per 60 runs; reruns push closer to 30-45h. |
| Experiment B (Opus+GPT-5.5, 400 runs) | ~15h | 20-30h | Cleaner cells; Plugboard quota is the binding constraint. |
| **Experiment C harness build (HotpotQA tool surface)** | not specified | **20-40h** | New benchmark loader, new search/retrieval tool, new answer parser, new scoring pipeline (or call official scorer), bridge/comparison stratified sampling, dry-run debugging. The "4h" estimate in the original plan was already unsupported; the user's revised plan does not re-estimate. |
| Experiment C (800 runs on HotpotQA) | ~30-40h | 30-60h | Distractor-only; fullwiki not feasible without retrieval tool. |
| Draft writing (6-page ACL) | not specified | 20-30h | Cannot reuse much from existing EMNLP draft (frozen, falsified ceiling-effect interpretation). New write. |
| Anonymization | not specified | **8-15h** | Must scrub: Meta affiliation, Plugboard references, Claude-Code-at-Meta, "Gemini CLI at Meta", `\citep{aiware2026}`, IEEE Software cross-reference (which double-blind forbids citing as forthcoming companion work), GitHub repo URL (`github.com/Krishnachaitanyakc/AgentTelemetry`), data inventory paths, and every CLI version disclosure. Non-trivial. |
| Cold-review loops (2-3 rounds) | "2-3 rounds" | 24-36h | Per project CLAUDE.md Section B2, iterate until PASS. Each round = 8-12h. |
| **Concurrent IEEE Software polish for July 7** | not in EMNLP budget | 15-25h | The IEEE Software submission is also load-bearing for the EB-1A portfolio and is on the same compute infrastructure. Cannot ignore. |
| Buffer | not specified | 10-20% slack | Day job, OpsMate work, six other in-flight venues to monitor. |

**Realistic sum (excluding IEEE Software work):** 25+20+30+45+25+12+30 = **187 hours** in 30 days = **6.2 hours/day every day** with zero misses, on top of the day job. With IEEE Software polish folded in: **>200 hours**, ≈ 7+ hours/day every day.

**Verdict:** infeasible by ~2× even under the most charitable accounting. The user has a day job, ongoing OpsMate work, and the IEEE Software deadline is 22 days after EMNLP — overlapping the cold-review and submission-prep windows. The plan as scoped requires either dropping Experiment C entirely (which the user has said is load-bearing for EMNLP scope-fit) or pushing the IEEE Software submission past July 7 (which the user has said is non-negotiable).

---

## 4. Harness risk for HotpotQA

### 4a. Output parseability

Modern CLIs (claude --print, codex exec, gemini) emit free-form text. Forcing `<answer>X</answer>` tags via system prompt **works ~70-90% of the time on frontier tiers** (Opus, GPT-5.5) and considerably worse on budget tiers (Haiku) — based on the existing v2 forced-tool-use evidence where Sonnet/Haiku had `patch_suppressions` averaging 4.67-5.75 indicating they routinely violate the protocol. For HotpotQA:
- Frontier tier: extract via regex on `<answer>...</answer>`, fall back to last-line heuristic. Probably workable.
- Budget tier: high parse-failure rate. Need an **LLM-judge fallback** (which adds cost, latency, a new validation step, and inter-rater reliability concerns). The user's existing AIware paper uses Cohen's κ=0.904 inter-rater for fault labeling — comparable rigor would be needed here.

The plan glosses this. Plan says "EM + F1 scoring" as if the model output goes directly into the official scorer. In practice it goes through a parser that fails on a non-trivial fraction of budget-tier outputs, and the fraction itself depends on min_searches (which is the IV) — creating a confound where "lower patch rate at high min_searches" might be "lower parseable-output rate at high min_searches", indistinguishable.

### 4b. Free-form answer scoring on official EM+F1

Official `hot_evaluate_v1.py` does aggressive normalization (lowercase, strip articles, strip punctuation, collapse whitespace) — this absorbs most cosmetic variation. **But it still requires you to extract a single answer string.** Free-form CLI outputs include reasoning chains, intermediate "let me check" statements, and sometimes multi-sentence answers. You need a parser. The parser is itself a confound. An LLM-judge resolves this but adds cost.

### 4c. Bridge vs comparison stratification

The HF dataset includes the `type` field. Stratifying n=50 across bridge vs comparison gives ~40 bridge / ~10 comparison per cell at the natural ratio, or 25/25 if forced-balanced. The plan does not specify. **At 25/25, sub-cell n=25 cuts MDE further** (MDE at n=25 baseline 30% is ~38pp — useless). At natural ratio, the comparison sub-cell at n=10 is unreportable. **The plan needs n≥80 per cell to support even a coarse bridge/comparison contrast at any MDE that would survive review.**

### 4d. Retrieval requirement

HotpotQA-distractor: 10 paragraphs in-context, no retrieval needed. Answerable from prompt. The forced-protocol mechanism (min_searches sweep) is **not meaningful** here because there is nothing to search — the answer is in the visible context. Forcing searches reduces to "the model wastes iterations on synthetic search calls before reading the context", which is a contrived setup an NLP reviewer will (correctly) call out as an artifact.

HotpotQA-fullwiki: requires real Wikipedia retrieval. The current harness's `search_code` stub returns hard-coded fake results. Building a real Wikipedia retrieval tool surface is 20-40 hours of harness engineering and itself becomes a confound (retrieval quality dominates answer quality, masking the protocol-forcing effect).

**Verdict on harness risk: HotpotQA is the wrong NLP task for the forced-protocol mechanism.** The mechanism only meaningfully exercises a tool surface when the tool is actually needed and the model has to choose between using it and not — on distractor the tool isn't needed; on fullwiki the tool quality dominates. A task with a genuinely-needed tool surface and a controllable correctness signal (e.g., a calculator-required math benchmark with the calculator behind a tool gate, or τ-bench's airline tasks where booking actions are gated behind verification calls) would be a cleaner match. HotpotQA is a brand-name NLP benchmark — which is why the plan chose it — but brand-name is not fit-for-purpose.

---

## 5. Worst-case: Experiments A+B succeed, Experiment C nulls

The user asks: if A+B produce a clean monotonic sweep gradient but C (HotpotQA) shows no gradient, does the paper still have a defensible story?

**No.** Specifically:

1. The plan's whole reason for adding HotpotQA was to address the EMNLP scope-fit problem (SWE-bench is not an NLP venue's natural domain). If C nulls, you have a SWE-bench-only paper at an NLP venue, which is the original scope problem the plan was trying to solve. The paper rejects on scope.

2. The plan's framing depends on "this is a general phenomenon, not a SWE-bench artifact." A null on the NLP task is direct evidence that **it might in fact be a SWE-bench artifact** (or, worse, a Plugboard-gateway-exit-error artifact, which IEEE Software §VII §L4 already concedes is a possibility). Either way, the EMNLP paper's central claim weakens, not strengthens.

3. The honest interpretation of a C-null result is: "forced protocol degrades models on code tasks, but not on QA tasks — perhaps because QA-style tool use is more deeply trained into modern instruct/RLHF models than code-search tool use." That is a perfectly publishable observation, but it is a different paper than the one planned — it would need a designed comparison across multiple task types, not a SWE-bench-centered paper with one NLP afterthought.

4. There's a known prior in HotpotQA-on-modern-LLMs: modern frontier models score ~70-85% F1 on HotpotQA-distractor near out-of-the-box. Forced retrieval scaffolds on a task the model can already handle from context are likely to either (a) help marginally (more deliberation), (b) hurt marginally (wasted iterations), or (c) show no effect. The null is the most likely outcome.

**Verdict: C-null is the modal outcome and it does kill the paper.** Plan B options the user might invoke ("reframe as code-specific finding") collapse the paper back into the IEEE Software territory and re-trigger the overlap-rejection risk from §1.

---

## 6. arXiv-deferral risk

The user proposes: do not post either paper to arXiv until both venues decide. Audit of leakage channels:

| Channel | Status | Risk |
|---|---|---|
| arXiv | User-controlled, deferred | None if deferral is honored. |
| **IEEE Software Author Portal preprint index** | IEEE policy does NOT publicly index submissions before acceptance (verified via IEEE Author Center pages; no public submission index found). | Low — not a discovery channel. |
| **AgentTelemetry public GitHub repo** | `github.com/Krishnachaitanyakc/AgentTelemetry` — **PUBLIC, HTTP 200**. But `paper/emnlp2026/` and `paper/ieee_software_2026/` directories are **NOT committed** (verified: `git ls-tree -r --name-only HEAD \| grep paper/emnlp\|paper/ieee_software` returns zero hits). The v2 harness files (`swebench_n60_v2_forced_tooluse.py`, `swebench_n60_opus_cli.py`, `tau_bench_runner.py`, `cli_subprocess.py`, `launch_n60*.sh`) are **also NOT committed** to the public repo (verified). | **Low for the v2-specific artifacts. Moderate for the broader research narrative** — the AIware paper, the position paper, and earlier SWE-bench experiments ARE in the public repo and form a clear research trail. A reviewer who Googles "AgentTelemetry" + "SWE-bench" + "forced protocol" finds the public README and the AIware lineage; finding the v2-specific files requires either the local laptop or a leaked draft. |
| **AIware 2026 accepted paper proceedings** | Conference is July 6-7, 2026 (BEFORE EMNLP review release ~August 20). Accepted papers go to ACM Digital Library. The AIware paper does cite the SWE-bench n=60 Opus replication but does NOT include the v2 forced-protocol Sonnet/Haiku collapse. | Moderate — establishes the author's research stream and makes the EMNLP paper feel like a sequel even if formally non-overlapping. |
| **NeurIPS 2026 submitted paper** | Under review during EMNLP review window. Cross-pollination unlikely (different reviewer pools) but possible. | Low. |
| **Author identity** | The user is publishing under their real name on AIware, NeurIPS, IEEE Software, and the GitHub repo. EMNLP is double-blind. **The EMNLP paper must be anonymized to the level where reviewers cannot guess the author from the data, harness, framing, or repo style.** Given that AIware (accepted, real name) and this EMNLP draft would share the AgentTelemetry framing and the SWE-bench v2 data, reviewers familiar with AIware would identify the author trivially. | **High.** This is independent of arXiv. Even with zero arXiv posting, a reviewer who has read AIware (which is now circulating in the field) will recognize the data + framing + author. |
| **Meta CLI / Plugboard references in the data + harness** | The data was collected via Meta's internal `claude` / `codex` / `gemini` binaries; this is openly disclosed in the IEEE Software draft. The EMNLP version would have to scrub or generalize these references, but the harness behavior (gateway exit errors at high min_searches counts) is itself a Plugboard artifact and is hard to anonymize without misrepresenting the data. | **High and irreducible.** Either you disclose the Meta CLI (which deanonymizes) or you don't (which creates a methodological gap a careful reviewer will flag as "what was the inference infrastructure?"). |

**arXiv-deferral does solve the arXiv-specific leakage but does NOT solve the broader discoverability and policy-violation problems.** The dominant risk is not "EMNLP reviewer finds the IEEE Software arXiv preprint" — it is "EMNLP reviewer either (a) recognizes the data from AIware and the GitHub repo, or (b) flags the Meta CLI infrastructure as a methodology issue, or (c) the area chair compares against IEEE Software submission disclosures if the author is required to declare concurrent submissions (which ARR/EMNLP policy implicitly requires by forbidding them)."

**Verdict: arXiv deferral is necessary but insufficient. The leak vectors that matter most are the public GitHub repo, the accepted AIware paper that establishes the research stream, and the Meta CLI infrastructure that is intrinsically non-anonymizable.**

---

## 7. Camera-ready duplication acceptability — what does "accept duplication" actually look like

The user said "accept duplication if both accept." Be specific about what that means:

### 7a. IEEE Software policy on overlap with conference papers

IEEE generally permits a journal version that extends a conference paper if (a) the journal version includes ≥30% new material and (b) the conference paper is properly cited. **But IEEE Software is a magazine**, not a journal — the IEEE Software CFP for the Edge-Cloud Continuum special issue (the venue this work is targeted at) follows IEEE periodical policy: substantial overlap with concurrent work requires disclosure at submission time and editor approval.

The user's plan is the inverse: a **short conference paper (EMNLP, 6 pages)** that significantly overlaps a **magazine article (IEEE Software, ~7-8 pages typical)** with no clean "extended journal version" relationship. There is no natural long-form / short-form split because both venues want the headline finding stated with full evidence.

### 7b. ARR/EMNLP policy on overlap

Already quoted in §1: *"we will not consider any paper that overlaps significantly in content or results with papers that will be (or have been) published elsewhere, without exception."* No exception for short-form magazine articles, IEEE Software, or any other venue type. **Under the literal reading of this policy, the plan is auto-reject grounds at EMNLP if discovered.** And ARR explicitly tells authors to "cite each other and discuss the differences in the related work section" — which requires non-anonymous cross-reference at submission, which violates double-blind submission requirements.

### 7c. The "honest broker" cross-reference

If both accept, the practitioner-clean way to honest-broker would be:
- IEEE Software (magazine, single-blind, short-form, deployment-flavored): the headline paper. Cites EMNLP version as "the technical evaluation of the protocol-forcing mechanism is reported in [EMNLP citation]."
- EMNLP (conference, double-blind, technical evaluation): cites IEEE Software as "the deployment context and case study are reported in [IEEE Software citation]."

This requires:
1. **Coordinated submission timing** (which the user has: EMNLP June 16, IEEE Software July 7).
2. **Non-overlapping core claims** (which the plan does not have — both papers feature the Sonnet/Haiku v2 collapse as a headline).
3. **Explicit cross-reference at submission** (which ARR/EMNLP forbids during double-blind review).
4. **Editor / area chair approval** (which the plan does not address).

The plan does not honest-broker. It hopes the duplication will not be noticed. That is not a strategy.

### 7d. If both accept and the overlap is later discovered

Possible outcomes ordered worst-to-best:
1. **EMNLP retraction post-acceptance** if reviewers later notice the IEEE Software submission. The ARR policy has no retraction-specific clause but the overlap clause is "without exception."
2. **IEEE Software editor requires removal of overlapping content** in camera-ready, which would gut the IEEE Software paper.
3. **Both venues publish; field discovers the duplication**; author reputation damage that persists for years on Google Scholar and outweighs the EB-1A benefit of having an extra publication.
4. **Both venues publish cleanly** with the duplication being technically permitted because IEEE Software is a magazine, not an archival journal — the most optimistic interpretation, but it requires explicit IEEE Software editor sign-off plus EMNLP area chair sign-off, neither of which is in the plan.

**Verdict: "accept duplication if both accept" is not a real plan. It is a hope.**

---

## 8. New evidence the prior audit did not surface fully

1. **ARR/EMNLP overlap clause is "without exception" and forward-looking ("will be").** Prior audit gestured at the overlap risk; the verbatim policy text is stronger than the prior framing.

2. **n=50 sample size analysis.** Prior audit only computed for n=30. The full table above shows n=50 buys ~5pp of MDE over n=30 — meaningful but nowhere near the user's stated 10pp goal.

3. **HotpotQA + forced-protocol mechanism is a category mismatch.** Distractor mode has the answer in-context (no need to search); fullwiki requires real retrieval (current harness can't do it). The forced-search mechanism that motivates the paper does not naturally exercise either HotpotQA setting.

4. **Meta CLI / Plugboard infrastructure is intrinsically non-anonymizable for a double-blind venue.** The user's own MEMORY rule for the DataPup paper says exactly this. Re-applying that rule here means the data the EMNLP paper depends on cannot be honestly disclosed in a double-blind submission without either deanonymizing the author or hiding the infrastructure (which is a methodology gap).

5. **AgentTelemetry public GitHub repo establishes the research stream under the author's real name.** Prior audit did not verify the GitHub repo's visibility or check what is/isn't tracked. Confirmed: repo public, paper/emnlp2026 and paper/ieee_software_2026 NOT tracked, v2 harness NOT tracked. Good news for v2-specific leakage; bad news for "EMNLP reviewer is told to do a quick Google search before submitting their review" — the AIware lineage is fully discoverable.

6. **HotpotQA official evaluator requires supporting-facts predictions for the headline metric (joint F1).** Plan glosses this. Reporting only answer F1 will look incomplete to NLP reviewers; emitting supporting facts requires the model to follow yet another protocol layer that is itself a confound on the IV (forced-protocol compliance).

---

## 9. Final verdict and recommendation

### Verdict: **ABANDON-AGAIN**

The plan's revisions (n=50 not n=30, dual-submit, HotpotQA extension, arXiv deferral) do not address the policy-violation, statistical-power, harness-fit, and anonymity problems. New evidence (full ARR/EMNLP policy text, n=50 MDE math, HotpotQA mechanism-fit analysis, Meta CLI / Plugboard anonymity, GitHub repo public status) strengthens the prior audit's conclusion rather than weakening it. The user's rationale ("submissions ≠ acceptances; parallel-submit is acceptable; accept camera-ready duplication") is reasonable as a meta-principle but does not apply here because:

- The submission itself is the policy violation (not just the acceptance).
- Parallel-submit is explicitly forbidden by ARR/EMNLP, including for journals.
- "Accept camera-ready duplication" is forbidden by the same clause and would require editor sign-offs that are not in the plan.

### Recommended action (in priority order)

1. **Mark EMNLP task #16 as `completed-deferred`** with a 1-line rationale: *"ARR/EMNLP overlap clause forbids parallel-submit with IEEE Software draft. Defer to EMNLP 2027 on new non-overlapping data."* Strike tasks #25 and #26.
2. **Redirect 100% of the 30-day energy to IEEE Software polish for July 7.** This is the venue where the headline finding belongs (single-blind, magazine-format, deployment-flavored, no overlap conflict). The cold-reviewer rounds already in flight on IEEE Software (`cold_reviewer_report_round3_2026-05-16.md`) are the highest-ROI use of available cycles.
3. **For an actual future EMNLP submission (2027 cycle, June 2027 deadline):**
   - Design from scratch for the NLP venue. Pick a benchmark with a meaningful tool surface (τ-bench airline/retail, ToolBench, GAIA — not HotpotQA).
   - Build the harness on public APIs (Anthropic public API, OpenAI public API, Gemini API), not Meta CLIs, so anonymization is clean.
   - Pre-register the sweep design with n≥150 per cell (to get sub-15pp MDE at intermediate baselines).
   - Plan a 60-90 day execution + writing window, not 30 days.

### What changes the verdict to PROCEED

If the user can produce, in writing, EITHER:
- (a) An EMNLP area-chair statement that this specific overlap arrangement is permitted, OR
- (b) An IEEE Software editor statement that the conference paper takes precedence and IEEE Software will accept publication subject to the conference paper appearing first, AND a re-scoped EMNLP paper that drops the SWE-bench data entirely and presents an n≥150 HotpotQA-fullwiki experiment with a real retrieval tool surface,

then the plan becomes a reasonable risk to take. Without either, the plan should not proceed.

### What the conditional fallback looks like (if the user insists)

**Minimum-viable salvage that does not violate ARR/EMNLP policy:**
- **Drop SWE-bench entirely from the EMNLP submission.** All SWE-bench data goes only to IEEE Software.
- **EMNLP paper is HotpotQA-only**, using a freshly-designed harness with real Wikipedia retrieval (20-40h engineering investment), public-API model inference (no Meta CLIs), n=150-200 per cell, focused on a different framing: "How does tool-use protocol strictness affect multi-hop QA performance across model tiers?"
- **Even this minimal salvage is not feasible in 30 days alongside the IEEE Software push** — engineering + 1,600+ HotpotQA runs + 6-page write + anonymization + cold review > 200 hours of focused work, which the user does not have available alongside their day job.

The honest conclusion is: defer to EMNLP 2027, polish IEEE Software for July 7, do not re-litigate this decision a third time.

---

## Evidence index (verifiable in this session)

- **ARR/EMNLP overlap and dual-submission policy:** https://aclrollingreview.org/cfp (WebFetch 2026-05-17). Verbatim: *"ARR will not consider any paper that is under review in a journal or another conference at the time of submission, and submitted papers must not be submitted elsewhere during the ARR review period."* and *"we will not consider any paper that overlaps significantly in content or results with papers that will be (or have been) published elsewhere, without exception."*
- **EMNLP 2026 Industry CFP policy:** https://2026.emnlp.org/calls/industry_track/ (WebFetch 2026-05-17). Verbatim: *"EMNLP 2026 will not consider any paper that is under review in a journal or another conference at the time of submission."*
- **HotpotQA dataset characteristics:** https://huggingface.co/datasets/hotpotqa/hot_qa. 90,447 train / 7,405 dev (distractor); CC BY-SA 4.0. Fields: id, question, answer, type (bridge|comparison), level (easy|medium|hard), supporting_facts, context.
- **HotpotQA evaluator:** https://raw.githubusercontent.com/hotpotqa/hot/master/hot_evaluate_v1.py. Requires `{answer: {id: str}, sp: {id: [[title, sent_id]]}}` for full scoring including joint F1.
- **IEEE Software paper Meta CLI / Plugboard disclosure:** `paper/ieee_software_2026/ieee_software_paper.tex:112, 165, 205, 207, 245`.
- **IEEE Software paper wall-clock:** line 112: *"approximately 75 hours of CLI-bound compute, with peak parallelism of three claude tracks"* for 480 runs → ~9.4 min/run.
- **v2 forced harness uses Meta CLIs:** `experiments/cli_subprocess.py:20-42` (`claude --print`), `:80-98` (`codex exec`), `experiments/swebench_n60_v2_forced_tooluse.py:96-127` (`Gemini CLI at Meta`).
- **v2 harness synthetic search stub:** `experiments/swebench_n60_v2_forced_tooluse.py:351`.
- **Public GitHub repo confirmed accessible:** `curl -s -o /dev/null -w "%{http_code}" https://github.com/Krishnachaitanyakc/AgentTelemetry` → 200.
- **Paper drafts NOT in public git:** `git ls-tree -r --name-only HEAD \| grep -E "paper/(emnlp\|ieee_software)"` → zero hits.
- **v2 harness scripts NOT in public git:** `git ls-tree -r --name-only HEAD \| grep -E "(launch_n60\|swebench_n60_v2\|forced_tooluse\|cli_subprocess)"` → zero hits.
- **AIware accepted, public author identity:** commit `1e9bf99 AIware 2026 camera-ready` in `git log` of public repo.
- **MDE computations:** Python/scipy normal-approximation, verified at n ∈ {30, 50, 60} across baselines {5, 13, 30, 50, 85, 90}%. See §2 table above.
- **n=50 v=2 cell statistics from existing data:** `paper/ieee_software_2026/data_inventory.json:197-273` (v2-sonnet 3.3%/3.3%, v2-haiku 13.3%/11.7%, all fisher_exact_p=1.000).
- **Prior EMNLP decision memo (Option E recommendation):** `paper/emnlp2026/EMNLP_DECISION_2026-05-16.md:77-85`.
- **Prior cold-reviewer ABANDON verdict:** `paper/emnlp2026/EMNLP_PLAN_STRESS_TEST_2026-05-17.md:9-13`.
- **User MEMORY rule against Meta CLI for double-blind papers:** *"No Meta CLI for DataPup paper — never use /usr/local/bin/{claude,gemini} for paper inference"* (`feedback_no_meta_cli_for_datapup.md`).
