# AgentTelemetry

[![PyPI version](https://img.shields.io/pypi/v/agenttelemetry.svg)](https://pypi.org/project/agenttelemetry/)
[![Python versions](https://img.shields.io/pypi/pyversions/agenttelemetry.svg)](https://pypi.org/project/agenttelemetry/)
[![License](https://img.shields.io/pypi/l/agenttelemetry.svg)](https://github.com/agenttelemetry/agenttelemetry/blob/main/LICENSE)

OpenTelemetry-based observability for AI agent systems. Provides 9 agent-specific span kinds, 7 framework adapters, privacy controls, and analysis tools for fault detection in autonomous agents.

## Papers

- **AIware 2026** — *AgentTelemetry: A Fault Detection Benchmark and Toolkit for LLM Agent Observability.* Krishna Chaitanya Balusu. 3rd ACM International Conference on AI-Powered Software, July 2026.
  Paper: [DOI: 10.1145/3805760.3814931](https://doi.org/10.1145/3805760.3814931) ·
  Software archive: [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20129005.svg)](https://doi.org/10.5281/zenodo.20129005) (this AIware snapshot: [`v0.1.0-aiware2026`](https://doi.org/10.5281/zenodo.20129006)) ·
  Camera-ready PDF: [`paper/aiware2026/aiware_paper.pdf`](paper/aiware2026/aiware_paper.pdf)

## Installation

```bash
pip install agenttelemetry
```

## Quickstart

```python
from agenttelemetry import configure, start_agent_span, AgentSpanKind

# One-line setup: configure tracing with console output
provider = configure(service_name="my-agent", console=True)
tracer = provider.get_tracer()

# Trace an agent task
with start_agent_span("research-task", AgentSpanKind.AGENT, tracer=tracer) as span:
    span.set_attribute("agent.name", "researcher")

    with start_agent_span("call-gpt4", AgentSpanKind.LLM_CALL, tracer=tracer) as llm:
        llm.set_attribute("llm.model", "gpt-4o")
        llm.set_attribute("llm.input_tokens", 500)
        llm.set_attribute("llm.output_tokens", 200)

    with start_agent_span("web-search", AgentSpanKind.TOOL_CALL, tracer=tracer) as tool:
        tool.set_attribute("tool.name", "search")
        tool.set_attribute("tool.status", "success")
```

## Features

- **9 agent-specific span kinds** -- AGENT, LLM_CALL, TOOL_CALL, PLANNING, REASONING, RETRIEVAL, GUARD_RAIL, DELEGATION, MEMORY
- **7 framework adapters** -- auto-instrumentation for LangChain, CrewAI, AutoGen, Anthropic SDK, OpenAI SDK, LlamaIndex, and a manual API for custom agents
- **3 privacy levels** -- NONE (structural only), METADATA_ONLY (default; adds model names, token counts, costs), FULL (captures prompt/completion content)
- **4 analysis modules** -- anomaly detection, cost aggregation, decision attribution, hallucination tracing
- **Built on OpenTelemetry** -- exports to Jaeger, Grafana Tempo, Datadog, or any OTLP-compatible backend
- **Cost estimation** -- automatic USD cost calculation for OpenAI and Anthropic models

## Framework Adapters

| Framework     | Adapter Class          | Strategy          | LOC |
|---------------|------------------------|-------------------|-----|
| LangChain     | `LangChainInstrumentor`  | Callback handler  | 359 |
| CrewAI        | `CrewAIInstrumentor`     | Hook system       | 264 |
| AutoGen       | `AutoGenInstrumentor`    | Monkey-patch      | 256 |
| Anthropic SDK | `AnthropicInstrumentor`  | Monkey-patch      | 294 |
| OpenAI SDK    | `OpenAIInstrumentor`     | Monkey-patch      | 245 |
| LlamaIndex    | `LlamaIndexInstrumentor` | Span handler      | 280 |
| Custom        | `start_agent_span` etc.  | Context managers   | 315 |

Each adapter uses lazy imports -- the framework package is only required at `instrument()` time, not at import time.

### Auto-instrumentation Example (OpenAI)

```python
from agenttelemetry import configure
from agenttelemetry.adapters import OpenAIInstrumentor

provider = configure(service_name="my-agent", console=True)
instrumentor = OpenAIInstrumentor()
instrumentor.instrument(tracer_provider=provider.tracer_provider)

# All openai.chat.completions.create() calls are now traced automatically
```

## Analysis Modules

| Module                  | Class                 | Description                                                       |
|-------------------------|-----------------------|-------------------------------------------------------------------|
| **Anomaly Detection**   | `AnomalyDetector`     | Detects circular delegation, infinite retries, cost explosions, and context overflow |
| **Cost Aggregation**    | `CostAggregator`      | Aggregates token counts and USD costs by model, agent, and trace  |
| **Decision Attribution**| `DecisionAttributor`  | Links each tool call back to the LLM decision that triggered it   |
| **Hallucination Tracing** | `HallucinationTracer` | Identifies LLM outputs not grounded in retrieved content (token-overlap heuristic) |

### Benchmark Results

In fault-detection experiments, AgentTelemetry detects **8 out of 8 fault types** at FDR = 1.0:

- Circular delegation loops
- Infinite tool retry loops
- Cost explosion (runaway spending)
- Context window overflow
- Ungrounded LLM outputs (hallucination candidates)
- Unattributed tool decisions
- Token budget violations
- Latency anomalies

## Privacy Controls

```python
from agenttelemetry import configure, PrivacyLevel

# Default: captures metadata but not prompt/completion content
provider = configure(service_name="my-agent", privacy_level=PrivacyLevel.METADATA_ONLY)

# Full capture for debugging (opt-in)
provider = configure(service_name="my-agent", privacy_level=PrivacyLevel.FULL)

# Minimal: structural info only (span kinds, timing, status)
provider = configure(service_name="my-agent", privacy_level=PrivacyLevel.NONE)
```

## API Reference

### Core

- `configure(service_name, privacy_level, console, json_file)` -- one-line setup, returns `AgentTelemetryProvider`
- `AgentTelemetryProvider` -- wraps OTel TracerProvider with agent-specific defaults
- `start_agent_span(name, kind, tracer, attributes)` -- context manager for agent spans
- `AgentSpanKind` -- enum of 9 span kinds
- `PrivacyLevel` -- `NONE`, `METADATA_ONLY`, `FULL`

### Adapters

- `AnthropicInstrumentor`, `OpenAIInstrumentor`, `LangChainInstrumentor`, `CrewAIInstrumentor`, `AutoGenInstrumentor`, `LlamaIndexInstrumentor`
- Manual helpers: `start_llm_span`, `start_tool_span`, `start_retrieval_span`, `start_planning_span`, `start_reasoning_span`, `start_guardrail_span`, `start_delegation_span`, `start_memory_span`

### Analysis

- `AnomalyDetector` / `Anomaly` / `AnomalyType`
- `CostAggregator` / `CostReport` / `ModelCost`
- `DecisionAttributor` / `ToolDecision`
- `HallucinationTracer` / `HallucinationCandidate`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code structure, and guidelines.

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the full text.

## Citation

If you use AgentTelemetry in your research, please cite:

```bibtex
@software{agenttelemetry2025,
  title     = {AgentTelemetry: OpenTelemetry-Based Observability for AI Agent Systems},
  author    = {Balusu, Krishna Chaitanya},
  year      = {2025},
  url       = {https://github.com/agenttelemetry/agenttelemetry},
  license   = {Apache-2.0},
}
```
