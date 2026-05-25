The issue describes agents as entities that "plan, reason, learn, and execute tasks by
orchestrating associated actions." But looking at the six proposed concepts — tasks,
actions, agents, teams, artifacts, memory — the planning step itself doesn't have a
home.

A task defines *what* needs to be done. An action defines *how* it gets carried out.
But the step where an agent formulates a strategy for a task — deciding which actions
to take and in what order — sits between the two. In traces, that step produces an LLM
call that looks identical to any other chat completion. There's no
`gen_ai.operation.name` value to mark it as planning vs. answering.

A `plan` value on the existing enum would fill this — no new attributes, just a new
member reusing `gen_ai.agent.name` and `gen_ai.system`. On @91pavan's point about
#1688, this stays within the existing `gen_ai` attribute group rather than introducing
new registry entries.

@robk777 — your point about task-level cost attribution gets more actionable if you can
split planning vs. execution cost within a task. Aggregating token usage by phase gives
you that breakdown.

I've been prototyping this in
[AgentTelemetry](https://github.com/Krishnachaitanyakc/AgentTelemetry), following the
pattern of PR #3233 (guardrails). If this gap resonates, I'll draft a minimal PR.
