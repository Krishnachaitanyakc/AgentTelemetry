# Critical Review of Updated Plan — 2026-04-11

*Produced by adversarial review agent. All blockers, weaknesses, and blind spots
documented below must be addressed before proceeding.*

---

## BLOCKERS (Issues that will kill the plan if not addressed)

### BLOCKER 1: Zero Reviewer Engagement May Be a Content Signal, Not a Process Problem

PR #3594 has been open for 9 days with zero reviewer comments. Maintainers trask
and lmolkova are **aware** (label added Apr 3, project board moved Apr 6) but have
not engaged with content.

**Alternative interpretation the plan refuses to consider:** The maintainers looked
at it, understood it, and deprioritized it. This is distinct from "hasn't noticed
it." A Slack ping will not fix deprioritization.

**Evidence:**
- trask merged #3514 (invoke_agent split) in the same timeframe
- lmolkova approved #3607 (streaming) recently
- #3473 (invoke_agent SERVER span) had zero engagement and was stale-botted — an
  exact precedent

**Fix:** Before pinging in Slack, find a concrete maintainer statement expressing
need for planning visibility. If none exists, the PR is solving a problem the
contributor defined, not the community. Attend GenAI SIG meeting FIRST (not as last
resort) to gauge whether this is on anyone's roadmap.

---

### BLOCKER 2: The Auto-Instrumentable Table Has Dishonest Entries

The cross-provider table claims "Yes" for auto-instrumentability across 5 frameworks.
At least 3 are misleading:

1. **LangChain: `AgentExecutor._take_next_step()`** — Private method on a deprecated
   class. LangChain has moved to LangGraph. Not stably auto-instrumentable.
2. **AutoGen: `GroupChatManager.run_chat()`** — Speaker selection is routing, not
   planning (task decomposition). Conceptual conflation.
3. **OpenAI Agents SDK: `Runner.run()` — handoff evaluation** — Handoff evaluation
   is delegation routing, not planning.

**Why fatal:** lmolkova's #1 rejection criterion (PATTERNS.md) is "cannot be set by
instrumentation libs automatically." If a reviewer checks even one claim and finds it
overstated, the entire table's credibility collapses.

**Fix:** Change LangChain, AutoGen, OpenAI Agents SDK to "Partial" with honest
descriptions. Two credible "Yes" entries (LlamaIndex, CrewAI) are stronger than six
inflated ones.

---

### BLOCKER 3: The Span Hierarchy Diagram Depicts a Pattern Most Frameworks Don't Produce

The PR shows a clean "plan-then-execute" hierarchy. But most frameworks (LangChain
ReAct, AutoGen GroupChat, OpenAI Agents SDK) do NOT work this way:

- LangChain ReAct: decides ONE action per iteration, no multi-step plan
- AutoGen GroupChat: routes to next speaker, not task decomposition
- OpenAI Agents SDK: handoff routing, not planning

Only CrewAI (`planning=True`) and LlamaIndex (`SubQuestionQueryEngine`) actually
implement the depicted pattern.

**Fix:** Either honestly depict the hierarchy for single-step agents, or scope the
claim: "Most useful for agents with explicit multi-step planning. For single-step
agents, wraps the action-selection LLM call."

---

## MAJOR WEAKNESSES

### WEAKNESS 1: "Zero New Attributes" Is a Double-Edged Sword

If the plan span adds no new attributes, a maintainer can argue: "If this span has
no unique attributes, it's purely structural. Structure is what grouping primitives
(#3575) or a `gen_ai.chat.purpose = 'planning'` attribute solves. Why add a new
span type?"

**Counter:** The plan span's value is duration measurement and parent-child hierarchy.
You cannot model a parent span as an attribute on its own child. **This must be
stated upfront in the PR, not as a response to pushback.**

### WEAKNESS 2: Sequential Submission Creates 6-12 Month Timeline

Plan → wait → reflect → wait → delegation = 6-12 months. Each stage depends on
the previous succeeding. Over that time: landscape shifts, #3575 could gain consensus,
maintainers could change.

**Mitigation:** Consider submitting delegation attribute in parallel (just an attribute,
doesn't trigger N+1 pushback). Or flip submission order — delegation attribute first
(highest probability, 50-60%), establishes credibility, then plan.

### WEAKNESS 3: Reference Implementation Has Minimal Credibility

AgentTelemetry on PyPI has minimal adoption. "Anyone can write a library that emits
spans matching their own proposal." The SIG will care about cross-framework analysis
honesty, not the reference library.

### WEAKNESS 4: No User Story From a Real User

The PR describes a structural gap but no concrete user scenario. Who suffers? What
decision can't they make?

**Fix:** Add: "When an agent produces an incorrect answer, an operator examining
the trace cannot determine whether the agent planned correctly but executed poorly,
or planned poorly from the start. The remediation is different: bad planning needs
prompt engineering; bad execution needs tool/retrieval fixes."

### WEAKNESS 5: lmolkova's #3575 Pushback Is Overinterpreted as Favorable

"What is the real problem?" is lmolkova's standard challenge to ANY proposal. She
asked it about grouping; she'll ask it about plan spans. Her skepticism of #3575
does not imply endorsement of our approach.

**Fix:** Stop citing lmolkova's #3575 comments as validation. Prepare to answer
"what is the real problem?" ourselves.

---

## DEVIL'S ADVOCATE CHALLENGES — Key Responses

### Most Dangerous: "Why not scope down to an attribute like #3540 skills?"

**Challenge strength: 9/10.** The skill span was proposed as a new operation and
the SIG said "just add attributes to execute_tool."

**Response:** "A skill maps 1:1 to a tool — it IS the tool execution with extra
context, so attributes work. A plan is the PARENT of multiple child spans (the chat
call that generates it AND the tool calls it produces). You cannot model a parent
span as an attribute on its own child." **This is the strongest argument but it's
currently buried in the PR description.**

### Second Most Dangerous: "Reflect is auto-instrumentable in only 2-3/6 frameworks"

**Challenge strength: 9/10.** Only LlamaIndex (Yes), LangChain (Yes), AutoGen
(Partial). CrewAI (No), Google ADK (No). Below the 3-framework minimum.

**Response:** Most likely outcome: "come back when more frameworks support it" or
scoping down to an attribute. Be prepared for both.

---

## STRATEGIC BLIND SPOTS

1. **No contingency for "scoped down to attributes"** — the most likely negative
   outcome is not rejection but "let's use `gen_ai.chat.purpose = 'planning'` instead."
   Need a prepared response AND willingness to accept as partial win.

2. **No champion strategy** — every successful external PR had a maintainer who
   actively shepherded it. Who is ours? nagkumar91 is a potential ally but not a
   maintainer.

3. **GenAI agent conventions may be deprioritized** — the SIG is focused on foundation
   model conventions. Agent work may not be urgent until H2 2026.

4. **Community engagement comments may look like agenda-setting** — 5 strategic
   comments → PR submission pattern is transparent. Better to have one deeply
   substantive contribution.

5. **Stale bot survival strategy creates low-value activity** — "add a substantive
   comment every 7 days" is transparent busywork. Better to make genuinely useful
   changes then let stale bot close if needed (can always reopen).

---

## VERDICT

| Proposal | Merge Probability | Rationale |
|----------|-------------------|-----------|
| Plan span | **35-45%** | Novel, no competition, but auto-instrumentability overstated, no maintainer interest expressed |
| Reflect span | **15-25%** | Only 2/6 frameworks auto-instrumentable, "come back later" most likely response |
| Delegation attribute | **50-60%** | Lightest-weight, just an attribute. Paradoxically highest probability despite planned last |

## TOP 3 ACTIONS TO INCREASE SUCCESS

1. **Fix the auto-instrumentability table immediately.** Honest "Partial" entries are
   more credible than inflated "Yes" entries. Addresses the #1 rejection criterion.

2. **Add a concrete user story / debugging scenario to the PR description.** Not
   "planning is invisible" but "operator cannot determine if failure was planning vs
   execution, and the fix is different." Addresses lmolkova's "what is the real problem?"

3. **Attend the next GenAI SIG meeting and present plan span as a 2-minute topic.**
   Don't wait until Apr 25. Meeting attendance accelerates review (cited in MCP PR
   #2083 history). Establishes community participation.

**Bonus:** Consider flipping submission order — delegation attribute FIRST (highest
probability), get it merged, establish credibility, THEN submit plan.
