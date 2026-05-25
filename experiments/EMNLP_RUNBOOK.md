# EMNLP 2026 — Pre-Submission Experiment Runbook

**Date:** 2026-05-11
**Purpose:** Run two experiments before EMNLP 2026 Industry Track submission (June 16, 2026 deadline).
**Both experiments use Meta CLIs (claude / codex) — $0 marginal cost.**

---

## Experiment 1 — SWE-bench n=60 closed-loop replication via Opus

### What it does
Extends the AIware paper's underpowered n=24 closed-loop intervention experiment (Fisher's exact p=0.53) to n=60 per arm. Tests whether the +12.5pp recovery effect holds at higher statistical power. This is the single most-asked-for result by the AIware reviewer feedback.

### Script (already exists, no changes needed)
`experiments/swebench_n60_opus_cli.py`

### Cost
- ~$0 marginal (uses Meta `claude` CLI via subprocess)
- ~6 hours wall-clock
- Runs 60 instances × 2 conditions (control + intervention) = 120 instance runs

### Pre-flight check
First, confirm the `claude` CLI is set up and the model is callable. Run this manually one time:

```bash
echo 'say only: pong' | claude --model claude-opus-4-7 --print
```

If prompted with the Meta CLI ack gate, type EXACTLY: `I HAVE REVIEWED AND VERIFIED`

If you get a clean `pong` response, you're ready.

### Launch command

```bash
cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PYTHONPATH=src:. .venv/bin/python3.12 experiments/swebench_n60_opus_cli.py \
    --n 60 \
    --model claude-opus-4-7 \
    --max-iterations 8 \
    --conditions control intervention \
    --output-dir results/swebench_n60_opus
```

**Note:** The script defaults to `claude-opus-4-6`; the command above uses `claude-opus-4-7` (current frontier per your CLAUDE.md). Either is acceptable — pick the one your CLI has access to.

### Output
- `results/swebench_n60_opus/results.json` — full result + per-instance traces
- `results/swebench_n60_opus/per_instance/*.json` — one file per instance × condition
- `results/swebench_n60_opus/summary.txt` — human-readable summary with Fisher's exact p-value

### Recommended: run in background with logging
```bash
cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PYTHONPATH=src:. nohup .venv/bin/python3.12 experiments/swebench_n60_opus_cli.py \
    --n 60 --model claude-opus-4-7 --max-iterations 8 \
    --conditions control intervention \
    --output-dir results/swebench_n60_opus \
    > results/swebench_n60_opus/run.log 2>&1 &
echo $! > results/swebench_n60_opus/run.pid
```

Then watch progress:
```bash
tail -f results/swebench_n60_opus/run.log
```

### What to do with the result

If `summary.txt` shows Fisher's exact p < 0.05: **strong replication; lead the EMNLP paper with this.**

If 0.05 < p < 0.20: **directional replication; report as "extends the n=24 trend with consistent effect direction."**

If p > 0.20 or effect reverses: **honest negative result; report as a deployment-experience finding ("the +12.5pp effect at n=24 did not hold at n=60 on Opus 4.7, suggesting the AIware result was overfit to GPT-4o-mini").** EMNLP Industry explicitly welcomes negative results.

---

## Experiment 2 — Multi-agent topology comparison via Meta CLIs

### What it does
Runs 3 multi-agent topologies (sequential, hierarchical, parallel) × 3 frontier models (Opus 4.7, Sonnet 4.6, GPT-5.5) × 5 research questions = **45 multi-agent traces**. Each trace exercises all 9 AgentTelemetry span kinds. Output: per-topology fault rates, costs, latencies, and AnomalyDetector results — gives the EMNLP paper a multi-agent deployment narrative that AIware doesn't have.

### Script (NEW — created today)
`experiments/multi_agent_topology_cli.py`

### Cost
- ~$0 marginal (uses Meta `claude` and `codex` CLIs)
- ~2.5 hours wall-clock (rate-limited by CLI throughput)

### Pre-flight check
Run the probe-only mode first to confirm both CLIs are accessible:

```bash
cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PYTHONPATH=src:. .venv/bin/python3.12 \
    experiments/multi_agent_topology_cli.py \
    --probe-only \
    --models claude_cli/claude-opus-4-7 claude_cli/claude-sonnet-4-6 codex_cli/gpt-5.5
```

Expected output:
```
=== Pre-flight CLI probes ===
  Probing claude_cli/claude-opus-4-7 ... OK (X.Xs)
  Probing claude_cli/claude-sonnet-4-6 ... OK (X.Xs)
  Probing codex_cli/gpt-5.5 ... OK (X.Xs)
Probe-only mode; exiting.
```

If any probe fails, the script prints the exact remediation command (e.g., manual ack via `echo 'say only: pong' | claude --model X --print`).

### Launch command (full run)

```bash
cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PYTHONPATH=src:. .venv/bin/python3.12 \
    experiments/multi_agent_topology_cli.py \
    --questions 5 \
    --topologies sequential hierarchical parallel \
    --models claude_cli/claude-opus-4-7 claude_cli/claude-sonnet-4-6 codex_cli/gpt-5.5 \
    --output-dir results/multi_agent_topology_cli
```

### Recommended: background launch with log
```bash
cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PYTHONPATH=src:. nohup .venv/bin/python3.12 \
    experiments/multi_agent_topology_cli.py \
    --questions 5 --topologies sequential hierarchical parallel \
    --models claude_cli/claude-opus-4-7 claude_cli/claude-sonnet-4-6 codex_cli/gpt-5.5 \
    --output-dir results/multi_agent_topology_cli \
    > results/multi_agent_topology_cli/run.log 2>&1 &
echo $! > results/multi_agent_topology_cli/run.pid
```

### Output
- `results/multi_agent_topology_cli/traces.jsonl` — all 9-span-kind spans across 45 runs (OTLP-compatible)
- `results/multi_agent_topology_cli/per_run/*.json` — per-run agent transcripts + telemetry (45 files)
- `results/multi_agent_topology_cli/summary.json` — per-(topology × model) aggregated stats
- `results/multi_agent_topology_cli/summary.txt` — human-readable table with completion rates, costs, latencies, and AnomalyDetector organic-fault counts

### What to do with the result

The summary table will show, per (topology, model) cell:
- **Completion rate** — did all 3 agents produce non-empty output?
- **Avg cost** — token-estimated cost per run (informational; CLI is free, but the metric tells you what it would cost via API)
- **Avg wall clock** — per-run latency
- **Avg input/output tokens** — token volume

The `organic_faults` block at the end will show what AnomalyDetector found in the traces. Common findings to expect:
- **Sequential:** highest latency, lowest fault rate (linear chain has nowhere to deadlock)
- **Hierarchical:** delegation-chain visibility; manager synthesis failures if specialist outputs conflict
- **Parallel:** memory-aggregation issues; potential cost-explosion if both researchers produce verbose output

EMNLP paper angle: "Across 3 topologies and 3 frontier models, we find [X] is the most common organic failure in production-tier deployments. The hierarchical pattern produces [N] delegation-chain anomalies invisible to vanilla OTel; the parallel pattern produces [M] cost-explosion events at the aggregator step."

---

## Suggested launch order

If both can run sequentially on the same machine:

1. **Now:** Pre-flight probes for both experiments (~2 min).
2. **Background experiment 1 (SWE-bench n=60)** — ~6 hours.
3. **In parallel: foreground writing on EMNLP paper** — the reformat work doesn't need experiment 1's results.
4. **After exp 1 completes, launch experiment 2 (multi-agent)** — ~2.5 hours.
5. **Total elapsed: ~8.5 hours of compute, all overnight feasible.**

**Why sequential, not parallel:** Both experiments use the Meta `claude` CLI, which serializes calls per process. Running them in parallel would double-stress the CLI rate limit and potentially cause one or both to fail. Sequential execution is cleaner.

If you want to launch experiment 2 immediately and let experiment 1 run after, that also works — the topology comparison touches more model variety (claude-opus + claude-sonnet + codex/gpt-5.5) and only one of those overlaps with experiment 1.

---

## Honest caveats

1. **CLI rate limits are unpredictable.** Both scripts are tested in spirit but the Meta CLI's exact throughput depends on your account tier and current load. If you see frequent timeouts, reduce `--n` (experiment 1) or `--questions` (experiment 2) for a smaller initial run.

2. **The token-cost estimates in experiment 2 are approximate** — `len(text) // 4` is the standard rough heuristic for OpenAI tokenization but undercounts for non-English / code-heavy content. The cost numbers are useful for relative comparison across topologies, not for absolute billing.

3. **Per-instance runtime varies wildly.** SWE-bench instances have very different complexity. The script's 480-second timeout per call should handle most cases, but a small fraction may time out — those are recorded with `error: "timeout..."` in the per-instance output.

4. **Experiment 2 uses the AgentTelemetry Custom adapter pattern.** Spans are created via `start_agent_span()` calls, not via auto-instrumentation hooks. This is the "manual instrumentation" path validated in the AIware paper's RQ5 — it produces the same 9-span-kind structure as native framework adapters, just in a more controlled way.

5. **None of this writes to the EMNLP paper directly.** After both experiments complete, you'll need to manually integrate the new findings into the EMNLP draft (per `emnlp2026_reformat_plan.md` §2 — expand RQ5 + RQ6).
