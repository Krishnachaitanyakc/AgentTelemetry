# OTEP Plan: Planning, Delegation, and Reflection Span Kinds

## Strategy

**One umbrella issue** linking to **three individual PRs** — one per span kind.

### Why this structure
- Umbrella issue tells a coherent story with shared motivation and empirical evidence
- Individual PRs allow independent review/merge and avoid one blocking the others
- Matches the pattern of issue #2664 (umbrella) with sub-issues per concept

### Submission order (least to most controversial)
1. **Planning** — well-understood agent concept, easy sell
2. **Delegation** — multi-agent is growing, clear real-time safety use case (cycle detection)
3. **Reflection** — most novel, needs the most justification

### Key reviewers to tag
- @lmolkova (Liudmila Molkova — GenAI SIG lead, reviews all GenAI PRs)
- @zhirafovod (active GenAI reviewer)
- @lzchen (active GenAI reviewer)
- @gyliu513 (Guangya Liu — opened issue #1530 on agent frameworks)
- @karthikscale3 (Karthik Kalyan — agent framework analysis in #1530)

### Cross-references
- Issue #2664 (Agentic Systems meta-issue) — our spans fill 3 of their 6 gaps
- Issue #1530 (Agent Framework Semantic Convention) — shared motivation
- Issue #3575 (Grouping primitives) — our spans complement, not conflict
- Issue #3419 (ReAct iteration spans) — our reflection span addresses this
- PR #3233 (Guardrails) — peer proposal, similar format
- PR #3250 (Memory) — peer proposal, similar format

---

## Umbrella Issue: "Semantic Conventions for Agent Cognitive Operations"

### Title
`Semantic Conventions for GenAI Agent Cognitive Operations (planning, delegation, reflection)`

### Body

```markdown
## Motivation

Current GenAI semantic conventions cover inference (`chat`/`generate_content`),
tool execution (`execute_tool`), retrieval (`retrieval`), and agent
invocation (`create_agent`/`invoke_agent`). However, they do not capture the
**cognitive operations** that happen *between* these primitives — the planning,
delegation, and reflection steps that distinguish agentic systems from simple
LLM pipelines.

Without these, observability tools can see *what* an agent did (called an LLM,
ran a tool) but not *why* (what plan led to the tool call, which agent delegated
to whom, whether the agent reflected on its output quality).

This gap is empirically validated. In our study of 112 SWE-bench instances
(3,060 spans across 12 repositories), 75% of agent failures were reasoning
loops — failures that are invisible without planning/reflection spans. Our
ablation study across 2,940 configurations shows each of these span kinds is
uniquely necessary for fault detection (block-diagonal necessity matrix).

## Proposed Span Kinds

| Operation Name | Span Kind | Purpose |
|---------------|-----------|---------|
| `plan` | INTERNAL | Agent formulating a strategy or decomposing a task |
| `delegate` | INTERNAL | Agent assigning work to another agent |
| `reflect` | INTERNAL | Agent evaluating its own output or reasoning |

## Cross-Provider Validation

| Framework | Planning | Delegation | Reflection |
|-----------|----------|------------|------------|
| LangChain | ✅ AgentAction events | ✅ Multi-agent handoff | ✅ Chain self-critique |
| CrewAI | ✅ Task planning | ✅ Crew task assignment | ✅ Quality review step |
| AutoGen | ✅ GroupChat planning | ✅ Agent-to-agent messaging | ✅ Reflection agent |
| LlamaIndex | ✅ Sub-question decomposition | — | ✅ Response evaluation |
| OpenAI Agents SDK | ✅ Handoff planning | ✅ Agent handoffs | — |
| Anthropic MCP | — | ✅ Server delegation | — |
| Google ADK | ✅ Task decomposition | ✅ Multi-agent delegation | ✅ Evaluation loops |

## Empirical Evidence

- **Ablation study:** Block-diagonal necessity matrix — each span kind uniquely
  detects faults the others cannot (2,940 configurations, 14 fault types)
- **Inter-rater reliability:** Cohen's kappa = 0.904 (almost perfect agreement)
  on span kind classification across 25 traces
- **SWE-bench case study:** 112 instances, 75% of failures are reasoning loops
  detectable via planning + reflection spans (95% CI [66%, 82%])
- **Closed-loop improvement:** +8.3pp task completion when planning/reflection
  spans feed back into agent behavior
- **Circuit breaker demo:** Delegation cycle detection catches 4/4 circular
  delegation faults in real-time using delegation spans

## Related Work

- AgentTelemetry library (PyPI: `agenttelemetry`) — working implementation
  across 7 frameworks with these span kinds
- MAST taxonomy (NeurIPS 2025) — 85.7% convergence with our fault types
- Issue #2664 — our `plan`/`delegate`/`reflect` map to their Tasks, Teams,
  and Agents concepts
- Issue #1530 — shared motivation for agent framework conventions
- PR #3233 (guardrails) and PR #3250 (memory) — peer proposals for other
  missing agent operations

## Sub-issues / PRs

1. [ ] Planning span (`plan`) — PR #TBD
2. [ ] Delegation span (`delegate`) — PR #TBD
3. [ ] Reflection span (`reflect`) — PR #TBD
```

---

## PR 1: Planning Span

### Title
`Add semantic conventions for GenAI planning span`

### Description

```markdown
Fixes #UMBRELLA_ISSUE_NUMBER

## Summary

Adds the `plan` operation for GenAI agent planning/task decomposition spans.

Agents routinely decompose complex tasks into sub-steps before executing them.
This planning phase is currently invisible in telemetry — you can see the
resulting tool calls and LLM invocations but not the plan that produced them.
The `plan` span captures this decision point.

## Span Definition

| Field | Value |
|-------|-------|
| **Span Name** | `plan {gen_ai.plan.strategy}` |
| **Span Kind** | `INTERNAL` |
| **Operation Name** | `plan` |

### Attributes

#### Required

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.operation.name` | string | MUST be `"plan"` |

#### Recommended

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.plan.strategy` | string | Planning approach used. Well-known values: `task_decomposition`, `tool_selection`, `step_sequencing`, `sub_question_decomposition`, `goal_refinement` |
| `gen_ai.plan.step.count` | int | Number of steps in the generated plan |
| `gen_ai.agent.name` | string | Name of the agent performing planning |
| `gen_ai.agent.id` | string | Unique identifier of the planning agent |

#### Opt-In (sensitive)

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.plan.steps` | string[] | Ordered list of planned step descriptions |
| `gen_ai.plan.goal` | string | The goal or objective being planned for |

### Span Hierarchy

Planning spans are children of agent spans (`invoke_agent`) and siblings of
inference spans (`chat`). A typical trace:

```
invoke_agent "research_agent"
├── plan "task_decomposition"          ← NEW
│   └── chat "gpt-4o"                 (LLM generates the plan)
├── execute_tool "web_search"          (executing step 1)
├── execute_tool "summarize"           (executing step 2)
└── reflect "evaluate_completeness"    (checking plan completion)
```

### Cross-Provider Evidence

| Framework | How Planning Manifests |
|-----------|----------------------|
| LangChain | `AgentAction` callback with tool selection reasoning |
| LlamaIndex | Sub-question decomposition engine (`SubQuestionQueryEngine`) |
| CrewAI | Task planning phase before crew execution |
| AutoGen | `GroupChatManager` selecting next speaker/action |
| OpenAI Agents SDK | Handoff planning before agent transfer |
| Google ADK | `planner` agent type with explicit plan generation |

### Sample Telemetry

```json
{
  "name": "plan task_decomposition",
  "kind": "INTERNAL",
  "attributes": {
    "gen_ai.operation.name": "plan",
    "gen_ai.plan.strategy": "task_decomposition",
    "gen_ai.plan.step.count": 3,
    "gen_ai.agent.name": "research_agent"
  },
  "events": [],
  "links": []
}
```

With opt-in content capture:

```json
{
  "name": "plan task_decomposition",
  "kind": "INTERNAL",
  "attributes": {
    "gen_ai.operation.name": "plan",
    "gen_ai.plan.strategy": "task_decomposition",
    "gen_ai.plan.step.count": 3,
    "gen_ai.plan.steps": [
      "Search web for recent papers",
      "Summarize top 5 results",
      "Cross-reference with existing knowledge"
    ],
    "gen_ai.plan.goal": "Find recent advances in LLM observability"
  }
}
```

### Implementation

Working implementation exists in AgentTelemetry (PyPI: `agenttelemetry`)
across 7 framework adapters, with automated classification for LangChain
and LlamaIndex.

### Why Not Use Existing Conventions?

- `invoke_agent` captures *that* an agent ran, not *what it planned*
- `chat` captures the LLM call that generates a plan, but not the planning
  *intent* — you cannot distinguish "LLM call for planning" from "LLM call
  for answering" without a parent planning span
- Issue #2665 proposes `gen_ai.task.kind: planning` as a task attribute, but
  tasks and plans are different concepts — a task is assigned work, a plan is
  a strategy for completing it
```

---

## PR 2: Delegation Span

### Title
`Add semantic conventions for GenAI delegation span`

### Description

```markdown
Fixes #UMBRELLA_ISSUE_NUMBER

## Summary

Adds the `delegate` operation for agent-to-agent work assignment spans.

Multi-agent systems (CrewAI crews, AutoGen group chats, OpenAI Agents SDK
handoffs) involve agents delegating sub-tasks to other agents. This delegation
is currently invisible — you see two `invoke_agent` spans but not the
relationship between them. The `delegate` span captures who delegated to whom
and why, enabling **circular delegation detection** and agent collaboration
analysis.

## Span Definition

| Field | Value |
|-------|-------|
| **Span Name** | `delegate {gen_ai.agent.name}` (target agent) |
| **Span Kind** | `INTERNAL` |
| **Operation Name** | `delegate` |

### Attributes

#### Required

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.operation.name` | string | MUST be `"delegate"` |
| `gen_ai.delegation.source.agent.name` | string | Name of the delegating agent |
| `gen_ai.delegation.target.agent.name` | string | Name of the agent receiving delegation |

#### Recommended

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.delegation.source.agent.id` | string | Unique ID of the delegating agent |
| `gen_ai.delegation.target.agent.id` | string | Unique ID of the receiving agent |
| `gen_ai.delegation.type` | string | Delegation pattern. Well-known values: `handoff`, `sub_task`, `escalation`, `round_robin`, `broadcast` |

#### Opt-In (sensitive)

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.delegation.reason` | string | Why this agent was chosen for delegation |
| `gen_ai.delegation.task` | string | Description of the delegated task |

### Span Hierarchy

Delegation spans are children of the source agent's span and parents of
the target agent's span:

```
invoke_agent "orchestrator"
├── plan "task_decomposition"
├── delegate "researcher"                ← NEW
│   └── invoke_agent "researcher"
│       ├── chat "gpt-4o"
│       └── execute_tool "web_search"
├── delegate "writer"                    ← NEW
│   └── invoke_agent "writer"
│       └── chat "gpt-4o"
└── reflect "evaluate_completeness"
```

### Safety: Circular Delegation Detection

The `source.agent.name` and `target.agent.name` attributes enable
**real-time circular delegation detection** via directed graph cycle analysis.
Without these attributes, A→B→C→A delegation cycles are invisible until
they exhaust resources.

Example anomaly:
```
delegate: orchestrator → researcher
delegate: researcher → analyst
delegate: analyst → orchestrator    ← CYCLE DETECTED
```

This is implemented and validated in AgentTelemetry's circuit breaker module,
which detects 4/4 circular delegation faults in real-time using DFS on the
delegation graph.

### Cross-Provider Evidence

| Framework | How Delegation Manifests |
|-----------|------------------------|
| CrewAI | `Task.delegate()` with `coworker` parameter |
| AutoGen | `GroupChat` agent-to-agent message routing |
| OpenAI Agents SDK | `Handoff` objects with target agent |
| Anthropic MCP | Server-to-server tool delegation |
| Google ADK | `transfer_to_agent()` function |
| LangGraph | `send()` to route to sub-graphs |

### Sample Telemetry

```json
{
  "name": "delegate researcher",
  "kind": "INTERNAL",
  "attributes": {
    "gen_ai.operation.name": "delegate",
    "gen_ai.delegation.source.agent.name": "orchestrator",
    "gen_ai.delegation.target.agent.name": "researcher",
    "gen_ai.delegation.type": "sub_task"
  }
}
```

### Why Not Use Existing Conventions?

- `invoke_agent` shows agent invocation but not the *delegation relationship*
  between two agents
- `invoke_workflow` coordinates multiple agents but does not capture pairwise
  delegation semantics (who delegated to whom, why)
- Issue #3575 proposes a `delegates_to` span link, but links are optional
  metadata — a dedicated span captures duration, attributes, and enables
  real-time circuit breaker policies
```

---

## PR 3: Reflection Span

### Title
`Add semantic conventions for GenAI reflection span`

### Description

```markdown
Fixes #UMBRELLA_ISSUE_NUMBER

## Summary

Adds the `reflect` operation for agent self-evaluation and reasoning
assessment spans.

Agentic systems increasingly use reflection loops — the agent evaluates its
own output, checks for hallucinations, assesses completeness, and decides
whether to iterate. These reflection steps are critical for understanding
agent behavior but are currently invisible. The `reflect` span captures
self-critique, quality checks, and reasoning chain evaluation.

## Span Definition

| Field | Value |
|-------|-------|
| **Span Name** | `reflect {gen_ai.reflection.type}` |
| **Span Kind** | `INTERNAL` |
| **Operation Name** | `reflect` |

### Attributes

#### Required

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.operation.name` | string | MUST be `"reflect"` |

#### Recommended

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.reflection.type` | string | Type of reflection. Well-known values: `self_critique`, `quality_check`, `completeness_check`, `hallucination_check`, `consistency_check`, `goal_evaluation` |
| `gen_ai.reflection.verdict` | string | Outcome of the reflection. Well-known values: `pass`, `fail`, `needs_improvement`, `acceptable`, `retry` |
| `gen_ai.reflection.iteration` | int | Iteration number in a reflection loop (1-indexed) |
| `gen_ai.agent.name` | string | Name of the reflecting agent |

#### Opt-In (sensitive)

| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.reflection.reasoning` | string | The reasoning chain or self-critique text |
| `gen_ai.reflection.confidence` | double | Confidence score (0.0 to 1.0) |
| `gen_ai.reflection.criteria` | string[] | Evaluation criteria used |

### Span Hierarchy

Reflection spans typically appear after execution spans, as siblings of
tool calls or at the end of an agent's processing:

```
invoke_agent "research_agent"
├── plan "task_decomposition"
├── chat "gpt-4o"
├── execute_tool "web_search"
├── reflect "completeness_check"         ← NEW (iteration 1)
│   └── chat "gpt-4o"                   (LLM evaluates output)
├── execute_tool "web_search"            (retry based on reflection)
└── reflect "quality_check"              ← NEW (iteration 2)
    └── chat "gpt-4o"
```

### Why This Matters: Reasoning Loop Detection

In our study of 112 SWE-bench instances, **75% of agent failures were
reasoning loops** (95% CI [66%, 82%]) — the agent reflects, finds its output
insufficient, retries, reflects again, and never converges.

Without reflection spans, these loops appear as repeated LLM calls with no
visible cause. With reflection spans, you can:

1. **Count iterations** via `gen_ai.reflection.iteration`
2. **Detect non-convergence** via repeated `verdict: needs_improvement`
3. **Set circuit breaker policies** (e.g., halt after 5 reflection iterations)
4. **Attribute tool decisions** — link which reflection triggered which retry

### Cross-Provider Evidence

| Framework | How Reflection Manifests |
|-----------|------------------------|
| LangChain | `OutputParser` retry chains, `LLMChain` self-critique |
| AutoGen | `ReflectionAgent`, `is_termination_msg` checks |
| CrewAI | `quality_review` step in task execution |
| LlamaIndex | `ResponseEvaluator`, `FaithfulnessEvaluator` |
| Google ADK | Evaluation loops with `before_model_callback` |
| DSPy | `Assert` / `Suggest` with backtracking |

### Relationship to Issue #3419 (ReAct Iteration Spans)

Issue #3419 discusses adding spans for ReAct (Reason-Act) iterations. The
`reflect` span directly addresses the "Reason" component — it captures the
agent's self-assessment between action steps. Combined with `plan` (for the
"planning" phase) and existing `execute_tool` (for the "Act" phase), the
full ReAct loop becomes observable:

```
Plan → Act → Reflect → Plan → Act → Reflect → ...
```

### Sample Telemetry

```json
{
  "name": "reflect quality_check",
  "kind": "INTERNAL",
  "attributes": {
    "gen_ai.operation.name": "reflect",
    "gen_ai.reflection.type": "completeness_check",
    "gen_ai.reflection.verdict": "needs_improvement",
    "gen_ai.reflection.iteration": 2,
    "gen_ai.agent.name": "research_agent"
  }
}
```

With opt-in content capture:

```json
{
  "name": "reflect quality_check",
  "kind": "INTERNAL",
  "attributes": {
    "gen_ai.operation.name": "reflect",
    "gen_ai.reflection.type": "quality_check",
    "gen_ai.reflection.verdict": "pass",
    "gen_ai.reflection.iteration": 3,
    "gen_ai.reflection.confidence": 0.92,
    "gen_ai.reflection.reasoning": "All 3 sub-tasks completed. Sources verified against knowledge base. Coverage satisfactory.",
    "gen_ai.reflection.criteria": ["completeness", "accuracy", "source_quality"]
  }
}
```

### Decision Attribution

Reflection spans enable **decision attribution** — linking tool calls to the
reasoning that triggered them. When a reflection span with
`verdict: needs_improvement` is followed by a tool call, observability tools
can show: "The agent re-ran web_search because its quality check found
incomplete coverage."

This is implemented in AgentTelemetry's `DecisionAttributor` analysis module,
which finds REASONING spans adjacent to tool calls and extracts the reasoning
chain.

### Why Not Use Existing Conventions?

- `chat` captures the LLM call within a reflection step, but not the
  reflection *intent* or *verdict*
- `gen_ai.evaluation.*` (PR #2563) evaluates model output quality from an
  external perspective — reflection is the agent evaluating *its own* output
- Issue #2665's `gen_ai.task.kind: reasoning` is a task classification, not
  a span for self-evaluation with verdicts and iteration tracking
- Issue #3419 identifies the need but proposes no concrete span definition
```

---

## Also: Comment on Existing PRs

### Comment on PR #3233 (Guardrails)

```markdown
Great proposal! We have a working implementation of guardrail spans in
AgentTelemetry (PyPI: `agenttelemetry`) across 7 agent frameworks. Our
empirical data from 2,940 configurations confirms that guardrail spans are
uniquely necessary for fault detection — our ablation study shows a
block-diagonal pattern where guardrail spans detect fault types that no
other span kind can.

Happy to share implementation experience if helpful.
```

### Comment on PR #3250 (Memory)

```markdown
+1 on this proposal. We implement memory spans in AgentTelemetry with a
similar scope attribute (NONE/METADATA_ONLY/FULL privacy levels). Our
experience across 7 framework adapters confirms the CRUD lifecycle you've
defined matches how frameworks actually use memory.

One observation: in our SWE-bench study (112 instances), memory access
patterns were diagnostic for agent state management failures — agents
that read the same memory repeatedly without updating it were strong
indicators of stuck loops.
```

### Comment on Issue #2664 (Agentic Systems)

```markdown
We'd like to contribute concrete span definitions for three of your six
proposed domains:

- **Tasks → `plan` span** — captures planning/task decomposition with
  strategy and step count attributes
- **Teams → `delegate` span** — captures agent-to-agent delegation with
  source/target identification, enabling circular delegation detection
- **Agents → `reflect` span** — captures self-evaluation with verdict,
  iteration count, and reasoning chain

These are backed by empirical evidence: ablation study across 2,940
configurations showing each span kind is uniquely necessary, inter-rater
reliability kappa=0.904, and 112 SWE-bench traces demonstrating that 75%
of agent failures are reasoning loops detectable via planning+reflection spans.

Working implementation: AgentTelemetry (PyPI: `agenttelemetry`) with
adapters for LangChain, CrewAI, AutoGen, LlamaIndex, OpenAI, Anthropic.

We're preparing individual PRs for each span kind. Would love feedback on
the approach.
```

---

## Current OTel Landscape (Reconnaissance — 2026-03-26)

### Already in `main`
- `create_agent`, `invoke_agent`, `invoke_workflow`, `execute_tool` operations
- `gen_ai.agent.id`, `gen_ai.agent.name`, `gen_ai.agent.description`, `gen_ai.agent.version`
- Full docs at `docs/gen-ai/gen-ai-agent-spans.md`

### NOT in repo (our contribution space)
- **`plan`** — not proposed anywhere
- **`delegate`** — #3575 proposes `delegates_to` span link but not a span
- **`reflect`** — #3419 discusses ReAct iterations but no span definition

### Key risk: Issue #3575 (Grouping Primitives, opened Mar 25)
Proposes `gen_ai.group.id/type` + typed span links as lightweight alternative to new
span types. Our counter-argument: plan/delegate/reflect are distinct *operations* with
own duration, attributes, hierarchy — like `execute_tool`, not just groupings.

### Open PRs we should support
- **PR #3233 (Guardrails):** `apply_guardrail` span — active review, key reviewers: aabmass, habibam
- **PR #3250 (Memory):** 5 memory ops — reopened, key reviewers: lmolkova, trask

### Key people
- @lmolkova (Liudmila Molkova — GenAI SIG lead)
- @trask (active semconv reviewer)
- @nagkumar91 (author of #3233 and #3250 — potential ally)
- @KazChe (author of #3575 — need to engage respectfully)

---

## Execution Checklist

### Phase 1: Reconnaissance (DONE — 2026-03-26)
- [x] Check current state of all referenced issues/PRs
- [x] Check existing `gen_ai.agent.*` conventions in main
- [x] Identify #3575 as competing/complementary approach
- [x] Write up findings in `RECONNAISSANCE.md`

### Phase 2: Community Engagement (draft comments in `DRAFT_COMMENTS.md`)
- [ ] Day 1: Comment on issue #2664 with contribution offer
- [ ] Day 2: Comment on issue #3419 (ReAct iterations) with empirical evidence
- [ ] Day 3: Comment on PR #3233 (guardrails) with empirical support
- [ ] Day 4: Comment on PR #3250 (memory) with empirical support
- [ ] Join CNCF Slack (#otel-genai, #otel-semconv)
- [ ] Attend 1-2 GenAI SIG meetings

### Phase 3: Umbrella Issue (after community engagement)
- [ ] Open umbrella issue "Semantic Conventions for GenAI Agent Cognitive Operations"
- [ ] Cross-reference #2664, #1530, #3575, #3419

### Phase 4: Individual PRs (following weeks)
- [ ] PR 1: Planning span (`plan`) — least controversial
- [ ] PR 2: Delegation span (`delegate`) — safety angle
- [ ] PR 3: Reflection span (`reflect`) — most novel

### Phase 5: YAML + Docs (with each PR)
- [ ] Add span definitions to `model/gen-ai/spans.yaml`
- [ ] Add attribute definitions to `model/gen-ai/registry.yaml`
- [ ] Add documentation to `docs/gen-ai/`
- [ ] Update attribute registry in `docs/attributes-registry/`

### Preparation (before Phase 4)
- [ ] Fork `open-telemetry/semantic-conventions`
- [ ] Study YAML schema format from existing `model/gen-ai/spans.yaml`
- [ ] Prepare sample telemetry JSON for each span kind
- [ ] Link to AgentTelemetry repo as reference implementation
