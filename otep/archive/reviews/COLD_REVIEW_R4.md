# Cold Review Round 4 — Final Fixes

*2026-03-26. Round 4 adversarial review. All 3 proposals passed with minor refinements.*

---

## Round 4 Results Summary

| Proposal | Blockers | Majors | Verdict |
|----------|----------|--------|---------|
| Plan span | 0 | 2 (both refinements) | READY — drop step.count for bulletproof PR |
| Reflect span | 0 | 2 (both quick fixes) | READY — downgrade link, specify aggregate verdict |
| Delegation attribute | 0 | 1 (enum refinement) | SOUND — expand to 3 values |

---

## Plan Span — Final Refinements

### M1: Drop `gen_ai.plan.step.count` from initial PR
The R4 reviewer made the strongest case: LangChain's ReAct loop has no explicit
multi-step plan (it decides one action per iteration), making step.count=1 always,
which is meaningless. Cross-framework comparability is broken.

**Decision:** Drop step.count. The PR becomes: one new operation value on an
existing required attribute, ZERO new attributes. This is nearly bulletproof.
Propose step.count as a follow-up PR once implementation data exists.

### M2: Strengthen #3575 and #2912 differentiation
Added: "A plan span is the *parent* of the task/tool spans it generates;
modeling it as a task attribute would collapse this causal relationship."

### Minor fixes:
- Label `reflect` in tree diagram as "(future proposal)"
- Add note: "gen_ai.agent.description and gen_ai.agent.version are set on the
  parent invoke_agent span and need not be repeated"
- Clarify: gen_ai.agent.name refers to the agent *performing* the planning
- Soften Google ADK: "Expected based on public API design"
- Add: "No new events. Plan content capture is handled by child chat span's
  existing completion events."
- Add standard error handling note

### FINAL Plan Span (submission-ready):
```
Operation: gen_ai.operation.name = "plan" (new enum member)
Span Kind: INTERNAL
Span Name: "plan {gen_ai.agent.name}" or "plan"

Attributes: ZERO new attributes
- gen_ai.operation.name (required) = "plan"         [existing]
- gen_ai.system (required)                          [existing]
- gen_ai.agent.name (recommended if available)      [existing]
- gen_ai.agent.id (recommended if available)        [existing]
- error.type (conditionally required)               [existing]
```

---

## Reflect Span — Final Refinements

### M1: Downgrade evaluates link from SHOULD to MAY
"If typed span link relationships are adopted (see #3575), reflect spans
SHOULD use the `evaluates` relationship. Until then, instrumentations MAY
include an untyped span link to the evaluated span."

### M2: Specify multi-output verdict semantics
"The verdict represents the overall outcome of the reflection operation.
If the reflection evaluates multiple outputs, the verdict reflects the
aggregate decision (fail if any sub-evaluation fails)."

### Minor fixes:
- Add gen_ai.agent.id as opt_in
- Ambiguous results: "Ambiguous or inconclusive evaluation results SHOULD
  be mapped to `fail`, since the agent will typically retry."
- Prepare defense against #3419: "Unlike pure iteration-tracking spans,
  reflect carries semantic content (verdict) that cannot be derived from
  child span topology alone."
- Label framework-specific limitations honestly

### FINAL Reflect Span (submission-ready):
```
Operation: gen_ai.operation.name = "reflect" (new enum member)
Span Kind: INTERNAL (opt-in)
Span Name: "reflect {gen_ai.agent.name}" or "reflect"

Attributes: ONE new attribute
- gen_ai.operation.name (required) = "reflect"       [existing]
- gen_ai.system (required)                           [existing]
- gen_ai.agent.name (recommended if available)       [existing]
- gen_ai.agent.id (opt_in)                           [existing]
- gen_ai.reflection.verdict (recommended) = pass|fail [NEW]
- error.type (conditionally required)                [existing]

Span link: MAY include untyped link to evaluated span.
```

---

## Delegation Attribute — Final Refinements

### M1: Expand to trigger-based semantics
Renamed to `gen_ai.agent.invocation.trigger` with 3 values:
- `user` — invoked directly by user/application
- `agent` — invoked via delegation from another agent
- `orchestrator` — invoked via routing/selection by orchestrator

This is more observable (who created the span) and less ambiguous than
trying to infer delegation intent.

### Minor fixes:
- Make attribute conditional (omit when unknown, don't default to "user")
- Specify SERVER span carries link back to CLIENT span (`delegated_by`)
- Add rationale for both parent-child AND link: "Parent-child captures
  temporal containment; the typed link captures semantic intent."
- Note as extension point: delegation task/reason can be added in follow-up

### FINAL Delegation Approach:
```
Attribute: gen_ai.agent.invocation.trigger (conditional on invoke_agent)
Values: user | agent | orchestrator
Span link: SERVER span MAY carry delegated_by link to CLIENT span
```

---

## Convergence Assessment

After 4 rounds of cold review (11 total review agents), the proposals have converged:

| Round | Plan | Reflect | Delegate |
|-------|------|---------|----------|
| R1 | 2 blockers | 3 blockers | 3 blockers → killed |
| R2 | 0 blockers, 2 majors | 1 blocker, 2 majors | N/A (pivoted) |
| R3 | 0 blockers, 0 majors | 0 blockers, 0 majors | N/A |
| R4 | 0 blockers, 2 refinements | 0 blockers, 2 refinements | 0 blockers, 1 refinement |

**No further review rounds needed.** The proposals are submission-ready.
