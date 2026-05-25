#!/bin/zsh
# Launch all 3 SWE-bench n=60 tier-stratification runs in parallel.
# Run from any directory:  bash launch_n60_tiers.sh
# Each track runs in background, logs to results/, prints its PID.

set -e

REPO=/Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PY=$REPO/.venv/bin/python3.12
SCRIPT=$REPO/experiments/swebench_n60_opus_cli.py

cd $REPO
mkdir -p results

# Sonnet
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model claude-sonnet-4-6 --max-iterations 8 \
  --conditions control intervention \
  --output-dir results/swebench_n60_sonnet \
  > results/swebench_n60_sonnet.log 2>&1 &
SONNET_PID=$!
echo SONNET PID: $SONNET_PID

# Haiku
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model claude-haiku-4-5 --max-iterations 8 \
  --conditions control intervention \
  --output-dir results/swebench_n60_haiku \
  > results/swebench_n60_haiku.log 2>&1 &
HAIKU_PID=$!
echo HAIKU PID: $HAIKU_PID

# GPT 5.5
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model gpt-5.5 --max-iterations 8 \
  --conditions control intervention \
  --output-dir results/swebench_n60_gpt55 \
  > results/swebench_n60_gpt55.log 2>&1 &
GPT55_PID=$!
echo GPT55 PID: $GPT55_PID

echo
echo Monitor with:
echo "  tail -f $REPO/results/swebench_n60_sonnet.log"
echo "  tail -f $REPO/results/swebench_n60_haiku.log"
echo "  tail -f $REPO/results/swebench_n60_gpt55.log"
