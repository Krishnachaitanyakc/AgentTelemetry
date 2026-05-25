#!/bin/zsh
# Launch all 3 SWE-bench n=60 forced-tool-use runs in parallel.
# Re-runs the tier stratification with the v2 harness that forces ReAct
# behavior so the AIware-style intervention can actually be tested.
#
# Run from any directory:  bash launch_n60_v2_tiers.sh

set -e

REPO=/Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PY=$REPO/.venv/bin/python3.12
SCRIPT=$REPO/experiments/swebench_n60_v2_forced_tooluse.py

cd $REPO
mkdir -p results

# IMPORTANT: The current Sonnet run (PID 30623) is still going on the v1 harness.
# v2 launches will share the claude CLI quota with it. If that causes throttling,
# kill 30623 first or wait for it to finish.

# Sonnet 4.6 v2
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model claude-sonnet-4-6 --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_sonnet \
  > results/swebench_n60_v2_sonnet.log 2>&1 &
SONNET_V2_PID=$!
echo SONNET_V2 PID: $SONNET_V2_PID

# Haiku 4.5 v2
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model claude-haiku-4-5 --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_haiku \
  > results/swebench_n60_v2_haiku.log 2>&1 &
HAIKU_V2_PID=$!
echo HAIKU_V2 PID: $HAIKU_V2_PID

# GPT 5.5 v2
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model gpt-5.5 --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_gpt55 \
  > results/swebench_n60_v2_gpt55.log 2>&1 &
GPT55_V2_PID=$!
echo GPT55_V2 PID: $GPT55_V2_PID

echo
echo Monitor with:
echo "  tail -f $REPO/results/swebench_n60_v2_sonnet.log"
echo "  tail -f $REPO/results/swebench_n60_v2_haiku.log"
echo "  tail -f $REPO/results/swebench_n60_v2_gpt55.log"
echo
echo Note: with min_searches=3 and stub tool responses, expected pacing is
echo "      ~6-8 min/instance (4-6 LLM calls per instance instead of 1)."
echo "      120 instances * ~7 min = ~14 hours per tier sequentially,"
echo "      ~5-7 hours running in parallel."
