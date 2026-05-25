# Final Proposals — Ready for Submission

*2026-03-26. Converged after 4 rounds of cold review (11 review agents).*

> [!IMPORTANT]
> Only `PR 1: Plan Span` should be treated as the current submission target.
> `reflect` is a follow-up candidate, not the next PR to open immediately.
> Delegation no longer has a recommended standalone span proposal.

---

## PR 1: Plan Span

### PR Title
`Add semantic conventions for GenAI agent planning operation`

### PR Description

```markdown
Partially addresses #2664

## Summary

Adds `plan` as a new `gen_ai.operation.name` value for agent planning/task
decomposition spans. Zero new attributes — only a new enum member on the
existing `gen_ai.operation.name` attribute.

Agents routinely decompose complex tasks into sub-steps before executing them.
This planning phase is currently invisible in telemetry — you can see the
resulting tool calls and LLM invocations but not the planning decision that
produced them. The `plan` span captures this phase.

## Span Definition

| Field | Value |
|-------|-------|
| **Span Name** | `plan {gen_ai.agent.name}` (or `plan` if agent name unavailable) |
| **Span Kind** | `INTERNAL` |
| **Operation Name** | `plan` |

### Attributes

| Attribute | Req. Level | Type | Description |
|-----------|-----------|------|-------------|
| `gen_ai.operation.name` | Required | string | MUST be `"plan"` |
| `gen_ai.system` | Required | string | Framework name (e.g., `langchain`, `crewai`) |
| `gen_ai.agent.name` | Recommended (if available) | string | Name of the agent performing the planning |
| `gen_ai.agent.id` | Recommended (if available) | string | ID of the planning agent |
| `error.type` | Cond. Required | string | If the operation ended in an error |

Zero new attributes. All reused from the existing registry.
`gen_ai.agent.description` and `gen_ai.agent.version` are set on the parent
`invoke_agent` span and need not be repeated here.

### Events

No new events are introduced. Plan content capture (if desired) is handled by
the child `chat` span's existing `gen_ai.content.completion` events.

### Span Hierarchy

A plan span is the *parent* of the LLM call that generates the plan, and a
*sibling* of the tool/task spans it produces. This causal relationship is
the key differentiator — modeling planning as a task attribute would collapse
this parent-child structure.

```
invoke_agent "research_agent"
├── plan "research_agent"              ← NEW (INTERNAL)
│   └── chat "gpt-4o"                 (LLM generates the plan)
├── execute_tool "web_search"          (step 1 from plan)
├── execute_tool "summarize"           (step 2 from plan)
└── chat "gpt-4o"                      (final response)
```

Span status SHOULD follow the standard
[Recording Errors](https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/)
document. If the planning phase fails, set span status to ERROR and record an
exception event.

### Relationship to Other Proposals

- **vs `gen_ai.task` (#2912):** `plan` = formulating a strategy (before
  execution). `task` = executing assigned work. A plan may produce tasks.
  A plan span is the *parent* of the task/tool spans it generates; modeling
  it as a task attribute would collapse this causal relationship. They are
  siblings under `invoke_agent`.
- **vs #3575 (grouping primitives):** A plan is a distinct operation with its
  own duration and hierarchy — the same argument for why `execute_tool` is
  its own operation rather than a tagged `chat` span. Grouping attributes
  are complementary for loose structural relationships (e.g., correlating
  spans within a ReAct round), while plan captures a specific decision phase.
- **vs `invoke_agent`:** `invoke_agent` = agent execution.
  `plan` = decision phase within execution.

### Cross-Provider Evidence

| Framework | Hookable API | Auto-instrumentable? |
|-----------|-------------|---------------------|
| LangChain | `AgentExecutor._take_next_step()` — planning before tool calls | Yes |
| LlamaIndex | `SubQuestionQueryEngine.query()` — decomposition before sub-queries | Yes |
| CrewAI | `Crew.kickoff()` with `planning=True` — explicit planning phase | Yes |
| AutoGen | `GroupChatManager.run_chat()` — speaker selection phase | Yes |
| OpenAI Agents SDK | `Runner.run()` — handoff evaluation before transfer | Yes |
| Google ADK | `planner` agent `plan()` method | Expected (based on public API design) |

### Reference Implementation

Working implementation across 7 framework adapters:
[AgentTelemetry](https://github.com/Krishnachaitanyakc/AgentTelemetry)
(PyPI: `agenttelemetry`)
```

### YAML Changes

```yaml
# registry.yaml — new enum member on gen_ai.operation.name
- id: plan
  value: "plan"
  brief: 'Agent formulating a strategy or decomposing a task'
  stability: development

# spans.yaml — new span definition
- id: span.gen_ai.plan.internal
  type: span
  stability: development
  span_kind: internal
  brief: >
    Describes an agent planning or task decomposition phase.
  note: |
    The `gen_ai.operation.name` SHOULD be `plan`.
    **Span name** SHOULD be `plan {gen_ai.agent.name}`.
    If `gen_ai.agent.name` is not available, the span name SHOULD
    be `plan`.
    A plan span represents the decision phase where an agent formulates
    a strategy before executing it. It is a sibling of `execute_tool`
    and `chat` spans under `invoke_agent`, and the parent of the LLM
    call that generates the plan.
    This is distinct from a task span (#2912): a plan formulates
    strategy; a task executes assigned work. A plan span is the parent
    of the task/tool spans it generates.
    No new events are introduced. Plan content capture is handled by
    child `chat` span completion events.
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
    - ref: error.type
      requirement_level:
        conditionally_required: "if the operation ended in an error"
```

---

## PR 2: Reflect Span

### PR Title
`Add semantic conventions for GenAI agent reflection operation`

### PR Description

```markdown
Partially addresses #2664, relates to #3419

## Summary

Adds `reflect` as a new `gen_ai.operation.name` value for agent
self-evaluation spans. One new attribute: `gen_ai.reflection.verdict`
(2-value enum: pass/fail).

Agentic systems increasingly use reflection — the agent evaluates its own
output, checks quality/completeness, and decides whether to iterate. These
steps are currently invisible. The `reflect` span captures self-evaluation.

This span is **opt-in** — it SHOULD only be emitted when detailed agent
debugging is enabled, consistent with the SIG position on iteration spans
(#3419). Unlike pure iteration-tracking spans, reflect carries semantic
content (verdict) that cannot be derived from child span topology alone.

## Span Definition

| Field | Value |
|-------|-------|
| **Span Name** | `reflect {gen_ai.agent.name}` (or `reflect` if unavailable) |
| **Span Kind** | `INTERNAL` |
| **Operation Name** | `reflect` |

### Attributes

| Attribute | Req. Level | Type | Description |
|-----------|-----------|------|-------------|
| `gen_ai.operation.name` | Required | string | MUST be `"reflect"` |
| `gen_ai.system` | Required | string | Framework name |
| `gen_ai.agent.name` | Recommended (if available) | string | Name of the reflecting agent |
| `gen_ai.agent.id` | Opt-In | string | ID of the reflecting agent |
| `gen_ai.reflection.verdict` | Recommended (if available) | enum | Outcome: `pass` or `fail` |
| `error.type` | Cond. Required | string | If the operation ended in an error |

One new attribute: `gen_ai.reflection.verdict` (2-value enum).

**Verdict semantics:**
- `pass` — reflection determined output is satisfactory
- `fail` — reflection determined output is unsatisfactory
- If the reflection operation *itself* fails (e.g., evaluator LLM times
  out), `gen_ai.reflection.verdict` SHOULD NOT be set; use `error.type`
  instead
- The verdict represents the overall outcome. If the reflection evaluates
  multiple outputs, the verdict reflects the aggregate decision (`fail` if
  any sub-evaluation fails)
- Ambiguous or inconclusive evaluation results SHOULD be mapped to `fail`,
  since the agent will typically retry

### Span Links

If typed span link relationships are adopted (see #3575), reflect spans
SHOULD use the `evaluates` relationship pointing to the span whose output
is being evaluated. Until then, instrumentations MAY include an untyped
span link to the evaluated span.

### Span Hierarchy

```
invoke_agent "research_agent"
├── chat "gpt-4o"                      (generates initial output)
├── execute_tool "web_search"
├── reflect "research_agent"           ← NEW (INTERNAL, opt-in)
│   └── chat "gpt-4o"                 (LLM evaluates output)
├── execute_tool "web_search"          (retry based on reflection)
└── reflect "research_agent"           ← NEW (INTERNAL, opt-in)
    └── chat "gpt-4o"
```

### Non-Goals

- **Not model-level reasoning.** Model-internal chain-of-thought is tracked
  via `gen_ai.usage.reasoning.output_tokens` (PR #3383). This span captures
  *agent-level* self-evaluation — a deliberate step where the agent assesses
  its own output.
- **Not guardrail evaluation.** Guardrails (PR #3233) check external policy
  compliance. A guardrail span is triggered by a policy rule external to the
  agent's reasoning loop; a reflect span is triggered by the agent's own
  decision to re-evaluate its output.

### Cross-Provider Evidence

| Framework | Hookable API | Auto? | Verdict mapping |
|-----------|-------------|-------|----------------|
| LlamaIndex | `ResponseEvaluator.evaluate()` | Yes | Returns pass/fail directly |
| LangChain | `RetryOutputParser.parse_with_prompt()` | Yes | Retry = fail, success = pass |
| AutoGen | `is_termination_msg` callback | Partial | True = pass, False = fail |
| CrewAI | Internal review loop | No | No public API |
| Google ADK | `before_model_callback` | No | Generic hook |

Frameworks without dedicated reflection APIs can instrument reflection by
wrapping the conditional logic that determines whether to retry or terminate
an agent loop.

### Reference Implementation

Working implementation across 7 framework adapters:
[AgentTelemetry](https://github.com/Krishnachaitanyakc/AgentTelemetry)
(PyPI: `agenttelemetry`)
```

### YAML Changes

```yaml
# registry.yaml — new enum member on gen_ai.operation.name
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
  note: |
    If the reflection operation itself fails (e.g., the evaluator LLM
    times out), this attribute SHOULD NOT be set. Use `error.type` to
    describe the failure instead.
    The verdict represents the overall outcome. If the reflection
    evaluates multiple outputs, the verdict reflects the aggregate
    decision (fail if any sub-evaluation fails).
    Ambiguous or inconclusive results SHOULD be mapped to fail.

# spans.yaml — new span definition
- id: span.gen_ai.reflect.internal
  type: span
  stability: development
  span_kind: internal
  brief: >
    Describes an agent self-evaluation or output quality check.
  note: |
    The `gen_ai.operation.name` SHOULD be `reflect`.
    **Span name** SHOULD be `reflect {gen_ai.agent.name}`.
    If `gen_ai.agent.name` is not available, the span name SHOULD
    be `reflect`.
    This span is opt-in and SHOULD only be emitted when detailed
    agent debugging is enabled, consistent with the SIG position
    on iteration spans (#3419).
    Unlike pure iteration-tracking spans, reflect carries semantic
    content (verdict) that cannot be derived from child span topology
    alone. This is the key differentiator from the "can be derived"
    argument raised in #3419.
    A reflect span captures *agent-level* self-evaluation. This is
    distinct from:
    - *Model-level* reasoning tracked via
      `gen_ai.usage.reasoning.output_tokens` (PR #3383)
    - *Guardrail* evaluation (PR #3233) which checks external policy
      compliance. A guardrail is triggered by a policy rule external
      to the agent's reasoning loop; a reflect span is triggered by
      the agent's own decision to re-evaluate its output.
    If typed span link relationships are adopted (see #3575), reflect
    spans SHOULD use the `evaluates` relationship. Until then,
    instrumentations MAY include an untyped span link to the evaluated
    span.
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
      requirement_level: opt_in
    - ref: gen_ai.reflection.verdict
      requirement_level:
        recommended: if available
    - ref: error.type
      requirement_level:
        conditionally_required: "if the operation ended in an error"
```

---

## PR 3: Delegation Attribute (Small PR)

### PR Title
`Add invocation trigger attribute for GenAI agent spans`

### PR Description

```markdown
Relates to #1961, #3575

## Summary

Adds `gen_ai.agent.invocation.trigger` as a conditional attribute on
`invoke_agent` spans, indicating how the agent invocation was initiated.
No new span types.

This attribute captures the distinction between an agent invoked directly
by a user/application, delegated to by a peer agent, or selected by an
orchestrator/router. This information is currently lost — all
`invoke_agent` spans look identical regardless of how they were triggered.

## Attribute Definition

| Attribute | Req. Level | Type | Description |
|-----------|-----------|------|-------------|
| `gen_ai.agent.invocation.trigger` | Recommended (if known) | enum | How the agent invocation was initiated |

Values:

| Value | Description |
|-------|-------------|
| `user` | Agent invoked directly by user or application |
| `agent` | Agent invoked via delegation from another agent |
| `orchestrator` | Agent invoked via routing/selection by an orchestrator |

This attribute is conditional — it SHOULD be omitted when the trigger
is unknown, rather than defaulting to `user`.

## Span Links

When `gen_ai.agent.invocation.trigger` is `agent` or `orchestrator`, the
SERVER `invoke_agent` span MAY include a span link back to the CLIENT
`invoke_agent` span that initiated the delegation. This captures the
semantic intent of "who chose this agent and why," complementing the
parent-child relationship which captures temporal containment.

- Parent-child captures **temporal containment** (B's work happened during
  A's invocation)
- The span link captures **semantic intent** (A deliberately chose B for
  this subtask)

## Cross-Provider Evidence

| Framework | Trigger Type | Hookable API |
|-----------|-------------|-------------|
| CrewAI | `agent` | `Task.delegate()` with coworker parameter |
| AutoGen | `orchestrator` | GroupChat speaker selection routing |
| OpenAI Agents SDK | `agent` | Handoff objects with target agent |
| Google ADK | `agent` | `transfer_to_agent()` function |
| LangGraph | `orchestrator` | `send()` / conditional edges |

## Reference Implementation

[AgentTelemetry](https://github.com/Krishnachaitanyakc/AgentTelemetry)
(PyPI: `agenttelemetry`)
```

### YAML Changes

```yaml
# registry.yaml — new attribute
- id: gen_ai.agent.invocation.trigger
  stability: development
  type:
    members:
      - id: user
        value: "user"
        brief: 'Agent invoked directly by user or application'
        stability: development
      - id: agent
        value: "agent"
        brief: 'Agent invoked via delegation from another agent'
        stability: development
      - id: orchestrator
        value: "orchestrator"
        brief: 'Agent invoked via routing/selection by an orchestrator'
        stability: development
  brief: How the agent invocation was initiated
  note: |
    This attribute SHOULD be omitted when the trigger is unknown,
    rather than defaulting to `user`.

# spans.yaml — add to invoke_agent span definitions
# (on both client and internal invoke_agent spans)
    - ref: gen_ai.agent.invocation.trigger
      requirement_level:
        recommended: if known
```

---

## Submission Checklist

### Before submitting:
- [ ] Fork `open-telemetry/semantic-conventions`
- [ ] Study existing YAML in `model/gen-ai/spans.yaml` and `registry.yaml`
- [ ] Create `.chloggen/*.yaml` changelog entries for each PR
- [ ] Join CNCF Slack (#otel-genai, #otel-semconv)
- [ ] Post community engagement comments (DRAFT_COMMENTS.md, 5-day cadence)
- [ ] Attend 1 GenAI SIG meeting before submitting PRs
- [ ] Identify a SIG champion who will keep PRs alive during review

### PR submission order:
1. Community engagement comments (5 days)
2. `plan` span PR — zero new attributes, least controversial
3. `reflect` span PR — opt-in, 1 new attribute, more novel
4. `gen_ai.agent.invocation.trigger` attribute PR — small, builds on #3575

### During review:
- [ ] Respond to every comment within 48 hours (stale bot kills after 7 days)
- [ ] Have instrumentability proof ready for each framework
- [ ] If #3575 gains traction, adapt span link guidance accordingly
- [ ] Be prepared for "why not use gen_ai.task with a planning type?" — answer:
      plan is the parent of tasks, collapsing them loses the causal relationship

### Future follow-up PRs (after initial PRs land):
- [ ] `gen_ai.plan.step.count` — once implementation data from 2+ frameworks exists
- [ ] Additional `gen_ai.reflection.verdict` values (e.g., `review`) — once frameworks support it
- [ ] `gen_ai.agent.delegation.task` — delegation task/reason metadata
