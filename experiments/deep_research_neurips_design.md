# Deep Research: NeurIPS-Grade Closed-Loop Intervention Experiment Design for AgentTelemetry

**Date:** 2026-04-30
**Mission:** Find a benchmark + experimental design where (1) reasoning-loop / planning failures are PREVALENT in frontier models, (2) ground-truth verification is automated, (3) sample size and effect size can clear NeurIPS statistical bars, and (4) it is feasible in ~3 days.

---

## Executive summary

**The SWE-bench Lite saturation problem is real and forces a pivot.** GPT-5.5 emits a `<patch>` tag on 99.4% of iter=1 problems and Claude Opus 4.7 on ~82%. There is no headroom for a "stop reasoning loop" intervention to demonstrate measurable lift on either model on SWE-bench Lite, regardless of n. Compounding this, our current metric (`<patch>` emission, not actual SWE-bench-harness resolution) reviewers will (rightly) reject as not ground truth.

**Two viable repositionings exist.** Either (A) move to a benchmark where frontier models solve <40% and loop-class failures are documented (best candidates: τ-bench retail/airline pass^k, AppWorld Challenge, GAIA Level-2/3, DABStep Hard, ScienceAgentBench, WebArena), or (B) reposition the contribution as a *detection* paper — measure precision/recall/latency of the 14 detectors against AgentDebug's `AgentErrorBench` and the MAST trace corpus rather than attempting closed-loop intervention. Option B is safer in 3 days; Option A is more impactful but riskier.

**The most defensible 3-day path** is a hybrid: a tightly scoped closed-loop intervention experiment on **τ-bench retail** (pass^k consistency where loops directly degrade pass^4) with two providers (Claude Opus 4.7 + GPT-5.5), n=115 tasks × 4 trials × 2 conditions × 2 models = 1,840 runs; **plus** a detection-precision evaluation against the AgentDebug `AgentErrorBench` corpus (released 2025-09) so the paper has both detection AND intervention evidence. This matches the experimental shape of the strongest recent comparators (Wink arXiv:2602.17037, Aegis arXiv:2508.19504, AgentDebug arXiv:2509.25370).

---

## 1. Top 5 candidate benchmarks — ranked

### #1 — τ-bench / τ²-bench (Yao et al., arXiv:2406.12045 / Barres et al., arXiv:2506.07982)

- **Sample size:** ~165 tasks (115 retail + 50 airline) in v1; τ²-bench adds telecom + banking, total ~275 tasks. τ-voice variant has 278 tasks.
- **Frontier baselines:** GPT-4o solves <50% pass^1, drops to **~25% pass^8 in retail (60% relative drop)**. Claude Sonnet 3.5 reportedly higher pass^1 but similar pass^k cliff. Reported by Sierra (taubench.com) and Yao et al.
- **Loop prevalence:** EXTREMELY HIGH — pass^k decay IS the failure mode. Agents inconsistently follow policy under repeated trials; the "policy-violation under user pressure" failure pattern is exactly a metacognitive intervention target.
- **Evaluation:** Database-state diff vs. annotated ground state. **Fully automated, no LLM judge.** This was a major reviewer ask.
- **Why it works for our intervention:** Our REASONING-loop detector flags consecutive identical tool calls; τ-bench's most-cited failure is agents capitulating to user pressure and looping on re-confirmation. The pass^k metric is *purpose-built* to surface intervention effects (more trials → more headroom for the intervention to either help reliability or expose detector overfitting).
- **Headroom:** Pass^1 ~50% and pass^8 ~25% give ~50pp of dynamic range. Even a +5pp lift is publishable.
- **3-day feasibility:** Tau-bench has a one-line `tau-bench` pip install, OpenAI/Anthropic SDK adapters, and runs a single retail task in <90s wall-clock. n=115 × 4 trials × 2 conditions × 2 models ≈ 1,840 runs ≈ 46 GPU-hours of API time, parallelizable to ~6 wall hours per provider with rate-limit headroom.

### #2 — AgentDebug AgentErrorBench (Yang et al., arXiv:2509.25370)

- **Sample size:** Annotated failure trajectories drawn from ALFWorld + GAIA + WebShop. The paper's own AgentDebug framework reports +24pp all-correct accuracy and +17pp step accuracy vs strongest baseline; +26% relative task-success improvement.
- **Loop prevalence:** Explicitly catalogued — their AgentErrorTaxonomy includes memory, reflection, **planning**, action, and system-level failure modes. Frontier baselines are reported to fail catastrophically on cascading-error scenarios.
- **Evaluation:** Per-step ground-truth annotated by humans + final task success on the underlying environments (test-based for ALFWorld/WebShop, human-judged for GAIA).
- **Why it works:** Our detection precision/recall can be evaluated *directly* on the released corpus without re-running any agents. Zero API cost. Highest-impact secondary table.
- **Headroom:** Direct comparison to AgentDebug as detection baseline — we can claim our 14-detector taxonomy is broader than their 5-class taxonomy.
- **3-day feasibility:** Trivial — pure offline classification once corpus is downloaded.

### #3 — AppWorld Challenge (Trivedi et al., arXiv:2407.18901, ACL 2024 Best Resource Paper)

- **Sample size:** 750 tasks; "challenge" subset has ~250 hard tasks.
- **Frontier baselines:** **GPT-4o ~30% on Challenge subset**, ~49% on Normal. Other models ≥16pp below.
- **Loop prevalence:** Documented — long-horizon tasks with 457 APIs across 9 apps; agents repeatedly call list endpoints and re-search instead of using found data. This is a textbook reasoning-loop manifestation.
- **Evaluation:** State-based unit tests — fully automated, harness-verified. Multiple valid solutions accepted.
- **Headroom:** 70pp of room on Challenge subset.
- **Why it might NOT work:** Setup overhead — AppWorld requires Docker containers per task, ~100 fictitious user databases, 60K LOC engine. Rate-limit-friendly but heavy infra. **Probably infeasible in 3 days from a cold start.**

### #4 — DABStep (Adyen + HuggingFace, 2025)

- **Sample size:** 450+ data-analysis tasks, split Easy/Hard.
- **Frontier baselines:** **Best model (o3-mini) only 16% accuracy. Claude 3.5 Sonnet 12%. DeepSeek V3 6%.** Massive headroom.
- **Loop prevalence:** Multi-step iterative reasoning required; reasoning models specifically flagged as needing extra prompt engineering, suggesting they thrash.
- **Evaluation:** Factoid answers with fuzzy/exact matching, **no LLM judge bias**.
- **3-day feasibility:** smolagents framework, Python-only, runs locally without per-task containers. Estimated ~200 tasks × 3 trials × 2 conditions × 2 models = 2,400 runs feasible in 12-24 wall hours.
- **Risk:** Very low absolute accuracy (16% best) means a +5pp absolute intervention lift is also a +30% relative lift, which sounds impressive but the small-N ceiling on the Hard subset (where LLMs solve 0-5% of tasks) means the intervention has nothing to "rescue." Mid-difficulty tier is the sweet spot.

### #5 — GAIA (Mialon et al., arXiv:2311.12983, ICLR 2024)

- **Sample size:** 466 questions total; 166 publicly graded; Level-1 (53), Level-2 (86), Level-3 (27) on validation.
- **Frontier baselines:** GPT-4-with-plugins originally 15%; modern frontier agents (GPT-5 deep research, Claude Opus 4 with tool use) ~70-75% on validation. Level-3 still very challenging.
- **Loop prevalence:** Multi-tool, multi-modal coordination — known failure mode is web-search loops on ambiguous queries.
- **Evaluation:** Exact-match graded against gold answers (some require LLM-judge for free-text).
- **Why it might NOT work:** Frontier models on Level-1/2 have nearly saturated; Level-3 has only 27 validation questions which is insufficient power. Level-2 (86 q) × 3 trials × 2 conditions × 2 models = 1,032 runs is feasible but baseline solve rate likely ≥60% which is ceiling-prone for our 2024-vintage intervention prompt.

### Honorable mentions — DO NOT pursue

- **WebArena (812 tasks):** Strong scientific value, GPT-4 only 14%, but each task requires 5 self-hosted Docker containers + Playwright. Setup is 1-2 days. Skip.
- **AgentBench (Liu et al., arXiv:2308.03688):** Aggregated 8-environment benchmark; nontrivial setup; superseded by AgentBoard in most modern papers.
- **AgentBoard (Ma et al., arXiv:2401.13178, NeurIPS 2024 oral):** 9 tasks / 1013 environments with progress-rate metric; strong scientific design but heavy multi-environment setup.
- **Multi-SWE-bench (arXiv:2504.02605):** Same `<patch>`-tag saturation problem on Java/Go as on Python; doesn't solve our underlying issue.
- **SWE-bench Multimodal (517 issues):** Stanford+Princeton, ICLR 2025. Visual elements not relevant to text-loop intervention.

---

## 2. Top 3 published intervention experiments to position against

### A. Wink (Nanda, Maddila et al., Meta, arXiv:2602.17037, Feb 2026)

**This is the closest existing comparator and the strongest single prior to position against.**

- **Setting:** Production coding agent at Meta, asynchronous self-intervention.
- **Misbehavior taxonomy:** 3 categories (Specification Drift, **Reasoning Problems** including repetitive loops, Tool Call Failures). Note: "Reasoning Problems" overlaps directly with our REASONING-loop detector.
- **Baseline failure rate:** ~30% of agent trajectories exhibit one of the three misbehaviors.
- **Sample size:** 10,554 A/B trajectories + 42,920 historical baseline + shadow-mode validation cohort.
- **Methodology:** Live A/B test, 50/50 traffic split, 15 days. Statistical significance reported (no specific test named in abstract).
- **Effect:** "90% of misbehaviors requiring single intervention" successfully resolved; statistically significant reductions in tool-call failures, tokens/session, engineer-interventions/session.
- **Frontier models tested:** Claude Sonnet 4 / 4.5, Claude Haiku 4.5, GPT-4o, GPT-5.1, Gemini 2.5 Pro.

**Positioning for AgentTelemetry:** Wink shows the field accepts production A/B as evidence; our paper offers (a) open-source, reproducible variant on public benchmark, (b) standardized OTel semantic conventions vs. Wink's internal logging, (c) detector taxonomy of 14 vs. their 3.

### B. Aegis (Song, Pekhimenko et al., arXiv:2508.19504)

- **Setting:** 5 agentic benchmarks (τ-airline, τ-retail, BFCL filesystem, CRMarena, MedAgentBench).
- **Failure taxonomy:** 6 modes — State-space Navigation, State Awareness, Tool Output Processing, Domain Rule Violation, User Instruction Following, Token/Turn Exhaustion.
- **Sample size:** 142 traces, 3,656 turns analyzed.
- **Intervention:** Three environment-side optimizations (observability enhancement, computation offloading, speculative actions).
- **Effect:** **+6.7-12.5% absolute success rate**, no agent or LLM modifications.
- **Statistical methodology:** Per-benchmark improvement table on analysis vs evaluation set, GPT-4.1 numbers headlined.

**Positioning:** Aegis intervenes on the *environment*; AgentTelemetry intervenes on the *agent's reasoning loop*. Complementary, not competitive. The +6.7-12.5pp range is also informative — it suggests our +12.5pp pilot was in-distribution for what's publishable, just under-powered.

### C. AgentDebug (Yang et al., arXiv:2509.25370)

- **Setting:** ALFWorld + GAIA + WebShop with annotated failure trajectories.
- **Failure taxonomy:** 5 high-level modes (memory / reflection / planning / action / system) refined into AgentErrorTaxonomy.
- **Effect:** +24pp all-correct accuracy, +17pp step accuracy vs strongest baseline; up to +26% relative task success improvement from targeted feedback.

**Positioning:** AgentDebug's intervention is similar in spirit (targeted corrective feedback) but post-hoc and human-annotated. Our intervention is real-time and detector-driven. Their corpus is the perfect detection-evaluation testbed for our 14 detectors.

### Older intervention literature (cite but don't position against)

- **Reflexion (Shinn et al., arXiv:2303.11366):** 91% pass@1 on HumanEval (vs. 80% baseline, +11pp). Self-reflection memory buffer. Different problem class (single-shot code) but seminal.
- **Self-Refine (Madaan et al., arXiv:2303.17651):** ~20% absolute improvement across 7 tasks via self-feedback. Same model in 3 roles.
- **Voyager (Wang et al., arXiv:2305.16291):** Skill library + iterative prompting in Minecraft. 3.3× unique items vs SOTA. Different domain.
- **DoVer (arXiv:2512.06749):** "Flips 18-28% of failed trials into successes" on GAIA/AssistantBench. Active failure-hypothesis verification. Recent (Dec 2025).
- **SCOPE (arXiv:2512.15374):** 14.23% → 38.64% on HLE via prompt evolution. Recent.
- **VIGIL (arXiv:2512.07094):** Self-healing reflective runtime. Recent.
- **ReIn (arXiv:2602.17022, ICLR 2026):** Test-time reasoning intervention for conversational error recovery.

---

## 3. Concrete experimental design recommendation

### Primary experiment: τ-bench retail × claude-opus-4.7 + gpt-5.5 × pass^k intervention

**Rationale:** Maximum headroom (pass^k cliff is the canonical loop failure), automated ground truth (DB-state diff), n=115 with 4 trials gives 460 trial-pairs per model — sufficient power for a Mann-Whitney U or paired-bootstrap on pass^k.

**Setup:**

| Parameter | Value |
|-----------|-------|
| Benchmark | τ-bench retail (n=115 tasks) |
| Models | claude-opus-4.7 (1M ctx) + gpt-5.5 — **both providers** addresses reviewer ask |
| Trials per task | k=4 (paired across conditions) |
| Conditions | A: baseline agent ; B: agent + AgentTelemetry detectors with closed-loop intervention |
| Total runs | 115 × 4 × 2 conditions × 2 models = **1,840 runs** |
| Detector triggers in scope | REASONING-loop (>=3 identical tool calls) + PLANNING-stall (no progress for >=N turns) + DELEGATION-cycle (handoff returns to same agent twice) |
| Intervention prompt | Same as current ("[INTERVENTION] You've called X 3+ times with same query. Stop. List 2 alternatives.") plus PLANNING-stall variant ("[INTERVENTION] You haven't made progress in N turns. Re-state goal and pick one concrete next action.") |

**Primary metric:** **pass^4** (probability all 4 trials succeed on the same task) — direct measure of reliability. Secondary: pass^1 (single-trial success).

**Statistical tests:**
- **Primary:** McNemar's test on per-task pass^4 (paired binary outcome A vs B). With n=115 and expected baseline pass^4 ~25%, a +10pp lift gives ~80% power at α=0.05.
- **Secondary:** Stratified bootstrap on pass^k curves (k=1..4) with 10K resamples; report 95% CI on the integral of pass^k.
- **Tertiary:** Per-failure-mode breakdown: of N tasks where REASONING-loop detector fired in baseline, how many flipped from fail→pass with intervention?

**Power analysis target:** Detect +10pp pass^4 lift at α=0.05 with 80% power. McNemar's with n=115 and baseline 25% → MDE ≈ 9-11pp. **If observed effect is <8pp, the experiment is null and we should not submit.**

**Ceiling-effect mitigation:**
- Use **pass^4 not pass^1** as primary — pass^k is purpose-built to defeat ceilings.
- Pre-register an *equivalence-margin* analysis: if intervention helps gpt-5.5 less (because gpt-5.5 has higher pass^1), report this honestly as a "ceiling discovered" finding.
- Stratify by initial-difficulty tier (top-quartile / middle-half / bottom-quartile baseline pass^1) — interventions concentrate in middle.

### Secondary experiment: detection precision/recall on AgentErrorBench

**Setup:** Download AgentDebug's released corpus (ALFWorld + GAIA + WebShop annotated failures). Run our 14 detectors over each trace. Compare detector outputs to human labels.

**Metrics:** Per-detector precision, recall, F1; macro-F1 across all 14; head-to-head vs AgentDebug's 5-class classifier.

**Sample size:** Whatever the released corpus contains (likely 500-2000 traces). No API cost.

**Time cost:** ~4 hours including download + classifier wiring.

### Tertiary experiment: real-LLM detector overhead on real workload

**Setup:** Re-purpose existing 159-run real-LLM corpus to report (a) p50/p95/p99 detector latency, (b) memory overhead, (c) span-emission cost. Already exists per task list (T2.5).

### What this gives the reviewer

1. Two providers ✓
2. Sample size n=115 × 4 × 2 = 920 paired comparisons per model ✓
3. Ground-truth verification (DB state diff) ✓
4. Statistical significance via McNemar on primary metric ✓
5. Detection precision/recall on a third-party annotated corpus ✓
6. Honest ceiling-effect disclosure ✓
7. Comparison to Wink/Aegis/AgentDebug as the contemporary baseline ✓

---

## 4. Anti-recommendations — DO NOT run these experiments

1. **DO NOT re-run SWE-bench Lite at any sample size.** Both frontier models near-saturate `<patch>` emission. No intervention can show effect against ceiling. Even with the official harness reducing to 30-40% true resolve rate, the intervention needs the *agent to be looping*, and `<patch>`-on-iter-1 means there's no loop to interrupt.

2. **DO NOT pursue WebArena from scratch in 3 days.** Setup of 5 Docker containers + auth per task is at least 1 full day and you will hit auth/network issues. Worth running for v2 of the paper, not now.

3. **DO NOT run AgentBench (full 8 environments).** Cumulative setup + heterogeneous evaluation is 2-3 days. Pick one environment if you must.

4. **DO NOT pursue any benchmark whose only ground truth is LLM-as-judge.** Reviewers explicitly asked for ground truth verification; LLM judges undermine the rebuttal.

5. **DO NOT add a third provider (Gemini).** Two is enough for "multiple providers"; a third triples API cost and adds another tail to the rate-limit graph without proportional reviewer credit.

6. **DO NOT report only pass^1 on τ-bench.** Pass^1 alone gets the same ceiling problem as SWE-bench Lite. Headline must be pass^k.

7. **DO NOT pursue HumanEval / MBPP / coding-benchmark interventions.** These are single-shot generation, not agent loops. Reflexion already covers this space and you'd be re-inventing.

---

## 5. Honest 3-day feasibility assessment

**You have 3 days before NeurIPS May 6 deadline. Realistic scope:**

**Day 1 (12h budget):**
- 4h: Wire τ-bench harness + AgentTelemetry into existing runner (reuse B1 infra). Verify single-task end-to-end on retail.
- 4h: Download AgentErrorBench, build offline classifier, get first detection P/R numbers.
- 4h: Kick off τ-bench retail × claude-opus-4.7 baseline (n=115 × k=4 = 460 runs); run in parallel with detector-on condition.

**Day 2 (12h budget):**
- 4h: Continue τ-bench runs for both providers + both conditions (~900 more runs). Parallelize across API keys.
- 4h: Build statistical analysis pipeline (McNemar + bootstrap + per-detector contribution table).
- 4h: Write up Detection P/R table + Aegis/Wink/AgentDebug positioning paragraph.

**Day 3 (12h budget):**
- 4h: Finish remaining runs, freeze numbers.
- 6h: Write results section, regenerate all figures, update abstract + intro to lead with τ-bench pass^k result.
- 2h: Cold-reviewer sub-agent pass + final compilation.

**Risk register:**
- **Highest risk:** τ-bench retail has fewer than expected loop-class failures on Claude Opus 4.7 → null result. Mitigation: pre-screen the first 20 baseline runs for loop incidence; if detector fires <15% of the time, switch primary to airline (harder) or fall back to AgentErrorBench detection-only paper.
- **Medium risk:** Rate-limit throttling on either provider extends run time. Mitigation: use multiple API keys + start runs Day 1.
- **Low risk:** AgentErrorBench corpus not actually released. Mitigation: check first thing Day 1; if unavailable, use MAST trace corpus (Cemri et al., arXiv:2503.13657) as substitute (~1600 traces).

**What the highest-quality publishable experiment finishable in 3 days looks like:**

> A paired-trial closed-loop intervention experiment on τ-bench retail (n=115 tasks, 4 trials each, 2 frontier providers — Claude Opus 4.7 and GPT-5.5), measuring pass^4 reliability under baseline vs. AgentTelemetry-driven intervention conditions. Ground truth via DB-state diff. Primary statistical test: McNemar on per-task pass^4. Secondary: detection precision/recall of all 14 detectors against AgentDebug's released AgentErrorBench corpus, head-to-head vs. their 5-class taxonomy. Tertiary: real-LLM overhead microbenchmark from existing 159-run corpus.
>
> Position as: "first open-source, reproducible counterpart to Meta's Wink (arXiv:2602.17037), evaluated on public benchmarks rather than internal traffic, with broader detector taxonomy than AgentDebug (arXiv:2509.25370) and complementary intervention surface to Aegis (arXiv:2508.19504, agent-side vs environment-side)."

This is publishable at NeurIPS Datasets & Benchmarks track or the Workshop on Foundation-Model Agents track (more realistic given the timeline). For the main NeurIPS track, the same experimental shell would need to expand to AppWorld and DABStep for an additional 2-3 weeks of work.

---

## Sources

- MAST: Cemri et al., "Why do Multi-Agent LLM Systems Fail?", arXiv:2503.13657 — 1600+ traces, 14 failure modes, 3 categories
- Aegis: Song, Pekhimenko et al., arXiv:2508.19504 — 142 traces, 6 failure modes, +6.7-12.5pp on 5 benchmarks
- AgentDebug: Yang et al., "Where LLM Agents Fail and How They Can Learn From Failures", arXiv:2509.25370 — AgentErrorBench, +24pp accuracy
- Wink: Nanda, Maddila, Khan, Paltenghi, Chandra (Meta), "Recovering from Misbehaviors in Coding Agents", arXiv:2602.17037 — 10,554 A/B trajectories, 30% misbehavior rate, 90% single-intervention resolution
- DoVer: arXiv:2512.06749 — 18-28% failed-trial recovery on GAIA/AssistantBench
- VIGIL: arXiv:2512.07094 — reflective runtime
- SCOPE: arXiv:2512.15374 — 14.23% → 38.64% on HLE
- ReIn: arXiv:2602.17022 (ICLR 2026) — test-time reasoning intervention
- AgentTrace: arXiv:2602.10133 (AAAI 2026 LaMAS Workshop) — structured logging framework
- τ-bench: Yao et al., arXiv:2406.12045 — 165 tasks, pass^k metric, GPT-4o pass^1<50%, pass^8<25%
- τ²-bench: Barres et al., arXiv:2506.07982 — adds telecom + banking
- GAIA: Mialon et al., arXiv:2311.12983 — 466 questions, 3 difficulty levels
- AppWorld: Trivedi et al., arXiv:2407.18901 — 750 tasks, GPT-4o ~30% on Challenge
- WebArena: Zhou et al., arXiv:2307.13854 — 812 tasks, GPT-4 14.41%
- AgentBench: Liu et al., arXiv:2308.03688
- AgentBoard: Ma et al., arXiv:2401.13178 (NeurIPS 2024 oral) — 9 tasks, 1013 environments
- ScienceAgentBench: arXiv:2410.05080 — 102 tasks, o1-preview 42.2%
- DABStep: HuggingFace + Adyen blog — 450+ tasks, best 16% (o3-mini)
- Multi-SWE-bench: arXiv:2504.02605 — 1632 instances, 7 languages
- BrowseComp: arXiv:2504.12516 (OpenAI) — 1266 questions
- ALFWorld: alfworld.github.io — 3553 training tasks
- WebShop: 12,087 instructions, best agent 29% vs 59% human expert
- ToolLLM/ToolBench: arXiv:2307.16789 — 16,464 APIs across 49 categories
- Reflexion: Shinn et al., arXiv:2303.11366 — 91% HumanEval (+11pp)
- Self-Refine: Madaan et al., arXiv:2303.17651 — +20% across 7 tasks
- Voyager: Wang et al., arXiv:2305.16291 — 3.3× SOTA on Minecraft
- AgentOps: Dong, Lu, Zhu, arXiv:2411.05285 — taxonomy paper, no empirical eval
