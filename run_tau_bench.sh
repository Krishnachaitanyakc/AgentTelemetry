#!/bin/bash
# τ-bench runner orchestrator.
#
# Design: 2 providers × 115 retail tasks × 4 trials × 2 conditions = 1,840 cells
#
# Usage:
#   bash run_tau_bench.sh smoke           # 1 task per provider, ~5 min
#   bash run_tau_bench.sh pilot           # 10 tasks per provider, ~30-60 min
#   bash run_tau_bench.sh full            # 115 tasks per provider, both conditions, ~10-20h
#   bash run_tau_bench.sh status          # check progress
#   bash run_tau_bench.sh aggregate       # combine results
#   bash run_tau_bench.sh stop            # kill running jobs
#
# Providers (each in own background process):
#   anthropic / claude-opus-4-7    (uses ANTHROPIC_API_KEY)
#   openai    / gpt-5.5            (uses OPENAI_API_KEY)
#
# User simulator: gpt-4o (litellm openai)

set -euo pipefail

REPO_ROOT="/Users/kcbalusu/Desktop/Project/research/AgentTelemetry"
PYTHON="${REPO_ROOT}/.venv/bin/python3.12"
SCRIPT="${REPO_ROOT}/experiments/tau_bench_runner.py"
OUT_ROOT="${REPO_ROOT}/results/tau_bench"
PID_DIR="${OUT_ROOT}/.pids"

cd "$REPO_ROOT"
mkdir -p "$OUT_ROOT" "$PID_DIR"

MODE="${1:-smoke}"

launch_arm() {
    local provider="$1"
    local model="$2"
    local n_tasks="$3"
    local trials="$4"
    local workers="$5"
    local label="$6"
    local outdir="${OUT_ROOT}/${label}"
    local log="${outdir}.log"
    local pidfile="${PID_DIR}/${label}.pid"

    if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
        echo "  $label already running with PID $(cat "$pidfile")"
        return
    fi

    mkdir -p "$outdir"
    local end_arg=""
    if [ "$n_tasks" -gt 0 ]; then
        end_arg="--end-task $n_tasks"
    fi
    echo "  launching $label ($provider/$model, $workers workers, $trials trials, $n_tasks tasks) -> $outdir"
    nohup env PYTHONPATH=external/tau-bench:src "$PYTHON" "$SCRIPT" \
        --provider "$provider" --model "$model" \
        --user-provider openai --user-model gpt-4o \
        --env retail --agent-strategy tool-calling \
        --trials "$trials" --temperature 0.0 \
        $end_arg \
        --conditions control intervention \
        --workers "$workers" \
        --output-dir "results/tau_bench/${label}" \
        > "$log" 2>&1 &
    local pid=$!
    echo "$pid" > "$pidfile"
    echo "    PID $pid; log $log"
}

case "$MODE" in
    smoke)
        echo "=== SMOKE: 1 task per provider, 1 trial, both conditions, ~5 min ==="
        launch_arm "anthropic" "claude-opus-4-7" 1 1 1 "opus-smoke"
        launch_arm "openai"    "gpt-5.5"          1 1 1 "gpt55-smoke"
        echo ""
        echo "Monitor: bash run_tau_bench.sh status"
        ;;

    pilot)
        echo "=== PILOT: 10 tasks per provider, 2 trials, both conditions, ~30-60 min ==="
        launch_arm "anthropic" "claude-opus-4-7" 10 2 4 "opus-pilot"
        launch_arm "openai"    "gpt-5.5"          10 2 4 "gpt55-pilot"
        echo ""
        echo "Monitor: bash run_tau_bench.sh status"
        ;;

    full)
        echo "=== FULL: 115 tasks per provider, 4 trials, both conditions ==="
        echo "    ~10-20h wall-clock per arm at 8 workers"
        echo "    Estimated cost: ~\$50-200 in API calls"
        launch_arm "anthropic" "claude-opus-4-7" 0 4 8 "opus-full"
        launch_arm "openai"    "gpt-5.5"          0 4 8 "gpt55-full"
        echo ""
        echo "Monitor: bash run_tau_bench.sh status"
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
results = d.get('results', [])
ctl = [r for r in results if r.get('condition') == 'control']
intv = [r for r in results if r.get('condition') == 'intervention']
ctl_pass = sum(1 for r in ctl if r.get('reward', 0) >= 0.999)
intv_pass = sum(1 for r in intv if r.get('reward', 0) >= 0.999)
fires = sum(r.get('intervention_fires', 0) for r in results)
print(f'    progress: {n_done}/{n_total} elapsed={elapsed:.0f}s')
print(f'    cells: control={len(ctl)} pass={ctl_pass}  intervention={len(intv)} pass={intv_pass}')
print(f'    intervention fires: {fires} total')
" 2>/dev/null || echo "    progress: (could not parse partial)"
            fi
            if [ -f "$log" ]; then
                last=$(tail -n 1 "$log" | head -c 200)
                echo "    last log: $last"
            fi
        done
        ;;

    aggregate)
        echo "=== Aggregating across all arms in $OUT_ROOT ==="
        "$PYTHON" -c "
import json, glob
from pathlib import Path
from math import comb

def fisher_two(a,b,c,d):
    n1,n2,k,N=a+b,c+d,a+c,a+b+c+d
    if N==0: return 1.0
    def hg(x):
        if x<0 or x>min(n1,k) or (k-x)>n2 or (k-x)<0: return 0.0
        return comb(n1,x)*comb(n2,k-x)/comb(N,k)
    p=hg(a)
    return sum(hg(x) for x in range(0,min(n1,k)+1) if hg(x)<=p+1e-12)

for arm_dir in sorted(Path('${OUT_ROOT}').glob('*/')):
    rfile = arm_dir / 'results.json'
    if not rfile.exists(): continue
    d = json.load(open(rfile))
    s = d['summary']
    print(f'=== {arm_dir.name} ===')
    print(f'  n_tasks={s[\"n_tasks\"]} trials={s[\"trials\"]} cost=\${s[\"total_cost_usd\"]:.2f}')
    print(f'  intervention fires: {s[\"total_intervention_fires\"]}')
    for k in range(1, s['trials']+1):
        c = s['pass_k_summary']['control'].get(str(k), s['pass_k_summary']['control'].get(k, 0))
        i = s['pass_k_summary']['intervention'].get(str(k), s['pass_k_summary']['intervention'].get(k, 0))
        print(f'  pass^{k}: control={c}/{s[\"n_tasks\"]} ({c/s[\"n_tasks\"]*100:.1f}%)  intervention={i}/{s[\"n_tasks\"]} ({i/s[\"n_tasks\"]*100:.1f}%)')
    mn = s['mcnemar_pass_full_k']
    sig = 'SIGNIFICANT' if mn['p_value'] < 0.05 else 'not sig'
    print(f'  McNemar pass^{mn[\"k\"]}: b={mn[\"b\"]} c={mn[\"c\"]} delta={mn[\"delta_pp\"]:+.1f}pp p={mn[\"p_value\"]:.4f} ({sig})')
    print()
"
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
        echo "Usage: bash run_tau_bench.sh [smoke|pilot|full|status|aggregate|stop]"
        exit 2
        ;;
esac
