# Updated Plan: Semantic Conventions Proposals — 2026-04-11

*Supersedes EXECUTION_PLAN.md. Based on comprehensive research of all open/closed
issues, merged/rejected PRs, and community dynamics as of 2026-04-11.*

---

## Executive Summary

PR #3594 (`plan` operation) has been open for 9 days with **zero reviewer
engagement**. All CI passes. Maintainers trask and lmolkova are aware (label
added, project board moved) but have not reviewed content. The landscape has
shifted significantly since our March 26 reconnaissance — most notably the
`invoke_agent` split (PR #3514, merged Apr 3) and lmolkova's skepticism of
the grouping primitives approach (#3575), which is favorable for dedicated
operation spans.

**Immediate priority:** Get reviewer engagement on #3594 before the stale bot
kills it (~14 days from last activity = around Apr 18).

---

## What Changed Since Last Reconnaissance (2026-03-26)

### Merged PRs (critical context)

| PR | Date | Impact |
|----|------|--------|
| #3514 | Apr 3 | **invoke_agent split into CLIENT + INTERNAL spans** — major structural change. Our plan span uses INTERNAL, consistent with this pattern. |
| #3595 | Apr 4 | gen_ai.tool.name now Required on execute_tool — minor but shows active evolution |
| #3249 | Mar 9 | invoke_workflow operation merged — establishes workflow tier above agents |
| #3436 | Mar 9 | GenAI exception event defined — error handling pattern established |

### Rejected/Closed PRs (lessons)

| PR | Date | Why |
|----|------|-----|
| #3473 | Apr 9 | **invoke_agent SERVER span rejected** — stale-botted, no maintainer engagement |
| #3540 | Apr 6 | Skill span → refined to attributes on execute_tool (SIG preference for reuse) |
| #2685 | — | Agent role attribute explicitly rejected by alexmojaki ("where are id, name, role, description all different?") |

### Issue Evolution

| Issue | Key Development |
|-------|----------------|
| #3575 (grouping) | **lmolkova pushed back**: "what is the real problem?" + Cirilla-zmh raised nested group concerns. 9 comments, no clear path forward. **Favorable for our approach.** |
| #3419 (ReAct) | Cirilla-zmh pushed back on derivation with nested agent/MCP examples. Our SWE-bench data (75% reflection loops) was cited. Still no PR. |
| #2912 (tasks/workflows) | `triage:accepted:ready-with-sig` label. invoke_workflow already merged from this. |
| #2664 (agentic systems) | Our Apr 2 comment is the most recent. Still no maintainer engagement. |
| #3602 (NEW) | gen_ai.agent.name on child spans for multi-agent cost attribution — gaining momentum |
| #3597 (NEW) | Agentic AI failure repair conventions — ambitious, no traction yet |

### Active Competing/Complementary PRs

| PR | Status | Relationship |
|----|--------|-------------|
| #3250 (memory) | **118 review comments**, active iteration | Complementary — demonstrates review depth required |
| #3233 (guardrails) | 35 review comments over 4 months | Complementary — sets precedent for agent capability spans |
| #3378 (tool defs) | 4 approvals, about to merge | Tangential |
| #3607 (streaming) | lmolkova approved | Tangential |
| #3553 (sampling attrs) | Draft + stale | Complementary — would benefit our plan span |

---

## Current State Assessment

### Strengths
1. **Plan span is genuinely unoccupied** — no competing PR, no alternative proposal
2. **lmolkova's skepticism of #3575 grouping** validates dedicated operations
3. **invoke_agent CLIENT/INTERNAL split** (#3514) establishes the pattern our plan span follows
4. **All CI passes** on #3594 — no technical blockers
5. **Community engagement done** — 5 comments posted across #3575, #2664, #3419, #3233, #3250
6. **SWE-bench evidence** was well-received in #3419 discussion

### Risks
1. **CRITICAL: Stale bot deadline ~Apr 18** — zero activity in 9 days, stale label at ~14-21 days, closure 7 days after
2. **Zero reviewer engagement** — trask and lmolkova have not reviewed our PR content
3. **Rebaseable is false** — may need rebase onto latest main after #3514 changes
4. **PR description inconsistency** — mentions workflow-based naming (`plan {gen_ai.workflow.name}`) but YAML may not implement it
5. **"N+1 span type" concern** — #3540 (skills) was scoped down to attributes. SIG may resist new span types
6. **Review timeline reality** — #3250 has 118 review comments over 3+ months; #3233 has 35 over 4 months. Our PR may take months even with engagement

---

## Updated Plan

### Phase 1: URGENT — Rescue #3594 (This Week)

**Goal: Get reviewer engagement before stale bot.**

1. **Check rebase status** — if main has diverged (especially from #3514), rebase our branch
2. **Verify PR description vs YAML consistency** — fix the workflow naming mention if YAML doesn't implement it
3. **Request review directly** — ping trask and/or lmolkova in #otel-genai Slack channel. Mention the PR number and ask for initial feedback. Do NOT just wait.
4. **Cross-reference the #3514 split** — add a brief comment on the PR noting that plan follows the INTERNAL span pattern established by #3514
5. **Engage with #3602** (agent.name on child spans) — short supportive comment, builds visibility with wrisa who is active in the space

### Phase 2: Maintain Engagement (Ongoing)

**Goal: Keep PR alive and respond to all feedback within 24-48 hours.**

- Monitor for stale bot warnings
- Respond to every review comment within 24 hours
- Be prepared to trim scope further if reviewers push back
- If asked "why not a grouping attribute?", point to #3575 where lmolkova questioned the grouping approach + argue that plan has meaningful duration as a parent span

### Phase 3: Reflect Span (Only After Plan Gets Positive Signal)

**Goal: Submit reflect span PR once plan has at least one approval or positive maintainer comment.**

**Do NOT submit reflect until plan has positive signal.** Submitting multiple
operation spans simultaneously will trigger "N+1 span type" pushback.

Updated reflect approach based on new learnings:
- Position as **opt-in** (aligns with #3419 SIG sentiment)
- One new attribute: `gen_ai.reflection.verdict` (pass/fail enum)
- Cite the #3419 discussion where Cirilla-zmh's nested agent examples showed
  derivation is insufficient
- Reference #3540 outcome (skills → attributes) proactively: "Unlike skills
  which can be modeled as execute_tool attributes, reflection has a distinct
  verdict outcome that cannot be derived from child span topology"
- Include honest auto-instrumentability table (only 2-3 of 6 frameworks)

### Phase 4: Delegation Attribute (After Reflect)

**Goal: Propose `gen_ai.agent.invocation.trigger` attribute on invoke_agent spans.**

This is the lightest-weight proposal — just one new attribute on an existing span.
- 3 values: `user`, `agent`, `orchestrator`
- No new span type (learned from #3540 skill span → attributes outcome)
- Cross-reference #3575 span links as complementary
- Include CrewAI, AutoGen, OpenAI Agents SDK, Google ADK evidence

---

## Key Tactical Adjustments from Original Plan

| Original Plan | Updated Plan | Why |
|---------------|-------------|-----|
| Wait for organic reviews | **Actively request reviews** in Slack | Stale bot kills after ~21 days; 9 days already elapsed |
| Submit reflect after plan PR opens | Submit reflect only after plan gets **positive signal** | #3540 showed SIG scopes down new span types; don't trigger N+1 pushback |
| Delegation as attribute + span link | Same, but reference #3540 precedent | Skills → attributes validates our pivot away from delegate span |
| Lead with structure in PR | Same, but also reference #3514 pattern | invoke_agent split establishes INTERNAL span pattern that plan follows |
| Umbrella issue first | Skip umbrella issue | #2664 already serves this role; our comments there anchor the work |

---

## Stale Bot Survival Checklist

The #1 killer of GenAI PRs is the stale bot (15+ PRs died this way).

- [ ] **Apr 11-13:** Request review in CNCF Slack #otel-genai
- [ ] **Apr 14:** If no response, comment on the PR with a substantive update (e.g., rebase note, cross-reference to #3514)
- [ ] **Apr 18:** If stale label appears, immediately respond with a comment
- [ ] **Every 7 days:** Add a substantive comment or push a commit to keep the PR active
- [ ] **If still no reviews by Apr 25:** Attend GenAI SIG meeting and raise the PR directly

---

## Evidence Strategy (Unchanged from EXECUTION_PLAN.md)

In the PR body:
- Lead with structure and auto-instrumentability
- Research claims are secondary support
- No SWE-bench percentages in the opening argument
- No ablation or closed-loop improvement claims

In review discussions (if challenged):
- SWE-bench data available if "why does this matter?" is asked
- Overhead data (p50=11.7us) available if volume is questioned
- Block-diagonal necessity matrix available if "is this truly needed?" is asked

---

## Outcome Metrics

| Milestone | Target Date | Status |
|-----------|------------|--------|
| Reviewer engagement on #3594 | Apr 18 | NOT STARTED — URGENT |
| First approval on #3594 | May 2026 | — |
| Plan span merged | Jun-Jul 2026 | — |
| Reflect span PR opened | After plan approval | — |
| Delegation attribute PR opened | After reflect opened | — |

---

## Appendix: Community Dynamics Map

### Gatekeepers (Must Engage)
- **lmolkova** — Primary GenAI maintainer. Skeptical of proliferating spans. Demands user problem articulation. Pushed back on #3575 grouping (good for us).
- **trask** — Active maintainer. Authored #3514 (invoke_agent split). Asks for concrete API mappings. Pragmatic.

### Allies (Should Engage)
- **nagkumar91** — Most active external contributor (#3233, #3250). Going through same review process. Potential collaboration.
- **Cirilla-zmh** — Pragmatic community contributor. Raised #3419. Pushed back on grouping feasibility. Values practical implementation.
- **keith-decker** — Authored #3595 (tool name required), #2912 (tasks/workflows). Active in agent space.

### Watch
- **KazChe** — #3575 grouping advocate. Competing philosophy but lmolkova not convinced.
- **wrisa** — Active on workflow metrics (#3565) and agent.name propagation (#3602).
