# `plan` PR Checklist

Use this checklist before opening the upstream PR and while driving review.

## Scope Lock

- [ ] PR contains only `plan`
- [ ] No `delegate`
- [ ] No `reflect`
- [ ] No new plan-specific attributes
- [ ] No new namespace or `agent.span_kind` language

## Submission Shape

- [ ] Title is `Add semantic conventions for GenAI agent planning operation`
- [ ] PR body starts with `Partially addresses #2664`
- [ ] PR explicitly distinguishes `plan` from `#2912`
- [ ] PR explicitly distinguishes `plan` from `#3575`
- [ ] PR includes a small hierarchy diagram
- [ ] PR includes a short cross-framework evidence table
- [ ] PR links one reference implementation

## Upstream Files

- [ ] `model/gen-ai/registry.yaml`
- [ ] `model/gen-ai/spans.yaml`
- [ ] `docs/gen-ai/gen-ai-agent-spans.md`
- [ ] `.chloggen/gen-ai-plan-operation.yaml`

## Mechanics

- [ ] `make generate-all`
- [ ] `make check`
- [ ] `make check-policies` if required
- [ ] No generated-doc drift remains

## Evidence Discipline

- [ ] Lead with structure and auto-instrumentability
- [ ] Research claims are secondary
- [ ] No SWE-bench percentages in the opening paragraph
- [ ] No ablation or closed-loop improvement claims in the opening argument

## Review Tactics

- [ ] Request GenAI review early
- [ ] Respond within 24-48 hours
- [ ] Prefer trimming scope over defending optional extras
- [ ] Do not open `reflect` or delegation follow-ups until `plan` gets positive signal

## Do Not Say This

- [ ] Do not pitch a broad "agent cognitive operations" program
- [ ] Do not claim grouping primitives are broadly wrong
- [ ] Do not imply all frameworks expose identical planning semantics
- [ ] Do not overclaim AutoGen / OpenAI Agents / Google ADK evidence
