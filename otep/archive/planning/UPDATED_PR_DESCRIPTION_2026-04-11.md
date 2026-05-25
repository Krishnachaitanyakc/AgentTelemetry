# Updated PR Description for #3594 (Concise)

*Copy everything below the line into the GitHub PR body.*

---

Partially addresses #2664

## Summary

Adds `plan` as a new `gen_ai.operation.name` value with an INTERNAL span
definition. Zero new attributes — only a new enum member reusing existing
attributes.

## The problem

When an agent fails, an operator sees `chat` and `execute_tool` spans but
cannot tell whether the agent planned poorly or executed poorly. The fix is
different — bad planning needs prompt changes; bad execution needs tool fixes.
A `plan` span separates planning latency and errors from execution, making this
distinction visible.

## Hierarchy

```text
invoke_agent "research_agent"
├── plan "research_agent"              ← NEW (INTERNAL)
│   └── chat "gpt-4o"                 (LLM generates the plan)
├── execute_tool "web_search"          (step 1 from plan)
├── execute_tool "summarize"           (step 2 from plan)
└── chat "gpt-4o"                      (final response)
```

The `plan` span is the parent of the planning LLM call and a sibling of the
tool spans that follow. This parent-child structure cannot be modeled as an
attribute on the child `chat` span or as a grouping primitive (#3575) — neither
captures planning duration or provides a parent boundary.

This is distinct from `gen_ai.task` (#2912): a plan formulates strategy before
execution; a task executes assigned work.

## Cross-provider evidence

| Framework | Planning Hook | Auto? |
|-----------|-------------|-------|
| CrewAI | `Crew.kickoff(planning=True)` — explicit `CrewPlanner` phase | Yes |
| LlamaIndex | `SubQuestionQueryEngine.query()` — decomposition before sub-queries | Yes |
| LangChain | `AgentExecutor._take_next_step()` (legacy, private) | Partial |
| AutoGen | `GroupChatManager.run_chat()` — speaker selection | Partial |
| OpenAI Agents SDK | `Runner.run()` — handoff evaluation | Partial |
| Google ADK | `planner` agent `plan()` method | Unverified |

Instrumentation SHOULD only emit `plan` when the framework exposes an explicit
planning boundary (see emission rules in `spans.yaml`).

## Out of scope

Plan-specific attributes (`strategy`, `step.count`), reflection, and delegation
are deferred to follow-up PRs.

## Reference implementation

[AgentTelemetry](https://github.com/Krishnachaitanyakc/AgentTelemetry) (PyPI: `agenttelemetry`)
