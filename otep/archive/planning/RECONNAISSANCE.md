# OTEP Reconnaissance — 2026-03-26

## Phase 1: Current State of OTel GenAI Agent Conventions

### What Already Exists in `main`

The OTel `semantic-conventions` repo already has agent-related conventions merged:

**Agent span types (in `model/gen-ai/spans.yaml`):**
| Operation | Span Kind | Description |
|-----------|-----------|-------------|
| `create_agent` | CLIENT | Agent initialization (remote services) |
| `invoke_agent` | CLIENT/INTERNAL | Agent execution |
| `invoke_workflow` | INTERNAL | Multi-agent coordinated processes |
| `execute_tool` | INTERNAL | Tool execution within agents |

**Agent attributes (in `model/gen-ai/registry.yaml`):**
| Attribute | Type | Description |
|-----------|------|-------------|
| `gen_ai.agent.id` | string | Unique identifier |
| `gen_ai.agent.name` | string | Human-readable name |
| `gen_ai.agent.description` | string | Free-form description |
| `gen_ai.agent.version` | string | Version identifier |
| `gen_ai.workflow.name` | string | Workflow name |
| `gen_ai.conversation.id` | string | Conversation identifier |

**Docs:** `docs/gen-ai/gen-ai-agent-spans.md` exists with full documentation.

### What Does NOT Exist (Our Opportunity)

The following are **not** in the repo and represent our contribution space:

| Concept | Status | Notes |
|---------|--------|-------|
| Planning spans (`plan`) | **Not proposed** | No issue, no PR |
| Delegation spans (`delegate`) | **Not proposed** | #3575 proposes `delegates_to` span link but not a span |
| Reflection spans (`reflect`) | **Not proposed** | #3419 discusses ReAct iterations but no span definition |
| Guardrail spans | **PR #3233 open** | `apply_guardrail` — active review, not merged |
| Memory spans | **PR #3250 open** | 5 memory operation spans — reopened, active review |

### Critical Implication for Our Strategy

Our OTEP_PLAN.md proposed 3 new span kinds: `plan`, `delegate`, `reflect`. This still holds — **none of these exist in the repo**. However, the namespace must use `gen_ai.*` (not `llm.*` or `agent.*` as in our comprehensive OTEP). Our span proposals should follow the pattern:

```
gen_ai.operation.name = "plan" | "delegate" | "reflect"
```

This is consistent with existing operations: `create_agent`, `invoke_agent`, `execute_tool`, `invoke_workflow`.

---

## Phase 1.2: Status of All Referenced Issues/PRs

### Issue #2664 — Agentic Systems (Meta-issue)
- **Status:** Open
- **Activity:** Mostly stalled. Only Tasks (`gen_ai.task.*`, #2665) has progressed. Five of six areas (Actions, Agents, Teams, Artifacts, Memory) still TBD.
- **Key comment (Sep 2025):** Cisco engineers suggested dependency on #1688 (workflow/tasks as generic concepts).
- **Implication:** This is the right umbrella to anchor our contributions. Low activity = opportunity to drive the conversation.

### Issue #1530 — Agent Framework Semantic Convention
- **Status:** Open, 10 comments
- **Activity:** Framework developers (AG2, Langtrace) have expressed interest. Discussion about separating "Agent" vs "Agent Framework" conventions.
- **Implication:** Shared motivation with our work. Good to reference but not the primary venue for our PRs.

### Issue #3575 — Grouping Primitives (NEW — Mar 25, 2026)
- **Status:** Open, 4 comments, brand new
- **Author:** KazChe (kam chehresa)
- **Proposal:** Instead of new span types, use:
  1. `gen_ai.group.id` + `gen_ai.group.type` attributes on existing spans
  2. Typed span links: `triggered_by`, `delegates_to`, `evaluates`
- **Key argument:** Solves the "N+1 span type problem" — each new pattern getting its own span type creates fragmentation
- **CRITICAL:** This is a **competing approach** to our individual span PRs. We need to address it directly — argue that planning/delegation/reflection are distinct *operations* (like `execute_tool` or `invoke_agent`), not just *groupings* of existing spans. A planning span has its own duration, attributes (strategy, step count), and hierarchy. A span link cannot capture that.

### Issue #3419 — ReAct Iteration Spans
- **Status:** Open, Todo
- **Activity:** SIG member (Mar 17, 2026) suggested any such span should be "opt-in" due to volume concerns. Also noted it could be "derived from llm response (tool_call) and the execute span next to it."
- **Implication:** There's skepticism about adding spans. Our empirical evidence (75% of SWE-bench failures are reasoning loops, only detectable with reflection spans) directly addresses the "can be derived" argument.

### PR #3233 — Guardrails Semantic Conventions
- **Status:** Open, active review
- **Author:** nagkumar91
- **Key conventions:** `apply_guardrail` span, `gen_ai.guardian.*` attributes, `gen_ai.security.decision.*` attributes
- **Key reviewers:** aabmass, habibam, Cirilla-zmh
- **Implication:** Our guardrail_check span kind maps to their `apply_guardrail`. We can offer empirical validation.

### PR #3250 — Memory Operations Semantic Conventions
- **Status:** Open, reopened (was auto-closed for lacking SIG sponsor)
- **Author:** nagkumar91
- **Key conventions:** 5 memory operation spans (`create_memory_store`, `search_memory`, `update_memory`, `delete_memory`, `delete_memory_store`), `gen_ai.memory.scope` attribute
- **Key reviewers:** lmolkova, trask, JWinermaSplunk
- **Implication:** Our memory_access span kind maps to their memory operations. The `scope` attribute parallels our privacy levels. We can offer empirical support from SWE-bench data.

---

## Updated Strategy Assessment

### Strengths of Our Position
1. **Empirical evidence** — nobody else has 2,940-config ablation studies, SWE-bench case studies, or inter-rater reliability data
2. **Working implementation** — AgentTelemetry on PyPI across 7 frameworks
3. **Clear gap** — plan/delegate/reflect are genuinely missing
4. **Aligned namespace** — our OTEP_PLAN.md already uses `gen_ai.operation.name` values

### Risks to Address
1. **#3575 (Grouping Primitives)** could gain traction and the SIG might prefer lightweight grouping over new span types
2. **Volume concerns** (#3419 discussion) — we need to argue these spans are worth the overhead (our overhead data: p50=11.7us)
3. **Scope creep** — the comprehensive OTEP (`agent-semantic-conventions.md`) proposes too much at once. Stick to the incremental approach.

### Recommended Adjustment
- **Do NOT submit the comprehensive OTEP** (`agent-semantic-conventions.md`) to the `oteps` repo. It proposes new namespaces (`llm.*`, `agent.*`) that conflict with established `gen_ai.*` conventions and will be rejected.
- **Do submit 3 focused PRs** to `semantic-conventions` repo using the OTEP_PLAN.md approach.
- **Engage with #3575** — acknowledge the grouping approach but argue that cognitive operations (plan/delegate/reflect) are first-class operations, not groupings.
