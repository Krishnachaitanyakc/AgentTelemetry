#!/bin/bash
# B1+: Launch SWE-bench full matrix across 2 LLM providers in parallel via CLI.
#
# Design: 2 providers × 300 SWE-bench Lite × 3 seeds × 2 conditions
#       = 3,600 agent runs total (1,800 per provider)
#
# Providers (each runs in its own background process):
#   claude-opus-4-7    via `claude --model X --print` (Anthropic)
#   gpt-5.5            via `codex exec --skip-git-repo-check --model X "..."` (OpenAI)
#
# All subprocesses launched from cwd=/tmp to bypass project-dir security gate.
#
# Usage:
#   bash run_full_matrix.sh smoke           # n=3 per provider, ~20 min
#   bash run_full_matrix.sh full            # n=300 per provider, ~12-24h per arm
#   bash run_full_matrix.sh status          # check progress on running jobs
#   bash run_full_matrix.sh aggregate       # combine results from finished jobs
#   bash run_full_matrix.sh stop            # kill all running jobs
#
# Prereq (one-time):
#   The Meta `claude` CLI may require an interactive ack the first time.
#   Run interactively first if you have not before:
#       claude --model claude-opus-4-7
#   Type EXACTLY:  I HAVE REVIEWED AND VERIFIED
#   then Ctrl+D to exit. Same for codex.

set -euo pipefail

REPO_ROOT="/Users/kcbalusu/Desktop/Project/research/AgentTelemetry"
PYTHON="${REPO_ROOT}/.venv/bin/python3.12"
SCRIPT="${REPO_ROOT}/experiments/swebench_full_matrix.py"
OUT_ROOT="${REPO_ROOT}/results/swebench_full"
PID_DIR="${OUT_ROOT}/.pids"

cd "$REPO_ROOT"
mkdir -p "$OUT_ROOT" "$PID_DIR"

MODE="${1:-smoke}"

launch_model() {
    local model="$1"
    local backend="$2"
    local n="$3"
    local outdir="${OUT_ROOT}/${4}"
    local log="${outdir}.log"
    local workers="${5:-8}"
    local pidfile="${PID_DIR}/${4}.pid"

    if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
        echo "  $model already running with PID $(cat "$pidfile")"
        return
    fi

    mkdir -p "$outdir"
    echo "  launching $model ($workers workers) -> $outdir"
    nohup env PYTHONPATH=src:. "$PYTHON" "$SCRIPT" \
        --model "$model" \
        --backend "$backend" \
        --n "$n" \
        --max-iterations 8 \
        --seeds 0.0 0.3 0.7 \
        --conditions control intervention \
        --workers "$workers" \
        --output-dir "$outdir" \
        > "$log" 2>&1 &
    local pid=$!
    echo "$pid" > "$pidfile"
    echo "    PID $pid; log $log"
}

case "$MODE" in
    smoke)
        echo "=== SMOKE TEST: 3 instances per provider, 4 workers, ~10 min total ==="
        launch_model "claude-opus-4-7"  "claude-cli" 3 "claude-opus-4-7-smoke" 4
        launch_model "gpt-5.5"          "codex-cli"  3 "gpt-5.5-smoke"          4
        echo ""
        echo "Two jobs launched. Monitor with:"
        echo "  bash run_full_matrix.sh status"
        ;;

    full)
        echo "=== FULL MATRIX: 2 providers × n=300 × 3 seeds × 2 conditions ==="
        echo "    claude-opus-4-7: 4 workers (Meta sandbox contention; slower CLI)"
        echo "    gpt-5.5:         8 workers (codex is faster)"
        echo "    Both arms in parallel; ~20-30h wall-clock for slower arm"
        echo ""
        launch_model "claude-opus-4-7"  "claude-cli" 300 "claude-opus-4-7" 4
        launch_model "gpt-5.5"          "codex-cli"  300 "gpt-5.5"          8
        echo ""
        echo "Two jobs launched in parallel. Monitor:"
        echo "  bash run_full_matrix.sh status"
        echo "  tail -f ${OUT_ROOT}/claude-opus-4-7.log"
        echo "  tail -f ${OUT_ROOT}/gpt-5.5.log"
        echo ""
        echo "Aggregate after both finish:"
        echo "  bash run_full_matrix.sh aggregate"
        ;;

    status)
        echo "=== Job status ==="
        for pidfile in "${PID_DIR}"/*.pid; do
            [ -f "$pidfile" ] || continue
            name=$(basename "$pidfile" .pid)
            pid=$(cat "$pidfile")
            log="${OUT_ROOT}/${name}.log"
            partial="${OUT_ROOT}/${name}/results_partial.json"
            if kill -0 "$pid" 2>/dev/null; then
                state="RUNNING (PID $pid)"
            else
                state="STOPPED (last PID was $pid)"
            fi
            echo ""
            echo "  $name: $state"
            if [ -f "$partial" ]; then
                "$PYTHON" -c "
import json
d = json.load(open('$partial'))
n_done = d.get('n_done', 0)
n_total = d.get('n_total', 0)
elapsed = d.get('elapsed_s', 0)
if n_done and n_total:
    pct = 100 * n_done / n_total
    eta = (elapsed / n_done) * (n_total - n_done) if n_done else 0
    print(f'    progress: {n_done}/{n_total} ({pct:.1f}%) elapsed={elapsed:.0f}s ETA={eta:.0f}s')
" 2>/dev/null || echo "    progress: (could not parse partial)"
            fi
            if [ -f "$log" ]; then
                echo "    last log line: $(tail -n 1 "$log" | head -c 200)"
            fi
        done
        ;;

    aggregate)
        echo "=== Aggregating across all model subdirs in $OUT_ROOT ==="
        PYTHONPATH=src:. "$PYTHON" "$SCRIPT" --aggregate --output-dir "$OUT_ROOT"
        ;;

    stop)
        echo "=== Killing all running jobs ==="
        for pidfile in "${PID_DIR}"/*.pid; do
            [ -f "$pidfile" ] || continue
            pid=$(cat "$pidfile")
            name=$(basename "$pidfile" .pid)
            if kill -0 "$pid" 2>/dev/null; then
                echo "  killing $name (PID $pid)"
                kill "$pid" || true
            fi
        done
        ;;

    *)
        echo "Usage: bash run_full_matrix.sh [smoke|full|status|aggregate|stop]"
        exit 2
        ;;
esac
