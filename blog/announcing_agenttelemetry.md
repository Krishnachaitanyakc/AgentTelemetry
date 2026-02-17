# Your AI Agents Are Black Boxes. Here's How to Fix That.

You deployed an AI agent into production last week. It was supposed to research competitors, summarize findings, and draft a report. Instead, it burned through $47 in API calls, called the same tool nine times in a loop, and returned a hallucinated summary citing papers that do not exist.

You have no idea why.

You check the application logs. They show HTTP 200s to the OpenAI API. Your APM dashboard reports healthy latency. Your error rate is zero. And yet the agent failed catastrophically -- not at the infrastructure level, but at the *reasoning* level. The tools you rely on for observability were never designed to answer the question that actually matters: **what was the agent thinking, and why did it go wrong?**

This is the problem AgentTelemetry was built to solve.

## The Observability Gap for AI Agents

Traditional observability stacks -- metrics, logs, and distributed traces -- were engineered for deterministic request-response architectures. A web request enters a service, fans out to a database and a cache, and returns. The trace is a clean tree. Every span maps to a well-understood operation.

AI agents break this model in fundamental ways:

- **Non-deterministic control flow.** The same input can produce different execution paths depending on the LLM's reasoning, temperature settings, or even the time of day.
- **Opaque reasoning steps.** An agent might plan, reflect, revise its plan, and re-execute -- none of which maps to a traditional span kind like `CLIENT` or `SERVER`.
- **Multi-agent delegation.** When one agent delegates a sub-task to another agent, the trace context must propagate across what are effectively separate "services" that share no infrastructure boundary.
- **Cost as a first-class concern.** Unlike microservices, where compute cost is amortized, every LLM call has a direct, measurable dollar cost that operators need to track per-task, per-model, and per-agent.

OpenTelemetry is the right foundation for observability. But its current semantic conventions have no vocabulary for tasks, reasoning steps, planning phases, reflections, or inter-agent communication. Bolting agent telemetry onto generic spans produces traces that are technically correct but semantically useless.

## Introducing AgentTelemetry

AgentTelemetry is an open-source Python SDK that provides purpose-built observability for autonomous AI agent systems. It maps agent-native concepts directly to structured traces and metrics, giving you full visibility into what your agents are doing, why, and at what cost.

The core API is intentionally minimal:

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

Each `with` block creates a span with an agent-specific kind -- `task`, `llm_call`, `tool_call`, `planning`, `reasoning`, `reflection`, `retrieval`, `agent_comm`, or `human_input`. These are not arbitrary labels. They form a semantic vocabulary that makes agent traces immediately legible to both humans and automated analysis tools.

If you are already using LangChain, CrewAI, AutoGen, or DSPy, you do not need to modify your agent code at all. Drop-in auto-instrumentors capture telemetry automatically:

```python
from agenttelemetry.instrumentors.langchain import LangChainInstrumentor

instrumentor = LangChainInstrumentor(capture_content=False)
instrumentor.instrument()

# Use LangChain as usual -- telemetry is captured automatically
```

## Key Design Decisions

Three architectural choices define AgentTelemetry and distinguish it from existing tools.

### 1. Agent-Specific Span Kinds

OpenTelemetry defines five span kinds: `INTERNAL`, `SERVER`, `CLIENT`, `PRODUCER`, and `CONSUMER`. None of these capture the semantic distinction between an agent planning its approach, calling an LLM, invoking a tool, and reflecting on the quality of its output. AgentTelemetry introduces nine span kinds that map directly to the phases of agent execution:

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

This is not just a cosmetic difference. When you open a trace in Jaeger or Grafana Tempo and every span is labeled `INTERNAL`, you are doing archaeology. When spans are labeled `planning`, `llm_call`, `tool_call`, `reflection`, you are reading a narrative of what the agent did and why.

### 2. Privacy-First Content Capture

Prompts and completions contain sensitive data -- user queries, proprietary documents, personal information. AgentTelemetry disables content capture by default. Recording prompt and completion text requires an explicit opt-in (`capture_content=True`), making the safe behavior the default behavior. This is a deliberate departure from tools that log everything and expect you to redact later.

### 3. Zero-Dependency Core with an OTel Bridge

The core tracing and metrics engine has no external dependencies. You can `pip install agenttelemetry` and start tracing immediately with the console or JSON file exporter. OpenTelemetry is an *optional export target*, not a requirement. When you are ready to send traces to Jaeger, Grafana Tempo, or Datadog, install the `otlp` extra and AgentTelemetry maps its spans 1:1 to OTel spans. You get the full power of the OTel ecosystem without coupling your agent code to it.

## What the Output Looks Like

Running the included basic usage example (`python examples/basic_usage.py`) produces structured trace output showing every phase of agent execution. A simplified view of the metrics summary:

```
--- Metrics Summary ---

  counters:
    agent.task.count: 1
    agent.tool.call.count: 1
    agent.llm.call.count: 2

--- Cost Breakdown (from trace spans) ---

  llm_call [gpt-4o]               $0.004500  (500 in / 200 out)
  llm_call [gpt-4o-mini]          $0.000180  (450 in / 150 out)
  --------------------------------------------------
  TOTAL                            $0.004680  (950 in / 350 out)
```

For multi-agent scenarios, context propagation ensures that spans from cooperating agents share a single trace ID. The multi-agent example demonstrates a planner agent delegating sub-tasks to a researcher agent, with all spans appearing in a unified trace:

```
  Unique trace IDs: 1
    trace a1b2c3d4e5f6...  agents={'planner', 'researcher'}  spans=14
      [planner     ] task         Research and summarize breakthroughs...
      [planner     ] planning     decompose_task
      [planner     ] agent_comm   communicate: researcher
      [researcher  ] task         research: Find recent breakthroughs...
      [researcher  ] tool_call    web_search
      [researcher  ] llm_call     llm_call [gpt-4o-mini]
      ...
```

Every span carries structured attributes -- token counts, latencies, tool inputs and outputs, cost estimates -- that feed directly into the included Grafana dashboards for agent performance monitoring, cost analysis, and error tracking.

## The Research Context

AgentTelemetry emerged from a systematic analysis of the observability gap in AI agent systems. Existing frameworks -- LangSmith, Arize Phoenix, OpenLLMetry, Helicone, and others -- provide valuable capabilities, but none offers a unified, agent-native semantic model that covers the full lifecycle of autonomous agent execution. The accompanying research paper details the gap analysis, proposes the semantic conventions implemented here, and evaluates the design against real-world agent workloads.

## Get Started

AgentTelemetry is available now as an open-source project under the Apache 2.0 license.

**Install it:**

```bash
pip install agenttelemetry
```

**Try the examples:**

```bash
git clone https://github.com/Krishnachaitanyakc/AgentTelemetry.git
cd AgentTelemetry
pip install -e .
python examples/basic_usage.py
python examples/multi_agent.py
```

**Explore the repository:** [github.com/Krishnachaitanyakc/AgentTelemetry](https://github.com/Krishnachaitanyakc/AgentTelemetry)

Contributions are welcome -- whether it is adding an instrumentor for a new framework, improving the semantic conventions, building exporters for additional backends, or reporting issues you encounter in production. If this project is useful to you, a star on GitHub helps others find it.

AI agents are becoming infrastructure. It is time their observability caught up.
