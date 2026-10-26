#!/bin/bash
# Record every ticket live once per framework, then replay it under every condition.
# Needs ANTHROPIC_API_KEY for the recording step only.
set -u
cd "$(dirname "$0")"
FORCE=${FORCE:-}
for fw in custom langgraph; do
  .venvs/ref/bin/python -u -m e1.run --mode record --condition ref --framework "$fw" ${FORCE:+--force} \
    || echo "recording $fw finished with failures"
done
for fw in custom langgraph; do
  for cond in ref sdk oi ollm otel; do
    venv=$cond; [ "$cond" = sdk ] && venv=ref
    .venvs/$venv/bin/python -u -m e1.run --mode replay --condition "$cond" --framework "$fw" \
      || echo "replay $fw/$cond finished with failures"
  done
done
