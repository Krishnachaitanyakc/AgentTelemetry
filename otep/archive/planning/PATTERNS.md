# OTel Proposal Patterns — Synthesized Learnings

*Compiled 2026-03-26 from analysis of 10 merged PRs, 10 rejected/controversial proposals,
and 20+ open issues/PRs in the OpenTelemetry semantic-conventions repository.*

---

## 1. What Gets Accepted

### Structure
- **"Fixes #NNNN"** referencing a specific GitHub issue
- **Small, focused scope** — one operation per PR, follow-up issues for future work
- **Cross-provider comparison table** showing how 3+ providers handle the concept
  (OpenAI, Anthropic, Google minimum)
- **Reference implementation** linked in at least one language (Python, Java, .NET)
- **Changelog entry** (`.chloggen/*.yaml`) — mandatory, PRs without it stall
- **CONTRIBUTING.md checklist** explicitly followed

### Technical
- **Attributes that instrumentation can set automatically** — this is the #1 gate
- **Follows existing `gen_ai.*` namespace** — no new top-level namespaces
- **INTERNAL span kind for in-process operations** (not CLIENT unless remote)
- **Minimal attribute set** — lmolkova consistently pushes to remove non-essential attrs
- **Enum values validated across 3+ frameworks** — trask does deep framework audits
- **Sampling-relevant attributes** declared at span level

### Process
- **Maintainer-authored PRs merge in hours/days** (trask, lmolkova)
- **External contributor PRs take 16-96 days** — expect multi-month timelines
- **Stale bot closes after 7 days inactivity** — must stay engaged
- **SIG meeting attendance** accelerates review (cited in MCP PR #2083)

### Merge timeline examples
| PR | Author | Time to merge |
|----|--------|--------------|
| #3428 (agent.version) | trask (maintainer) | Same day |
| #3499 (response.model) | lmolkova (maintainer) | 6 days |
| #2881 (invoke_agent docs) | external | 16 days |
| #3163 (cached tokens) | external | 56 days |
| #2924 (retrieval) | external | 96 days |
| #2083 (MCP) | lmolkova | 277 days |

---

## 2. What Gets Rejected — The Killers

### Killer #1: "Cannot be set by instrumentation libs automatically"
- **Frequency:** Very common. Killed `agent.pattern` (#2394), `agent.role` (#2685)
- **lmolkova quote:** "We should avoid introducing attributes without clear meaning,
  criteria how to set it, or ability to populate them in instrumentation libraries."
- **Our risk:** `gen_ai.plan.strategy` and `gen_ai.reflection.type` could face this.
  Mitigation: show these are derivable from framework APIs (LangChain callbacks,
  CrewAI task types, AutoGen message routing).

### Killer #2: Semantic overlap with existing attributes
- **Frequency:** Common. Killed `session.id` (#2594, overlaps `conversation.id`),
  `agent.role` (#2685, overlaps `agent.name`/`agent.description`)
- **Our risk:** `delegate` could be seen as overlapping `invoke_agent`. Must clearly
  distinguish: invoke_agent = "agent ran", delegate = "agent A assigned work to agent B
  with intent/reason".

### Killer #3: Orphaned attributes (no span type references them)
- **Frequency:** Common. Killed `agent.node.*` (#2247)
- **lmolkova quote:** "We don't recommend defining attributes that are not referenced
  by any semantic conventions."
- **Our mitigation:** Always define span type + attributes together. Never submit
  attributes without a span definition that references them.

### Killer #4: Scope too broad
- **Frequency:** Architectural. Blocks `session.id` (cross-SIG), #1530 (scope unclear)
- **Our mitigation:** Individual PRs per span kind. Never bundle plan+delegate+reflect
  in one PR.

### Killer #5: Wrong span kind
- **Frequency:** Common. Killed task PR #2713 (used CLIENT instead of INTERNAL)
- **Rule:** INTERNAL for in-process operations, CLIENT for remote API calls
- **Our spans:** All three (plan/delegate/reflect) should be INTERNAL.

### Killer #6: Stale bot
- **Frequency:** Very common. 7 days of inactivity → auto-close
- **Our mitigation:** Respond to every review comment within 48 hours. Set calendar
  reminders.

### Killer #7: Namespace violations
- **Frequency:** Structural. Killed task PR #2713
- **Rules:** `.id`/`.name` are paired attributes. Use dot-separated snake_case.
  Follow existing patterns in registry.yaml.

---

## 3. Key People and Their Positions

| Person | Role | Position on Agent Spans |
|--------|------|------------------------|
| **@lmolkova** | GenAI SIG lead, codeowner | Gatekeeper. Favors minimal attrs, automatic instrumentability. Will push back hard on anything she can't envision setting in code. |
| **@trask** | SIG maintainer | Drives structural refactoring. Does deep framework audits. Fast merger for his own PRs. Values cross-provider evidence. |
| **@aabmass** | Active reviewer | Terminology precision (guardian→guardrail). Asks "what's the user story?" |
| **@nagkumar91** | External contributor | Author of guardrail (#3233) and memory (#3250) PRs. Potential ally — going through the same process we will. |
| **@Cirilla-zmh** | Active contributor | Provided key argument for splitting invoke_agent. Asks good questions about sampling. |
| **@KazChe** | Issue author | Proposed #3575 (grouping primitives). Competing philosophical approach. Engage respectfully. |

---

## 4. Critical Strategic Updates

### OTEPs Repository is ARCHIVED
The `open-telemetry/oteps` repository was **archived on Nov 17, 2025**. It is read-only.
No new OTEPs can be filed. The comprehensive OTEP in `agent-semantic-conventions.md`
cannot be submitted there. The correct venue is now:
- **Issues** on `open-telemetry/semantic-conventions` for proposals
- **PRs** on `open-telemetry/semantic-conventions` for implementations

### The N+1 Span Type Debate (#3575)
Issue #3575 argues against proliferating span types in favor of generic grouping
attributes + typed span links. Our counter-arguments:
1. `execute_tool` has its own span for similar reasons — tool-specific attributes and
   duration tracking justify it over a tagged `chat` span
2. Our ablation study shows each span kind is uniquely necessary for fault detection
3. Generic grouping can't capture duration, hierarchy, or span-specific attributes
4. Grouping and dedicated operations can coexist (grouping for loose structure,
   operations for distinct phases)

### Three Span Kinds Remain Unique
No one in the OTel community has proposed plan, delegate, or reflect operations:

| Our Span | Nearest OTel Equivalent | Gap |
|----------|------------------------|-----|
| `plan` | Nothing | Complete gap |
| `delegate` | A2A protocol (#3218) is wire-level only | Semantic gap |
| `reflect` | ReAct iterations (#3419) is broader | No self-evaluation span |

---

## 5. Checklist for Our PRs

Before submitting each PR, verify:

- [ ] References a GitHub issue ("Fixes #NNNN" or "Partially addresses #NNNN")
- [ ] Span kind is INTERNAL (not CLIENT)
- [ ] All attributes can be set by instrumentation libraries automatically
- [ ] Cross-provider table with 3+ frameworks showing how the concept manifests
- [ ] Reference implementation linked (AgentTelemetry on PyPI)
- [ ] Follows `gen_ai.*` namespace (not `llm.*` or `agent.*`)
- [ ] Minimal attribute set (Required + 2-3 Recommended, rest is Opt-In)
- [ ] Registry attributes defined in `registry.yaml` with `ref:` in `spans.yaml`
- [ ] Changelog entry in `.chloggen/`
- [ ] Stability = development on all new items
- [ ] Documentation section with `<!-- semconv -->` markers
- [ ] No orphaned attributes — every attribute referenced by the span definition
- [ ] Addresses #3575 argument (why this needs a span, not just grouping)
