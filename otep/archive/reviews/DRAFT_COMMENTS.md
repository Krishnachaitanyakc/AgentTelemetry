# Draft Comments for OTel Community Engagement (v3)

*Revised 2026-03-31. Fixes from plagiarism/authenticity review: varied structure, reduced
self-promotion, honest research framing, thread-specific engagement, no repeated data.*

---

## Comment 1: Issue #3575 (Grouping Primitives)

**Post to:** https://github.com/open-telemetry/semantic-conventions/issues/3575
**Purpose:** Engage with competing approach. Establish complementarity.
**No AgentTelemetry link. No SWE-bench. Conversational tone.**

```markdown
The N+1 span type problem is real — I've been thinking about this exact tension while
working on agent instrumentation.

One case where I think grouping and dedicated operations solve different problems:

An agent planning phase. The agent calls an LLM to decompose a task, then executes each
step. You could tag those spans with `gen_ai.group.type = "plan"`, but you'd lose the
duration of the planning phase itself — how long did the agent spend deciding *what* to do
vs. actually doing it? The `chat` call that generates the plan is causally a *child* of
the planning decision, not a sibling that happens to share a group tag.

`execute_tool` exists as its own operation for the same reason — it could be a grouped
`chat` span, but tool-specific attributes and the timing of the tool phase justify a
dedicated operation.

So maybe: grouping for loose structural relationships (correlating spans in a ReAct round
or conversation turn), and dedicated operations where the phase has its own meaningful
duration and hierarchy. They'd work together rather than replace each other.

Where do you see the line between "this is just a grouping concern" and "this needs its
own operation"?
```

---

## Comment 2: Issue #2664 (Agentic Systems Meta-issue)

**Post to:** https://github.com/open-telemetry/semantic-conventions/issues/2664
**Purpose:** Introduce contribution intent. Only AgentTelemetry link across all 5 comments.
**Lead with the gap, not the library. Propose `plan` first, mention others briefly.**

```markdown
I've been instrumenting agent frameworks (LangChain, CrewAI, AutoGen, LlamaIndex, OpenAI
Agents SDK, Google ADK) for an observability library I maintain
([AgentTelemetry](https://github.com/Krishnachaitanyakc/AgentTelemetry)), and there's a
gap I keep hitting: operations that happen *between* `invoke_agent`, `execute_tool`, and
`chat`.

The clearest example is planning. Every framework has some version of it:

| Framework | How planning manifests |
|-----------|----------------------|
| LangChain | `AgentExecutor._take_next_step()` — reasoning before tool calls |
| LlamaIndex | `SubQuestionQueryEngine.query()` — decomposition before sub-queries |
| CrewAI | `Crew.kickoff()` with `planning=True` — explicit planning phase |
| AutoGen | `GroupChatManager.run_chat()` — speaker/action selection |
| OpenAI Agents SDK | `Runner.run()` — handoff evaluation before transfer |
| Google ADK | `planner` agent type with explicit `plan()` method |

But in traces, the LLM call that generates a plan looks identical to the LLM call that
generates a final answer — both are `chat` spans. You can't tell why the agent called the
LLM without a parent span marking the intent.

I'd like to start with a PR for a `plan` operation (`gen_ai.operation.name = "plan"`)
using zero new attributes — just a new enum member and span definition reusing
`gen_ai.agent.name` and `gen_ai.system`. Following the pattern of PR #3233 and PR #3250.

There are similar gaps for delegation and reflection that I'd address in follow-up PRs,
but I want to start small. Would a focused `plan` PR be the right entry point, or does
the SIG prefer a broader discussion issue first?
```

---

## Comment 3: Issue #3419 (ReAct Iteration Spans)

**Post to:** https://github.com/open-telemetry/semantic-conventions/issues/3419
**Purpose:** Address "can be derived" with ONE deep failure case. No AgentTelemetry link.
**Reference @lmolkova's March 17 comment directly.**

```markdown
@lmolkova's point about derivation from tool_call patterns is fair for the simple case,
but there's a failure mode where it breaks down completely.

In a study we conducted on SWE-bench agent traces (112 instances across 12 repos), the
dominant failure pattern wasn't tool-related at all — it was reflection-only loops. The
agent evaluates its own output, decides it's insufficient, calls the LLM again, evaluates
again, never converges. There's no tool call in the loop, so there's no tool→LLM pair to
derive iteration boundaries from. Every span in the loop is just `chat`.

This accounted for roughly 75% of the failures we observed. The agent is stuck, burning
tokens, and the trace looks like a sequence of identical `chat` spans with no indication
anything is wrong.

A `reflect` operation with a simple pass/fail verdict would make these loops immediately
visible — you'd see repeated `reflect` spans with `verdict: fail` and could set a circuit
breaker policy on iteration count.

On the opt-in question — agreed. These should only be emitted when detailed debugging is
enabled. The overhead per span is negligible relative to LLM latency, but the volume
concern is valid.
```

---

## Comment 4: PR #3233 (Guardrails)

**Post to:** https://github.com/open-telemetry/semantic-conventions/pull/3233
**Purpose:** Short, specific, reference existing discussion. No AgentTelemetry link.
**Note: PR moved to codeowners approval on March 27 — acknowledge progress.**

```markdown
Good to see this moving toward approval.

One thing I've been thinking about from @Cirilla-zmh's point about span kind — the
CLIENT vs INTERNAL distinction matters for hierarchy too. When the guardrail is
in-process (INTERNAL), it works well as a sibling of the `chat` span it evaluates:

```
invoke_agent "support_agent"
├── chat "gpt-4o"
├── apply_guardrail "pii_filter"
└── execute_tool "send_reply"
```

But when it's a remote service (CLIENT), the guardrail span is really wrapping a
network call and might need to be a parent of the service-side span. Is that handled
by the client/server split, or does the instrumentation need to make that choice?
```

---

## Comment 5: PR #3250 (Memory)

**Post to:** https://github.com/open-telemetry/semantic-conventions/pull/3250
**Purpose:** Genuinely short +1. Reference @agent-morrow's March 30 compliance comment.
**No AgentTelemetry link. No SWE-bench.**

```markdown
+1 on the CRUD lifecycle. The `gen_ai.memory.scope` attribute is particularly useful —
in testing, repeated `search_memory` calls with no intervening `update_memory` turned
out to be a reliable signal for stuck agent loops.

On @agent-morrow's GDPR/retention point — I think that's worth a follow-up PR rather
than blocking this one. The core memory operations are provider-agnostic; compliance
attributes are inherently jurisdiction-specific and would benefit from their own
focused discussion.
```

---

## Posting Order

| Day | Target | Unique contribution |
|-----|--------|-------------------|
| 1 | #3575 (Grouping) | Grouping and operations are complementary — execute_tool precedent |
| 2 | #2664 (Agentic Systems) | Focused `plan` PR proposal with hookable API table |
| 3 | #3419 (ReAct Iterations) | Reflection-only loops as the failure case derivation can't catch |
| 4 | PR #3233 (Guardrails) | CLIENT vs INTERNAL hierarchy question |
| 5 | PR #3250 (Memory) | Support + recommend deferring compliance to follow-up |

---

## Pre-Posting Checklist

- [ ] Join CNCF Slack (https://communityinviter.com/apps/cloud-native/cncf) BEFORE posting
- [ ] Verify AgentTelemetry GitHub link resolves
- [ ] Re-read most recent 2-3 comments on each thread right before posting
- [ ] Check if any PRs have been merged since this was drafted
