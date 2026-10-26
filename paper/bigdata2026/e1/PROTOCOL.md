# E1: Structural visibility in traces emitted by real instrumentation libraries

This protocol is written and committed before any agent run.

## Question

The submitted paper measured query answerability on *projections*: event fields
were retained or removed by hand according to its Table III. E1 asks the same
question of traces that real, unmodified instrumentation libraries emit for the
same agent executions:

> For each of the paper's eight structural query families, can an analyst answer
> the query from the spans a library emits out of the box?

## Conditions

| Condition | Packages (pinned) | What is enabled |
|---|---|---|
| `oi` | openinference-instrumentation-langchain 0.1.80, openinference-instrumentation-anthropic 3.1.0 | LangChain + Anthropic instrumentors, default config |
| `ollm` | opentelemetry-instrumentation-langchain 0.62.4, opentelemetry-instrumentation-anthropic 0.62.4 (Traceloop OpenLLMetry) | LangChain + Anthropic instrumentors, default config |
| `otel` | opentelemetry-instrumentation-genai-langchain 1.3b0, opentelemetry-instrumentation-genai-anthropic 1.3b0 (official OTel GenAI) | LangChain + Anthropic instrumentors, default config |
| `ref` | agenttelemetry 0.2.0 (this repository) | Agent spans emitted by the harness at each logical step |

Shared base in every condition: anthropic 2.3.0, langgraph 1.2.17,
langchain-core 1.7.0, opentelemetry-sdk 1.45.1, Python 3.12. Each condition has
its own virtual environment. Spans are exported with a synchronous processor to
one JSONL file per run.

Defaults are deliberate. The study measures what a team gets without writing
library-specific hints such as extra metadata or custom attributes. Whether a
library captures message content by default is recorded, not changed.

## Agent and frameworks

The same synthetic customer-support agent is implemented twice:

- `langgraph`: a LangGraph `StateGraph` with nodes `load_memory`, `planner`,
  `retrieve_policies`, `agent`, `refund_guardrail`, `tools`, `save_memory`, and a
  `billing_specialist` subgraph used for delegation. Tools are LangChain
  `StructuredTool`s. The policy knowledge base is a LangChain `BaseRetriever`.
  Memory is a LangGraph `InMemoryStore`. Model calls use the Anthropic SDK
  directly inside nodes.
- `custom`: the same logic as plain Python functions on the Anthropic SDK, with
  no agent framework.

Every logical step is one of these kinds: memory read/write, planning (one model
call), retrieval, reasoning iterations (model calls with tools), tool executions,
a guardrail check before every refund, and delegation to a billing sub-agent
that runs its own model loop.

## Same execution in every condition

Each ticket is run live once (model `claude-opus-5-5`, effort `low`), and the
Anthropic HTTP exchange is recorded at the transport layer. Every library
condition then replays the recorded responses through the same transport.
Instrumentors wrap the SDK above the transport, so they observe ordinary calls,
while the execution (plan, tool calls, loops, decisions) is identical across
conditions. A replay that requests a body that was not recorded is an error, and
every replay must consume exactly the recorded exchanges.

## Ground truth

The harness logs each logical event independently of OpenTelemetry, with
monotonic start/end timestamps, kind, agent name and identifiers. These
ground-truth instances are counted:

| Family | Ground-truth instance |
|---|---|
| Loops | three or more consecutive executions of the same tool where every execution before the last returned an error |
| Plan | one planning step |
| Guard | one guardrail decision (allow or block) |
| Memory | one memory read or write |
| Deleg. | one hand-off from the support agent to the billing sub-agent |
| Tool prov. | one tool execution, paired with the model call whose `tool_use` block requested it |
| Tokens | one model call |
| Retr. | one retrieval step |

## Scoring each instance

Spans are matched to an instance by time: a span matches when its interval
overlaps the instance's interval within the same run. For each instance and
library the result is one of:

- **Standard**: answerable using only the library's documented standard
  attributes (OpenInference `openinference.span.kind` and attribute names,
  Traceloop `traceloop.span.kind` and `gen_ai.*`/`llm.*` names, OTel
  `gen_ai.operation.name` and `gen_ai.*` names, AgentTelemetry
  `agenttelemetry.span.kind`) plus generic OTel structure (parent IDs,
  timestamps, status).
- **App-specific**: answerable only when the analyst also uses application
  naming, such as LangGraph node names in span names or metadata. Such a mapping
  has to be written for each application, so it is not portable.
- **Not answerable**: neither of the above.

Per family, answerable means:

- Loops: identify each tool execution in the loop, its tool name, and its error
  outcome, in order.
- Plan: identify the planning step as a distinct span.
- Guard: identify the guardrail check as a distinct span. Whether the decision is
  in a standard attribute, only in captured content, or absent is reported
  separately.
- Memory: identify the memory operation as a distinct span. Operation type
  (read/write) visibility is reported separately.
- Deleg.: identify an agent-invocation span for the sub-agent, with its agent
  identity, under the delegating agent's context.
- Tool prov.: identify the tool execution span and link it to the requesting
  model-call span by a parent link or a tool-call ID that appears on both sides.
  A link that holds only by sibling order is counted as app-specific.
- Tokens: the matched model-call span carries input and output token counts.
- Retr.: identify the retrieval step as a distinct span.

Outputs are per-family instance recall under each level, by condition and
framework. The paper's projection predictions are compared against these
measured values. Disagreements are reported as findings, not tuned away.

## Budget

There is a hard cap of USD 100 for model calls. A 5-ticket pilot measures the
cost per run before the full run.
