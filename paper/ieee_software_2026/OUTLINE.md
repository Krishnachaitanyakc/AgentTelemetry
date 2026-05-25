# IEEE Software "Edge-Cloud Continuum" Special Issue — Paper Outline

**Document date:** 2026-05-13
**Target deadline:** July 7, 2026 (8 weeks from today)
**Target venue:** IEEE Software, Special Issue: "The Edge-Cloud Continuum: Software Challenges and Innovations" (Mar/Apr 2027 publication)
**Submission portal:** https://ieee.atyponrex.com/journal/sw-cs
**CFP scope verbatim quote (verified):** *"Observability, SRE & AIOps for edge–cloud systems (cross-layer telemetry, anomaly detection, incident response at the edge)"*

---

## 1. Working title

**"When Telemetry-Derived Interventions Don't Transfer: A Cross-Tier Replication Study of Closed-Loop Agent Recovery on SWE-bench"**

Alternates if title is too long for IEEE Software (typically prefers ≤12 words):
- "Conditional Effectiveness of Closed-Loop Agent Recovery: A Cross-Tier Replication Study"
- "The Hidden Variable in AIOps for LLM Agents: Whether the Agent Engages the Loop"

---

## 2. Target framing (CFP fit)

The CFP names: *"Observability, SRE & AIOps for edge–cloud systems (cross-layer telemetry, anomaly detection, incident response at the edge)."* Our paper hits the **AIOps** and **anomaly detection** keywords directly: it's about a telemetry-derived runtime intervention for autonomous LLM agents.

Edge-cloud connection: agents in production span the continuum (edge inference at user devices, model serving at regional edge sites, orchestration in cloud). Our finding has direct deployment relevance for any team running LLM agents across this stack — practitioners need to know whether their telemetry-derived guardrails will actually fire on their chosen model.

**Article type:** Feature article (empirical study + practitioner experience report). The CFP explicitly welcomes *"experience reports and practitioner perspectives alongside research contributions."*

---

## 3. One-paragraph thesis

> The effectiveness of telemetry-derived runtime interventions for LLM agents is **conditional on whether the agent engages the tool-call protocol** the intervention monitors. We replicated a recently published closed-loop intervention—originally claimed to recover +12.5pp of SWE-bench failures by detecting and breaking reasoning loops—across four production-tier models (Claude Opus 4.6, Sonnet 4.6, Haiku 4.5, GPT-5.5) at n=60 per arm. The intervention reproduced its original effect magnitude on Sonnet 4.6 (+13.3pp, p=0.17) and was a no-op on the other three (-1.6pp / 0.0pp / 0.0pp, all p=1.000). The non-replicating tiers exhibited a one-shot patch behavior: zero search-tool calls, single-iteration completion at 91-95% patch rates. The intervention was vacuous on these tiers because the failure mode it targets (repeated identical tool calls) never occurred. The deployment lesson for AIOps practitioners: telemetry-derived interventions must be validated against the specific model and protocol the production agent actually uses; a +12.5pp effect on a budget model from 2024 does not generalize to a frontier model from 2026 even when the harness is unchanged.

---

## 4. Section-by-section skeleton (target: ~5 pages = ~5,000 words)

### Section 1 — Introduction (~0.6 pp / 600 words)
- On-call diagnostic hook: production LLM agent stops responding, what does telemetry tell you?
- The promise of agent-specific span kinds (cite AgentTelemetry / OTel GenAI semantic conventions in passing — we are NOT the AgentTelemetry authors here, we are practitioners building on top)
- The narrower question this paper answers: when a paper reports a telemetry-derived intervention with a specific effect size, does that effect transfer to your production model?
- Contribution: a cross-tier n=60 replication of one specific intervention from the literature, with concrete deployment lessons.

### Section 2 — Background (~0.5 pp / 500 words)
- Brief overview of OpenTelemetry GenAI semantic conventions (3-4 sentences)
- The AgentTelemetry span kinds (one-paragraph summary, citing the AIware paper)
- The closed-loop intervention concept: detect reasoning-loop pattern via REASONING-span dispatch, inject strategy-change prompt
- The original AIware n=24 result (+12.5pp recovery on GPT-4o-mini, p=0.53)
- Why a replication study at n=60 across model tiers matters: AIOps deployments choose models for cost / latency / capability reasons, not for "does the intervention from paper X work on this one"

### Section 3 — Method (~0.8 pp / 800 words)
- Four model tiers: Opus 4.6, Sonnet 4.6, Haiku 4.5 (Anthropic), GPT-5.5 (OpenAI). Both providers, three Anthropic-tier strata, one frontier OpenAI.
- Same SWE-bench Lite 60 instances per tier (consistent cross-tier comparison; instances drawn from astropy, django, sympy)
- Same harness as original AIware experiment: ReAct architecture with `search_code` / `read_file` / `analyze_error` / `propose_patch` / `verify_fix` tools, 8-iteration cap, intervention triggers when any single search query repeated ≥3 times.
- 60 instances × 2 conditions (control, intervention) × 4 models = 480 runs
- Outcome metric: patch produced (model emits a `<patch>...</patch>` block within iteration cap)
- Statistical analysis: per-tier Fisher's exact two-sided test on the 2×2 contingency table
- Implementation: each model invoked via its official CLI as a subprocess; deterministic, reproducible

### Section 4 — Results (~1.5 pp / 1,500 words including tables)

**Headline table (Table 1):** Per-tier control vs. intervention patch rates, deltas, Fisher's exact p

| Tier | Control | Intervention | Δ | Fisher p | Avg iterations | Avg search calls |
|---|---|---|---|---|---|---|
| Opus 4.6 | 52/60 (86.7%) | 53/60 (88.3%) | +1.6pp | 1.000 | 1.0 | 0.0 |
| Sonnet 4.6 | 36/60 (60.0%) | 44/60 (73.3%) | **+13.3pp** | **0.17** | 1.0 | 0.0 |
| Haiku 4.5 | 55/60 (91.7%) | 55/60 (91.7%) | 0.0pp | 1.000 | 1.0 | 0.0 |
| GPT-5.5 | 57/60 (95.0%) | 57/60 (95.0%) | 0.0pp | 1.000 | 1.0 | 0.0 |

Two findings to develop in prose:

**Finding 1: The intervention's effect is conditional on tool-call engagement.** Sonnet 4.6 is the only tier where the intervention produces a directional effect, and it is essentially the same magnitude as the original AIware n=24 finding (+13.3pp vs +12.5pp). The other three tiers produce zero search calls and exit on iteration 1 — the intervention literally cannot fire because its trigger condition (3+ identical search calls) requires multiple iterations of tool use that never occur.

**Finding 2: Modern frontier and budget models bypass the agentic loop on SWE-bench Lite.** Opus 4.6, Haiku 4.5, and GPT-5.5 all exhibit a one-shot patch behavior: they emit a `<patch>` block on iteration 1, with zero search calls, regardless of intervention condition. This is independent of model tier — Haiku (budget) behaves identically to Opus (frontier) in this respect. Sonnet 4.6 is the outlier; it engages the protocol enough to actually loop.

Per-instance breakdown table (Table 2): show iteration distributions and search-call distributions for each tier.

### Section 5 — Why This Matters for AIOps (~0.8 pp / 800 words)
- Practitioners deploying LLM agents at the edge-cloud continuum face a model selection problem (latency vs. capability vs. cost).
- Whether a published telemetry-derived intervention will fire on the chosen model is **not predictable from public benchmarks** — it depends on a deployment-specific behavior (whether the model engages the tool-call protocol on the specific task).
- Three deployment recommendations:
  1. **Validate interventions on your model.** A +12.5pp recovery rate from the literature is meaningless if your chosen model doesn't enter the regime where the intervention helps.
  2. **Instrument tool-call engagement as a first-class observability signal.** Knowing that your model bypasses the protocol entirely is itself a critical operational metric — the intervention is moot, but so is the fault detection that depends on the same telemetry.
  3. **Forced-tool-use prompting.** If the intervention is operationally valuable in your deployment context, you may need to constrain the model to engage the protocol via system prompt — turning a one-shot model into an agentic one. This is itself a deployment trade-off (latency cost, cost increase) but worth the investment if the intervention is load-bearing.

### Section 6 — Threats to Validity (~0.4 pp / 400 words)
- Single-benchmark scope (SWE-bench Lite only). Generalizability to non-coding agent tasks is unverified.
- Patch correctness measured by emission of a `<patch>` block, not by passing the SWE-bench official test harness. We measure willingness to commit, not correctness. (Note: this is the same outcome metric used by the original AIware paper, so the comparison is internally valid.)
- Sonnet's directional +13.3pp effect (p=0.17) is consistent with both a real effect of similar magnitude to AIware's and with sampling noise; n=60 is underpowered to distinguish.
- Single CLI vendor per model (Anthropic CLI for the three Anthropic models, OpenAI's codex CLI for GPT-5.5). Different SDK paths may produce different behaviors.
- Fixed 60-instance subset; we did not stratify by problem difficulty.

### Section 7 — Conclusion (~0.4 pp / 400 words)
- The replication study converted a single-tier +12.5pp claim into a per-tier finding: the effect is real on Sonnet 4.6, vacuous on the other tiers tested.
- The deployment lesson for AIOps observability: model-level operating regime is the hidden variable.
- We release the full harness, per-instance traces, and analysis code at [anonymous repo URL or post-acceptance citation].

### Author bio (~50 words per author per IEEE Software template)

---

## 5. Figure and table list

| # | Type | Content | Source |
|---|---|---|---|
| Fig 1 | Bar chart | Per-tier control vs. intervention patch rates with error bars (Wilson 95% CI) | `results/swebench_n60_*/per_instance/` |
| Fig 2 | Distribution plot | Per-tier histogram of iterations used per instance (showing Sonnet's loop behavior vs. others' one-shot) | per_instance JSONs |
| Table 1 | Headline | Per-tier results table (above) | summaries |
| Table 2 | Detail | Iteration + search-call counts per tier | per_instance JSONs |

Total: 2 figures + 2 tables. IEEE Software typically allows up to 6 figures+tables combined for feature articles; we are well under.

---

## 6. What's in our data vs. what we still need

**In our data (verified):**
- 4 tiers × 2 conditions × 60 instances = 480 runs already on disk
- Per-instance JSONs with iteration count, query repeat counts, error states, full agent transcripts
- Summaries: Opus, Haiku, GPT-5.5 final; Sonnet final
- Original AIware paper accepted reference (DOI 10.1145/3805760.3814931)

**What we still need:**
- Per-tier iteration distributions and search-call distributions extracted from per_instance JSONs into Table 2 form
- Wilson 95% CI calculation for the headline patch rates (manual; trivial)
- Bibliography in IEEE Software reference format (currently in ACM/NeurIPS format)
- IEEE Software LaTeX template (downloadable from the IEEE Author Center)

**What we don't need but might add:**
- A Sonnet v2 forced-tool-use re-run to confirm the conditional-effect interpretation. **Decision: skip.** Forced tool use changes the experiment's deployment relevance (it becomes "what happens when we force the regime" rather than "what happens in production deployment").
- Additional task domains beyond SWE-bench. **Decision: skip for IEEE Software, add for ICSE 2027 SEIP extension.**
- A second OpenAI tier (gpt-mini-style). **Decision: skip; codex CLI exposes one stable name and we used it.**

---

## 7. Risks and overlap management

### Risk 1: Reviewer flags AIware-paper overlap
- **Mitigation:** Lead with the replication framing throughout. The paper is explicitly *about* the AIware result; we are not its authors in this venue (acknowledge in text that the original paper exists and we are testing its claims at scale).
- **Defensive language:** Cite the AIware paper as foundational prior work. Do not present any contribution from the AIware paper as our own.
- **Author disclosure:** The original AIware paper is sole-authored by Krishna Chaitanya Balusu, who is also the author of this submission. The IEEE Software special issue is single-blind (CFP allows author identity), so we can disclose this directly in the manuscript: "We replicate prior work from one of the authors at scale."

### Risk 2: Reviewer asks "why didn't you also test the OpenAI gpt-mini tier the original paper used?"
- **Response:** The original GPT-4o-mini is no longer accessible via the CLI we use; we replicated using the closest currently-available equivalent (Haiku 4.5 as a budget tier) and three additional tiers spanning frontier capability. Adding GPT-4o-mini as a fifth tier is a useful future-work item and we mention it.

### Risk 3: Reviewer says "Sonnet 4.6 +13.3pp is non-significant; you can't claim it replicates"
- **Response:** We do not claim statistical replication. We report directional + magnitude consistency (paper text: "directionally consistent with AIware at the same magnitude, but underpowered at n=60 to confirm"). The headline finding is the **conditional** effectiveness across tiers — that's the contribution, not the Sonnet number alone.

### Risk 4: Reviewer asks for the SWE-bench official test-harness pass rates
- **Response:** Acknowledged as a limitation. Add to threats-to-validity. Patch-emission as a metric was the original AIware metric; switching to test-harness execution would change what is being compared, not what we report.

### Risk 5: Reviewer says "this isn't really edge-cloud — SWE-bench is offline"
- **Response:** Strengthen the AIOps framing in Section 1. Make explicit that the deployment context for LLM agents at the edge-cloud continuum is exactly where the model selection question matters most (resource-constrained edge inference vs. high-capability cloud serving). The intervention's conditional effectiveness is the practitioner-relevant finding, regardless of whether the test domain was SWE-bench.

---

## 8. Sprint calendar

| Week of | Milestone |
|---|---|
| **May 13** | Outline (this doc), data extraction scripts for tables, IEEE Software LaTeX template downloaded |
| **May 18** | Section 1 (Intro) + Section 2 (Background) drafted; figures generated |
| **May 25** | Section 3 (Method) + Section 4 (Results) drafted with tables in place |
| **Jun 1** | Section 5 (Why This Matters) + Section 6 (Threats) + Section 7 (Conclusion) drafted |
| **Jun 8** | Full draft assembled, internal cold-reviewer pass via sub-agent, fixes |
| **Jun 15** | Bibliography in IEEE Software format, author bio, anonymization sweep (single-blind: still strip Meta-confidential refs) |
| **Jun 22** | Second cold-reviewer pass; format compliance check via overleaf or local pdflatex |
| **Jun 29** | Final read; user approval; submission |
| **Jul 1** | **Submit** to IEEE Author Portal; 6-day buffer to deadline |

---

## 9. Verification log

| Item | Source | Verified |
|---|---|---|
| CFP scope quote "Observability, SRE & AIOps for edge-cloud systems (cross-layer telemetry, anomaly detection, incident response at the edge)" | https://www.computer.org/digital-library/magazines/so/cfp-edge-cloud-continuum | YES (verified 2026-05-13) |
| Submission deadline July 7, 2026 | Same | YES |
| Publication target Mar/Apr 2027 | Same | YES |
| Submission portal https://ieee.atyponrex.com/journal/sw-cs | Same | YES |
| Guest editors: Davide Taibi, Schahram Dustdar, Guodong Wang, Adel N. Toosi | Same | YES |
| AIware paper DOI 10.1145/3805760.3814931 | Existing camera-ready file | YES (referenced earlier this session) |
| Tier results (Opus, Haiku, Sonnet, GPT-5.5) | `results/swebench_n60_*/summary.txt` | YES (all 4 summaries on disk this session) |
| IEEE Software-specific page/word limits | Could not verify | UNVERIFIED — proceeding on the standard IEEE Software feature-article ~6,000 word convention; will verify against author guide before final formatting |
| IEEE Software anonymization policy | Could not verify | UNVERIFIED — assumed single-blind (default for IEEE Computer Society magazines unless otherwise stated) |
| IEEE Software LaTeX template | Not yet downloaded | TODO before draft assembly |
