#!/bin/zsh
# Launch Opus 4.6 v2 with 600s timeout. Run alongside the existing
# Sonnet (22878) and Haiku (22879) v2 runs.
set -e
REPO=/Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PY=$REPO/.venv/bin/python3.12
SCRIPT=$REPO/experiments/swebench_n60_v2_forced_tooluse.py

cd $REPO
mkdir -p results

PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model claude-opus-4-6 --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_opus \
  > results/swebench_n60_v2_opus.log 2>&1 &
OPUS_V2_PID=$!
echo OPUS_V2 PID: $OPUS_V2_PID
echo
echo "Monitor: tail -f $REPO/results/swebench_n60_v2_opus.log"
