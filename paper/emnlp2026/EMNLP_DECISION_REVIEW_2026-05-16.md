# Cold-Reviewer Verification of EMNLP_DECISION_2026-05-16.md

**Reviewer:** Skeptical sub-agent, 2026-05-16
**Memo under review:** `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/emnlp2026/EMNLP_DECISION_2026-05-16.md`
**Verdict:** **REVISE** — Option C's central premise (the 13-LLM corpus and topology data are non-overlapping with other in-flight work) is materially wrong. The recommendation may still be salvageable, but only with substantial reframing; the memo as written does not surface the largest hidden risk.

---

## Verification task 1 — "Verified facts" table

Every row in the memo's table was checked against ground truth.

| Memo claim | Ground truth | Pass? |
|---|---|---|
| EMNLP Industry deadline / submission portal / 6-page review, 7-page CR / arXiv allowed, double-blind | Confirmed from `https://2026.emnlp.org/calls/industry_track/` via WebFetch: deadline June 16, 2026 (11:59 PM UTC-12); OpenReview; 6 pages review / 7 pages camera-ready; no anonymity period (arXiv allowed); double-blind on submission. | PASS |
| EMNLP draft .tex last modified May 12, 2026 20:25 | `stat` confirms `emnlp_paper.tex` mtime: May 12 20:25. | PASS |
| Compiled PDF size 193,452 bytes / 7 pages | `wc -c` = 193,452. `mdls` reports `kMDItemNumberOfPages = 7`. | PASS |
| Draft abstract: "both arms produce patches at ~92% (p=1.000)" / "did not replicate" | Verified at `emnlp_paper.tex:49-52`: "the prior $+12.5$pp closed-loop intervention effect did \\emph{not replicate} at the larger sample on a frontier model: both arms produce patches at $\\sim$92\\%" and "$p{=}1.000$" appears at line 313. | PASS (quote is accurate; see Task 2 for whether the framing is "wrong") |
| Draft attributes the null to "frontier-model ceiling effect" | Verified at `emnlp_paper.tex:52-53` and again at line 624. | PASS |
| AIware citation language (third-person "Building on the AgentTelemetry taxonomy…") | This exact phrase does **not** appear verbatim in `emnlp_paper.tex`. The draft instead cites `\\citep{aiware2026}` at line 289 ("Prior work~\\citep{aiware2026} reported a closed-loop telemetry-guided…"). The intent (third-person AIware reference) is correctly described, but the quoted string in the memo is paraphrased, not verbatim. | PARTIAL — non-material, but the table column says "verified by grep on the .tex" which overstates what was checked. |

**Table verdict: 7/8 rows fully PASS, 1 row is a paraphrase mislabeled as a verbatim quote.** Not material to the decision; flag for cleanup.

---

## Verification task 2 — Is the May 12 framing actually wrong, or is the memo overstating?

**Verdict: the memo is correct that the framing is misleading, but slightly overstates how flatly "wrong" the draft's claim is.**

What the draft actually says (verified at `emnlp_paper.tex:289-346`):

- The replication finding ("+12.5pp did not replicate at n=60 on Opus") is mathematically consistent with the v1-opus row in `data_inventory.json` (control 0.85 / intervention 0.883, p=0.7891, delta=+3.33pp). The draft's headline number ("~92%") is a rounding of the v1 88.3% intervention rate — slightly generous but defensible.
- The "frontier-model ceiling effect" interpretation is presented as one of *two* candidate explanations at line 335 ("**Why the effect did not replicate.** Two interpretations are…"). It is not stated as the sole conclusion. The memo's TL;DR ("Its current headline framing 'ceiling effect on Opus' is **factually inconsistent with the data we now have**") is **directionally correct but rhetorically stronger than the draft itself**.

What the v2 data (now available) actually shows (verified directly in `data_inventory.json`):

- **v2-opus** (forced harness): control 88.3% / intervention 90.0%, avg_searches 3.23/3.42, avg_iterations 4.03/4.03, `intervention_triggers=0.0`, `max_query_repeats_observed=1`. The model **does** engage the search protocol (3+ searches per run on average); it just never repeats a query, so the trigger condition `max_query_repeats > 1` never fires. The memo's reading is correct: this is **not** a ceiling effect, it is a **trigger-condition-never-fires effect**.
- Across **all 8 cells** (v1×4 + v2×4, n=60 each = 960 instance-runs), `avg_intervention_triggers = 0.0` everywhere. The null is structural, not tier-specific. The memo correctly identifies this.
- **v2-sonnet** collapses to 3.3%/3.3% and **v2-haiku** to 13.3%/11.7%. The memo correctly identifies these as forced-protocol resistance, not a ceiling.

**Bottom line: the memo's substantive critique is right.** The EMNLP draft (a) presents the ceiling-effect interpretation as the more parsimonious of two alternatives without having the v2 data that decisively rules it out, and (b) attributes the null to a tier-specific phenomenon when the v2 data shows it is universal. Submitting the May 12 draft as-is would mean publishing an interpretation the author already knows is wrong. The memo's claim of "factual inconsistency" is slightly stronger than "the most parsimonious interpretation is now refuted," but the practical implication (do not submit the May 12 draft unchanged) is correct.

---

## Verification task 3 — Option C data availability

**Verdict: data exists on disk, but with TWO caveats the memo does not flag.**

### Multi-agent topology data
- `results/multi_agent_topology_cli/summary.txt` confirms **45 runs across 3 topologies × 3 models × 5 questions**, all 9 cells complete (`n=5, done=5` for each).
- 570 spans across 8 kinds (AGENT, LLM_CALL, DELEGATION, PLANNING, GUARD_RAIL, REASONING, MEMORY, RETRIEVAL).
- mtime May 12 (summary.json) — consistent with memo.
- **Anomaly:** `summary.txt` reports `AnomalyDetector unavailable: ModuleNotFoundError: No module named 'agenttelemetry.analysis.anomaly'`. The detector that the EMNLP paper would presumably analyze never ran. The memo's caveat ("may need additional analysis") is correct but undersells: the analysis pipeline currently errors out.

### 13-LLM real-API research-assistant corpus
- `results/real_llm/` exists with: `phase1_results.json` (122 KB), `phase2_results.json` (96 KB), `phase3_results.json` (67 KB), `phase4_results.json` (3 KB), `checkpoint.json`, `tables/`, and 122 trace files under `traces/`.
- `checkpoint.json` confirms **13 models**, **600 completed runs** across 4 phases (phase1: 260, phase2: 195, phase3: 130, phase4: 15). NeurIPS cites a "159-run" subset; the 600-run figure here matches the full corpus.
- All 13 models match the memo's claim (claude-3-5-sonnet, claude-haiku-4-5, claude-opus-4-5/4-6, claude-sonnet-4-5/4-6, gpt-4.1/4.1-mini/4.1-nano, gpt-4o/4o-mini, o3-mini, o4-mini).
- **Caveat the memo missed: data mtime is March 24, 2026, not May 11/12.** The memo's own Citable Sources line says "13-LLM real-API corpus (UNVERIFIED in this memo)" — this is now verified, but the dating in the memo body ("May 11/12 experiment, 159 runs") is wrong. The corpus was generated March 24 and has been the basis for AIware and NeurIPS papers since.

**Bottom line: data is on disk, complete, and analyzable. But: (a) the anomaly detector module is broken, and (b) the data is older than the memo claims, which matters for Task 5.**

---

## Verification task 4 — Overlap-policy characterization

**Verdict: memo's "25% threshold" number is correct; the memo's framing of consequences is slightly off.**

Verified at `https://2026.emnlp.org/calls/industry_track/` via WebFetch:

- > "Authors submitting more than one paper to EMNLP 2026 must ensure that their submissions do not overlap significantly (>25%) with each other."
- For concurrent submissions by the same / nearly identical author groups covering overlapping topics, the CFP requires: **mutual citations**, **discussion of each work in the main body**, and **anonymized PDFs of cited concurrent submissions as supplementary materials**. Non-compliance risks rejection of all non-compliant submissions.

Important nuance the memo does not surface: the >25% rule is explicitly for two papers **at EMNLP**, not between an EMNLP paper and a concurrent non-EMNLP paper. EMNLP cannot directly enforce 25% against an IEEE Software submission. The real risk for Option B is reviewer perception (reviewers will see the IEEE Software preprint on arXiv since EMNLP allows it, and may dock the EMNLP paper for low novelty) rather than a mechanical desk-reject. The memo's qualitative conclusion ("high overlap risk, avoid Option B") survives, but the specific causal mechanism it cites ("EMNLP Industry's policy forbids >25%") is mis-stated as a cross-venue rule when it is an intra-venue rule.

---

## Verification task 5 — Stress-test the recommendation

**Verdict: Option C as recommended has a substantial hidden risk the memo missed. The recommendation should be REVISED.**

### Hidden risk #1 — Option C's "non-overlapping data" claim is **false against the other in-flight papers**.

The memo argues Option C is low-risk because the 13-LLM corpus and multi-agent topology data are NOT in the IEEE Software paper. Verified — that specific claim is true (IEEE Software is SWE-bench only, see `ieee_software_paper.tex:201` "Single-benchmark scope. We tested SWE-bench Lite only"). But the memo does not check the four OTHER concurrent venues, and they DO use this data:

- **AIware 2026 (ACCEPTED, not just submitted):** `aiware2026/aiware_paper.tex:417` introduces "The standardized benchmark task is a research assistant agent…" and lines 742-757 contain a "Per-model real-API overhead" table evaluated on the same real_llm corpus (5 tasks per model, multiple models). This is the **same data and same task** Option C proposes to feature.
- **NeurIPS 2026:** `neurips2026/neurips_2026.tex:1069-1071` says verbatim: "(3) the 159-run real-LLM validation corpus (13 models across Anthropic and OpenAI providers, span trees with full timing and cost metadata, organic-fault labels)." This is **exactly** the dataset Option C proposes to make EMNLP's centerpiece — and NeurIPS already publishes it.
- **ESEM 2026 (submitted, per memo):** `esem_paper.tex:684-687` references a "real-LLM sanity check" but does not appear to feature the full corpus.
- **MDE 2026 (submitted, per memo):** `mde_paper.tex` does not appear to use the 13-LLM corpus (uses mocked LLMs on a coverage matrix instead).

**Implication:** Option C's promise of "two non-overlapping papers in flight simultaneously" holds against IEEE Software but **fails against AIware (accepted!) and NeurIPS (submitted!)**. Submitting an EMNLP paper whose centerpiece is the 13-LLM real-API research-assistant corpus would:
- Re-publish data that AIware 2026 already has the publication right to (potential self-plagiarism flag if AIware proceeds to publication first).
- Compete directly with NeurIPS 2026's claim to that corpus as a benchmark contribution.
- Create reviewer-visible duplication (preprints of AIware/NeurIPS are likely on arXiv or near it; reviewers will Google).

**This is the largest single risk in the memo and it is entirely unflagged.** The memo's risk analysis stopped at "IEEE Software vs EMNLP" and missed the four other venues already in flight.

### Hidden risk #2 — Multi-agent topology data is paper-thin.

The topology dataset is 45 runs total (5 per cell × 9 cells). The memo treats this as a credible standalone contribution. But: with n=5 per cell, no statistical comparison is meaningful, the anomaly detector module is broken (see Task 3), and the dataset has no held-out comparator. As a centerpiece for an EMNLP submission this would be visibly under-powered and would invite reviewer pushback. The memo does not surface this.

### Hidden risk #3 — Data is older than the memo claims.

The memo's body refers to "the 13-LLM real-API research-assistant corpus (May 11/12 experiment, 159 runs across Anthropic + OpenAI models on a non-SWE-bench task)." Ground truth from `stat`: the corpus was generated **March 24, 2026**, and the run count is **600** (with NeurIPS's 159 being a subset). If the EMNLP draft cites May 2026 as the data date, that is a misrepresentation. If reviewers cross-reference the AIware paper (same data, March origin), the EMNLP submission would look like a repackaging of months-old data.

### Hidden risk #4 — Lost opportunity cost.

Even if Option C succeeds, the 4-6 hours invested in writing competes with: (a) submitting IEEE Software (task #10, due July 7, after the EMNLP deadline so it's not actually in tension here), (b) cold-reviewer follow-ups on ESEM/MDE submissions if reviews come in, (c) writing ICSE 2027 SEIP (task #15, due Oct 23). The memo asserts "highest EV per hour invested" without comparing against these alternatives.

### Alternatives the memo did not consider

**Option D — Submit a focused EMNLP paper on the v2 forced-harness collapse on Sonnet/Haiku.** This finding (v2-Sonnet 3.3% / v2-Haiku 13.3% — see `data_inventory.json` lines 197-273) is genuinely novel, is NOT the centerpiece of any other in-flight paper, and matches EMNLP Industry's interest in deployment-relevance ("forced prompt engineering scaffolds can catastrophically degrade mid-tier and budget-tier model performance in production agent harnesses, with implications for prompt-template design"). Data is in the same `swebench_n60_v2_*` dirs that IEEE Software uses, but the *framing* (negative interaction effect between prompt scaffolds and tier) is orthogonal to IEEE Software's framing (interventions don't transfer). Overlap risk would need explicit handling but would be cleaner than Option C's collision with AIware/NeurIPS.

**Option E — Defer to EMNLP Industry 2027.** With one accepted (AIware) and three submitted papers already covering this work, the marginal value of one more in-flight venue is low relative to the cross-paper conflict risk. EB-1A Criterion 6 needs *accepted* publications, not in-flight ones; an EMNLP submission that gets rejected for redundancy adds nothing and consumes reviewer goodwill. Adding a 6th in-flight venue covering substantially the same research program is a portfolio-management red flag.

---

## Summary of recommended revisions

1. **Strike Option C's "no overlap with anything else" claim.** Replace with a frank assessment: the 13-LLM corpus overlaps with AIware (accepted) and NeurIPS (submitted), so this is not a free option.
2. **Add Option D (v2 forced-harness collapse on Sonnet/Haiku)** as an alternative narrowing that is genuinely non-overlapping with the other in-flight papers.
3. **Add Option E (defer / decline).** With AIware accepted and three other venues submitted, the marginal EB-1A value of adding a fifth in-flight slot — at substantial overlap risk — is low.
4. **Fix the data-date claim** ("May 11/12") to match ground truth (March 24, 2026).
5. **Fix the EMNLP overlap-policy framing**: the >25% rule is intra-EMNLP; cross-venue risk is reviewer perception via arXiv preprints, not a CFP-policy desk-reject.
6. **Fix the AIware quote** in the Verified Facts table (it is paraphrased, not verbatim).
7. **Run `agenttelemetry.analysis.anomaly` against the topology data** before committing to any option that features that dataset — the analysis pipeline currently errors out.

If after these revisions Option C still scores best, the memo should explicitly address how the EMNLP paper avoids self-plagiarism against AIware 2026's accepted "real API traces" overhead table.

**Verdict: REVISE.** The memo's diagnosis of the May 12 draft is sound; the recommendation is not.
