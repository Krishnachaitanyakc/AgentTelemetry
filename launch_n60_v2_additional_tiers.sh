#!/bin/zsh
# Launch 5 ADDITIONAL v2 tier runs to complete the cross-provider study:
#   2 OpenAI tiers (gpt-5.4 frontier, gpt-5.2 mid)
#   3 Gemini tiers (3.1-pro frontier, 2.5-pro mid, 2.5-flash-lite budget)
#
# These run alongside the in-flight Sonnet+Haiku+Opus claude tracks and
# the already-completed gpt-5.5 v2 run.
#
# Run from any directory:  bash launch_n60_v2_additional_tiers.sh
#
# IMPORTANT: assumes you have already verified each model with a manual
# probe call (codex exec ... / gemini -m ... -p ...) and got back "pong".
#
# Per-call timeout 600s (set in the script). Resume logic active — re-running
# this launcher will skip completed instances.

set -e

REPO=/Users/kcbalusu/Desktop/Project/research/AgentTelemetry
PY=$REPO/.venv/bin/python3.12
SCRIPT=$REPO/experiments/swebench_n60_v2_forced_tooluse.py

cd $REPO
mkdir -p results

# ============================================================
# OpenAI: GPT-5.4 (frontier)
# ============================================================
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model gpt-5.4 --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_gpt54 \
  > results/swebench_n60_v2_gpt54.log 2>&1 &
GPT54_PID=$!
echo GPT54_V2 PID: $GPT54_PID

# ============================================================
# OpenAI: GPT-5.2 (mid)
# ============================================================
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model gpt-5.2 --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_gpt52 \
  > results/swebench_n60_v2_gpt52.log 2>&1 &
GPT52_PID=$!
echo GPT52_V2 PID: $GPT52_PID

# ============================================================
# Gemini: 3.1 Pro (frontier)
# ============================================================
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model gemini-3.1-pro-preview --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_gemini31pro \
  > results/swebench_n60_v2_gemini31pro.log 2>&1 &
GEM31_PID=$!
echo GEMINI_31_PRO_V2 PID: $GEM31_PID

# ============================================================
# Gemini: 2.5 Pro (mid)
# ============================================================
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model gemini-2.5-pro --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_gemini25pro \
  > results/swebench_n60_v2_gemini25pro.log 2>&1 &
GEM25_PID=$!
echo GEMINI_25_PRO_V2 PID: $GEM25_PID

# ============================================================
# Gemini: 2.5 Flash Lite (budget)
# ============================================================
PYTHONPATH=src:. nohup $PY $SCRIPT \
  --n 60 --model gemini-2.5-flash-lite --max-iterations 8 \
  --min-searches 3 --min-repeats 3 \
  --conditions control intervention \
  --output-dir results/swebench_n60_v2_gemini25flashlite \
  > results/swebench_n60_v2_gemini25flashlite.log 2>&1 &
GEM25LITE_PID=$!
echo GEMINI_25_FLASH_LITE_V2 PID: $GEM25LITE_PID

echo ""
echo "5 additional v2 tracks launched. Running alongside the 3 in-flight"
echo "claude tracks (Sonnet, Haiku, Opus). Total: 8 v2 tracks parallel."
echo ""
echo "Monitor any with:"
echo "  tail -f $REPO/results/swebench_n60_v2_<tier>.log"
echo ""
echo "tier dirs: gpt54 gpt52 gemini31pro gemini25pro gemini25flashlite"
