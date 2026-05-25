# OBSOLETE: Do Not Submit An OTEP

The guidance in the previous version of this file is no longer valid.

## Why

- The `open-telemetry/oteps` repository is archived.
- New GenAI semantic convention work goes directly to
  `open-telemetry/semantic-conventions`.
- The broad AgentTelemetry OTEP draft in this directory is background material,
  not a live submission artifact.

## Current Submission Path

The active proposal path is:

1. Open or reference a focused issue in
   `open-telemetry/semantic-conventions`.
2. Submit a narrow PR against `open-telemetry/semantic-conventions`.
3. Follow the repo mechanics:
   - `.chloggen` entry
   - `model/gen-ai/*.yaml` updates
   - generated docs updated
   - `make generate-all`
   - `make check`
4. Keep the PR active and respond to review quickly.

## AgentTelemetry-Specific Direction

The current submit-now target is the minimal `plan` proposal:

- one new `gen_ai.operation.name` value: `plan`
- one `INTERNAL` span definition
- no new plan-specific attributes in v1

Use these files instead:

- `otep/submission/plan_span_pr_description.md`
- `otep/submission/plan_span_pr.patch`
- `otep/archive/planning/EXECUTION_PLAN.md`
- `otep/archive/planning/PLAN_PR_CHECKLIST.md`

Everything else in `otep/` should be treated as research or background unless
it explicitly says it is part of the current `plan` submission package.
