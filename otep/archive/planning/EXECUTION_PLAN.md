# Execution Plan: Submit `plan` To OpenTelemetry Semantic Conventions

This file is the canonical go-forward plan for the next submission.

## Goal

Open exactly one focused PR to `open-telemetry/semantic-conventions` for the
`plan` operation.

## What We Are Submitting

- new `gen_ai.operation.name` enum member: `plan`
- one `INTERNAL` span definition: `span.gen_ai.plan.internal`
- existing attributes only

## What We Are Not Submitting

- no OTEP
- no umbrella "agent cognitive operations" PR
- no `delegate`
- no `reflect`
- no `plan.strategy`
- no `plan.step.count`
- no `plan.steps`
- no `plan.goal`
- no new namespaces
- no `agent.span_kind` framing

## Canonical Framing

Lead with structure, not research:

- `plan` captures an agent phase where a strategy or decomposition is formulated
  before downstream execution.
- The planning phase has meaningful duration.
- The `chat` span that generates the plan is a child of the `plan` span.
- Grouping primitives and typed links can correlate spans, but they do not
  represent the planning phase itself.

## Two Objections To Preempt In The PR

### 1. Versus `#3575` grouping primitives

Action item:
- add a short paragraph explaining that grouping is complementary, but does not
  capture the planning phase as a timed parent span with a child `chat` call

### 2. Versus `#2912` task/workflow semantics

Action item:
- add a short paragraph explaining that `task` is execution of assigned work,
  while `plan` is strategy formulation before execution

## Required PR Shape

- Title: `Add semantic conventions for GenAI agent planning operation`
- Body starts with: `Partially addresses #2664`
- tiny hierarchy diagram
- short cross-framework table
- one reference implementation link
- explicit "out of scope" list

## Required Files In The Upstream Fork

- `model/gen-ai/registry.yaml`
- `model/gen-ai/spans.yaml`
- `docs/gen-ai/gen-ai-agent-spans.md`
- `.chloggen/gen-ai-plan-operation.yaml`

## Required Mechanics

- `make generate-all`
- `make check`
- `make check-policies` if the repo requires it
- no unresolved generated-doc drift

## Review Strategy

- request GenAI review early
- optimize for minimalism
- respond within 24-48 hours
- prefer cutting optional scope over defending it
- do not queue `reflect` or delegation follow-ups until `plan` gets positive
  signal

## Evidence Strategy

Use in the PR body:

- conservative cross-framework hookability
- hierarchy and duration argument
- existing-schema fit

Do not lead with:

- SWE-bench percentages
- ablation claims
- closed-loop improvement numbers
- broad agent observability vision

## Current Package

The live local package for the `plan` submission is:

- `otep/plan_span_pr_description.md`
- `otep/plan_span_pr.patch`
- `otep/PLAN_PR_CHECKLIST.md`

All other `otep/` files are background unless they explicitly say otherwise.
