# Cold Review Round 1 — Findings & Fixes

*2026-03-26. Three parallel cold reviews of plan/delegate/reflect span proposals.*

---

## Summary of Round 1 Findings

| Span | Blockers | Majors | Minors | Verdict |
|------|----------|--------|--------|---------|
| `plan` | 2 | 3 | 3 | Strip to minimum |
| `delegate` | 3 | 2 | 2 | **Rethink entirely** — may not need its own span |
| `reflect` | 3 | 4 | 3 | Strip to minimum |

---

## Plan Span — Fixes Applied

### Blockers resolved:
- B1: **Dropped `gen_ai.plan.strategy`** — cannot be set automatically. Instrumentation
  libs see function calls, not planning intent. Span name is now just `plan`.
- B2: **Dropped `gen_ai.plan.steps` (string[])** — unbounded array of natural language
  content. If step detail needed, use events (like prompt/completion events).

### Majors resolved:
- M1: **Added positioning vs #2912 (`gen_ai.task`)** — plan is about *formulating* a
  strategy, task is about *executing* assigned work. A plan produces tasks.
- M2: **Dropped `gen_ai.plan.goal`** — only auto-instrumentable in CrewAI (1/6 frameworks).
- M3: **Added concrete hook points** for each framework.

### Revised proposal:
```yaml
# registry.yaml additions
- id: gen_ai.operation.name  # new enum member
  members:
    - id: plan
      value: "plan"
      brief: 'Agent formulating a strategy or decomposing a task'
      stability: development

- id: gen_ai.plan.step.count
  stability: development
  type: int
  brief: Number of steps in the generated plan
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
    **Span name** SHOULD be `plan`.
  attributes:
    - ref: gen_ai.operation.name
      requirement_level: required
      sampling_relevant: true
    - ref: gen_ai.agent.name
      requirement_level: recommended
    - ref: gen_ai.agent.id
      requirement_level: recommended
    - ref: gen_ai.plan.step.count
      requirement_level: recommended
    - ref: error.type
      requirement_level:
        conditionally_required: "if the operation ended in an error"
```

**Cross-provider hook points:**
| Framework | Hookable API | Auto-instrumentable? |
|-----------|-------------|---------------------|
| LangChain | `AgentExecutor._take_next_step()` → planning phase before tool calls | Yes |
| LlamaIndex | `SubQuestionQueryEngine.query()` → decomposition before sub-queries | Yes |
| CrewAI | `Crew.kickoff()` with `planning=True` → explicit planning phase | Yes |
| AutoGen | `GroupChatManager.run_chat()` → speaker selection phase | Yes |
| OpenAI Agents SDK | `Runner.run()` → handoff evaluation before transfer | Yes |
| Google ADK | `planner` agent type → `plan()` method | Yes |

---

## Delegate Span — RETHOUGHT

### Key finding from cold review:
The delegate span has **3 blockers** that are fundamental, not fixable:
1. Semantic overlap with `invoke_agent` CLIENT span
2. #3575 span links (`delegates_to`) already solve this more cleanly
3. Most attributes aren't auto-instrumentable

### Decision: **Do NOT propose a `delegate` span type.**

Instead:
1. **Contribute to #3575** — add our cross-framework delegation evidence to the
   span-link proposal (`delegates_to` link type)
2. **Propose a single attribute** on `invoke_agent` spans:
   `gen_ai.agent.invocation.type` — enum: `direct`, `delegated`, `transferred`
   This captures "why was this agent invoked" without a new span.
3. **File the circular delegation detection** as an analysis capability built on
   `delegates_to` links, not as a span-level convention.

### Revised approach:
```yaml
# registry.yaml — new attribute on invoke_agent
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
      - id: transferred
        value: "transferred"
        brief: 'Agent invoked via handoff/transfer from another agent'
        stability: development
  brief: How the agent invocation was initiated
```

Plus a comment on #3575 contributing the `delegates_to` link type with our
cross-framework evidence.

---

## Reflect Span — Fixes Applied

### Blockers resolved:
- B1: **Reduced `gen_ai.reflection.type`** to 3 auto-instrumentable values:
  `retry` (OutputParser retry), `evaluation` (explicit evaluator call),
  `termination_check` (AutoGen is_termination_msg). Dropped the 6 semantic values.
- B2: **Aligned verdict with guardrail pattern** — 3 values: `pass`, `fail`, `review`.
  Dropped `needs_improvement`, `acceptable`, `retry` (ambiguous).
- B3: **Tightened cross-provider evidence** — honest about which frameworks have
  clean hook points vs manual instrumentation.

### Majors resolved:
- M1: **Dropped `gen_ai.reflection.reasoning`** — redundant with child chat span events.
- M2: **Dropped `gen_ai.reflection.confidence`** — undefined semantics, not normalizable.
- M3: **Dropped `gen_ai.reflection.criteria`** — application config, not telemetry.
- M4: **Positioned as opt-in** to align with #3419 SIG decision. Added "Non-goals"
  distinguishing agent reflection from model reasoning tokens.

### Added:
- **`evaluates` span link** pointing to the span whose output is being evaluated
  (per #3575 pattern).

### Revised proposal:
```yaml
# registry.yaml additions
- id: gen_ai.operation.name  # new enum member
  members:
    - id: reflect
      value: "reflect"
      brief: 'Agent evaluating its own output or reasoning'
      stability: development

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
      - id: review
        value: "review"
        brief: 'Reflection flagged output for further review'
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
    **Span name** SHOULD be `reflect`.
    This span is opt-in and SHOULD only be emitted when detailed
    agent debugging is enabled.
    Non-goal: this span captures *agent-level* self-evaluation, not
    *model-level* reasoning (which is tracked via
    `gen_ai.usage.reasoning.output_tokens`).
  attributes:
    - ref: gen_ai.operation.name
      requirement_level: required
      sampling_relevant: true
    - ref: gen_ai.agent.name
      requirement_level: recommended
    - ref: gen_ai.reflection.verdict
      requirement_level: recommended
    - ref: error.type
      requirement_level:
        conditionally_required: "if the operation ended in an error"
```

**Cross-provider hook points (honest assessment):**
| Framework | Hookable API | Auto-instrumentable? |
|-----------|-------------|---------------------|
| LlamaIndex | `ResponseEvaluator.evaluate()`, `FaithfulnessEvaluator.evaluate()` | Yes — clean API |
| LangChain | `RetryOutputParser.parse_with_prompt()` | Yes — retry is detectable |
| AutoGen | `is_termination_msg` callback, `ReflectionAgent` | Partial — callback detectable, but reflection config unstable across versions |
| CrewAI | Internal review loop in task execution | No — no public API |
| Google ADK | `before_model_callback` | No — generic hook, can't distinguish reflection from other callbacks |
| DSPy | `dspy.Assert`, `dspy.Suggest` | Partial — hookable but semantically these are constraints, not reflection |

**Auto-instrumentable in 2-3 of 6 frameworks.** The others require manual instrumentation.
This is honest and the SIG will appreciate the transparency.

---

## Updated Submission Plan

### What we're now submitting:
1. **PR 1: `plan` span** — minimal (operation name + step.count + agent attrs)
2. **PR 2: `reflect` span** — minimal, opt-in (operation name + verdict + evaluates link)
3. **Comment on #3575** — contribute `delegates_to` evidence + propose
   `gen_ai.agent.invocation.type` attribute on invoke_agent

### What we're NOT submitting:
- ~~`delegate` span~~ — replaced with attribute on invoke_agent + span link
- ~~`gen_ai.plan.strategy`~~ — not auto-instrumentable
- ~~`gen_ai.plan.steps`~~ — unbounded array
- ~~`gen_ai.plan.goal`~~ — not auto-instrumentable in most frameworks
- ~~`gen_ai.reflection.type`~~ — not auto-instrumentable (may add in follow-up)
- ~~`gen_ai.reflection.reasoning/confidence/criteria`~~ — removed

### Submission order:
1. `plan` span — least controversial, clear gap, all frameworks have planning
2. `reflect` span — more novel but positioned as opt-in
3. Delegation attribute + #3575 comment — builds on existing conversation
