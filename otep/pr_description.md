## OTEP: Semantic Conventions for AI Agent Observability

### Summary

This OTEP proposes **semantic conventions for observing autonomous AI agent workloads** within OpenTelemetry. As AI agents -- systems that use large language models to reason, plan, and act autonomously over multiple steps -- become a dominant application architecture, the observability gap between "single LLM call" instrumentation and "multi-step agent workflow" observability has become critical.

This proposal introduces:

- **Agent-specific span classification** via a new `agent.span_kind` attribute with values for task execution, reasoning, LLM calls, tool invocations, planning, reflection, retrieval, inter-agent communication, and human-in-the-loop interactions
- **Standardized attribute namespaces** (`agent.*`, `llm.*`, `tool.*`) covering agent identity, LLM invocation metadata, and tool invocation metadata
- **Cost tracking conventions** (`llm.cost_usd`) enabling operators to monitor and attribute the financial cost of LLM usage across multi-step agent traces
- **Context propagation extension** (`agentstate` header) for distributed tracing across multi-agent systems
- **Agent-specific event types** (`guardrail_triggered`, `cost_threshold`, `human_feedback`, etc.) for discrete occurrences within agent execution

### Motivation

OpenTelemetry's existing GenAI semantic conventions ([OTEP 0248](https://github.com/open-telemetry/oteps/blob/main/text/0248-genai-semconv.md)) address observability for individual LLM API calls. However, they do not address the observability needs of the **agentic orchestration layer** -- the multi-step reasoning, tool invocation, task decomposition, multi-agent coordination, and cost accumulation that define agent workloads.

Without standardized conventions for agent observability:
- Traces from different agent frameworks (LangChain, CrewAI, AutoGen, etc.) cannot be correlated or compared
- Operators cannot build vendor-neutral dashboards for agent cost, latency, and error rates
- Instrumentation library authors must write custom exporters for each observability backend

This OTEP closes the gap by proposing conventions that capture the **structure, cost, and coordination** of multi-step, multi-agent AI workloads.

### Design Approach

The proposal maps agent concepts to existing OpenTelemetry primitives (Resources, Traces, Spans, Span Events, Context Propagation) without requiring changes to the core OTel specification, OTLP, or any SDK. Agent span classification is achieved via a semantic attribute (`agent.span_kind`) rather than new `SpanKind` enum values.

### Reference Implementation

- **AgentTelemetry**: [https://github.com/AgentTelemetry](https://github.com/AgentTelemetry) -- A standalone Python library implementing these conventions with OTel-compatible export. Validated against LangChain, CrewAI, and custom agent implementations.

### Research Paper

- **Zenodo DOI**: *[Insert DOI link when published]* -- Academic paper presenting the design rationale, evaluation methodology, and empirical results.

### Relationship to Existing Work

This OTEP is designed to **layer on top of** the existing GenAI semantic conventions (OTEP 0248), not replace them. An `llm_call` span under these conventions can and should also carry `gen_ai.*` attributes. The proposal includes a full mapping table between the proposed `llm.*` namespace and the existing `gen_ai.*` namespace.

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `agent.span_kind` attribute instead of new `SpanKind` enum values | Avoids changes to OTLP, SDKs, and backends |
| Nine span kind values (task, reasoning, llm_call, tool_call, planning, reflection, retrieval, agent_comm, human_input) | Covers the full agent execution lifecycle observed across major frameworks |
| `llm.cost_usd` as a first-class attribute | LLM cost is a metered resource unlike traditional compute |
| `agentstate` propagation header | Enables agent identity propagation across multi-agent boundaries |
| Privacy-sensitive attributes (prompt, completion, tool I/O) as Opt-In | Aligns with OTel privacy principles |

### Request for Feedback

We are seeking feedback from the OpenTelemetry community on:

1. **Namespace design**: Should agent-related LLM attributes use `llm.*` or be integrated into the existing `gen_ai.*` namespace?
2. **Span kind granularity**: Are the nine proposed `agent.span_kind` values the right level of classification?
3. **Context propagation**: Is a dedicated `agentstate` header the right approach, or should agent identity be carried via W3C `tracestate` or Baggage?
4. **Cost tracking**: Is `llm.cost_usd` (double, USD) the right representation for cost data?
5. **Scope**: Should this be one OTEP or split into multiple proposals (core attributes, cost tracking, propagation)?

We welcome discussion on this PR, in `#otel-genai` on CNCF Slack, and at upcoming Semantic Conventions SIG and GenAI SIG meetings.

---

cc @open-telemetry/specs-semconv-approvers @open-telemetry/semconv-genai-approvers
