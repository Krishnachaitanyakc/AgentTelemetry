# PR: Add semantic conventions for GenAI agent planning operation

## Title
Add semantic conventions for GenAI agent planning operation

## Description

Partially addresses #2664

### Summary

Adds `plan` as a new `gen_ai.operation.name` value for agent planning and task
decomposition spans. Zero new plan-specific attributes — only a new enum member
and an INTERNAL span definition reusing existing attributes:
`gen_ai.operation.name`, `gen_ai.system`, `gen_ai.agent.name`,
`gen_ai.agent.id`, and `error.type`.

### The problem

Agents routinely decompose tasks into sub-steps before executing them. This
planning phase is invisible in current telemetry — the LLM call that generates a
plan looks identical to the LLM call that generates a final answer. Both are
`chat` spans. You cannot tell why the agent called the LLM without a parent span
marking the planning phase.

### Span Definition

| Field | Value |
|-------|-------|
| **Span Name** | `plan {gen_ai.agent.name}` (or `plan` if agent name unavailable) |
| **Span Kind** | `INTERNAL` |
| **Operation Name** | `plan` |

#### Attributes

| Attribute | Req. Level | Type | Description |
|-----------|-----------|------|-------------|
| `gen_ai.operation.name` | Required | string | MUST be `"plan"` |
| `gen_ai.system` | Required | string | Framework or provider identifier |
| `gen_ai.agent.name` | Recommended (if available) | string | Name of the agent performing the planning |
| `gen_ai.agent.id` | Recommended (if available) | string | ID of the planning agent |
| `error.type` | Cond. Required | string | If the operation ended in an error |

Zero new plan-specific attributes. All fields are reused from the existing
registry.

### Span Hierarchy

A plan span is the *parent* of the LLM call that generates the plan, and a
*sibling* of the tool/task spans it produces:

```text
invoke_agent "research_agent"
├── plan "research_agent"              ← NEW (INTERNAL)
│   └── chat "gpt-4o"                 (LLM generates the plan)
├── execute_tool "web_search"          (step 1 from plan)
├── execute_tool "summarize"           (step 2 from plan)
└── chat "gpt-4o"                      (final response)
```

This parent-child relationship is the key differentiator. Modeling planning as a
task attribute or a grouping tag would collapse this hierarchy and lose the
ability to measure planning duration independently.

### Why This Is Not Just A Grouping Primitive

Issue #3575 proposes grouping primitives and typed span links for structural
relationships. That approach is complementary, but not sufficient here. A
grouping attribute can correlate spans that participate in planning; it does not
represent the planning phase itself as a timed span with its own parent-child
boundary.

### Why This Is Not Just A Task Attribute

Issue #2912 discusses workflows, agents, and tasks. `plan` is narrower:
`task` captures execution of assigned work, while `plan` captures strategy
formulation before execution. A `plan` span can be the parent of the task or
tool spans it produces; collapsing planning into task metadata loses that causal
structure.

### Relationship to Other Proposals

- **vs `gen_ai.task` (#2912):** `plan` = formulating strategy. `task` = executing
  assigned work. A plan may produce tasks.
- **vs #3575 (grouping primitives):** A plan is a distinct operation with its own
  duration and hierarchy. Grouping attributes are complementary for loose
  structural relationships, but they do not represent the planning phase itself.
- **vs `invoke_agent`:** `invoke_agent` = agent execution. `plan` = decision phase
  within execution.

### Cross-Provider Evidence

| Framework | Hookable API | Auto-instrumentable? |
|-----------|-------------|---------------------|
| LangChain | `AgentExecutor._take_next_step()` — next-step selection before tool calls | Yes |
| LlamaIndex | `SubQuestionQueryEngine.query()` — decomposition before sub-queries | Yes |
| CrewAI | `Crew.kickoff()` with `planning=True` — explicit planning phase | Yes |
| AutoGen | `GroupChatManager.run_chat()` — speaker selection / coordination phase | Partial |
| OpenAI Agents SDK | `Runner.run()` — handoff evaluation before transfer | Partial |
| Google ADK | `planner` agent `plan()` method | Expected, verify before PR |

### Out Of Scope For This PR

- `plan.strategy`
- `plan.step.count`
- plan content capture
- delegation semantics
- reflection semantics
- any new namespace or broader agent taxonomy

### Reference Implementation

Working implementation across 7 framework adapters:
[AgentTelemetry](https://github.com/Krishnachaitanyakc/AgentTelemetry)
(PyPI: `agenttelemetry`)

### Files Changed

- `model/gen-ai/registry.yaml` — new `plan` enum member on `gen_ai.operation.name`
- `model/gen-ai/spans.yaml` — new `span.gen_ai.plan.internal` span definition
- `docs/gen-ai/gen-ai-agent-spans.md` — plan span section with semconv marker
- `.chloggen/gen-ai-plan-operation.yaml` — changelog entry
