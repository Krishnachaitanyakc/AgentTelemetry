#!/bin/bash
# B1: Run SWE-bench n=60 matched control via Claude Opus 4.6 CLI
#
# Usage:
#   bash run_b1.sh smoke      # ~10 min, ~$0.50 — verifies end-to-end works
#   bash run_b1.sh full       # ~6 hours, ~$15 — the real n=60 run
#   bash run_b1.sh full bg    # same as full but runs detached in background
#
# Output:
#   results/swebench_n3_smoke/    (smoke)
#   results/swebench_n60_opus/    (full)
#
# Prereq (one-time):
#   The Meta `claude` CLI requires an interactive ack the first time it runs.
#   If this is your first claude CLI use on this machine, run interactively:
#       echo "say only: pong" | claude --model claude-opus-4-6 --print
#   When prompted, type EXACTLY:  I HAVE REVIEWED AND VERIFIED
#   Then re-run this script.

set -euo pipefail

REPO_ROOT="/Users/kcbalusu/Desktop/Project/research/AgentTelemetry"
PYTHON="${REPO_ROOT}/.venv/bin/python3.12"
SCRIPT="${REPO_ROOT}/experiments/swebench_n60_opus_cli.py"
MODEL="claude-opus-4-6"

cd "$REPO_ROOT"

# Pre-flight checks
if [ ! -x "$PYTHON" ]; then
  echo "ERROR: Python interpreter not found: $PYTHON"
  echo "       Make sure the venv exists at .venv/ with python3.12 binary."
  exit 1
fi

if [ ! -f "$SCRIPT" ]; then
  echo "ERROR: B1 script not found: $SCRIPT"
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "ERROR: \`claude\` CLI not found in PATH."
  exit 1
fi

# Verify python sees datasets
if ! "$PYTHON" -c "from datasets import load_dataset" >/dev/null 2>&1; then
  echo "INFO: installing 'datasets' package..."
  "${REPO_ROOT}/.venv/bin/pip" install datasets >/dev/null 2>&1 || \
    "$PYTHON" -m pip install datasets
fi

MODE="${1:-smoke}"
BG="${2:-}"

case "$MODE" in
  smoke)
    echo "=== Smoke test: n=3, max-iter=4, ~10 min, ~\$0.50 ==="
    PYTHONPATH=src:. "$PYTHON" "$SCRIPT" \
      --n 3 \
      --model "$MODEL" \
      --max-iterations 4 \
      --conditions control intervention \
      --output-dir results/swebench_n3_smoke
    echo ""
    echo "Smoke test complete. Inspect:"
    echo "  cat results/swebench_n3_smoke/summary.txt"
    ;;

  full)
    if [ "$BG" = "bg" ]; then
      LOG="${REPO_ROOT}/results/swebench_n60_opus.log"
      mkdir -p "$(dirname "$LOG")"
      echo "=== Full run, BACKGROUND: n=60, ~6h, ~\$15 ==="
      echo "    Log: $LOG"
      nohup env PYTHONPATH=src:. "$PYTHON" "$SCRIPT" \
        --n 60 \
        --model "$MODEL" \
        --max-iterations 8 \
        --conditions control intervention \
        --output-dir results/swebench_n60_opus \
        > "$LOG" 2>&1 &
      PID=$!
      echo "    PID: $PID"
      echo ""
      echo "Monitor:"
      echo "  tail -f $LOG"
      echo "  cat results/swebench_n60_opus/results_partial.json | $PYTHON -c \"import json,sys; d=json.load(sys.stdin); print(f'done {d[\\\"n_done\\\"]}/120 in {d[\\\"elapsed_s\\\"]:.0f}s')\""
      echo ""
      echo "Stop:"
      echo "  kill $PID"
    else
      echo "=== Full run, FOREGROUND: n=60, ~6h, ~\$15 ==="
      echo "    Press Ctrl+C to abort. Partial results saved every 5 tasks."
      echo ""
      PYTHONPATH=src:. "$PYTHON" "$SCRIPT" \
        --n 60 \
        --model "$MODEL" \
        --max-iterations 8 \
        --conditions control intervention \
        --output-dir results/swebench_n60_opus
      echo ""
      echo "Full run complete. Final result:"
      echo "  cat results/swebench_n60_opus/summary.txt"
    fi
    ;;

  *)
    echo "Unknown mode: $MODE"
    echo "Usage: bash run_b1.sh [smoke|full] [bg]"
    exit 2
    ;;
esac
