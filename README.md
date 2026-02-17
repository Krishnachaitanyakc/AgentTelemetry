# AgentTelemetry

**Unified observability for autonomous AI agent systems.**

---

## The Problem

Modern AI agents operate as opaque black boxes -- they chain LLM calls, invoke tools, delegate to sub-agents, and make autonomous decisions, yet there is no standardized way to observe, debug, or audit their behavior.  Existing observability tools were designed for deterministic microservices, not for the non-deterministic, multi-step reasoning loops that define agentic workflows.  AgentTelemetry closes this gap by providing a purpose-built observability SDK that maps agent-native concepts (tasks, reasoning steps, tool calls, inter-agent communication) directly to structured traces and metrics.

## Key Features

- **Agent-native semantic conventions** -- first-class span kinds for tasks, reasoning, LLM calls, tool invocations, planning, reflection, retrieval, and inter-agent communication.
- **Zero-dependency core** -- the tracing and metrics engine has no external dependencies; OpenTelemetry is an optional export target, not a requirement.
- **Auto-instrumentation** -- drop-in instrumentors for LangChain, CrewAI, AutoGen, and DSPy that capture telemetry without modifying agent code.
- **Multi-agent context propagation** -- W3C Trace Context-compatible carrier format that lets spans from cooperating agents share a single trace.
- **Privacy-first design** -- prompt and completion capture is disabled by default and must be explicitly opted in.
- **Built-in cost tracking** -- automatic token counting and USD cost estimation for major LLM providers.
- **Flexible export** -- console, JSON Lines file, and OpenTelemetry Protocol (OTLP) exporters included; bring-your-own-exporter interface for custom backends.
- **Pre-built Grafana dashboards** -- ready-to-import dashboards for agent performance, cost analysis, and error tracking.

## Quick Start

### Installation

```bash
# Core SDK (no dependencies)
pip install agenttelemetry

# With auto-instrumentation for LangChain
pip install agenttelemetry[langchain]

# With OpenTelemetry export (Jaeger, Grafana Tempo, Datadog, etc.)
pip install agenttelemetry[otlp]

# Everything
pip install agenttelemetry[all]
```

### Basic Usage

```python
from agenttelemetry import AgentTracer, AgentMetrics
from agenttelemetry.exporters import ConsoleExporter

# Create a tracer for your agent
tracer = AgentTracer(agent_name="researcher", framework="custom")
tracer.add_exporter(ConsoleExporter())

# Instrument your agent's workflow
with tracer.start_task("Summarize document") as task:

    with tracer.start_llm_call(model="gpt-4o") as llm:
        # ... call your LLM ...
        llm.set_attribute("llm.input_tokens", 500)
        llm.set_attribute("llm.output_tokens", 200)

    with tracer.start_tool_call("web_search") as tool:
        # ... invoke a tool ...
        tool.set_attribute("tool.input", "latest AI news")
        tool.set_attribute("tool.success", True)

# Spans are automatically exported on completion
```

### Auto-Instrumentation (LangChain)

```python
from agenttelemetry.instrumentors.langchain import LangChainInstrumentor

instrumentor = LangChainInstrumentor(capture_content=False)
instrumentor.instrument()

# Use LangChain as usual -- telemetry is captured automatically
# ...

instrumentor.uninstrument()
```

## Architecture

```
                         AgentTelemetry SDK
 +-----------------------------------------------------------------+
 |                                                                   |
 |   Agent Framework          Instrumentor           Core Engine     |
 |   (LangChain, CrewAI,      (auto-patches         (AgentTracer,   |
 |    AutoGen, DSPy,           framework calls)       AgentMetrics)  |
 |    or custom code)                                                |
 |         |                       |                      |          |
 |         v                       v                      v          |
 |   +-----------+          +-------------+        +------------+    |
 |   |  Agent    |  ------> | Instrumentor| -----> | AgentTracer|    |
 |   |  Code     |          | (langchain, |        | AgentMetrics    |
 |   |           |          |  crewai,    |        |            |    |
 |   +-----------+          |  autogen,   |        +-----+------+    |
 |                          |  dspy)      |              |           |
 |                          +-------------+              |           |
 |                                                       v           |
 |                                                +-------------+    |
 |                                                |  Exporters  |    |
 |                                                | +---------+ |    |
 |                                                | | Console | |    |
 |                                                | +---------+ |    |
 |                                                | | JSON    | |    |
 |                                                | +---------+ |    |
 |                                                | | OTLP    | |    |
 |                                                | +---------+ |    |
 |                                                +------+------+    |
 |                                                       |           |
 +-----------------------------------------------------------------+
                                                         |
                                                         v
                                              +--------------------+
                                              |  Backends          |
                                              |  * Grafana / Tempo |
                                              |  * Jaeger          |
                                              |  * Datadog         |
                                              |  * Custom          |
                                              +--------------------+
```

**Data flow:**

```
Agent Code  --->  Instrumentor  --->  AgentTracer  --->  Exporter  --->  Backend
  (or manual)     (auto-patch)       (spans + metrics)  (console,      (Grafana,
                                                         JSON, OTLP)    Jaeger)
```

## Supported Frameworks

| Framework | Instrumentor Class       | Status      | Install Extra |
|-----------|--------------------------|-------------|---------------|
| LangChain | `LangChainInstrumentor`  | Available   | `langchain`   |
| CrewAI    | `CrewAIInstrumentor`     | Available   | `crewai`      |
| AutoGen   | `AutoGenInstrumentor`    | Available   | `autogen`     |
| DSPy      | `DSPyInstrumentor`       | Available   | `dspy`        |
| Custom    | Manual via `AgentTracer` | Always      | (none)        |

## Semantic Conventions

AgentTelemetry defines semantic attribute keys that follow OpenTelemetry naming conventions, extended for agent-specific concepts.

### Span Kinds

| SpanKind       | Description                              |
|----------------|------------------------------------------|
| `task`         | Top-level task (root of a trace)         |
| `reasoning`    | Chain-of-thought / reasoning step        |
| `llm_call`     | Call to a language model                 |
| `tool_call`    | Tool or function invocation              |
| `planning`     | Task decomposition / planning step       |
| `reflection`   | Self-evaluation or critique              |
| `retrieval`    | RAG / knowledge retrieval                |
| `agent_comm`   | Inter-agent communication                |
| `human_input`  | Human-in-the-loop interaction            |

### Attribute Keys

| Attribute                        | Type   | Description                        |
|----------------------------------|--------|------------------------------------|
| `agent.name`                     | string | Name of the agent                  |
| `agent.framework`                | string | Framework name (langchain, etc.)   |
| `agent.framework.version`        | string | Framework version                  |
| `agent.task`                     | string | Task description                   |
| `llm.model`                      | string | Model identifier                   |
| `llm.provider`                   | string | Provider name (openai, anthropic)  |
| `llm.input_tokens`               | int    | Input / prompt token count         |
| `llm.output_tokens`              | int    | Output / completion token count    |
| `llm.total_tokens`               | int    | Total token count                  |
| `llm.cost_usd`                   | float  | Estimated cost in USD              |
| `llm.latency_ms`                 | float  | LLM call latency in milliseconds   |
| `llm.temperature`                | float  | Sampling temperature               |
| `llm.prompt`                     | string | Prompt text (opt-in only)          |
| `llm.completion`                 | string | Completion text (opt-in only)      |
| `tool.name`                      | string | Tool / function name               |
| `tool.input`                     | string | Tool input parameters              |
| `tool.output`                    | string | Tool output / return value         |
| `tool.success`                   | bool   | Whether the tool call succeeded    |
| `tool.error`                     | string | Error message if tool failed       |
| `agent.interaction.type`         | string | Communication type (delegation, request, etc.) |
| `agent.interaction.source_agent` | string | Sending agent name                 |
| `agent.interaction.target_agent` | string | Receiving agent name               |

### Pre-defined Metrics

| Metric Name               | Type      | Description                    |
|---------------------------|-----------|--------------------------------|
| `agent.task.count`        | Counter   | Total tasks executed           |
| `agent.llm.call.count`    | Counter   | Total LLM calls made           |
| `agent.tool.call.count`   | Counter   | Total tool calls made          |
| `agent.error.count`       | Counter   | Total errors encountered       |
| `agent.llm.tokens.input`  | Counter   | Cumulative input tokens        |
| `agent.llm.tokens.output` | Counter   | Cumulative output tokens       |
| `agent.cost.total_usd`    | Counter   | Cumulative cost in USD         |
| `agent.task.duration_ms`  | Histogram | Task duration distribution     |
| `agent.llm.latency_ms`    | Histogram | LLM call latency distribution  |
| `agent.tool.latency_ms`   | Histogram | Tool call latency distribution |

## Examples

See the [examples/](examples/) directory for runnable scripts:

| Example                                            | Description                                      |
|----------------------------------------------------|--------------------------------------------------|
| [basic_usage.py](examples/basic_usage.py)          | Manual instrumentation, console export, cost tracking |
| [multi_agent.py](examples/multi_agent.py)          | Two-agent collaboration with context propagation |
| [langchain_example.py](examples/langchain_example.py) | Auto-instrumentation with LangChain          |

Run any example from the project root:

```bash
# Install in development mode
pip install -e .

# Run examples
python examples/basic_usage.py
python examples/multi_agent.py
python examples/langchain_example.py
```

## Grafana Dashboards

Pre-built Grafana dashboards are available in the [dashboards/](dashboards/) directory. Import them into your Grafana instance to visualize:

- **Agent Overview** -- task counts, success rates, active agents
- **LLM Performance** -- latency distributions, token usage, cost per model
- **Tool Analytics** -- tool call frequency, success rates, error breakdown
- **Multi-Agent Traces** -- end-to-end trace visualization across agent boundaries

<!-- Screenshots will be added here once dashboards are finalized -->
```
dashboards/
  agent_overview.json
  llm_performance.json
  tool_analytics.json
```

## Project Structure

```
AgentTelemetry/
  src/agenttelemetry/
    core/
      trace.py          # AgentTracer, AgentSpan, AgentSpanKind
      metrics.py         # AgentMetrics, counters, histograms
      context.py         # AgentContext for multi-agent propagation
      events.py          # AgentEvent, EventType
    instrumentors/
      base.py            # BaseInstrumentor (abstract)
      langchain.py       # LangChain auto-instrumentation
      crewai.py          # CrewAI auto-instrumentation
      autogen.py         # AutoGen auto-instrumentation
      dspy.py            # DSPy auto-instrumentation
    exporters/
      console.py         # Print spans to stdout
      json_file.py       # Write spans to JSON Lines files
      otlp.py            # Export to OpenTelemetry backends
  examples/
    basic_usage.py
    multi_agent.py
    langchain_example.py
  dashboards/
    agent_overview.json
    llm_performance.json
    tool_analytics.json
  tests/
    test_core/
    test_instrumentors/
    test_exporters/
```

## Contributing

Contributions are welcome. To get started:

1. Fork the repository and create a feature branch.
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run the test suite:
   ```bash
   pytest
   ```
4. Submit a pull request with a clear description of the change.

Please follow the existing code style, add tests for new functionality, and update documentation as needed.

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for the full text.

## Citation

If you use AgentTelemetry in your research, please cite:

```bibtex
@software{agenttelemetry2025,
  title     = {AgentTelemetry: Unified Observability for Autonomous AI Agent Systems},
  author    = {AgentTelemetry Contributors},
  year      = {2025},
  url       = {https://github.com/agenttelemetry/agenttelemetry},
  license   = {Apache-2.0},
  note      = {An open-source observability SDK providing agent-native tracing,
               metrics, and auto-instrumentation for LLM-powered agent frameworks}
}
```
