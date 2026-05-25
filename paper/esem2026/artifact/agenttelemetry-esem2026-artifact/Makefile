.PHONY: reproduce smoke cli-smoke clean

PYTHON ?= python3

reproduce:
	$(PYTHON) generate_trace_corpus.py --output traces_full.jsonl
	$(PYTHON) score_traces.py traces_full.jsonl --output results_full.tsv
	$(PYTHON) analysis.py results_full.tsv --traces traces_full.jsonl
	$(PYTHON) compute_fpr.py results_full.tsv
	$(PYTHON) compute_roc.py
	$(PYTHON) generate_no_fault_suite.py --output no_fault_suite_traces.jsonl
	$(PYTHON) threshold_holdout.py --controls no_fault_suite_traces.jsonl --faults traces_full.jsonl --output threshold_holdout.tsv
	$(PYTHON) eval_prompt_subexperiment.py
	$(PYTHON) run_real_llm_sanity.py

smoke:
	$(PYTHON) generate_trace_corpus.py --output /tmp/agenttelemetry_traces_smoke.jsonl
	$(PYTHON) score_traces.py /tmp/agenttelemetry_traces_smoke.jsonl --output /tmp/agenttelemetry_results_smoke.tsv
	$(PYTHON) analysis.py /tmp/agenttelemetry_results_smoke.tsv --traces /tmp/agenttelemetry_traces_smoke.jsonl

cli-smoke:
	$(PYTHON) run_cli_agents.py --trials 1 --output /tmp/agenttelemetry_cli_sanity.tsv

clean:
	rm -f traces_full.jsonl results_full.tsv no_fault_suite_traces.jsonl threshold_holdout.tsv
	find . -name '__pycache__' -type d -prune -exec rm -r {} +
