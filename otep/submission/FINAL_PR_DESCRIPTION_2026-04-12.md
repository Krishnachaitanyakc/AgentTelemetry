# Final PR Description for #3594
## Approved after OTel Expert + AI Agents Expert dual review

*Copy everything below the line into the GitHub PR body.*

---

Partially addresses #2664

## Summary

Adds `plan` as a new `gen_ai.operation.name` value following the same pattern as `execute_tool` -- a dedicated operation name because planning has independent duration, error status, and parent-child structure that justify a distinct span. Zero new attributes; only a new enum member reusing existing attributes.

## The problem

An agent produces a wrong answer. Was it bad planning (wrong task decomposition) or bad execution (tool returned stale data)? The remediation is different: bad planning needs prompt changes; bad execution needs tool or retrieval fixes.

Without a `plan` span, the operator sees this:

```text
invoke_agent "research_agent"          1200ms
├── chat "gpt-4o"                       400ms  ← planning? reasoning? unclear
├── execute_tool "web_search"           350ms
├── execute_tool "summarize"            200ms
└── chat "gpt-4o"                       250ms  ← final response? another plan?
```

The first `chat` span might be planning, reasoning, or a direct answer attempt. The operator cannot distinguish these failure modes.

With a `plan` span:

```text
invoke_agent "research_agent"          1200ms
├── plan "research_agent"               400ms  ← planning duration isolated
│   └── chat "gpt-4o"                  400ms  (LLM generates the plan)
├── execute_tool "web_search"           350ms  (step 1)
├── execute_tool "summarize"            200ms  (step 2)
└── chat "gpt-4o"                       250ms  (final response)
```

Planning latency, errors, and the LLM call that produced the plan are now isolated under a parent boundary. An operator can filter on `gen_ai.operation.name = plan`, set sampling rules on planning spans independently, and immediately see whether planning or execution consumed the time budget.

## Why a span, not an attribute or grouping primitive

`execute_tool` got its own span -- not an attribute on `chat` -- because tool execution has independent duration, error status, and parent-child structure. Planning has the same properties. A grouping attribute (#3575) correlates sibling spans; a `plan` span creates a parent boundary with its own duration. You cannot model a parent as an attribute on its own child.

## Relationship to `gen_ai.task` (#2912)

A plan formulates strategy before execution; a task executes assigned work. The plan span is the parent of the planning LLM call and a sibling of the task/tool spans that follow.

## Cross-provider evidence

| Framework | Planning Hook | Auto-instrumentable | Source |
|-----------|---------------|:-------------------:|--------|
| CrewAI | `CrewPlanner` -- explicit planning phase before task execution | Yes | [planning_handler.py](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/utilities/planning_handler.py) |
| LlamaIndex | `SubQuestionQueryEngine` -- question decomposition before sub-queries | Yes | [sub_question_query_engine.py](https://github.com/run-llama/llama_index/blob/main/llama-index-core/llama_index/core/query_engine/sub_question_query_engine.py) |
| LangChain | `AgentExecutor._take_next_step()` -- deprecated, private API | Partial | -- |
| Google ADK | `planner` agent with `plan()` method | Unverified | -- |

Instrumentation SHOULD only emit `plan` when the framework exposes an explicit planning boundary (see emission rules in `spans.yaml`).

## Out of scope

Plan-specific attributes (`strategy`, `step.count`), reflection, and delegation are deferred to follow-up PRs.
