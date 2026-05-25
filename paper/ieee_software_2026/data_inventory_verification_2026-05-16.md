# Data Inventory Verification Report — 2026-05-16

**Verdict: PASS**

All 8 runs in `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/data_inventory.json` were independently recomputed from the raw `per_instance/*.json` files and every reported metric matches to the precision recorded in the inventory.

- File count per run: 120 / 120 (60 control + 60 intervention) for all 8 runs
- Patch counts: match on all 16 (run, condition) cells
- `avg_iterations`, `avg_searches`, `avg_patch_suppressions`, `avg_intervention_triggers`: match on all 16 cells (to 2 decimal places)
- `max_query_repeats_observed`: match on all 16 cells
- `timeouts` / `errors`: match on all 16 cells
- `fisher_exact_p_two_sided`: match on all 8 runs (to 4 decimal places)

Method: independent Python script (`/tmp/verify_inventory.py`) that ignores the inventory file and recomputes every field by walking each run's `per_instance/` directory. Fisher's exact two-sided p-value computed with `scipy.stats.fisher_exact` on the 2x2 contingency table `[[patches_ctrl, n_ctrl-patches_ctrl], [patches_int, n_int-patches_int]]`. For v1 runs, `total_searches` derived from `sum(tool_pattern.values())` and `max_query_repeats` derived from `max(tool_pattern.values())` per the inventory's documented v1 semantics. For v2 runs, `total_searches` and `max_query_repeats` read directly from those fields.

---

## Per-Run Verification Tables

Format: `field — inventory | recomputed — match`. Floats rounded to 2 dp (4 dp for Fisher p).

### v1-opus — `results/swebench_n60_opus`

Files on disk: **120** | expected 120 — OK

| Field | Cond | Inventory | Recomputed | Match |
|---|---|---|---|---|
| n | control | 60 | 60 | OK |
| patches | control | 51 | 51 | OK |
| avg_iterations | control | 1.03 | 1.03 | OK |
| avg_searches | control | 0.00 | 0.00 | OK |
| avg_patch_suppressions | control | 0.00 | 0.00 | OK |
| avg_intervention_triggers | control | 0.00 | 0.00 | OK |
| max_query_repeats_observed | control | 0 | 0 | OK |
| timeouts | control | 9 | 9 | OK |
| errors | control | 9 | 9 | OK |
| n | intervention | 60 | 60 | OK |
| patches | intervention | 53 | 53 | OK |
| avg_iterations | intervention | 1.03 | 1.03 | OK |
| avg_searches | intervention | 0.00 | 0.00 | OK |
| avg_patch_suppressions | intervention | 0.00 | 0.00 | OK |
| avg_intervention_triggers | intervention | 0.00 | 0.00 | OK |
| max_query_repeats_observed | intervention | 0 | 0 | OK |
| timeouts | intervention | 7 | 7 | OK |
| errors | intervention | 7 | 7 | OK |
| fisher_p_two_sided | — | 0.7891 | 0.7891 | OK |

### v1-sonnet — `results/swebench_n60_sonnet`

Files on disk: **120** | expected 120 — OK

| Field | Cond | Inventory | Recomputed | Match |
|---|---|---|---|---|
| n | control | 60 | 60 | OK |
| patches | control | 36 | 36 | OK |
| avg_iterations | control | 1.00 | 1.00 | OK |
| avg_searches | control | 0.00 | 0.00 | OK |
| avg_patch_suppressions | control | 0.00 | 0.00 | OK |
| avg_intervention_triggers | control | 0.00 | 0.00 | OK |
| max_query_repeats_observed | control | 0 | 0 | OK |
| timeouts | control | 24 | 24 | OK |
| errors | control | 24 | 24 | OK |
| n | intervention | 60 | 60 | OK |
| patches | intervention | 44 | 44 | OK |
| avg_iterations | intervention | 1.02 | 1.02 | OK |
| avg_searches | intervention | 0.00 | 0.00 | OK |
| avg_patch_suppressions | intervention | 0.00 | 0.00 | OK |
| avg_intervention_triggers | intervention | 0.00 | 0.00 | OK |
| max_query_repeats_observed | intervention | 0 | 0 | OK |
| timeouts | intervention | 16 | 16 | OK |
| errors | intervention | 16 | 16 | OK |
| fisher_p_two_sided | — | 0.1749 | 0.1749 | OK |

### v1-haiku — `results/swebench_n60_haiku`

Files on disk: **120** | expected 120 — OK

| Field | Cond | Inventory | Recomputed | Match |
|---|---|---|---|---|
| n | control | 60 | 60 | OK |
| patches | control | 55 | 55 | OK |
| avg_iterations | control | 1.02 | 1.02 | OK |
| avg_searches | control | 0.00 | 0.00 | OK |
| avg_patch_suppressions | control | 0.00 | 0.00 | OK |
| avg_intervention_triggers | control | 0.00 | 0.00 | OK |
| max_query_repeats_observed | control | 0 | 0 | OK |
| timeouts | control | 5 | 5 | OK |
| errors | control | 5 | 5 | OK |
| n | intervention | 60 | 60 | OK |
| patches | intervention | 55 | 55 | OK |
| avg_iterations | intervention | 1.00 | 1.00 | OK |
| avg_searches | intervention | 0.00 | 0.00 | OK |
| avg_patch_suppressions | intervention | 0.00 | 0.00 | OK |
| avg_intervention_triggers | intervention | 0.00 | 0.00 | OK |
| max_query_repeats_observed | intervention | 0 | 0 | OK |
| timeouts | intervention | 5 | 5 | OK |
| errors | intervention | 5 | 5 | OK |
| fisher_p_two_sided | — | 1.0000 | 1.0000 | OK |

### v1-gpt55 — `results/swebench_n60_gpt55`

Files on disk: **120** | expected 120 — OK

| Field | Cond | Inventory | Recomputed | Match |
|---|---|---|---|---|
| n | control | 60 | 60 | OK |
| patches | control | 57 | 57 | OK |
| avg_iterations | control | 1.00 | 1.00 | OK |
| avg_searches | control | 0.00 | 0.00 | OK |
| avg_patch_suppressions | control | 0.00 | 0.00 | OK |
| avg_intervention_triggers | control | 0.00 | 0.00 | OK |
| max_query_repeats_observed | control | 0 | 0 | OK |
| timeouts | control | 3 | 3 | OK |
| errors | control | 3 | 3 | OK |
| n | intervention | 60 | 60 | OK |
| patches | intervention | 57 | 57 | OK |
| avg_iterations | intervention | 1.00 | 1.00 | OK |
| avg_searches | intervention | 0.00 | 0.00 | OK |
| avg_patch_suppressions | intervention | 0.00 | 0.00 | OK |
| avg_intervention_triggers | intervention | 0.00 | 0.00 | OK |
| max_query_repeats_observed | intervention | 0 | 0 | OK |
| timeouts | intervention | 3 | 3 | OK |
| errors | intervention | 3 | 3 | OK |
| fisher_p_two_sided | — | 1.0000 | 1.0000 | OK |

### v2-opus — `results/swebench_n60_v2_opus`

Files on disk: **120** | expected 120 — OK

| Field | Cond | Inventory | Recomputed | Match |
|---|---|---|---|---|
| n | control | 60 | 60 | OK |
| patches | control | 53 | 53 | OK |
| avg_iterations | control | 4.03 | 4.03 | OK |
| avg_searches | control | 3.23 | 3.23 | OK |
| avg_patch_suppressions | control | 1.02 | 1.02 | OK |
| avg_intervention_triggers | control | 0.00 | 0.00 | OK |
| max_query_repeats_observed | control | 1 | 1 | OK |
| timeouts | control | 3 | 3 | OK |
| errors | control | 7 | 7 | OK |
| n | intervention | 60 | 60 | OK |
| patches | intervention | 54 | 54 | OK |
| avg_iterations | intervention | 4.03 | 4.03 | OK |
| avg_searches | intervention | 3.42 | 3.42 | OK |
| avg_patch_suppressions | intervention | 0.95 | 0.95 | OK |
| avg_intervention_triggers | intervention | 0.00 | 0.00 | OK |
| max_query_repeats_observed | intervention | 1 | 1 | OK |
| timeouts | intervention | 5 | 5 | OK |
| errors | intervention | 6 | 6 | OK |
| fisher_p_two_sided | — | 1.0000 | 1.0000 | OK |

### v2-sonnet — `results/swebench_n60_v2_sonnet`

Files on disk: **120** | expected 120 — OK

| Field | Cond | Inventory | Recomputed | Match |
|---|---|---|---|---|
| n | control | 60 | 60 | OK |
| patches | control | 2 | 2 | OK |
| avg_iterations | control | 5.30 | 5.30 | OK |
| avg_searches | control | 0.28 | 0.28 | OK |
| avg_patch_suppressions | control | 4.67 | 4.67 | OK |
| avg_intervention_triggers | control | 0.00 | 0.00 | OK |
| max_query_repeats_observed | control | 1 | 1 | OK |
| timeouts | control | 17 | 17 | OK |
| errors | control | 25 | 25 | OK |
| n | intervention | 60 | 60 | OK |
| patches | intervention | 2 | 2 | OK |
| avg_iterations | intervention | 5.70 | 5.70 | OK |
| avg_searches | intervention | 0.28 | 0.28 | OK |
| avg_patch_suppressions | intervention | 5.07 | 5.07 | OK |
| avg_intervention_triggers | intervention | 0.00 | 0.00 | OK |
| max_query_repeats_observed | intervention | 1 | 1 | OK |
| timeouts | intervention | 17 | 17 | OK |
| errors | intervention | 22 | 22 | OK |
| fisher_p_two_sided | — | 1.0000 | 1.0000 | OK |

### v2-haiku — `results/swebench_n60_v2_haiku`

Files on disk: **120** | expected 120 — OK

| Field | Cond | Inventory | Recomputed | Match |
|---|---|---|---|---|
| n | control | 60 | 60 | OK |
| patches | control | 8 | 8 | OK |
| avg_iterations | control | 6.45 | 6.45 | OK |
| avg_searches | control | 1.15 | 1.15 | OK |
| avg_patch_suppressions | control | 5.12 | 5.12 | OK |
| avg_intervention_triggers | control | 0.00 | 0.00 | OK |
| max_query_repeats_observed | control | 1 | 1 | OK |
| timeouts | control | 12 | 12 | OK |
| errors | control | 12 | 12 | OK |
| n | intervention | 60 | 60 | OK |
| patches | intervention | 7 | 7 | OK |
| avg_iterations | intervention | 7.10 | 7.10 | OK |
| avg_searches | intervention | 1.02 | 1.02 | OK |
| avg_patch_suppressions | intervention | 5.75 | 5.75 | OK |
| avg_intervention_triggers | intervention | 0.00 | 0.00 | OK |
| max_query_repeats_observed | intervention | 1 | 1 | OK |
| timeouts | intervention | 10 | 10 | OK |
| errors | intervention | 10 | 10 | OK |
| fisher_p_two_sided | — | 1.0000 | 1.0000 | OK |

### v2-gpt55 — `results/swebench_n60_v2_gpt55`

Files on disk: **120** | expected 120 — OK

| Field | Cond | Inventory | Recomputed | Match |
|---|---|---|---|---|
| n | control | 60 | 60 | OK |
| patches | control | 50 | 50 | OK |
| avg_iterations | control | 4.47 | 4.47 | OK |
| avg_searches | control | 2.62 | 2.62 | OK |
| avg_patch_suppressions | control | 0.85 | 0.85 | OK |
| avg_intervention_triggers | control | 0.00 | 0.00 | OK |
| max_query_repeats_observed | control | 1 | 1 | OK |
| timeouts | control | 10 | 10 | OK |
| errors | control | 10 | 10 | OK |
| n | intervention | 60 | 60 | OK |
| patches | intervention | 51 | 51 | OK |
| avg_iterations | intervention | 4.67 | 4.67 | OK |
| avg_searches | intervention | 2.77 | 2.77 | OK |
| avg_patch_suppressions | intervention | 0.92 | 0.92 | OK |
| avg_intervention_triggers | intervention | 0.00 | 0.00 | OK |
| max_query_repeats_observed | intervention | 1 | 1 | OK |
| timeouts | intervention | 8 | 8 | OK |
| errors | intervention | 8 | 8 | OK |
| fisher_p_two_sided | — | 1.0000 | 1.0000 | OK |

---

## Discrepancies

**None.** Every recomputed field matched the inventory at the inventory's reported precision (2 decimal places for averages, 4 decimal places for Fisher p, exact integer match for counts).

---

## Spot-Check JSONs (3)

Three per-instance JSONs were read in full to verify the per-instance schema and data types.

### 1. v1 spot-check: `results/swebench_n60_opus/per_instance/astropy__astropy-12907_control.json`

- Schema confirmed: `instance_id` (str), `repo` (str), `model` (str), `max_iterations` (int), `intervention_enabled` (bool), `iterations` (int), `proposed_patch` (bool), `answer_len` (int), `tool_pattern` (dict, empty in v1 for non-search runs), `error` (str or null), `history` (list of dicts).
- Confirms v1 schema: uses `tool_pattern` (dict mapping query strings to repeat counts) and `answer_len`. No `total_searches`, `max_query_repeats`, `patch_suppressions`, or `intervention_triggers` fields — consistent with the inventory's documented v1 semantics (avg_searches=0, avg_patch_suppressions=0 across all v1 runs).
- Specific instance: timeout after 480s, 1 iteration, no patch — contributes to v1-opus control timeouts/errors count.

### 2. v2 spot-check: `results/swebench_n60_v2_opus/per_instance/astropy__astropy-12907_control.json`

- Schema confirmed: `instance_id` (str), `repo` (str), `model` (str), `max_iterations` (int), `min_searches` (int), `min_repeats` (int), `intervention_enabled` (bool), `iterations` (int), `proposed_patch` (bool), `patch_len` (int), `total_searches` (int), `unique_queries` (int), `max_query_repeats` (int), `patch_suppressions` (int), `intervention_triggers` (int), `query_counts` (dict), `error` (str or null), `history` (list).
- Confirms v2 schema has dedicated counter fields (`total_searches`, `max_query_repeats`, `patch_suppressions`, `intervention_triggers`) — consistent with the inventory's v2 reading convention.
- Specific instance: 5 iterations, patch produced, 3 total searches, 3 unique queries, max repeat = 1, 1 patch suppression.

### 3. Unusual spot-check: `results/swebench_n60_v2_sonnet/per_instance/astropy__astropy-14182_intervention.json`

- Selected because v2-sonnet has only 2 patches out of 60 in each condition (extremely low patch rate) — wanted to verify what failure mode the bulk of cases exhibit.
- Schema-conformant v2 record: 7 iterations, `proposed_patch: false`, `patch_len: 0`, 0 total searches, **6 patch_suppressions**, 0 intervention_triggers. `error` is a Claude Code at Meta gateway exit message ("claude exit 1: Claude Code at Meta ... Using AI Gateway").
- Finding: v2-sonnet's near-zero patch rate appears driven by upstream gateway/exit errors after repeated patch-suppression iterations, not by silent agent failure. The high `patch_suppressions` (avg ~4.67 control / 5.07 intervention) means agents produced patches that were repeatedly suppressed by the v2 forced-harness validator, eventually hitting the exit error. This is consistent with the inventory's reported errors (25 control, 22 intervention).
- This is a notable pattern to flag in the paper but is not a data integrity issue — the inventory's numbers accurately reflect this state.

---

## Notes / Observations (not discrepancies)

- For v1 runs, `avg_searches` is 0 across all conditions because `tool_pattern` is empty in every v1 per_instance file inspected. The v1 harness does not record tool calls in this field for the runs in scope, so the inventory's zeros are faithful (and not a bug in the script).
- v2-sonnet's near-floor success rate (3.3% in both conditions) coincides with a 36% / 42% error rate driven by gateway exit errors after many patch-suppression cycles. This may warrant a footnote in the paper about gateway/throttling effects masking the intervention signal for that model.
- `avg_intervention_triggers` is 0.0 in every run, in every condition. Worth confirming with the experiment author that this is the intended state (i.e., the intervention pathway never fires in either condition for any v2 model), since otherwise the v2 control vs. intervention comparison reduces to a re-run with the same harness. The data integrity is correct as recorded; the experimental interpretation is the concern.
- All 8 runs contain exactly 120 files (60 per condition). No missing or extra files detected.

---

## Verification Script

`/tmp/verify_inventory.py` — standalone Python 3 script that reads the inventory, recomputes every metric from scratch, and prints a per-field diff. Exit code 0 = PASS, 1 = FAIL. The script ran to completion with PASS for all 8 runs (0 discrepancies).
