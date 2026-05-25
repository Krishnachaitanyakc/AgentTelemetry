# EMNLP 2026 Industry Track — Decision Memo (Revised v2)

**Date:** 2026-05-16 (revised after cold-reviewer audit)
**Author:** Krishna Chaitanya Balusu
**Decision deadline:** before June 16, 2026 (EMNLP submission deadline) — 31 days from today
**For:** KC

---

## TL;DR (revised)

The EMNLP 2026 Industry Track draft is frozen at May 12, 2026. Its current ceiling-effect interpretation is no longer the most parsimonious reading of the v2 data — submitting as-is means publishing an interpretation the author already knows is contradicted by subsequent experiments. The original v1 memo proposed Option C (narrow EMNLP to the 13-LLM real-API corpus + multi-agent topology). **The cold-reviewer audit found that Option C overlaps with AIware 2026 (already ACCEPTED) and NeurIPS 2026 (submitted) — Option C is no longer viable.** Two alternatives surfaced by the auditor are now leading: **Option D** (focus on the v2 forced-protocol Sonnet/Haiku collapse — novel, non-overlapping) or **Option E** (defer / decline). My revised recommendation: **Option E**.

---

## Verified facts about the EMNLP draft

| Fact | Source | Verified |
|---|---|---|
| EMNLP 2026 Industry Track deadline | https://2026.emnlp.org/calls/industry_track/ | YES (June 16, 2026 11:59 PM UTC-12) |
| Submission portal | Same | OpenReview |
| Format | ACL template, 6 pages review / 7 pages camera-ready | YES |
| Anonymization | Double-blind on submission; no anonymity period (arXiv allowed) | YES |
| EMNLP draft TeX last modified | May 12, 2026 20:25 | YES |
| Compiled PDF size | 193,452 bytes / 7 pages | YES |
| Draft headline finding (verbatim) | "the prior $+12.5$pp closed-loop intervention effect did \emph{not replicate} at the larger sample on a frontier model: both arms produce patches at $\sim$92\% ... $p{=}1.000$" | YES (emnlp_paper.tex line 49-52, 313) |
| Draft interpretation | "frontier-model ceiling effect — the failure mode the intervention targets is largely absent at the frontier tier" | YES (line 52-53, 624) |
| AIware citation form | Third-person `\citep{aiware2026}` at line 289: "Prior work~\citep{aiware2026} reported a closed-loop telemetry-guided..." | YES |
| EMNLP >25% overlap rule | Verified — it is INTRA-EMNLP (between two papers BOTH submitted to EMNLP), NOT cross-venue with IEEE Software | YES (corrected from v1 memo) |

## Why the May 12 framing is no longer the most parsimonious reading

The EMNLP draft was written before v2 forced-protocol data on all 4 tiers was available. The data we now have (in `paper/ieee_software_2026/data_inventory.json`, independently verified in `data_inventory_verification_2026-05-16.md`, 0 discrepancies) shows:

1. **"Ceiling effect on Opus" is one of two interpretations the draft offered (line 335 of EMNLP draft: "Two interpretations are consistent with the data, both deployment-relevant").** Now-available v2 data favors the second interpretation. v2-Opus shows the model DID engage the protocol cleanly (avg_searches 3.23/3.42, avg_iterations 4.03/4.03), patches at 88.3%/90.0%, and `max_query_repeats_observed=1` — so the trigger doesn't fire because the model varies queries every time, not because of any ceiling.

2. **The null is structural, not tier-specific.** Across all 8 runs × 2 conditions = 16 cells × 60 instances = 960 instance-runs, `avg_intervention_triggers=0.0` everywhere. The data we have now eliminates the tier-specific ceiling-effect explanation as the right reading.

3. **Sonnet/Haiku v2 forced-harness collapse is a NEW finding the EMNLP draft does not mention.** v2-Sonnet (3.3%/3.3%) and v2-Haiku (13.3%/11.7%) collapse because they resist the forced protocol — `patch_suppressions` averages 4.67-5.75 per run. This is novel and is NOT in the EMNLP draft.

## Four options

### Option A — Kill EMNLP entirely
- Withdraw the EMNLP plan; the IEEE Software paper carries the new findings.
- **Pros:** Zero risk of submitting stale framing. Zero overlap risk. Zero writing burden.
- **Cons:** Loses one in-flight venue. EB-1A Criterion 6 portfolio currently has AIware 2026 ACCEPTED + ESEM/MDE/ICML AgenticUQ submitted; EMNLP would be a 5th venue. But marginal value of #5 is low compared to risks.
- **Effort:** Zero.

### Option B — Pivot EMNLP to match IEEE Software fully
- Rewrite EMNLP to mirror the IEEE Software paper's 8-cell finding.
- **Pros:** EMNLP paper would be technically defensible.
- **Cons:** **High reviewer-perception overlap risk.** Both papers same-author, same data, same conclusion. EMNLP allows arXiv preprints, so IEEE Software's preprint would be visible to EMNLP reviewers. Risk of "low novelty" rejection. The CFP >25% overlap rule is INTRA-EMNLP only (corrected from v1 memo), so it doesn't directly desk-reject this, but reviewer perception is the real risk.
- **Effort:** ~10 hours.
- **Risk:** Substantial.

### Option C — Submit narrower EMNLP on 13-LLM real-API corpus + multi-agent topology
- **STRIKE — no longer viable.** Cold-reviewer audit confirmed:
  - The 13-LLM corpus (600 runs, dated March 24, 2026 — NOT May 11/12 as v1 memo claimed) is already the basis of the per-model real-API overhead table in AIware 2026 (ACCEPTED) at `aiware_paper.tex` lines 742-757.
  - The same corpus is also cited verbatim in NeurIPS 2026 (submitted): "(3) the 159-run real-LLM validation corpus (13 models across Anthropic and OpenAI providers, span trees with full timing and cost metadata, organic-fault labels)" at `neurips_2026.tex` lines 1069-1071.
  - Submitting this corpus as EMNLP's centerpiece would compete with both AIware (accepted) and NeurIPS (submitted) for the same data → self-plagiarism risk if AIware publishes first, novelty challenge from NeurIPS reviewers if both are in flight.
  - Multi-agent topology data is paper-thin: 45 runs total (5 per cell × 9 cells), no statistical power, anomaly detector module currently broken (`ModuleNotFoundError`).

### Option D — Focus EMNLP on v2 forced-protocol Sonnet/Haiku collapse (NEW, surfaced by auditor)
- Frame the EMNLP paper around the **v2-Sonnet 3.3% / v2-Haiku 11.7%-13.3% collapse**. This is genuinely novel and is NOT the centerpiece of IEEE Software (which emphasizes the cross-cell trigger-never-fires finding), NOT in AIware (which uses different harness), NOT in NeurIPS (different corpus).
- Headline claim: "Forced prompt-engineering scaffolds (search-first protocols) can catastrophically degrade mid-tier and budget-tier model performance in production agent harnesses, with implications for prompt-template design across the deployment tier."
- **Pros:** Genuinely novel finding. Cleanly orthogonal to IEEE Software's "interventions don't transfer" framing. Cleanly orthogonal to AIware/NeurIPS (different harness).
- **Cons:** Requires rewriting EMNLP draft from scratch (~6-10 hours). Need to verify there's enough substance for a 6-page paper just on this finding. Sample is still just 4 cells (v2-Sonnet ctrl + intv + v2-Haiku ctrl + intv) so the finding's statistical anchor is narrow. Same-author overlap with IEEE Software still exists at the corpus level (same swebench n60 v2 data) — needs explicit reviewer-visible disclosure.
- **Effort:** Medium-High (~6-10 hours).
- **Risk:** Medium — requires care on overlap framing with IEEE Software, but the finding is distinct enough to defend.

### Option E — Defer to EMNLP Industry 2027 (NEW, surfaced by auditor)
- Do not submit anything to EMNLP 2026 Industry. Withdraw the plan.
- **Pros:** Removes all cross-venue overlap risk. Saves 6-10 hours. AIware 2026 (ACCEPTED) + ESEM + MDE + ICML AgenticUQ + IEEE Software is already 5 venues in flight covering this research program — adding a 6th is portfolio-management red flag. EB-1A Criterion 6 needs *accepted* publications, not in-flight ones; a rejected EMNLP submission helps nothing and consumes reviewer goodwill.
- **Cons:** Forgoes a peer-reviewed venue. But EMNLP Industry runs annually, so a 2027 cycle is available for a stronger, cleanly-non-overlapping paper.
- **Effort:** Zero (and avoids the multiple hours that Option D would consume).

## My revised recommendation: Option E (defer)

The cold-reviewer audit makes the strongest case for Option E: **adding a 6th in-flight venue at substantial overlap risk does not improve the EB-1A portfolio meaningfully.** The portfolio benefit per hour invested is best served by:

- Polishing the IEEE Software submission for the July 7 deadline (high single-venue ROI)
- Following up on ESEM/MDE/ICML decisions when they come (zero new effort)
- Writing the ICSE 2027 SEIP paper (October 23 deadline, single-blind so Meta affiliation visible, 10-page format) — this is the natural extended-data home for the same line of work and faces no overlap risk

If you strongly prefer to submit something to EMNLP, **Option D is the only honestly defensible content angle.** Option B and Option C are off the table after the audit.

## Action items

1. **You decide:** A, B, D, or E. (C is ruled out by the audit.)
2. **If E (RECOMMENDED):** Mark EMNLP task complete-deleted; remove from pipeline inventory. Estimated ~10 minutes of housekeeping.
3. **If D:** I write a narrowed draft over the next 6-10 hours, with explicit overlap-disclosure to IEEE Software.
4. **If A or B:** Per the audit, A is straightforward (~0 hours); B has high reviewer-perception risk and I would push back on it.

---

## Citable sources (audited)

- IEEE Software paper (this session): `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/ieee_software_paper.tex`
- IEEE Software data inventory: `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/data_inventory.json` (verified 2026-05-16, 0 discrepancies)
- IEEE Software cold reviewer reports (all three rounds): `cold_reviewer_report_2026-05-16.md`, `cold_reviewer_report_round2_2026-05-16.md`, `cold_reviewer_report_round3_2026-05-16.md`
- EMNLP draft (frozen May 12): `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/emnlp2026/emnlp_paper.tex`
- EMNLP cold-reviewer audit (this memo): `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/emnlp2026/EMNLP_DECISION_REVIEW_2026-05-16.md`
- EMNLP CFP: https://2026.emnlp.org/calls/industry_track/
- AIware paper (ACCEPTED): `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/aiware2026/aiware_paper.tex` (per-model overhead table at lines 742-757)
- NeurIPS paper (submitted): `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/neurips2026/neurips_2026.tex` (159-run corpus at lines 1069-1071)
- 13-LLM real-API corpus: `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/results/real_llm/` (600 runs, dated March 24, 2026)
- Multi-agent topology data: `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/results/multi_agent_topology_cli/` (45 runs, 9 cells; analysis module broken)
