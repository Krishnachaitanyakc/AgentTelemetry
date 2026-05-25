# Semantic Conventions for Autonomous AI Agent Workloads

> [!WARNING]
> Background draft only. Do not submit this document to OpenTelemetry.
>
> The `open-telemetry/oteps` repository is archived, and this document reflects
> an older umbrella strategy based on `agent.*`, `llm.*`, `tool.*`, and
> `agent.span_kind`. The active submission path is now a narrow PR to
> `open-telemetry/semantic-conventions`, starting with the minimal `plan`
> proposal described in `plan_span_pr_description.md` and `EXECUTION_PLAN.md`.

|||
|---|---|
| **OTEP** | NNNN (draft) |
| **Current Status** | Draft |
| **Authors** | AgentTelemetry Contributors |
| **Sponsoring SIG** | [Semantic Conventions SIG](https://github.com/open-telemetry/community#semantic-conventions-sig), [GenAI SIG](https://github.com/open-telemetry/community#genai-sig) |
| **Related OTEPs** | [OTEP 0248 (GenAI Semantic Conventions)](https://github.com/open-telemetry/oteps/blob/main/text/0248-genai-semconv.md) |
| **Created** | 2026-02-17 |

## Summary

This OTEP proposes semantic conventions for observing **autonomous AI agent workloads** within OpenTelemetry. It introduces:

1. A set of **agent-specific span attribute values** (via a new `agent.span_kind` attribute) that classify the distinct phases of agent execution: `TASK`, `REASONING`, `LLM_CALL`, `TOOL_CALL`, `PLANNING`, `REFLECTION`, `RETRIEVAL`, `AGENT_COMM`, and `HUMAN_INPUT`.

2. Standardized **semantic attribute namespaces** -- `agent.*`, `llm.*`, and `tool.*` -- covering agent identity, LLM invocation metadata (including cost and token usage), and tool invocation metadata.

3. A **context propagation extension** (`agentstate` header) that enables distributed tracing across multi-agent systems, carrying agent identity alongside the existing W3C `traceparent` header.

4. **Cost tracking conventions** (`llm.cost_usd`, `llm.input_tokens`, `llm.output_tokens`) that allow operators to monitor and attribute the financial cost of LLM usage within agent traces.

5. A set of **agent-specific event types** (`guardrail_triggered`, `cost_threshold`, `human_feedback`, etc.) that capture discrete occurrences within agent spans that have no direct analog in traditional service observability.

## Motivation

### The rise of autonomous agents

AI agents -- systems that use large language models to reason, plan, and act autonomously over multiple steps -- have become a dominant application architecture. Frameworks such as LangChain, LangGraph, CrewAI, AutoGen, OpenAI Agents SDK, and Anthropic's Claude Code are deployed in production at scale. Unlike traditional request/response LLM applications (single-turn chat completions), agents exhibit:

- **Multi-step reasoning**: A single user request may trigger dozens of LLM calls, tool invocations, and internal planning cycles before producing a result.
- **Non-deterministic execution paths**: The same input may traverse different sequences of reasoning, tool use, and retrieval depending on intermediate LLM outputs.
- **Multi-agent collaboration**: Multiple agents with distinct roles communicate, delegate tasks, and share context across process and network boundaries.
- **Cost accumulation**: A single agent task can consume hundreds of thousands of tokens across multiple model calls, with costs ranging from cents to tens of dollars per execution.
- **Human-in-the-loop interactions**: Many agent workflows pause for human approval, feedback, or correction at critical decision points.

### The observability gap

OpenTelemetry's existing GenAI semantic conventions ([OTEP 0248](https://github.com/open-telemetry/oteps/blob/main/text/0248-genai-semconv.md), the `gen_ai.*` namespace) address the observability needs of **individual LLM API calls** -- recording model name, token counts, and prompts/completions for a single inference request. However, they do not address the observability needs of the **agentic layer** that orchestrates those calls:

| Concern | Covered by GenAI SemConv? | Needed for Agents? |
|---|---|---|
| Which model was called and token usage | Yes | Yes |
| What reasoning step led to this LLM call | No | Yes |
| Why did the agent choose to invoke this tool | No | Yes |
| How did the agent decompose the task | No | Yes |
| What was the total cost of a multi-step task | No | Yes |
| Which agent delegated work to which other agent | No | Yes |
| Where did the agent pause for human input | No | Yes |
| How did the agent evaluate its own output | No | Yes |
| End-to-end trace across multiple cooperating agents | Partial (W3C context) | Yes (needs agent identity) |

Without standardized conventions for these concerns, every agent framework and observability vendor invents its own schema. This fragmentation means:

- **No interoperability**: Traces from a LangChain agent cannot be meaningfully correlated with traces from a CrewAI agent in the same pipeline.
- **No portable dashboards**: Operators cannot build vendor-neutral dashboards or alerts for agent cost, latency, and error rates.
- **No standard instrumentation**: Library authors must write custom exporters for each observability backend rather than targeting a single semantic contract.

### Goal

This OTEP closes the gap between "single LLM call" observability (GenAI SemConv) and "autonomous agent workflow" observability by proposing semantic conventions that capture the structure, cost, and coordination of multi-step, multi-agent AI workloads.

## Explanation

### Conceptual mapping

The proposal maps agent concepts to OpenTelemetry primitives as follows:

| Agent Concept | OTel Primitive | Description |
|---|---|---|
| Agent | Resource | An autonomous entity with a name, role, and framework |
| Agent Task | Trace | A complete end-to-end execution initiated by a user request |
| Execution Step | Span | One reasoning step, LLM call, tool invocation, or agent interaction |
| Step Category | `agent.span_kind` attribute | Classifies the type of work a span represents |
| Step-level Data | Span Attributes | Semantic attributes under `agent.*`, `llm.*`, `tool.*` |
| Discrete Occurrence | Span Event | Guardrail triggers, cost thresholds, human feedback |
| Cross-agent Link | Context Propagation | W3C `traceparent` + `agentstate` header |

### How it works for an operator

Consider an operator running a multi-agent customer support system. Agent A (router) receives a user query, reasons about which specialist to involve, and delegates to Agent B (billing specialist). Agent B calls an LLM to understand the billing issue, invokes a `lookup_account` tool, calls the LLM again to draft a response, and returns to Agent A.

With these conventions, the operator sees a single trace containing:

```
Trace: abc123
  [TASK] "Handle customer query"                    agent=router
    [REASONING] "Classify intent"                   agent=router
      [LLM_CALL] "llm.gpt-4o"                      llm.input_tokens=320, llm.cost_usd=0.004
    [PLANNING] "Route to specialist"                agent=router
    [AGENT_COMM] "comm.router->billing_specialist"  agent=router
      [TASK] "Resolve billing issue"                agent=billing_specialist
        [LLM_CALL] "llm.gpt-4o"                    llm.input_tokens=850, llm.cost_usd=0.012
        [TOOL_CALL] "tool.lookup_account"           tool.success=true, tool.latency_ms=45
        [REFLECTION] "Verify response accuracy"     agent=billing_specialist
          [LLM_CALL] "llm.gpt-4o"                  llm.input_tokens=400, llm.cost_usd=0.006
```

The operator can now:
- See the full execution path across both agents in a single trace view
- Sum `llm.cost_usd` across all `LLM_CALL` spans to get total task cost ($0.022)
- Alert on tasks where `TOOL_CALL` spans have `tool.success=false`
- Measure time spent in `REASONING` vs `TOOL_CALL` vs `LLM_CALL`
- Identify which agent contributed most to latency or cost

## Internal Details

### 1. Agent Span Kind Attribute

Rather than proposing new `SpanKind` enum values in the core OpenTelemetry specification (which would require changes to OTLP, all SDKs, and all backends), this proposal introduces a **semantic attribute** `agent.span_kind` that classifies the type of work an agent span represents.

#### Attribute: `agent.span_kind`

| Property | Value |
|---|---|
| **Type** | `string` |
| **Requirement Level** | Recommended |
| **Description** | Classifies the type of work performed by the agent in this span. |

##### Defined values for `agent.span_kind`

| Value | Description |
|---|---|
| `task` | Top-level task execution. Typically the root span of an agent trace. Represents the complete unit of work requested by a user or another agent. |
| `reasoning` | A reasoning or chain-of-thought step. The agent is processing information, drawing inferences, or constructing an internal argument. May or may not involve an LLM call. |
| `llm_call` | A call to a large language model for inference. This is the agent's primary "thinking" mechanism. The span SHOULD carry `llm.*` attributes. |
| `tool_call` | An invocation of an external tool, function, or API. The span SHOULD carry `tool.*` attributes. |
| `planning` | A task decomposition or planning step. The agent is breaking a complex task into sub-tasks, ordering steps, or constructing an execution plan. |
| `reflection` | A self-evaluation or critique step. The agent is assessing the quality, correctness, or completeness of its own previous output. |
| `retrieval` | A retrieval or RAG (Retrieval-Augmented Generation) step. The agent is fetching information from a knowledge base, vector store, or external data source to ground its reasoning. |
| `agent_comm` | An inter-agent communication step. The agent is sending a message to, receiving a message from, or delegating a task to another agent. |
| `human_input` | A human-in-the-loop interaction. The agent is requesting input, approval, or feedback from a human operator. |

#### Span naming conventions

Spans SHOULD follow these naming patterns:

| `agent.span_kind` | Span Name Pattern | Example |
|---|---|---|
| `task` | `{task_description}` | `"Handle customer query"` |
| `reasoning` | `reasoning` or `{description}` | `"Classify intent"` |
| `llm_call` | `llm.{model_name}` | `"llm.gpt-4o"` |
| `tool_call` | `tool.{tool_name}` | `"tool.web_search"` |
| `planning` | `planning` or `{description}` | `"Decompose research task"` |
| `reflection` | `reflection` or `{description}` | `"Verify response accuracy"` |
| `retrieval` | `retrieval` or `{description}` | `"Search knowledge base"` |
| `agent_comm` | `comm.{source}->{target}` | `"comm.router->specialist"` |
| `human_input` | `human_input` or `{description}` | `"Await approval"` |

### 2. Semantic Attribute Conventions

#### 2.1 Agent Attributes (`agent.*`)

These attributes identify the agent and its execution context. They SHOULD be set on all spans produced by agent instrumentation.

| Attribute | Type | Req. Level | Description |
|---|---|---|---|
| `agent.name` | `string` | **Required** | The logical name of the agent (e.g., `"researcher"`, `"code_reviewer"`). |
| `agent.framework` | `string` | Recommended | The agent framework in use (e.g., `"langchain"`, `"crewai"`, `"autogen"`, `"custom"`). |
| `agent.framework.version` | `string` | Recommended | The version of the agent framework. |
| `agent.role` | `string` | Recommended | The role or persona assigned to the agent (e.g., `"senior_researcher"`, `"qa_engineer"`). |
| `agent.task` | `string` | Recommended | A human-readable description of the top-level task being executed. |
| `agent.interaction.type` | `string` | Conditionally Required [1] | The type of inter-agent interaction (e.g., `"delegation"`, `"broadcast"`, `"request_response"`). |
| `agent.interaction.source_agent` | `string` | Conditionally Required [1] | The `agent.name` of the agent initiating the interaction. |
| `agent.interaction.target_agent` | `string` | Conditionally Required [1] | The `agent.name` of the agent receiving the interaction. |

[1] Required when `agent.span_kind` is `agent_comm`.

#### 2.2 LLM Attributes (`llm.*`)

These attributes describe a call to a large language model. They SHOULD be set on spans where `agent.span_kind` is `llm_call`, and MAY be set on other spans that internally invoke an LLM (e.g., `reasoning` or `reflection` spans that wrap an LLM call).

| Attribute | Type | Req. Level | Description |
|---|---|---|---|
| `llm.model` | `string` | **Required** | The model identifier (e.g., `"gpt-4o"`, `"claude-3-5-sonnet"`). |
| `llm.provider` | `string` | Recommended | The model provider or API endpoint (e.g., `"openai"`, `"anthropic"`, `"azure_openai"`). |
| `llm.input_tokens` | `int` | Recommended | Number of input (prompt) tokens consumed by the call. |
| `llm.output_tokens` | `int` | Recommended | Number of output (completion) tokens generated by the call. |
| `llm.total_tokens` | `int` | Recommended | Total tokens consumed (`input_tokens + output_tokens`). |
| `llm.temperature` | `double` | Opt-In | The temperature parameter used for generation. |
| `llm.cost_usd` | `double` | Recommended | The estimated or actual cost of the LLM call in US dollars. |
| `llm.latency_ms` | `double` | Recommended | The wall-clock latency of the LLM call in milliseconds. |
| `llm.prompt` | `string` | Opt-In | The full prompt text sent to the model. **Privacy-sensitive; MUST be opt-in.** |
| `llm.completion` | `string` | Opt-In | The full completion text returned by the model. **Privacy-sensitive; MUST be opt-in.** |

##### Relationship to existing `gen_ai.*` conventions

The existing OpenTelemetry GenAI semantic conventions use the `gen_ai.*` namespace (e.g., `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`). This proposal uses a shorter `llm.*` namespace that is designed specifically for the agent context. Implementations SHOULD support mapping between the two namespaces:

| This Proposal (`llm.*`) | GenAI SemConv (`gen_ai.*`) |
|---|---|
| `llm.model` | `gen_ai.request.model` |
| `llm.provider` | `gen_ai.system` |
| `llm.input_tokens` | `gen_ai.usage.input_tokens` |
| `llm.output_tokens` | `gen_ai.usage.output_tokens` |
| `llm.temperature` | `gen_ai.request.temperature` |
| `llm.prompt` | (captured via `gen_ai.content.prompt` event) |
| `llm.completion` | (captured via `gen_ai.content.completion` event) |
| `llm.cost_usd` | *No equivalent* -- new in this proposal |
| `llm.latency_ms` | *No equivalent* (derivable from span duration) |

Instrumentations MAY emit both namespaces during a transition period. The long-term resolution of namespace convergence is deferred to the GenAI SIG.

#### 2.3 Tool Attributes (`tool.*`)

These attributes describe a tool or function invocation. They SHOULD be set on spans where `agent.span_kind` is `tool_call`.

| Attribute | Type | Req. Level | Description |
|---|---|---|---|
| `tool.name` | `string` | **Required** | The name of the tool or function invoked (e.g., `"web_search"`, `"code_interpreter"`). |
| `tool.description` | `string` | Recommended | A human-readable description of what the tool does. |
| `tool.input` | `string` | Opt-In | The input (arguments) passed to the tool. **May be privacy-sensitive.** |
| `tool.output` | `string` | Opt-In | The output (return value) of the tool. **May be privacy-sensitive.** |
| `tool.success` | `boolean` | Recommended | Whether the tool invocation succeeded. |
| `tool.error` | `string` | Conditionally Required [2] | Error message if the tool invocation failed. |
| `tool.latency_ms` | `double` | Recommended | The wall-clock latency of the tool invocation in milliseconds. |

[2] Required when `tool.success` is `false`.

### 3. Span Events

Agent spans MAY record events that capture discrete occurrences during execution. The following event types are defined:

| Event Name | Description | Applicable `agent.span_kind` |
|---|---|---|
| `llm_start` | Marks the beginning of an LLM inference request. | `llm_call` |
| `llm_end` | Marks the completion of an LLM inference request. | `llm_call` |
| `llm_stream_chunk` | A single chunk received during streaming LLM output. | `llm_call` |
| `tool_start` | Marks the beginning of a tool invocation. | `tool_call` |
| `tool_end` | Marks the completion of a tool invocation. | `tool_call` |
| `agent_start` | Marks the beginning of an agent's task execution. | `task` |
| `agent_end` | Marks the completion of an agent's task execution. | `task` |
| `agent_message` | An inter-agent message was sent or received. | `agent_comm` |
| `planning_start` | Marks the beginning of a planning phase. | `planning` |
| `planning_end` | Marks the completion of a planning phase. | `planning` |
| `retrieval_hit` | A relevant document or chunk was retrieved. | `retrieval` |
| `human_feedback` | Human feedback was received. | `human_input` |
| `error` | An error occurred during span execution. | Any |
| `warning` | A non-fatal warning occurred. | Any |
| `guardrail_triggered` | A safety guardrail (content filter, output validator) was triggered. | Any |
| `cost_threshold` | A cost threshold or budget limit was reached. | Any |

#### Event attributes

Events SHOULD carry relevant attributes. For example:

- `guardrail_triggered` events SHOULD include `guardrail.name`, `guardrail.action` (`"block"`, `"warn"`, `"log"`), and `guardrail.reason`.
- `cost_threshold` events SHOULD include `cost.threshold_usd`, `cost.current_usd`, and `cost.action` (`"warn"`, `"stop"`).
- `retrieval_hit` events SHOULD include `retrieval.source`, `retrieval.score`, and `retrieval.document_id`.
- `human_feedback` events SHOULD include `feedback.type` (`"approval"`, `"rejection"`, `"correction"`) and optionally `feedback.content`.

### 4. Context Propagation for Multi-Agent Systems

#### Problem

In multi-agent systems, agents communicate via messages, HTTP calls, queues, or shared memory. For an operator to see a unified end-to-end trace that spans multiple agents, trace context must propagate across agent boundaries.

The W3C `traceparent` header provides trace ID and parent span ID propagation. However, multi-agent systems have an additional requirement: the **receiving agent needs to know which agent sent the context** so it can set `agent.interaction.source_agent` correctly.

#### Proposed extension: `agentstate` header

This proposal introduces a new propagation header, `agentstate`, that carries agent identity metadata alongside the standard `traceparent` header.

##### Header format

```
agentstate: {source_agent_name}
```

The value is the `agent.name` of the agent that is propagating the context. It is a simple string value.

##### Full carrier format

When an agent propagates context to another agent, the carrier (e.g., HTTP headers, message metadata) contains:

```
traceparent: 00-{trace_id}-{parent_span_id}-01
agentstate: {source_agent_name}
baggage: key1=value1,key2=value2
```

- `traceparent`: Standard W3C Trace Context header. Unchanged.
- `agentstate`: New header. Carries the name of the source agent.
- `baggage`: Standard W3C Baggage header. Can carry additional agent metadata (e.g., `agent.role`, `agent.task`). Unchanged.

##### Serialization and deserialization

**Producing agent (serialization):**

```python
carrier = {
    "traceparent": f"00-{trace_id}-{parent_span_id}-01",
    "agentstate": source_agent_name,
}
# Optionally include baggage
if baggage:
    carrier["baggage"] = ",".join(f"{k}={v}" for k, v in baggage.items())
```

**Consuming agent (deserialization):**

```python
# Parse traceparent
parts = carrier["traceparent"].split("-")
trace_id = parts[1]
parent_span_id = parts[2]

# Parse agentstate
source_agent = carrier.get("agentstate", "")

# Create child spans with the received trace_id and parent_span_id
# Set agent.interaction.source_agent = source_agent
```

##### Relationship to W3C Trace Context

The `agentstate` header is designed to be **complementary** to W3C Trace Context, not a replacement. It follows the same carrier pattern (HTTP headers or message metadata) and does not modify the semantics of `traceparent` or `tracestate`.

If the OpenTelemetry specification later adopts a more general mechanism for propagating actor/service identity (e.g., via `tracestate` vendor keys), the `agentstate` header can be deprecated in favor of that mechanism.

### 5. Cost Tracking Conventions

#### Rationale

LLM inference is a metered resource. Unlike traditional compute (where CPU and memory costs are amortized and indirect), every LLM call has a direct, measurable cost that operators need to track, attribute, and control.

#### Attribute: `llm.cost_usd`

| Property | Value |
|---|---|
| **Type** | `double` |
| **Requirement Level** | Recommended |
| **Description** | The estimated or actual cost of the LLM call in US dollars. |

##### Cost calculation

The cost MAY be calculated by the instrumentation library using published model pricing:

```
cost_usd = (input_tokens * input_price_per_million / 1,000,000)
         + (output_tokens * output_price_per_million / 1,000,000)
```

Alternatively, if the LLM provider returns cost information in the API response (e.g., via response headers or metadata), that value SHOULD be used instead of an estimate.

##### Aggregation

Operators can compute the total cost of an agent task by summing `llm.cost_usd` across all `llm_call` spans within a trace:

```
total_task_cost = SUM(llm.cost_usd) WHERE trace_id = X AND agent.span_kind = "llm_call"
```

##### Currency

This proposal uses US dollars (USD) as the standard currency for cost reporting. This aligns with the pricing conventions of all major LLM providers (OpenAI, Anthropic, Google, Cohere, Mistral). If a provider prices in a different currency, the instrumentation SHOULD convert to USD using the exchange rate at the time of the call.

### 6. Span Status

Agent spans use the standard OpenTelemetry `StatusCode` enum (`UNSET`, `OK`, `ERROR`). This proposal adds guidance for an additional status value that instrumentations MAY report via a span attribute:

| Attribute | Type | Description |
|---|---|---|
| `agent.status` | `string` | Extended status for agent spans. Values: `unset`, `ok`, `error`, `timeout`. |

The `timeout` value indicates that the span exceeded a configured time limit. This is common in agent workloads where LLM calls or tool invocations may hang or take unexpectedly long. When `agent.status` is `timeout`, the standard OTel `StatusCode` SHOULD be set to `ERROR` with a descriptive `Status.description`.

### 7. Resource Attributes

Agent identity SHOULD also be recorded as resource attributes on the `Resource` associated with the TracerProvider:

| Attribute | Type | Description |
|---|---|---|
| `agent.name` | `string` | The logical name of the agent. |
| `agent.framework` | `string` | The agent framework (e.g., `"langchain"`, `"crewai"`). |
| `agent.framework.version` | `string` | The version of the agent framework. |

This enables backend systems to group and filter traces by agent identity without inspecting individual span attributes.

## Trade-offs and Mitigations

### Why not just use existing GenAI semantic conventions?

The existing `gen_ai.*` semantic conventions address the observability of **individual LLM API calls**. They model a single inference request with its prompt, completion, token usage, and model parameters. They are necessary but not sufficient for agent observability.

Agent workloads introduce concerns that have no analog in single-call GenAI instrumentation:

- **Execution structure**: Agents have multi-step execution with reasoning, planning, and reflection phases that must be captured as distinct spans.
- **Tool orchestration**: Agents invoke external tools as part of their execution loop; these are not LLM calls but are critical to trace completeness.
- **Multi-agent coordination**: Agents delegate to and communicate with other agents, requiring trace context propagation with agent identity.
- **Cost accumulation**: The total cost of an agent task is the sum of many LLM calls, which must be aggregable.
- **Human-in-the-loop**: Agents may pause for human input, which is a fundamentally different kind of span.

This proposal is designed to **layer on top of** the existing GenAI conventions, not replace them. An `llm_call` span under these conventions can (and should) also carry `gen_ai.*` attributes.

### Why `agent.span_kind` attribute instead of new OTel `SpanKind` values?

Adding new values to the core `SpanKind` enum would require:

1. Changes to the OTLP protobuf definitions
2. Changes to every language SDK
3. Changes to every backend (Jaeger, Zipkin, Tempo, etc.)
4. A lengthy specification process with high bar for consensus

Using a semantic attribute (`agent.span_kind`) achieves the same classification capability without any changes to the core specification or SDKs. Backends that want to render agent spans differently can key on this attribute.

**Mitigation**: If agent workloads become prevalent enough to warrant core `SpanKind` values, this attribute provides a well-tested design that can inform a future core specification change.

### Why `llm.*` instead of `gen_ai.*`?

The shorter `llm.*` namespace is more concise and ergonomic for the agent context where LLM attributes are set frequently. However, this creates a namespace divergence with the existing `gen_ai.*` conventions.

**Mitigation**: This proposal includes a full mapping table between `llm.*` and `gen_ai.*` and recommends that instrumentations support both during a transition period. The long-term namespace resolution is an open question for the GenAI SIG.

### Why a new `agentstate` header instead of using W3C `tracestate`?

W3C `tracestate` is designed for vendor-specific key-value pairs and has strict formatting requirements. Using it for agent identity would require defining a vendor key (e.g., `otel-agent=router`) and would be subject to the 512-byte limit and key-ordering rules of `tracestate`.

The `agentstate` header is simpler and purpose-built for the agent use case. It carries a single value (the source agent name) with no formatting complexity.

**Mitigation**: If the OTel specification evolves a general-purpose actor identity mechanism (e.g., via `tracestate` or a new propagation field), `agentstate` can be deprecated.

### Privacy concerns with `llm.prompt` and `llm.completion`

Full prompt and completion text can contain sensitive user data. This proposal marks these attributes as **Opt-In** and requires that instrumentations default to NOT capturing them. The `capture_content` flag pattern (used in the reference implementation) provides a clear opt-in mechanism.

### Cost estimation accuracy

The `llm.cost_usd` attribute may be an estimate based on published pricing, which can become stale as providers change prices. Estimates also may not account for discounts, commitments, or batch pricing.

**Mitigation**: The attribute description explicitly allows for both "estimated" and "actual" costs. Instrumentations SHOULD prefer actual costs from provider responses when available.

## Prior Art and Alternatives

### AgentTelemetry (reference implementation)

The semantic conventions in this proposal are derived from the [AgentTelemetry](https://github.com/AgentTelemetry) project, which implements a standalone agent tracing library with OTel-compatible export. AgentTelemetry defines the `AgentSpanKind` enum, the `agent.*` / `llm.*` / `tool.*` attribute namespaces, the `agentstate` propagation header, and cost tracking, and has been validated against LangChain, CrewAI, and custom agent implementations.

### LangSmith (LangChain)

[LangSmith](https://smith.langchain.com/) provides tracing and evaluation for LangChain applications. It uses a proprietary schema with "run types" (`llm`, `chain`, `tool`, `retriever`) that are conceptually similar to `agent.span_kind` values. LangSmith captures token usage and cost but uses a LangChain-specific data model that is not interoperable with other frameworks.

### Arize Phoenix

[Arize Phoenix](https://phoenix.arize.com/) provides LLM observability with OpenTelemetry-based tracing. It uses `openinference` semantic conventions with span kinds like `LLM`, `CHAIN`, `TOOL`, `RETRIEVER`, `AGENT`, `RERANKER`, and `EMBEDDING`. The `openinference` conventions influenced this proposal's attribute design but use a different namespace structure.

### Braintrust

[Braintrust](https://www.braintrust.dev/) provides AI application logging and evaluation. It captures LLM calls, tool invocations, and costs using a proprietary schema with "span types" and nested function calls. Braintrust's cost tracking model informed the `llm.cost_usd` design.

### OpenLLMetry (Traceloop)

[OpenLLMetry](https://github.com/traceloop/openllmetry) provides OpenTelemetry-based instrumentation for LLM applications. It uses the `gen_ai.*` namespace from the OTel GenAI semantic conventions and adds workflow-level concepts. OpenLLMetry demonstrates the value of OTel-native LLM instrumentation but does not address multi-agent coordination or agent-specific span classification.

### AgentOps

[AgentOps](https://www.agentops.ai/) provides agent observability with session-based tracing. It captures agent "events" (LLM calls, tool calls, errors) and provides cost tracking. AgentOps uses a proprietary event model that does not map to OTel spans.

### OpenInference (Arize)

The [OpenInference](https://github.com/Arize-ai/openinference) specification defines semantic conventions for AI observability built on OpenTelemetry. It introduces span kinds (`LLM`, `CHAIN`, `TOOL`, `RETRIEVER`, `EMBEDDING`, `AGENT`, `RERANKER`, `GUARDRAIL`) and attributes under `input.*`, `output.*`, `llm.*`, `retrieval.*` namespaces. OpenInference is the closest prior art to this proposal and has informed several design decisions.

Key differences from this proposal:

| Aspect | OpenInference | This Proposal |
|---|---|---|
| Span classification | Custom `OpenInferenceSpanKind` enum | `agent.span_kind` string attribute |
| Planning/Reflection | Not distinguished | Explicit `planning` and `reflection` kinds |
| Multi-agent | Not addressed | `agent_comm` kind + `agentstate` propagation |
| Human-in-the-loop | Not addressed | Explicit `human_input` kind |
| Cost tracking | Not standardized | `llm.cost_usd` attribute |
| Guardrail events | `GUARDRAIL` span kind | `guardrail_triggered` event type |

## Open Questions

### 1. Namespace convergence with `gen_ai.*`

Should the `llm.*` attributes proposed here ultimately be merged into the `gen_ai.*` namespace, or should they remain a separate, agent-focused namespace? The `gen_ai.*` conventions use verbose qualified names (e.g., `gen_ai.usage.input_tokens`) while the `llm.*` conventions use shorter flat names (e.g., `llm.input_tokens`). A resolution requires input from the GenAI SIG.

### 2. `agentstate` header formalization

Should the `agentstate` header carry additional metadata beyond agent name (e.g., agent role, framework)? Should it use a structured format (e.g., `name=router;role=coordinator;framework=langchain`)? Or should this metadata be carried exclusively in W3C Baggage?

### 3. Span kind granularity

Are the proposed `agent.span_kind` values the right level of granularity? Some frameworks may distinguish between different types of reasoning (e.g., "deductive reasoning" vs. "analogical reasoning") or different types of tool calls (e.g., "read tool" vs. "write tool"). Should the conventions support sub-classification via additional attributes?

### 4. Cost tracking currency and precision

Is USD the right default currency? Should `llm.cost_usd` be a `double` (risking floating-point precision issues for aggregation) or should it be an integer representing micro-dollars or milli-dollars?

### 5. Streaming LLM calls

For streaming LLM responses, should token counts and cost be updated incrementally (via span events or span attribute updates) or only set once at stream completion? The `llm_stream_chunk` event type supports incremental reporting, but many backends do not support mutable span attributes.

### 6. Agent lifecycle spans

Should there be conventions for agent lifecycle events that are not part of a specific task? For example, agent initialization, model loading, tool registration, and shutdown. These are analogous to service startup/shutdown spans in traditional observability.

### 7. Evaluation and scoring

Many agent frameworks include evaluation steps where the output is scored (e.g., by another LLM acting as a judge, or by a human rater). Should there be semantic conventions for evaluation spans and scoring attributes (e.g., `evaluation.score`, `evaluation.criteria`, `evaluation.judge_model`)?

### 8. Memory and state

Agents often maintain memory (conversation history, working memory, long-term memory). Should there be conventions for tracking memory operations (e.g., `memory.read`, `memory.write`, `memory.size_tokens`)?

## Future Possibilities

### Metrics semantic conventions

This OTEP focuses on trace-based conventions. A natural follow-up would define **metrics** semantic conventions for agent workloads:

- `agent.task.duration` (histogram) -- End-to-end task latency
- `agent.task.cost_usd` (histogram) -- Total cost per task
- `agent.llm_calls.count` (counter) -- Number of LLM calls per task
- `agent.tool_calls.count` (counter) -- Number of tool calls per task
- `agent.tool_calls.error_rate` (gauge) -- Tool call failure rate
- `agent.tokens.total` (counter) -- Total tokens consumed
- `agent.human_input.wait_time` (histogram) -- Time waiting for human input

### Log semantic conventions

Agent frameworks produce rich structured logs (reasoning traces, intermediate outputs, decision justifications). Conventions for mapping these to OpenTelemetry Logs with agent-specific attributes would complement the trace conventions.

### Profiling integration

OpenTelemetry Profiling could be extended to capture agent-level profiling data, such as:

- Time distribution across span kinds (what fraction of time is spent in LLM calls vs. tool calls vs. reasoning?)
- Token consumption profiles (which reasoning steps are most token-intensive?)
- Cost profiles (which tools or models are most expensive?)

### Agent benchmarking and evaluation

Standardized telemetry enables standardized benchmarking. Future conventions could define how to record evaluation results, benchmark scores, and regression test outcomes as part of agent traces, enabling CI/CD-integrated agent quality monitoring.

### Multi-modal agents

As agents incorporate vision, audio, and other modalities, the conventions may need to be extended to capture modality-specific attributes (e.g., `llm.input_images`, `llm.audio_duration_seconds`).

### Agent-to-agent protocol standardization

The `agentstate` propagation mechanism is a minimal starting point. As multi-agent systems become more sophisticated, a richer agent-to-agent protocol (carrying capabilities, trust levels, delegation policies) may be needed. This could build on the context propagation foundation established here.

### Integration with AI safety and governance

The `guardrail_triggered` event type is a starting point for safety observability. Future conventions could define standard attributes for content safety classifications, model behavior auditing, and compliance reporting.

---

## Appendix A: Complete Attribute Reference

### Agent Namespace (`agent.*`)

| Attribute | Type | Req. Level | Description |
|---|---|---|---|
| `agent.name` | `string` | Required | Logical name of the agent |
| `agent.framework` | `string` | Recommended | Agent framework name |
| `agent.framework.version` | `string` | Recommended | Agent framework version |
| `agent.role` | `string` | Recommended | Agent role or persona |
| `agent.task` | `string` | Recommended | Top-level task description |
| `agent.span_kind` | `string` | Recommended | Type of work: `task`, `reasoning`, `llm_call`, `tool_call`, `planning`, `reflection`, `retrieval`, `agent_comm`, `human_input` |
| `agent.status` | `string` | Recommended | Extended status: `unset`, `ok`, `error`, `timeout` |
| `agent.interaction.type` | `string` | Cond. Required | Inter-agent interaction type |
| `agent.interaction.source_agent` | `string` | Cond. Required | Source agent name |
| `agent.interaction.target_agent` | `string` | Cond. Required | Target agent name |

### LLM Namespace (`llm.*`)

| Attribute | Type | Req. Level | Description |
|---|---|---|---|
| `llm.model` | `string` | Required | Model identifier |
| `llm.provider` | `string` | Recommended | Model provider |
| `llm.input_tokens` | `int` | Recommended | Input (prompt) tokens |
| `llm.output_tokens` | `int` | Recommended | Output (completion) tokens |
| `llm.total_tokens` | `int` | Recommended | Total tokens consumed |
| `llm.temperature` | `double` | Opt-In | Generation temperature |
| `llm.cost_usd` | `double` | Recommended | Cost in US dollars |
| `llm.latency_ms` | `double` | Recommended | Call latency in milliseconds |
| `llm.prompt` | `string` | Opt-In | Full prompt text (privacy-sensitive) |
| `llm.completion` | `string` | Opt-In | Full completion text (privacy-sensitive) |

### Tool Namespace (`tool.*`)

| Attribute | Type | Req. Level | Description |
|---|---|---|---|
| `tool.name` | `string` | Required | Tool or function name |
| `tool.description` | `string` | Recommended | Tool description |
| `tool.input` | `string` | Opt-In | Tool input/arguments (privacy-sensitive) |
| `tool.output` | `string` | Opt-In | Tool output/return value (privacy-sensitive) |
| `tool.success` | `boolean` | Recommended | Whether invocation succeeded |
| `tool.error` | `string` | Cond. Required | Error message on failure |
| `tool.latency_ms` | `double` | Recommended | Invocation latency in milliseconds |

## Appendix B: Context Propagation Wire Format

### Carrier example (HTTP headers)

```http
POST /agent/billing_specialist/task HTTP/1.1
Host: agents.example.com
Content-Type: application/json
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
agentstate: router
baggage: agent.role=coordinator,agent.task=handle_billing_query

{"message": "Please resolve the billing issue for account #12345"}
```

### Carrier example (message queue metadata)

```json
{
  "headers": {
    "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    "agentstate": "router",
    "baggage": "agent.role=coordinator,agent.task=handle_billing_query"
  },
  "body": {
    "message": "Please resolve the billing issue for account #12345"
  }
}
```

## Appendix C: Example Trace (JSON)

The following is a simplified JSON representation of spans from a multi-agent trace, showing the proposed attributes:

```json
[
  {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "a1b2c3d4e5f60001",
    "parent_span_id": null,
    "name": "Handle customer query",
    "kind": "SPAN_KIND_INTERNAL",
    "status": {"code": "STATUS_CODE_OK"},
    "start_time_unix_nano": 1708185600000000000,
    "end_time_unix_nano": 1708185612000000000,
    "attributes": {
      "agent.name": "router",
      "agent.framework": "langchain",
      "agent.framework.version": "0.3.1",
      "agent.span_kind": "task",
      "agent.task": "Handle customer query"
    }
  },
  {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "a1b2c3d4e5f60002",
    "parent_span_id": "a1b2c3d4e5f60001",
    "name": "Classify intent",
    "kind": "SPAN_KIND_INTERNAL",
    "status": {"code": "STATUS_CODE_OK"},
    "attributes": {
      "agent.name": "router",
      "agent.span_kind": "reasoning"
    }
  },
  {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "a1b2c3d4e5f60003",
    "parent_span_id": "a1b2c3d4e5f60002",
    "name": "llm.gpt-4o",
    "kind": "SPAN_KIND_CLIENT",
    "status": {"code": "STATUS_CODE_OK"},
    "attributes": {
      "agent.name": "router",
      "agent.span_kind": "llm_call",
      "llm.model": "gpt-4o",
      "llm.provider": "openai",
      "llm.input_tokens": 320,
      "llm.output_tokens": 45,
      "llm.total_tokens": 365,
      "llm.cost_usd": 0.00125,
      "llm.latency_ms": 890
    }
  },
  {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "a1b2c3d4e5f60004",
    "parent_span_id": "a1b2c3d4e5f60001",
    "name": "comm.router->billing_specialist",
    "kind": "SPAN_KIND_PRODUCER",
    "status": {"code": "STATUS_CODE_OK"},
    "attributes": {
      "agent.name": "router",
      "agent.span_kind": "agent_comm",
      "agent.interaction.type": "delegation",
      "agent.interaction.source_agent": "router",
      "agent.interaction.target_agent": "billing_specialist"
    }
  },
  {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "a1b2c3d4e5f60005",
    "parent_span_id": "a1b2c3d4e5f60004",
    "name": "Resolve billing issue",
    "kind": "SPAN_KIND_INTERNAL",
    "status": {"code": "STATUS_CODE_OK"},
    "attributes": {
      "agent.name": "billing_specialist",
      "agent.framework": "crewai",
      "agent.span_kind": "task",
      "agent.task": "Resolve billing issue"
    }
  },
  {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "a1b2c3d4e5f60006",
    "parent_span_id": "a1b2c3d4e5f60005",
    "name": "tool.lookup_account",
    "kind": "SPAN_KIND_CLIENT",
    "status": {"code": "STATUS_CODE_OK"},
    "attributes": {
      "agent.name": "billing_specialist",
      "agent.span_kind": "tool_call",
      "tool.name": "lookup_account",
      "tool.success": true,
      "tool.latency_ms": 45.2
    }
  },
  {
    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
    "span_id": "a1b2c3d4e5f60007",
    "parent_span_id": "a1b2c3d4e5f60005",
    "name": "Verify response accuracy",
    "kind": "SPAN_KIND_INTERNAL",
    "status": {"code": "STATUS_CODE_OK"},
    "attributes": {
      "agent.name": "billing_specialist",
      "agent.span_kind": "reflection"
    },
    "events": [
      {
        "name": "guardrail_triggered",
        "time_unix_nano": 1708185610500000000,
        "attributes": {
          "guardrail.name": "pii_filter",
          "guardrail.action": "warn",
          "guardrail.reason": "Response may contain account number"
        }
      }
    ]
  }
]
```
