# Cold Review Round 2 — Fixes & Round 3 Proposals

*2026-03-26. Applying R2 feedback, preparing final proposals.*

---

## Plan Span — R2 Fixes Applied

### M1 fix: Defined "step" + demoted to opt_in
`gen_ai.plan.step.count` is now opt_in (not recommended). Definition added:
"The number of discrete actions or sub-tasks the agent's planning phase determined
should be executed." Noted that granularity varies by framework.

### M2 fix: Added explicit span tree diagram
```
invoke_agent "research_agent"          (CLIENT or INTERNAL)
├── plan "research_agent"              ← THIS PROPOSAL (INTERNAL)
│   └── chat "gpt-4o"                 (LLM generates plan, if any)
├── execute_tool "web_search"          (step 1 from plan)
├── execute_tool "summarize"           (step 2 from plan)
└── reflect "research_agent"           (evaluating plan completion)
```
Plan and task (#2912) are siblings under invoke_agent. Plan = formulating
strategy (before execution). Task = executing assigned work.

### m1 fix: Span name = `plan {gen_ai.agent.name}`
### m2 fix: Added note that step.count is set at span end
### m3 fix: Google ADK flagged as "Auto: Expected" not "Auto: Yes"

### FINAL Plan Span Proposal (Round 3):

```yaml
# registry.yaml — new enum member
- id: plan
  value: "plan"
  brief: 'Agent formulating a strategy or decomposing a task'
  stability: development

# registry.yaml — new attribute
- id: gen_ai.plan.step.count
  stability: development
  type: int
  brief: >
    The number of discrete actions or sub-tasks the agent's planning
    phase determined should be executed
  note: |
    Granularity varies by framework. In LangChain, a step is typically
    a tool call. In CrewAI, a step is a task in the generated plan.
    This attribute is set at span end, after the planning phase completes.
  examples: [3, 5]

# spans.yaml
- id: span.gen_ai.plan.internal
  type: span
  stability: development
  span_kind: internal
  brief: >
    Describes an agent planning or task decomposition phase.
  note: |
    The `gen_ai.operation.name` SHOULD be `plan`.
    **Span name** SHOULD be `plan {gen_ai.agent.name}`.
    A plan span represents the decision phase where an agent formulates
    a strategy before executing it. It is a sibling of `execute_tool`
    and `chat` spans under `invoke_agent`.
    This is distinct from a task span (#2912): a plan formulates
    strategy; a task executes assigned work. A plan may produce tasks.
  attributes:
    - ref: gen_ai.operation.name
      requirement_level: required
      sampling_relevant: true
    - ref: gen_ai.system
      requirement_level: required
    - ref: gen_ai.agent.name
      requirement_level:
        recommended: if available
      sampling_relevant: true
    - ref: gen_ai.agent.id
      requirement_level:
        recommended: if available
    - ref: gen_ai.plan.step.count
      requirement_level: opt_in
    - ref: error.type
      requirement_level:
        conditionally_required: "if the operation ended in an error"
```

---

## Reflect Span — R2 Fixes Applied

### B1 fix: Span name = `reflect {gen_ai.agent.name}`
### M1 fix: Added `gen_ai.system` (required)
### M2 fix: Trimmed verdict to 2 values (pass/fail)
Removed `review` — no framework produces this signal automatically.
Can be added in follow-up when frameworks support it.
### m1 fix: Removed redundant error.type re-specification (just reference general convention)
### m2 fix: Tighter guardrail differentiation added
### m3 fix: Removed DSPy from table (constraints, not reflection)

### FINAL Reflect Span Proposal (Round 3):

```yaml
# registry.yaml — new enum member
- id: reflect
  value: "reflect"
  brief: 'Agent evaluating its own output or reasoning'
  stability: development

# registry.yaml — new attribute
- id: gen_ai.reflection.verdict
  stability: development
  type:
    members:
      - id: pass
        value: "pass"
        brief: 'Reflection determined output is satisfactory'
        stability: development
      - id: fail
        value: "fail"
        brief: 'Reflection determined output is unsatisfactory'
        stability: development
  brief: Outcome of the agent's self-evaluation

# spans.yaml
- id: span.gen_ai.reflect.internal
  type: span
  stability: development
  span_kind: internal
  brief: >
    Describes an agent self-evaluation or output quality check.
  note: |
    The `gen_ai.operation.name` SHOULD be `reflect`.
    **Span name** SHOULD be `reflect {gen_ai.agent.name}`.
    This span is opt-in and SHOULD only be emitted when detailed
    agent debugging is enabled, consistent with the SIG position
    on iteration spans (#3419).
    A reflect span captures *agent-level* self-evaluation — the agent
    assessing its own output quality. This is distinct from:
    - *Model-level* reasoning tracked via
      `gen_ai.usage.reasoning.output_tokens` (PR #3383)
    - *Guardrail* evaluation (PR #3233) which checks external policy
      compliance. A guardrail is triggered by a policy rule external
      to the agent's reasoning loop; a reflect span is triggered by
      the agent's own decision to re-evaluate its output.
    A reflect span SHOULD include a span link of relationship type
    `evaluates` pointing to the span whose output is being evaluated.
  attributes:
    - ref: gen_ai.operation.name
      requirement_level: required
      sampling_relevant: true
    - ref: gen_ai.system
      requirement_level: required
    - ref: gen_ai.agent.name
      requirement_level:
        recommended: if available
      sampling_relevant: true
    - ref: gen_ai.reflection.verdict
      requirement_level:
        recommended: if available
    - ref: error.type
      requirement_level:
        conditionally_required: "if the operation ended in an error"
```

**Cross-provider hook points (final, honest):**
| Framework | Hookable API | Auto | Verdict mapping |
|-----------|-------------|------|----------------|
| LlamaIndex | `ResponseEvaluator.evaluate()` | Yes | returns pass/fail directly |
| LangChain | `RetryOutputParser.parse_with_prompt()` | Yes | retry = fail, success = pass |
| AutoGen | `is_termination_msg` callback | Partial | True = pass, False = fail |
| CrewAI | Internal review loop | No | No public API |
| Google ADK | `before_model_callback` | No | Generic hook |

---

## Delegation — Revised Approach (No Span)

Instead of a `delegate` span, contribute to existing proposals:

### 1. New attribute on invoke_agent spans:
```yaml
- id: gen_ai.agent.invocation.type
  stability: development
  type:
    members:
      - id: direct
        value: "direct"
        brief: 'Agent invoked directly by user or application'
        stability: development
      - id: delegated
        value: "delegated"
        brief: 'Agent invoked via delegation from another agent'
        stability: development
  brief: How the agent invocation was initiated
```

### 2. Comment on #3575:
Contribute `delegates_to` link type with cross-framework evidence:
- CrewAI: `Task.delegate()` with coworker parameter
- AutoGen: GroupChat agent-to-agent message routing
- OpenAI Agents SDK: Handoff objects with target agent
- Google ADK: `transfer_to_agent()` function
- LangGraph: `send()` to route to sub-graphs
