# Deep Dive: PR #2713 — Semantic Conventions for Generative AI Tasks (gen_ai.task.*)

> Research compiled: 2026-04-12
> Source: https://github.com/open-telemetry/semantic-conventions/pull/2713

---

## 1. PR Metadata

| Field | Value |
|-------|-------|
| **Title** | Semantic Conventions for Generative AI Tasks (gen_ai.task.*) — Task Identity and Purpose |
| **Author** | divyapathak24 |
| **State** | Closed (NOT merged) |
| **Created** | 2025-09-01 |
| **Closed** | 2025-10-16 |
| **Merged** | No |
| **Labels** | `Stale`, `area:gen-ai` |
| **Branch** | `gen_ai-task` → `main` |
| **Stats** | 307 additions, 14 deletions, 5 files |
| **Issue Comments** | 6 |
| **Review Comments** | 21 |

---

## 2. Full PR Body

> Fixes
> - #2664
> - #2665
>
> ### Changes
>
> This PR introduces a foundational set of semantic attributes under a new domain prefix: `gen_ai.task.*`, specifically for representing **task-level telemetry** in agentic and generative AI systems. **Tasks** are fundamental **units** of work in AI Agentic systems, capturing structured goals like planning, reasoning, and synthesis. The ability to trace and observe these tasks is essential for production readiness, particularly from an **SRE or observability** standpoint.
>
> Benefits:
> (1) Adding GenAI tasks will provide **unified tracing** by standardizing spans and traces across different agent middleware frameworks (such as CrewAI, LangGraph, AutoGen).
> (2) Manifestation of raw spans from the task perspective, i.e., **n spans may abstract to m** (where, m <= n) tasks, by merging non-informative child spans into their parent spans recursively.
>
> This initial proposal on tasks includes attributes to support task identity and purpose.
>
> **New Semantic Conventions Added (gen_ai.task.*):**
>
> - gen_ai.task.id — Unique identifier for a task instance.
> - gen_ai.task.parent.id — ID of the parent task (if applicable).
> - gen_ai.task.name — Human-readable task label.
> - gen_ai.task.code.id — Reference to the source code defining the task.
> - gen_ai.task.code.vendor — Vendor/framework used (e.g., LangGraph, CrewAI).
> - gen_ai.task.kind — Describes the task's purpose (e.g., retrieval, reasoning).
> - gen_ai.task.tags — Custom tags for filtering, analytics, and domain grouping.
>
> **Motivation**
>
> These conventions standardize how agent task metadata is captured across spans. This supports:
> - Trace correlation across distributed workflows
> - Root cause analysis via parent-child task relationships
> - Filtering by task type and tags for debugging, performance, and SLO monitoring
>
> **For more details and a demo example, please refer to this document:** [Google Document Link](https://docs.google.com/document/d/15s1VPlzIaIx4XI7JnmUET4eZZROsdShp8NTH8VSKCO4/edit?tab=t.0)

---

## 3. All Issue Comments (Chronological)

### Comment 1 — linux-foundation-easycla[bot] (2025-09-01)
CLA check passed for divyapathak24.

### Comment 2 — divyapathak24 (2025-09-01)
> cc: @PRATIBHA-Moogi @gyliu513 @hk-bmi

### Comment 3 — ShipraJain01 (2025-09-02)
> @divyapathak24: thanks for putting up the PR. We have a proposal created on similar lines to define Multi-Agents tracing and introducing a new Span type - 'execute-task' and its relevant attributes earlier in July'25. Please find more details here - https://docs.google.com/document/d/1fcPe3SB_koRNeOoioq28RbA1BC7MNA7-/edit?usp=drive_link&ouid=109914447143824537379&rtpof=true&sd=true we can discuss further on slack

**Key takeaway:** ShipraJain01 (Cisco) had an independent, earlier proposal from July 2025 for a similar concept ("execute-task" span type). This signals convergent thinking from multiple parties but also competition/fragmentation.

### Comment 4 — thompson-tomo (2025-09-08)
> So on revisiting this and clarification via comment, I have the feeling that we should look to use a common definition as proposed in #2223 for the core concept and enrich it with gen-ai attributes. Hence my suggestion would be to pick what is required from #2223 the Workflow.task & Workflow.execution sub namespaces. Then only add the gen-ai attributes which is specific to tasks within gen-ai scope.

**Key takeaway:** thompson-tomo argues that "task" is NOT gen_ai-specific and should use a generic `workflow.task.*` namespace (from issue #1688 / PR #2387), with gen_ai-specific attributes layered on top. This is the central tension in the PR.

### Comment 5 — github-actions[bot] (2025-10-09)
> This PR was marked stale due to lack of activity. It will be closed in 7 days.

### Comment 6 — github-actions[bot] (2025-10-16)
> Closed as inactive. Feel free to reopen if this PR is still being worked on.

**Key takeaway:** The PR died from inactivity — no response from the author to thompson-tomo's critical feedback about generic vs gen_ai-specific namespacing.

---

## 4. All Inline Review Comments (Chronological)

### 4.1 — thompson-tomo on `model/gen-ai/registry.yaml` (2025-09-02)
> Is the code sub-namespace necessary?

### 4.2 — thompson-tomo on `model/gen-ai/registry.yaml` (2025-09-02)
> Does gen_ai.task.id uniquely identify a definition of a task which is reused everytime the task is used or is it identifying the usage of the definition aka the instance and will change?

### 4.3 — thompson-tomo on `model/gen-ai/registry.yaml` (2025-09-02)
> Would it be possible to use the code namespace?

### 4.4 — thompson-tomo on `model/gen-ai/spans.yaml` (2025-09-02)
> Would internal be more accurate given client implies a client/server relationship? Or add server attributes.

### 4.5 — thompson-tomo on `model/gen-ai/registry.yaml` (2025-09-02)
> This should also be an enum

### 4.6 — gyliu513 on `model/gen-ai/registry.yaml` (2025-09-02)
> What is the benefit of specifying the exact code here? Why not use documentation instead? For the end user customer of GenAI observability, using documentation maybe better?

### 4.7 — gyliu513 on `model/gen-ai/spans.yaml` (2025-09-02)
> this needs to be put to https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md, you can refer to https://github.com/open-telemetry/semantic-conventions/blob/main/CONTRIBUTING.md#2-update-the-markdown-files for how to add a new group.

### 4.8 — ShipraJain01 on `model/gen-ai/spans.yaml` (2025-09-02)
> @divyapathak24 : could you help explain where in the Agent's hierarchy this span would be initiated? Is this proposed to be a parent or child to agent's span?

### 4.9 — ShipraJain01 on `model/gen-ai/registry.yaml` (2025-09-02)
> @divyapathak24 : same question

### 4.10 — ShipraJain01 on `model/gen-ai/registry.yaml` (2025-09-02)
> @divyapathak24 : do you think `kind` depends on the multi-agent pattern and not all of the enum stated below are generically applicable?

### 4.11 — ShipraJain01 on `model/gen-ai/registry.yaml` (2025-09-02)
> @divyapathak24 : Every additional string array attribute increases payload size. An unbounded attribute like `tags` without strict schema can become inconsistent, reducing reliability for analytics, and would lead to telemetry overhead. In what cases could we really need `tags` in telemetry?

### 4.12 — ShipraJain01 on `model/gen-ai/registry.yaml` (2025-09-02)
> @divyapathak24 : How do you see reference to source code of task logic in telemetry helps?

### 4.13 — dany-moshkovich on `model/gen-ai/registry.yaml` (2025-09-08)
> @ShipraJain01 @thompson-tomo @divyapathak24
> The gen_ai.task.id reflects the specific instance of a task (not a meta-class) and is used to identify all updates to the task throughout its lifecycle.
> The gen_ai.task.code.* attributes are used to represent the meta-class associated with the instance. I hope this answers your second question.

### 4.14 — dany-moshkovich on `model/gen-ai/spans.yaml` (2025-09-08)
> @thompson-tomo @divyapathak24 I also think that internal would be more appropriate here

### 4.15 — thompson-tomo on `model/gen-ai/registry.yaml` (2025-09-08)
> Based on that, the name/kind attributes should also be in the same sub namespace as they correspond to id to remove confusion.

### 4.16 — divyapathak24 on `model/gen-ai/registry.yaml` (2025-09-11)
> @thompson-tomo @ShipraJain01
> 1. `gen_ai.task.id` uniquely identifies a task instance within a trace
> 2. `task.name` and `task.kind` reflect the task's runtime name and role and are not static, so they belong at the top level namespace, while .code.* is vendor-specific and static.

### 4.17 — divyapathak24 on `model/gen-ai/registry.yaml` (2025-09-11)
> @thompson-tomo Just to clarify—are you suggesting keeping `gen_ai.code.*`? If so, we placed `code.*` under task because it describes the implementation of a specific task, not a general code entity, so `gen_ai.task.code.*` preserves that scoped relationship.

### 4.18 — divyapathak24 on `model/gen-ai/registry.yaml` (2025-09-11)
> @gyliu513 @ShipraJain01 Linking the exact code can prove critical for debugging — for example, if gen_ai.task.code.id points to `task.py:56:Task`, an SRE/engineers can jump straight from a failing span to the exact function implementation, instead of searching through docs that may be outdated or ambiguous. For end users, docs can aid understanding, but linking exact code ensures engineers resolve issues quickly.

### 4.19 — divyapathak24 on `model/gen-ai/registry.yaml` (2025-09-11)
> @ShipraJain01 We have made the `gen_ai.task.kind` values as generic as possible. For example, action—"Executing a concrete command (e.g., tool, API, function)"—can represent any actionable step. Depending on the multi-agent pattern, you can choose the most appropriate value, but the enum values are designed to apply broadly across workflows.

### 4.20 — divyapathak24 on `model/gen-ai/registry.yaml` (2025-09-11)
> @ShipraJain01 `tags` are useful and **optional** in telemetry when you need flexible, filterable metadata—like "customer-support", "marketing", "compliance".

### 4.21 — thompson-tomo on `model/gen-ai/registry.yaml` (2025-09-12)
> I understand but *.id/*.name is usually used & viewed as a pair of attributes but here you are breaking that established pattern which will lead to confusion like it has.
>
> Hence I would rename task.id to be task.instance.id similar to other namespaces. Also get rid of the code sub-namespace as there is no reason to split based on if it is static given that they are all properties of the same object.

### 4.22 — pradystar on `docs/gen-ai/gen-ai-spans.md` (2025-09-23)
> I remember there was a discussion around this attribute and the plan was to add a `gen_ai.framework` to inference spans. Based on the description both attributes mean the same. Can you consider switching to `gen_ai.framework`?

---

## 5. Referenced Issues and PRs (Recursive Deep Dive)

### 5.1 Issue #2664 — Semantic Conventions for Generative AI Agentic Systems (gen_ai.*)

| Field | Value |
|-------|-------|
| **Author** | dany-moshkovich |
| **State** | Open |
| **Created** | 2025-08-20 |
| **Labels** | `enhancement`, `experts needed`, `triage:needs-triage`, `area:gen-ai` |

**Body:** This is the **meta-issue** for the entire agentic AI semantic conventions effort. It proposes six sub-domains:
- **Tasks** — Minimal trackable work units (→ Issue #2665, PR #2713)
- **Actions** — Execution mechanisms (tool calls, LLM queries, API requests)
- **Agents** — Autonomous, stateful entities
- **Teams** — Dynamic groups of agents
- **Artifacts** — Observable inputs/outputs
- **Memory** — Persistent, scoped storage

**Key comments on #2664:**

1. **91pavan (2025-09-11):** "Some of us (from Cisco) have also been thinking in this regard, about introducing new attributes around `workflows` and `tasks`... We were told `workflow` and `tasks` is a generic concept that applies to other namespaces in addition to GenAI, and this issue would first need to be addressed — https://github.com/open-telemetry/semantic-conventions/issues/1688"

2. **robk777 (2026-01-20):** "+1 on the workflow/task point from #1688... One thing I keep seeing come up in enterprise deployments: cost attribution at the task level. Teams want to aggregate token usage by task hierarchy and map it back to a cost centre or project."

3. **ashwin-pc (2026-02-08):** "One suggestion would be to use expected trajectory or outcomes since it's not a binary outcome that we usually want to evaluate against."

4. **Krishnachaitanyakc (2026-04-02):** "The proposed conventions define what agents do (tasks, actions, tools) but there's a gap around how they formulate strategy before acting, which is planning... I've been prototyping this in https://github.com/Krishnachaitanyakc/AgentTelemetry, following the pattern of PR #3233 (guardrails). If this gap resonates, I'll draft a minimal PR."

---

### 5.2 Issue #2665 — Semantic Conventions for Generative AI Tasks (gen_ai.task.*)

| Field | Value |
|-------|-------|
| **Author** | dany-moshkovich |
| **State** | Open |
| **Created** | 2025-08-20 |
| **Labels** | `enhancement`, `experts needed`, `area:gen-ai` |

**Body:** The detailed specification issue for tasks. Proposes attribute categories:
- **Identity & Purpose:** task ID, parent ID, name, code reference, kind, tags
- **Requester:** ID, type (human/system), role, external request ID
- **Lifecycle:** state (created through ended), status (success/failure/timeout/cancelled)
- **Input:** goal, instructions, examples, data, metadata
- **Output:** values, ranking scores, metadata
- **Scheduling:** dependency IDs, expected times, priority
- **Feedback:** source type, rating (0.0-1.0), metric data

**Key comment on #2665:**

1. **Cirilla-zmh (2025-11-04):** "According to the definition 'Tasks are the minimal trackable units of work, describing what needs to be done,' it seems that any operation could be considered a task. Strictly speaking, even an LLM call could be seen as a kind of task. So, how should we treat calls that represent task-like operations?"

---

### 5.3 Issue #1688 — Unified Semantic Conventions for Tasks, Workflows, Pipelines, Jobs

| Field | Value |
|-------|-------|
| **Author** | svrnm (Severin Neumann — OTel maintainer) |
| **State** | Open |
| **Created** | 2024-12-16 |
| **Labels** | `enhancement`, `experts needed`, `area:new`, `triage:needs-triage` |
| **Comments** | 16 |

**This is the critical "generic workflow" issue that the community keeps redirecting gen_ai.task proposals to.**

**Body (key points):**
- Identifies fragmentation: AI Agent, CI/CD, build tool, and other domains are all creating overlapping "task" and "workflow" conventions independently
- Proposes unified `workflow.*` namespace with common attributes:
  - `workflow.name`, `workflow.id`
  - `workflow.task.name`, `workflow.task.id`
  - `workflow.task.run.id`
- Argues the same visualization/dashboarding patterns apply across ALL workflow types (CI/CD, AI agents, business workflows, build tools)

**Key comments on #1688:**

1. **svrnm (2024-12-19) — CRITICAL long comment:** Extensive analysis with Mermaid diagrams showing that workflow visualization is identical across GitHub Actions, Argo Workflows, Camunda BPMN, Make/Makefile, etc. The core monitoring questions are the same regardless of domain: "How many runs are successful? Which tasks fail most? Which tasks are slowest?" Only drill-down into specific tasks requires domain-specific attributes.

2. **shivanshuraj1333 (2025-03-10):** "This is also applicable to task processing systems like Celery and not just CI/CD workflow task processors."

3. **thompson-tomo (2025-06-16):** Suggests following serverlessworkflow terminology. Started working on PR #2387.

4. **grzuy (2025-11-06):** Also applicable to Ruby active_job and Erlang/Elixir Oban instrumentations — both currently using "messaging" conventions as a workaround.

5. **thompson-tomo (2025-11-07):** "There is certainly widespread use/need for a common definition of tasks/workflows... I doubt we would have any difficulty in reaching at least a dozen instrumentations which fall into this category."

6. **adrielp (2025-11-10):** From CICD SIG: "The original proposal for pipeline was to be non-focused on cicd, but at the time it was recommended to focus exclusively on CICD due to the nature of needing so much support from so many different domains as a new SIG."

7. **horovits (2026-04-01) — IMPORTANT:** "As we approach maturity of the CI/CD SemConv, I have to relate to @lmolkova comment [on not over-generalizing]... attempt to widen the scope and be all-encompassing ended up with dwelling in Development status for extended periods... Carving out a well-defined scope and carrying it to stability is a priority of the OTel project at present."

---

### 5.4 PR #2387 — Initial Implementation of Workflows (#1688)

| Field | Value |
|-------|-------|
| **Author** | thompson-tomo |
| **State** | Closed (NOT merged) |
| **Created** | 2025-06-18 |
| **Closed** | 2025-10-26 |
| **Labels** | `area:faas`, `area:k8s`, `area:deployment`, `area:aws`, `area:gcp`, `area:cicd`, `breaking`, **`triage:rejected:declined`** |
| **Stats** | 2,353 additions, 18 files |

**Body:** Attempted to add generic "workflow" concepts encompassing CI/CD, cron, FaaS, deployments.

**How it died:** Auto-closed by bot because the "workflow" area does not have an active SIG/project:
> "This PR contains changes to area(s) that do not have an active SIG/project and will be auto-closed: workflow. Such changes may be rejected or put on hold until a new SIG/project is established."

**Key takeaway:** Generic workflows have no SIG ownership, making it nearly impossible to get merged through normal channels. This is a structural blocker.

---

### 5.5 Issue #2912 — Add Workflows/Agents/Tasks to gen_ai

| Field | Value |
|-------|-------|
| **Author** | keith-decker |
| **State** | Open |
| **Created** | 2025-10-14 |
| **Labels** | `area:gen-ai`, `triage:accepted:ready-with-sig` |

**Body:** Proposes two new span types (Workflow and Task) plus new metrics and agent context. Notable that this is `triage:accepted:ready-with-sig` — meaning the GenAI SIG has accepted it for work.

**Key comment from thompson-tomo (2025-10-15):**
> "My thought is that we should be striving to offer a generic solution to workflows. This would mean: `gen_ai.workflow.name` would become `workflow.definition.name`, `gen_ai.task.*` would become `workflow.task.*`."

---

### 5.6 PR #3594 — Add Semantic Conventions for GenAI Agent Planning Operation

| Field | Value |
|-------|-------|
| **Author** | Krishnachaitanyakc |
| **State** | Open |
| **Created** | 2026-04-02 |
| **Labels** | `area:gen-ai`, `enhancement` |

**Body:** Adds `plan` as a new `gen_ai.operation.name` enum value. Key argument: operators cannot distinguish between planning failures (requiring prompt adjustments) and execution failures (requiring tool fixes). No new attributes — just a new operation name.

Cross-references: #2664, #2912, #3575.

Reference implementation: https://github.com/Krishnachaitanyakc/AgentTelemetry

---

### 5.7 PR #3233 — gen-ai: Add Security Guardian (apply_guardrail) Span + Finding Event

| Field | Value |
|-------|-------|
| **Author** | nagkumar91 |
| **State** | Open |
| **Created** | 2025-12-22 |
| **Labels** | `enhancement`, `area:gen-ai` |

Proposes `apply_guardrail` span with guardian, security decision, policy, and content inspection attributes. Relevant as a pattern example for how new gen_ai span types are proposed.

---

### 5.8 Issue #3575 — Generic Grouping and Relationship Primitives for GenAI Semantic Conventions

| Field | Value |
|-------|-------|
| **Author** | KazChe |
| **State** | Open |
| **Created** | 2026-03-25 |
| **Labels** | `area:gen-ai`, `triage:needs-triage` |
| **Comments** | 9 |

**Body:** Addresses the "N+1 span type problem" — multiple competing proposals each introducing new span types (#3419 ReAct, #2912 Workflow/Task, #2993 Tool orchestration, #3540 Skill). Proposes:
1. **`gen_ai.group.id`** + **`gen_ai.group.type`** — lightweight grouping attributes added to existing spans
2. **Typed span links** — `triggered_by`, `delegates_to`, `evaluates` relationships using OTel's existing span link mechanism

**Key insight:** This is a counter-proposal to creating new span types. Instead of `task` spans, `skill` spans, `react_round` spans, etc., use grouping attributes on existing spans.

---

### 5.9 Issue #3540 — Add Skill Span

| Field | Value |
|-------|-------|
| **Author** | clongbupt |
| **State** | Open |
| **Created** | 2026-03-13 |
| **Labels** | `area:gen-ai`, `enhancement`, `experts needed` |

Proposes `gen_ai.skill` span type. Discussion evolved toward adding skill attributes to existing `execute_tool` spans rather than creating a new span type — similar to the grouping primitives argument.

---

### 5.10 Issue #3419 — Adding ReAct Iterations Spans

| Field | Value |
|-------|-------|
| **Author** | Cirilla-zmh |
| **State** | Open |
| **Created** | 2026-02-09 |
| **Labels** | `area:gen-ai`, `enhancement`, `experts needed` |

Proposes ReAct iteration spans. **lmolkova (maintainer, 2026-03-17)** assessed: "noisy and can be derived from llm response (tool_call) and the execute span next to it" — recommends opt-in only if implemented.

---

### 5.11 Issue #1648 — CI/CD: Producing Long-Running Traces

| Field | Value |
|-------|-------|
| **Author** | Joibel |
| **State** | Open |
| **Created** | 2024-12-04 |
| **Labels** | `enhancement`, `area:cicd`, `triage:accepted:ready-with-sig` |

About spans that last minutes-to-days across service restarts (e.g., Argo Workflows). Tangentially related — highlights that workflow/task spans face SDK limitations for long-running operations.

---

### 5.12 PR #1954 — messaging: Add Celery to Messaging System Values

| Field | Value |
|-------|-------|
| **Author** | xrmx |
| **State** | Closed (NOT merged) |

Attempted to add Celery as a messaging system value. Staled out. Relevant because Celery's task-processing model is currently shoehorned into messaging semantics — illustrating the need for proper task/workflow conventions.

---

## 6. Other Related Open Issues (Broader Landscape)

| # | Title | Author | Status |
|---|-------|--------|--------|
| 3602 | Proposal: `gen_ai.agent.name` on GenAI child spans and client metrics | wrisa | Open |
| 3597 | Propose semantic conventions for agentic AI failure repair (gen_ai.repair.*) | marisaSim | Open |
| 3580 | Proposal: Reinforcement Learning Semantic Conventions (`rl.*` namespace) | courageJ | Open |
| 3567 | Add server-side inference metrics | bs258q | Open |
| 3553 | Mark agent attributes and conversation id as sampling relevant for invoke_agent span | trask | Open |
| 3532 | MCP: update context propagation | lmolkova | Open |
| 3500 | GenAI: define and document declarative configuration options | lmolkova | Open |
| 3447 | How to capture user information who performs GenAI operation? | singankit | Open |
| 3398 | Semantic Conventions for GenAI Evaluation | anirudha | Open |
| 3378 | Add JSON Schema Definition for gen_ai.tool.definitions | Cirilla-zmh | Open |
| 3250 | gen-ai: semantic conventions for memory operations | nagkumar91 | Open |

---

## 7. Key Participants and Their Positions

### divyapathak24 (PR Author)
- Co-authored with dany-moshkovich
- Proposed gen_ai.task.* under gen_ai namespace
- Defended code.* sub-namespace for debugging utility
- Did not respond to thompson-tomo's critical feedback about generic namespacing → PR went stale

### dany-moshkovich (Co-proposer)
- Authored the meta-issue #2664 and detailed spec #2665
- Clarified that task.id = instance ID, task.code.* = meta-class/definition
- Agreed that "internal" span kind is more appropriate than "client"

### thompson-tomo (Key Reviewer)
- Consistently advocates for generic `workflow.*` namespace (not gen_ai-specific)
- Created PR #2387 (generic workflows) — auto-closed because no SIG owns "workflow" area
- Review feedback shaped the discussion significantly
- Position: tasks/workflows are cross-domain concepts; gen_ai should extend generic definitions

### ShipraJain01 (Cisco)
- Had an independent, earlier proposal (July 2025) for "execute-task" span type
- Raised critical design questions about hierarchy, kind enum genericity, tags overhead, code reference utility
- Represents Cisco's interests in multi-agent tracing

### 91pavan (Cisco)
- Also from Cisco with separate workflow/task proposals
- Pointed to #1688 as the prerequisite issue

### gyliu513 (Reviewer)
- Questioned the code.* sub-namespace value
- Pointed out missing documentation updates (gen-ai-spans.md)

### pradystar (Reviewer)
- Suggested using existing `gen_ai.framework` attribute instead of `gen_ai.task.code.vendor`

### svrnm (OTel Maintainer)
- Authored issue #1688 (unified workflows)
- Provided the most comprehensive analysis of why workflows should be generic
- Significant influence as a maintainer

### lmolkova (OTel Maintainer)
- Cautioned against over-generalizing (referenced in multiple discussions)
- Assessed ReAct spans as "noisy" — prefers opt-in
- Her position on scope vs. generality is frequently cited

### horovits (OTel Maintainer)
- Explicitly warned against widening scope: "attempt to widen the scope and be all-encompassing ended up with dwelling in Development status for extended periods"
- Prioritizes stability over comprehensiveness

### KazChe
- Proposed grouping primitives (#3575) as alternative to proliferating span types
- Framed the "N+1 span type problem"

### Krishnachaitanyakc
- Created AgentTelemetry prototype
- Filed PR #3594 for planning operation
- Active contributor building on the foundations laid by PR #2713

---

## 8. Central Tensions and Debates

### Tension 1: Generic `workflow.*` vs. Domain-Specific `gen_ai.task.*`

**The fundamental unresolved question.** Two camps:

- **Generic camp** (thompson-tomo, svrnm, 91pavan, robk777): Tasks and workflows exist in CI/CD, Celery, active_job, Oban, business processes, etc. Creating `gen_ai.task.*` will create incompatible duplicates when `workflow.task.*` eventually arrives. The core monitoring questions (success rate, duration, error attribution) are identical across domains.

- **Domain-specific camp** (divyapathak24, dany-moshkovich, keith-decker): GenAI tasks have unique properties (kinds like planning/reasoning/retrieval, LLM-specific code references, agent hierarchy). The GenAI SIG exists and can move forward now; a generic "workflow" SIG does not exist and may never materialize.

- **Pragmatic middle** (horovits, lmolkova): Over-generalizing stalls progress. Better to ship something scoped and stable. But also don't want to create incompatible conventions that will need breaking changes later.

**Status:** Unresolved. PR #2387 (generic workflows) was auto-closed for lack of SIG. Issue #1688 has 16 comments but no clear path forward. Meanwhile, issue #2912 (gen_ai tasks/workflows) is `triage:accepted:ready-with-sig` under the GenAI SIG.

### Tension 2: New Span Types vs. Grouping Attributes

- **New span type camp** (#2912, #3540, #3419): Tasks, skills, and ReAct iterations need their own spans for proper parent-child relationships, independent duration measurement, and error attribution.

- **Grouping primitives camp** (#3575): Adding `gen_ai.group.id` + `gen_ai.group.type` to existing spans avoids the "N+1 span type problem." Use span links for relationships.

- **Maintainer leaning** (lmolkova): Skeptical of noisy spans; prefers opt-in. This suggests grouping attributes may be more acceptable.

### Tension 3: Task Identity — Instance vs. Definition

- `gen_ai.task.id` = instance ID (unique per execution)
- `gen_ai.task.code.*` = definition/meta-class (reusable template)
- thompson-tomo argues this breaks the established `*.id/*.name` pairing pattern and suggests `task.instance.id` instead
- Unresolved in PR #2713

### Tension 4: Namespace Design — Flat vs. Hierarchical

- PR #2713 uses `gen_ai.task.code.id` and `gen_ai.task.code.vendor` (hierarchical)
- thompson-tomo argues: "get rid of the code sub-namespace as there is no reason to split based on if it is static given that they are all properties of the same object"
- pradystar suggests reusing existing `gen_ai.framework` instead of `gen_ai.task.code.vendor`

---

## 9. Why PR #2713 Failed

1. **No response to critical feedback:** divyapathak24 responded to initial review comments but did not address thompson-tomo's fundamental point about generic vs. gen_ai-specific namespacing (the Sept 8 comment). The PR went stale.

2. **Structural blocker:** The generic workflow question (#1688) has no SIG ownership, creating a chicken-and-egg problem. You can't merge gen_ai tasks without resolving whether they should be generic. But you can't resolve the generic question without a SIG.

3. **Missing prototype:** The PR predates the prototype requirement (PR #2502), but increasingly reviewers expect working instrumentations.

4. **Competing proposals:** ShipraJain01's independent "execute-task" proposal, thompson-tomo's workflow PR, and others create fragmentation.

5. **Incomplete implementation:** Missing documentation updates (gen-ai-spans.md), span kind issues (client vs. internal), unbounded tags attribute.

---

## 10. Current State of Play (as of 2026-04-12)

### What's Moving Forward
- **Issue #2912** (Workflows/Agents/Tasks in gen_ai) is `triage:accepted:ready-with-sig` — the GenAI SIG owns this
- **PR #3594** (planning operation) is open — minimal, follows established patterns
- **PR #3233** (guardrails) is open — shows the pattern for new operations
- **Issue #3575** (grouping primitives) is generating discussion as an alternative approach

### What's Stalled
- **Issue #1688** (generic workflows) has no SIG, no clear path
- **PR #2387** (generic workflow implementation) was auto-closed and rejected
- **PR #2713** (this PR) is closed/stale

### The Path Most Likely to Succeed
Based on the evidence:
1. The GenAI SIG will likely define task/workflow spans under `gen_ai.*` (not generic `workflow.*`)
2. The approach will probably follow the pattern of `gen_ai.operation.name` enum values rather than entirely new span structures
3. Grouping primitives (#3575) may complement or partially replace the need for dedicated task spans
4. A prototype/reference implementation (like AgentTelemetry) is increasingly expected
5. The maintainer preference is for focused, scoped, stable conventions — not ambitious all-encompassing frameworks

---

## 11. Key Takeaways for Our Work

1. **The "task" concept is contested territory.** Any proposal must explicitly address the generic-vs-specific namespace question and have a clear answer for "why not `workflow.task.*`?"

2. **Grouping primitives are gaining traction** as a lighter-weight alternative to new span types. Consider whether `gen_ai.group.id` + `gen_ai.group.type` could address the same use cases.

3. **Prototypes are now expected.** PR #2502 established this requirement. Any new proposal should ship with working instrumentation code.

4. **The GenAI SIG is the viable path.** Generic "workflow" has no SIG ownership. Working within the GenAI SIG (label: `area:gen-ai`) is the pragmatic approach.

5. **Maintainers favor incremental, scoped proposals.** Adding a new `gen_ai.operation.name` value (like `plan` in PR #3594) is much more likely to succeed than a sweeping new attribute namespace.

6. **Cost attribution at the task level** is a strong user demand (robk777's comment). This is a concrete use case that resonates with enterprise users.

7. **The `gen_ai.task.kind` enum** needs careful design — values like "planning", "reasoning", "retrieval", "action" overlap with operation names and other proposals.

8. **Instance vs. definition identity** must be cleanly separated, following OTel's established patterns (thompson-tomo's `task.instance.id` suggestion).

9. **Avoid unbounded attributes** like `tags` — reviewers flagged telemetry overhead concerns.

10. **Multiple Cisco contributors** (ShipraJain01, 91pavan) are active in this space with their own proposals — coordination or differentiation is important.
