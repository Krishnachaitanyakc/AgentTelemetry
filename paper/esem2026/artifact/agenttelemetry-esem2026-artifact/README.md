# Agent-Telemetry ESEM 2026 Replication Package

This is the anonymized artifact for double-anonymous review. It contains the DSM metamodel, executable adapter/fault-injection harness, trace corpus generator, detector predicates, per-run results, and scripts used to reproduce the paper's count/statistical claims.

## Quick Reproduction

```sh
python run_benchmarks.py --traces-output traces_full.jsonl --output results_full.tsv
python analysis.py results_full.tsv --traces traces_full.jsonl
```

Additional table-specific checks:

```sh
python compute_fpr.py results_full.tsv
python compute_roc.py
python generate_no_fault_suite.py --output no_fault_suite_traces.jsonl
python threshold_holdout.py --controls no_fault_suite_traces.jsonl --faults traces_full.jsonl --output threshold_holdout.tsv
python run_real_llm_sanity.py
```

Randomness is confined to the adapter-cluster and kappa bootstraps in
`analysis.py`; both use seed `20260506` (`mast_mapping_review.md` records the
same seed). The benchmark generator, detector scoring, threshold sweep,
held-out no-fault threshold check, and real-LLM cached sanity checks are
deterministic.

Optional live-LLM CLI smoke check, if three command-line front-ends
are locally authenticated and configured through environment variables.
Each command template is split as shell words; use the literal
`{prompt}` token where the generated task prompt should be passed, and
optionally `{output}` for tools that write their final answer to a file:

```sh
export AGENTTELEMETRY_CLI_A_CMD='frontier-cli-a --print {prompt}'
export AGENTTELEMETRY_CLI_B_CMD='frontier-cli-b --output {output} {prompt}'
export AGENTTELEMETRY_CLI_C_CMD='frontier-cli-c --prompt {prompt}'
python run_cli_agents.py --trials 1 --output real_llm_sanity.tsv
```

The generated `results_full.tsv` has 3,780 rows:

```text
7 adapters x 6 anonymized models x 6 telemetry conditions x 15 workload cases
```

## Files

| file | purpose |
|---|---|
| `agentmm.ecore` | Ecore DSM metamodel |
| `agentmm.ocl` | OCL well-formedness invariants |
| `coverage_matrix.md` | per-adapter DSM diagnostic coverage and scope rules |
| `source_survey_evidence.tsv` | pinned source-survey file/line evidence for included and excluded adapter/kind decisions |
| `live_sdk_validation.tsv` | live SDK spot-checks comparing emitted kinds with simulated profile kinds |
| `workload_design.md` | anonymized freeze-order record |
| `mast_mapping.md` | mapping from benchmark faults to MAST labels |
| `mast_mapping_review.md` | dual-coding agreement summary |
| `mast_mapping_review.tsv` | item-level annotator labels used for kappa |
| `run_benchmarks.py` | deterministic generator for `results_full.tsv` |
| `adapter_harness.py` | executable adapter profiles and fault injectors that emit raw spans |
| `generate_trace_corpus.py` | drives the adapter harness to create the JSONL trace corpus |
| `trace_schema.md` | trace-corpus schema |
| `trace_detectors.py` | executable detector predicates over traces |
| `score_traces.py` | recomputes `results_full.tsv` from traces |
| `traces_full.jsonl` | generated raw span traces |
| `Makefile` | `make reproduce` and `make smoke` entry points |
| `typed_predicates.py` | primary standardized-field predicate bank |
| `permissive_predicates.py` | compatibility wrapper pointing to executable permissive rules in `trace_detectors.py` |
| `extended_predicates.py` | compatibility wrapper pointing to executable extended-attribute rules in `trace_detectors.py` |
| `predicates_lines.tsv` | per-bank predicate line counts |
| `telemetry_field_audit.tsv` | predicate input classification: production-plausible vs benchmark-oracle |
| `detector_fairness_checklist.tsv` | per-fault comparator/DSM detector fairness checklist |
| `compute_fpr.py` | FPR aggregation |
| `compute_roc.py` | threshold false/true-positive sweep |
| `threshold_sweep.tsv` | threshold-sweep false/true-positive counts |
| `generate_no_fault_suite.py` | supplemental six-workflow no-fault trace generator |
| `no_fault_suite_traces.jsonl` | generated supplemental no-fault trace suite |
| `threshold_holdout.py` | train/held-out no-fault threshold validation |
| `threshold_holdout.tsv` | held-out threshold-validation counts |
| `analysis.py` | CIs, McNemar/Holm/Newcombe/Cohen h, GEE, production-plausible sensitivity, and count checks |
| `eval_prompt_subexperiment.py` | OpenInference EVALUATOR/PROMPT counterfactual supporting the manuscript sensitivity rows |
| `eval_prompt_matrix.tsv` | per-adapter EVALUATOR/PROMPT counterfactual matrix |
| `kind_ablation.tsv` | per-kind ablation table |
| `run_cli_agents.py` | optional live-LLM CLI sanity runner |
| `run_real_llm_sanity.py` | prints cached live-LLM CLI sanity-check cells |
| `real_llm_sanity.tsv` | cached live-LLM CLI sanity-check result table |
| `real_llm_14fault.tsv` | cached 14-fault live-LLM recovery-decision protocol cells |
| `requirements.lock` | pinned Python dependency versions used by the authors |

## Anonymization

The package uses anonymized model aliases (`model-A1` through `model-B3`) and
contains no author names, institutions, personal paths, API keys, or
author-identifying repository URLs. Public framework names and public
study-subject repository identifiers are retained because they are required for
replication and are not author identifiers.
