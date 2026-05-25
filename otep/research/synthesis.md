# Research Synthesis: Lessons from PR #2014, #4959, #2713, #124

## Compiled: 2026-04-13

## Key Patterns from Failed/Closed PRs

### 1. MONOLITHIC PROPOSALS DIE (PR #2014, #4959, #2713)
- PR #2014 (multi-agent attributes): lmolkova explicitly said "I don't believe we're ready to define multi-agent semantic conventions. We don't even have a clear definition of single agent ones."
- PR #4959 (ATSC 21 span kinds): trask showed most concepts already exist. lmolkova closed it.
- PR #2713 (gen_ai.task.*): Died from inactivity after critical namespace feedback.
- **Lesson:** Our focused single-attribute PR (#3614) follows the right pattern.

### 2. THE GENERIC vs GEN_AI NAMESPACE TENSION (#1688, #2223, #2387)
- thompson-tomo consistently argues "task/workflow is NOT gen_ai-specific"
- Should live under generic `workflow.*` namespace, not `gen_ai.*`
- This tension is UNRESOLVED and blocks large proposals
- **Impact on us:** Our `gen_ai.agent.invocation.trigger` is explicitly agent-specific — it only makes sense on `invoke_agent` spans. No namespace tension.

### 3. lmolkova's GATEKEEPING PATTERN
- Consistent message: "finalize single agent first, then multi-agent"
- Requires: concrete instrumentation, not abstract attributes
- Rejects: attributes without corresponding spans/events/metrics
- **Impact on us:** Our attribute attaches to an EXISTING span (`invoke_agent`) — no new spans needed. This passes her bar.

### 4. trask's RESPONSE PATTERN
- Responds in HOURS to things he cares about (ATSC got 2-hour response)
- Creates comparison tables showing what already exists
- Demands cross-provider evidence with links
- **Impact on us:** Our cross-provider table has 5 frameworks with source links. This matches his standard.

### 5. TaoChenOSU's (AutoGen/Microsoft) VIEW ON MULTI-AGENT
- "We should distinguish between single agent and multi-agent workflows"
- "Only need a very thin layer for multi-agent in GenAI conventions"
- Suggested attributes: agents in a team, pattern employed, transfer events
- **Impact on us:** "Transfer events" aligns directly with our delegation trigger attribute.

### 6. WHAT SUCCEEDED: FOCUSED, INCREMENTAL ADDITIONS
- `invoke_agent` started as a simple operation name (merged)
- `agent.version` was a single attribute addition (merged same day by trask)
- `tool.name` required was a one-line change (merged quickly)
- **Our PR follows this exact pattern.**

## Implications for PR #3614 (Delegation Attribute)

### STRENGTHS (validated by research):
1. Single attribute on existing span — matches every success pattern
2. No new namespace — avoids the #1688 tension entirely
3. Explicitly agent-specific — no generic/workflow overlap
4. Cross-provider evidence for 5 frameworks
5. Addresses TaoChenOSU's "transfer events" concept from #1961

### POTENTIAL CONCERNS:
1. No linked accepted issue — trask and lmolkova may ask "which issue does this address?"
   - We link #1961 and #2664, both are open issues requesting multi-agent conventions
2. "Can this be derived from parent-child?" — addressed in PR description
3. The enum design (`direct`/`agent`) — cleaner than original `user`/`agent` after Codex review

### NO CHANGES NEEDED TO PR #3614
The research validates our approach. The PR is well-positioned because:
- It is the opposite of every failed PR (focused vs monolithic)
- It attaches to existing infrastructure (invoke_agent) rather than proposing new concepts
- It follows the exact pattern of successfully merged PRs (agent.version, tool.name)
- The `direct`/`agent` enum is clean and auto-instrumentable
