# E1: what real instrumentation libraries record for the same agent runs

[PROTOCOL.md](PROTOCOL.md) defines the conditions, ground truth and scoring. It
was committed before any run.

## Layout

- `e1/domain.py`: synthetic support domain, 44 tickets, tools and prompts
- `e1/custom_agent.py`, `e1/graph_agent.py`: the same agent without a framework and on LangGraph
- `e1/harness.py`: record/replay transport, ground-truth log, JSONL span exporter
- `e1/run.py`: runs tickets in one condition; `run_all.sh` runs everything
- `e1/analyze.py`: scores runs and writes `data/results.json`
- `data/recordings/`: the recorded Anthropic API exchanges and the cost ledger
- `data/runs.tar.gz`: spans, ground truth and metadata for every run

## Reproduce

Create one virtual environment per condition with the pinned versions in
PROTOCOL.md. Every environment also needs `langchain` 1.4.7, because the
official OTel LangChain instrumentor does nothing without it. Then:

```bash
./run_all.sh                       # replays the recordings; no API key needed
.venvs/ref/bin/python -m e1.analyze
```

Re-recording (`FORCE=1 ./run_all.sh` with `ANTHROPIC_API_KEY` set) calls
`claude-opus-5-5`. The recorded runs cost USD 2.96 in total.

## Deviations from the protocol

- Tickets S37-S44 were added after the first run produced few retry loops: the
  model usually retried a failing lookup once or twice and then answered. These
  tickets ask the agent to keep retrying. The scoring rules did not change.
- `langchain` 1.4.7 was installed in every environment after the first pilot,
  because the official OTel LangChain instrumentor requires it and otherwise
  emits no spans.
- `data/results.json` also reports, for each failed tool execution, whether its
  error is visible on a span. This is descriptive and not one of the eight
  protocol families.
