#!/bin/zsh
# Re-launch Sonnet + Haiku v2 with bumped 600s per-call timeout.
# GPT-5.5 v2 already completed cleanly — no re-run needed.
#
# Run from any directory:  bash launch_n60_v2_resume_sonnet_haiku.sh
#
# Expected runtime per tier: with 600s ceiling but most calls returning
# in 100-300s, and resume logic skipping nothing (fresh dirs after archive),
# expect ~5-7 hours per tier solo, or ~6-9 hours with both running in
# parallel (claude CLI quota shared between the two).

set -e

REPO=/Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PY=$REPO/.venv/bin/python3.12
SCRIPT=$REPO/experiments/swebench_n60_v2_forced_tooluse.py

cd $REPO
mkdir -p results

# Sonnet 4.6 v2 with 600s timeout
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model claude-sonnet-4-6 --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_sonnet \
  > results/swebench_n60_v2_sonnet.log 2>&1 &
SONNET_V2_PID=$!
echo SONNET_V2 PID: $SONNET_V2_PID

# Haiku 4.5 v2 with 600s timeout
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model claude-haiku-4-5 --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_haiku \
  > results/swebench_n60_v2_haiku.log 2>&1 &
HAIKU_V2_PID=$!
echo HAIKU_V2 PID: $HAIKU_V2_PID

echo
echo Monitor with:
echo "  tail -f $REPO/results/swebench_n60_v2_sonnet.log"
echo "  tail -f $REPO/results/swebench_n60_v2_haiku.log"
echo
echo "Note: per-call timeout is now 600s (up from 240s)."
echo "      Sonnet may genuinely need that long for the v2 prompt."
echo "      Resume logic active: if you kill and re-launch, completed"
echo "      instances will be skipped."
