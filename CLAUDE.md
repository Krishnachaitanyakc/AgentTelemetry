# CLAUDE.md — AgentTelemetry Project

## Project Overview

AgentTelemetry is an OpenTelemetry-based observability SDK for AI agent systems. 9 agent-specific span kinds, 7 framework adapters, privacy controls, and analysis tools.

## Build & Test

```bash
pip install -e .
pytest tests/
python examples/basic_usage.py
```

## Key directories
- `agenttelemetry/` — core SDK
- `agenttelemetry/adapters/` — framework instrumentors (LangChain, CrewAI, AutoGen, etc.)
- `agenttelemetry/analysis/` — anomaly detection, cost aggregation, decision attribution
- `paper/` — research papers (position paper, AIware, ASE, NeurIPS)
- `otep/` — OTel semantic conventions proposal materials
- `blog/` — blog posts
