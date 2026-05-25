# Deep Dive: PR #2014 - Multi-Agent Semantic Conventions

> Research compiled: 2026-04-12
> Purpose: Exhaustive analysis of the multi-agent semantic conventions discussion in OpenTelemetry

---

## 1. PR #2014 Overview

| Field | Value |
|-------|-------|
| **Title** | Added multiagent semantic conventions along with single agent additions |
| **Author** | PRATIBHA-Moogi |
| **State** | CLOSED (not merged) |
| **Created** | 2025-03-25T06:40:21Z |
| **Closed** | 2025-12-21T03:44:42Z |
| **Merged** | false |
| **Labels** | Stale |
| **Head Branch** | multiagent-semantic-conventions |
| **Base Branch** | main |
| **URL** | https://github.com/open-telemetry/semantic-conventions/pull/2014 |
| **Issue Comments** | 5 |
| **Review Comments** | 0 (inline) |

---

## 2. Full PR Body

> To address - https://github.com/open-telemetry/semantic-conventions/issues/1961#issue-2897759988. This PR addresses the need for defining multiagent semantic conventions
>
> Fixes # NIL
>
> ## Changes
>
> Added multiagent application key attributes in addition to that added extra attributes for single agent application.
>
> ## Merge requirement checklist
>
> * [ ] [CONTRIBUTING.md](https://github.com/open-telemetry/semantic-conventions/blob/main/CONTRIBUTING.md) guidelines followed.
> * [ ] Change log entry added, according to the guidelines in [When to add a changelog entry](https://github.com/open-telemetry/semantic-conventions/blob/main/CONTRIBUTING.md#when-to-add-a-changelog-entry).
>   * If your PR does not need a change log, start the PR title with `[chore]`
> * [ ] [schema-next.yaml](https://github.com/open-telemetry/semantic-conventions/blob/main/schema-next.yaml) updated with changes to existing conventions.

---

## 3. Files Changed

**Single file modified:** `model/gen-ai/registry.yaml` (35 additions, 0 deletions)

### New Attributes Proposed

1. **`gen_ai.agent.tools`** (string array, stability: development)
   - "Lists the name of the tools configured with agent"
   - Example: `["search-web", "summarise-searched-results", "publish-results"]`

2. **`gen_ai.agent.llm`** (string, stability: development)
   - "Name of the llm configured with Agent application"
   - Example: `["OpenAI", "Ollama", "Anthropic"]`

3. **`gen_ai.multiagent.id`** (string, stability: development)
   - "The unique identifier of the GenAI multiagent"
   - Example: `['multiasst_5j66UpCpwteGg4YSxUnt7lPY']`

4. **`gen_ai.multiagent.name`** (string, stability: development)
   - Human-readable designation for multiagent systems
   - Example: `["TripPlanner", "InvestmentRecommender"]`

5. **`gen_ai.multiagent.description`** (string, stability: development)
   - Free-form explanation of multiagent functionality
   - Example: `["Helps with planning your trip as per your requirements with best cost"]`

6. **`gen_ai.multiagent.agentlist`** (string array, stability: development)
   - "List of agents used for composing the underlying multiagent application"
   - Example: `["SearchDestination", "RecommendPlace", "MakeReservation"]`

7. **`gen_ai.multiagent.topology`** (string array, stability: development)
   - "Nature of multiagent topology expressed by array of strings"
   - Example: `["Agent1:Agent2", "Agent2:Agent3", "Agent1:Agent3"]`

---

## 4. All Comments on PR #2014

### Comment 1 - linux-foundation-easycla[bot]
**Date:** 2025-03-25T06:40:26Z

> CLA Signed - login: PRATIBHA-Moogi / (660103ea74c8da7b869ed052186dd221263d0593)
> The committers listed above are authorized under a signed CLA.

### Comment 2 - PRATIBHA-Moogi
**Date:** 2025-03-26T06:38:58Z

> Thanks for your comments @lmolkova . I am working on it along with @gyliu513 . Regarding current gen_ai.agent.xx conventions, it doesn't represent a multiagent set of attributes. We can surely expand that one first. I also find bit of overlap on different concepts such as Workflow, flows, tasks, agents, tools, as well as runnable etc. as expressed by different agentic-application-frameworks e.g. langchain/langgraph, crew.ai, autogen, IBM Bee framework, Llamaindex etc. Is there we are maintaining a document to freeze on a common set of defnitions across these middleware framework ?

### Comment 3 - gyliu513
**Date:** 2025-03-26T13:30:59Z

> @lmolkova totally agree with you, I will work with @PRATIBHA-Moogi to improve the single agent first, and then extend to multi-agent

### Comment 4 - github-actions[bot]
**Date:** 2025-04-11T03:25:04Z

> This PR was marked stale due to lack of activity. It will be closed in 7 days.

### Comment 5 - github-actions[bot]
**Date:** 2025-12-14T03:44:26Z

> This PR has been labeled as stale due to lack of activity. It will be automatically closed if there is no further activity over the next 14 days.

---

## 5. Reviews on PR #2014

### Review 1 - lmolkova (CHANGES_REQUESTED)
**Date:** 2025-03-25T19:04:00Z

Full verbatim text:

> I don't believe we're ready to define multi-agent semantic conventions. We don't even have a clear definition of a single agent ones, especially when it comes to client-side agent frameworks.
>
> Multi-agent support is tight to general-purpose workflow #1688 and as suggested in the #1961 (comment) may need a few attributes and events or spans defined (e.g. for transition between agents).
>
> From general semconv perspective, we don't encourage defining attributes without a corresponding span/event/metric or at least an instrumentation that would use them. I don't believe these new attributes would apply to existing GenAI spans the conventions cover.
>
> TL;DR: The suggestion is:
>
> - please help us finalize conventions for a single agent
> - if you're interested in multi-agent conventions:
>   - consider how to express it in a more general way - any workflow involving agents, humans, or non-AI bots would have similar characteristics as multi-agent one
>   - it's best to start by prototyping the actual instrumentation and thinking about information that would be unique and essential for multi-agent flows.

---

## 6. Referenced Issue: #1961 - Add MultiAgent Semantic Conventions

| Field | Value |
|-------|-------|
| **Title** | Add MultiAgent Semantic Conventions |
| **Author** | PRATIBHA-Moogi |
| **State** | Open |
| **Created** | 2025-03-05T16:08:00Z |
| **Labels** | area:gen-ai |

### Full Body

> ### Area(s)
> area:gen-ai
>
> ### What's missing?
> Current semantic conventions don't cover MultiAgentic System attributes to define MultiAgentic System space. MultiAgent-->Tasks-->Agents-->Tools is a topological view that should cover attributes to define MultiAgent, Task, Agents, Tools specific attributes. This will help us discover MultiAgentic System topology view in a standardised manner and help us draw correlations among all key attributes to draw deeper insights on health and performance monitoring on such complex systems (or agentic workflows).
>
> ### Is your change request related to a problem? Please describe.
>
> Based on the work on "A Taxonomy of AgentOps for Enabling Observability of Foundation Model based Agents" we need to have coverage on all the attributes of MultiAgentic systems which govern Agentic Behaviour & its performance in a holistic manner. Ref Publication https://arxiv.org/html/2411.05285v1
>
> Based on the taxonomy published by the above work, MultiAgentic systems can follow different topologies or workflows defined over multiple agents (a set of experts).
>
> Task can be composed over a specific Agent call or a set of Agents, with a Gen AI model, given Task description, given expected output specification etc. It can also follow a specific topology that of defining a DAG or a workflow over multiple agents.
>
> Here, Task key attributes such as Task description, Agents involved, expected_output can be added to the semantic conventions to well define Task resources.
>
> Each Agent further can be composed with a bundle of tools required to carry out Agent's goal given its role, given a prompt_template, in-context info. So Agent Goal, Role, Task, Tool, Expected output can characterise individual Agents attributes and can be added to the semantic conventions for covering Agent resources.
>
> Each tool also can be characterised with a set of attributes - tool_type, tool_description, tool_argument etc. So those attributes can also be added into semantic conventions.
>
> Each prompt can also be described by means of prompt_template_type, prompt_template_info. And further to that other constructs of prompt_template_info - User Goal, Instruction, Query, Few-Shot examples, Output format ask, Tools List, ChatHistory etc can also be added as a set of attributes to characterise Prompts.
>
> The above some of the key MultiAgentic System attributes, if added to the semantic conventions, can further enable rich set of Observability views as the below:
>
> 1. Discovery of MultiAgentic system topology view
> 2. Discovery of Tasks, Task-Agent relationship
> 3. Discovery of Agent-Tool relationship
> 4. Discovery of Agent-Prompt attributes relationship
> 5. Discovery of Tools usage, Tools Types & associated performance metrics
> 6. Correlations of Agent's performance with Prompts attributes
> 7. System level metrics associated at each components of MultiAgentic System
>
> ### Describe the solution you'd like
>
> A new semantic conventions with the key attributes to describe multiagentic systems / applications.

### Comments on #1961

**Comment 1 - gyliu513 (2025-03-05T16:11:09Z):**
> Related with https://github.com/open-telemetry/semantic-conventions/issues/1530

**Comment 2 - TaoChenOSU (2025-03-20T17:41:06Z):**
> We should distinguish between single agent and multi-agent workflows. We may only need a very thin layer for multi-agent workflows in the GenAI conventions. It's because the underlying mechanism of multi-agent-workflows is message passing, which is not GenAI specific. The things we should probably trace may include the following:
> - Attributes
>   - The agents in a team
>   - The pattern employed by the team (Round robin, group chat style, MagenticOne, etc.)
> - Events
>   - Start event
>   - Transfer events (from one agent to another)
>   - Termination event

**Comment 3 - gyliu513 (2025-03-20T18:06:52Z):**
> @TaoChenOSU totally agree with you, besides this, I think we also need to consider introducing some new attributes, I think there should be at least two new concepts for mulit agent, including flow/workflow and task. I was working with @PRATIBHA-Moogi for this, but glad to discuss here, thanks!

**Comment 4 - lmolkova (2025-03-25T19:05:23Z):**
> Related to https://github.com/open-telemetry/semantic-conventions/issues/1688

**Comment 5 - aabmass (2025-06-10T16:58:55Z):**
> Looks like A2A has some tracing in their SDK now https://github.com/google-a2a/a2a-python/blob/main/src/a2a/utils/telemetry.py

---

## 7. Referenced Issue: #1530 - AI Agent Framework Semantic Convention

| Field | Value |
|-------|-------|
| **Title** | AI Agent framework Semantic Convention |
| **Author** | gyliu513 |
| **State** | Open |
| **Created** | 2024-10-29T19:14:49Z |
| **Labels** | enhancement, experts needed, area:gen-ai |

### Full Body

> ### Area(s)
> area:gen-ai
>
> ### Is your change request related to a problem? Please describe.
>
> There are now many agent frameworks for GenAI, including ibm bee stack, ibm wxflow, crewai, autogen, langgraph etc. Those agents will include many different components, like agent, tools, tasks etc, we need a semantic convention for those resources as well for agents.
>
> @lmolkova @nirga @drewby @karthikscale3 ^^
>
> ### Describe the solution you'd like
>
> Extend the GenAI Semantic Convention to cover agents

### Comments on #1530 (10 total)

**Comment 1 - lmolkova (2024-10-29T19:18:23Z):**
> FYI: I'm baking some early prototype here https://github.com/microsoft/opentelemetry-semantic-conventions/pull/3, I'll re-send the PR against this repo after a bit more prototyping

**Comment 2 - gyliu513 (2024-10-29T19:19:52Z):**
> I did some test with crewai and Instana observability at https://gyliu513.github.io/jekyll/update/2024/10/22/crewai-observability.html, we may need some agent framework level semantic convention.
>
> [Screenshots of crewai observability traces with Instana and Langtrace]
>
> Also did some test with langtrace, it can also capture some tracing and metrics when I was using crewai based on langchain.
>
> @karthikscale3 has some demo for agent observability with langtrace as well.
>
> @lmolkova it is great you have a PR under-going, will take a look, thanks!

**Comment 3 - lmolkova (2024-10-29T19:26:50Z):**
> wow, this looks awesome!
>
> I'm struggling with a couple of things and hope to gets your thoughts on a few big things:
> - what's the scope: client framework, client to service-side agent, multi-agent story. How may layers do we need?
> - the level of unification - e.g. task execution is the same as openai assistant run and will be the same as azure AI agent run - how far do we need to go in attempts to unify
>
> Essentially my main worry is that I don't fully understand what exactly we want to unify in semconv or what we want the conventions for.
>
> There is always an alternative that the LLM client level is unified but frameworks do some extra stuff which does not need much consistency. LMK what you think.

**Comment 4 - karthikscale3 (2024-10-29T19:50:10Z):**
> Thanks for starting the thread @gyliu513 . Shown below the span graph on Langtrace for CrewAI. Generally speaking, here's a general pattern that's emerging across agentic frameworks:
>
> [1] Sessions - Each session can have multiple agents working independently or together to perform a bunch of tasks.
> [2] Agents - Different agents that can do different tasks
> [3] Agent Config - Sequential, Hierarchical, Networked
> [4] Tools - Tools that agents have access to
> [5] Tasks - Tasks defined for agents
>
> Based on our experience at Langtrace, developers like to see:
> [1] traces that are isolated and grouped at these high level constructs (agents, tools, tasks etc.)
> [2] see the relationship between these constructs per session
> [3] see metadata related to each one of these constructs
>
> With all the above requirements in mind, we designed our instrumentation for crewai and other agentic frameworks we support. I think we can come up with sem conv for these high level constructs that are common for these agentic frameworks. Let me know what you all think.

**Comment 5 - gyliu513 (2024-10-30T02:06:21Z):**
> @karthikscale3 good summary, thanks!
>
> @lmolkova comments for this? I think may answer your above question, hope it is clear.

**Comment 6 - drewby (2024-11-12T05:37:34Z):**
> This paper may be useful inputs for this discussion: https://arxiv.org/abs/2411.05285
>
> In particular, Fig 7 takes a stab at generalizing the various steps that may appear in a Trace.

**Comment 7 - gyliu513 (2025-01-08T22:03:40Z):**
> I was now checking the white paper for agent from google https://www.kaggle.com/whitepaper-agents , I was wondering maybe we need two issues for agent, one is `Agent` semantic convention and another is `Agent Framework` semantic convention.
>
> - Agent was composed by model and tools
> - There are different Agent frameworks, those framework have concepts like Agent, Task, Agent Orchestration framework, like CrewAI, AutoGen, Langgraph etc (Some comparison for different agent frameworks https://gyliu513.github.io/jekyll/update/2024/12/17/battle-of-ai-agent-frameworks.html)
>
> Comments? Thanks!

**Comment 8 - marklysze (2025-01-08T23:09:49Z):**
> At [AG2](https://github.com/ag2ai/ag2) (based on AutoGen) we're currently implementing OpenTelemetry support and would like to align with the conventions.
>
> I think a separation between agent and framework could be useful.

**Comment 9 - TaoChenOSU (2025-01-09T18:37:16Z):**
> We currently have the LLM conventions, which should be able to capture most of what is happening within an agent, i.e. chat messages should contain the thought process and tool calls carried out by an agent.
>
> However, we don't have standard ways to capture useful information when multiple agents are working together, i.e. how the next agent is selected, or how the task is determined successful. These are probably more framework oriented.

**Comment 10 - gyliu513 (2025-01-09T19:34:40Z):**
> An issue for AI Agent Semantic Convention was created here https://github.com/open-telemetry/semantic-conventions/issues/1732

---

## 8. Referenced Issue: #1732 - AI Agent Semantic Convention

| Field | Value |
|-------|-------|
| **Title** | AI Agent Semantic Convention |
| **Author** | gyliu513 |
| **State** | Closed |
| **Created** | 2025-01-09T19:34:17Z |
| **Labels** | enhancement, area:gen-ai |

### Full Body

> ### Area(s)
> area:gen-ai
>
> ### Is your change request related to a problem? Please describe.
>
> Based on the white paper from Google from google https://www.kaggle.com/whitepaper-agents , we need semantic convention for a SINGLE AI Agent, the SINGLE AI Agent will be composed by LLM and Tools, and Tools will contain DataStore, Functions, Extensions
>
> /cc @lmolkova

### Comments on #1732 (3 total)

**Comment 1 - TaoChenOSU (2025-01-10T01:21:51Z):**
> Thank @gyliu513 for creating this issue to continue our discussion from the WG call.
>
> When we invoke an agent to perform a task, the agent invokes the LLM one or more times and can potentially run tools that are available to it. We could reuse the existing gen_ai convention for the LLM calls. I am not sure if a convention for tool will be necessary since tools can take on different forms, such as a code executor, an external service call, and data retrieval, etc. Each of the type should have its own conventions instead and some of them already exist. For example, data retrieval should follow the (vector) database convention.
>
> I do agree we need to capture information about an agent, including id, name, instruction, and different settings.

**Comment 2 - joaopgrassi (2025-01-10T16:01:16Z):**
> @gyliu513 @TaoChenOSU any of you will be taking this? Given it is already part of the GenAI project, I removed the "needs triage" label but would be good to get it assigned to someone from the SIG.

**Comment 3 - gyliu513 (2025-01-10T17:28:13Z):**
> @joaopgrassi I was working for the PR, hope I can have a draft next week, thanks

---

## 9. Referenced Issue: #1688 - Unified Semantic Conventions for Tasks, Workflows, Pipelines, Jobs

| Field | Value |
|-------|-------|
| **Title** | Unified semantic conventions for tasks, workflows, pipelines, jobs |
| **Author** | svrnm |
| **State** | Open |
| **Created** | 2024-12-16T15:06:41Z |
| **Labels** | enhancement, experts needed, area:new, triage:needs-triage |

### Full Body

> **Is your change request related to a problem? Please describe.**
>
> While reviewing the AI Agent Span Semantic Convention, the commenter noted that definitions of `ai_agent.workflow.*` and `ai_agent.task.*` should not be unique, as similar tasks and workflows exist outside the AI agent scope. The same applies to existing experimental CICD pipeline attributes. Other examples include cronjobs, business processes, and build tools like make or goyek.
>
> **Describe the solution you'd like**
>
> A unified set of attributes describing "workflow" with domain-specific attributes in related specifications, similar to HTTP SemConv's use of `server.*` or `url.*` attributes.
>
> Proposed mappings:
> * cicd.pipeline.name => workflow.name
> * cicd.pipeline.run.id => workflow.run.id
> * cicd.pipeline.task.name => workflow.task.name
> * cicd.pipeline.task.run.id => workflow.task.run.id
> * cicd.pipeline.task.run.url.full => workflow.task.url.full
> * cicd.pipeline.task.type => workflow.task.type
>
> Similarly for AI agents:
> * ai_agent.workflow.name => workflow.name
> * ai_agent.task.name => workflow.task.name
> * ai_agent.task.output => workflow.task.output
>
> And for goyek:
> * goyek.flow.output => workflow.output
>
> Both GenAI and CICD working groups should collaborate on broader "workflow" thinking.

### Key Comments on #1688 (16 total - selected highlights)

**Comment 3 - svrnm (2024-12-19T11:55:55Z) [MAJOR - detailed analysis]:**

Extensive post analyzing workflow visualization across different solutions (GitHub Actions, Argo Workflows, Camunda BPMN, Make). Key points:

> So what all workflows have in common is that they can be represented by a graph where the vertices represent tasks, the edges the dependencies between tasks. There are "start vertices" and "end vertices", and a run is a flow through that graph from a start to an end.
>
> From an observability standpoint, what I want to understand from a highlevel is:
> * How many runs through my workflow are successful? How many fail?
> * How long do my runs through my workflow take? How many are slow?
>
> These questions are independent of the workflow I am looking at. This is how I would troubleshoot a CICD workflow, a AI Agent workflow, a business workflow, a build workflow, etc.

Proposed common attributes:
- `workflow.name`
- `workflow.id`
- `workflow.task.name`
- `workflow.task.id`
- `workflow.task.run.id`

Proposed common metrics:
- `workflow.run.duration`
- `workflow.failed_runs`
- `workflow.active_runs`
- `workflow.task.run.duration`
- `workflow.task.active_runs`
- `workflow.task.failed_runs`

**Comment 4 - shivanshuraj1333 (2025-03-10T15:42:06Z):**
> I think this is also applicable to task processing systems like Celery and not just CI/CD workflow task processors.

**Comment 5 - thompson-tomo (2025-06-16T12:24:54Z):**
> I would suggest we follow the terminology as outlined in serverlessworkflow specification.

**Comment 10 - grzuy (2025-11-06T17:23:42Z):**
> For what is worth, this would also be applicable to the following task/job processing libraries/platforms:
> - ruby active_job instrumentation
> - erlang/elixir oban instrumentation
> which are currently following "messaging" conventions

**Comment 12 - adrielp (2025-11-10T15:16:05Z):**
> I like the idea of unifying this. The original proposal for pipeline was to be non-focused on cicd, but at the time it was recommended to focus exclusively on CICD due to the nature of needing so much support from so many different domains as a new SIG.

**Comment 16 - horovits (2026-04-01T05:44:20Z):**
> as we approach maturity of the CI/CD SemConv, I have to relate to @lmolkova comment, and to our learning across OTel's different projects, where attempt to widen the scope and be all-encompassing ended up with dwelling in Development status for extended periods with difficulty moving forward in maturity and converging towards stability. This in turn causes frustration by end-users who at some point stop waiting and start implementing those, and then changes are disruptive to them and cause friction even if formally defined "still" as non-stable. Carving out a well-defined scope and carrying it to stability is a priority of the OTel project at present.

---

## 10. Referenced PR: microsoft/opentelemetry-semantic-conventions#3 - lmolkova's Prototype

| Field | Value |
|-------|-------|
| **Title** | Define client spans for Generative AI agents |
| **Author** | lmolkova |
| **State** | MERGED |
| **Created** | 2024-10-21T16:51:35Z |
| **Merged** | 2025-03-30T22:16:55Z |
| **Repo** | microsoft/opentelemetry-semantic-conventions (Microsoft's fork) |
| **Changes** | 1,705 additions, 139 deletions across 19 files |

This was lmolkova's prototype for single-agent client spans. Key commits:
1. "Azure AI Foundry agent semconv draft"
2. Various lint fixes
3. Updates

This prototype eventually influenced the current `gen_ai.agent.*` attributes and `create_agent`/`invoke_agent` spans that now exist in the main semantic conventions repository.

---

## 11. Current State of Agent Semantic Conventions (as of April 2026)

The following agent attributes now exist in the main repo (`model/gen-ai/registry.yaml`):

| Attribute | Type | Stability | Description |
|-----------|------|-----------|-------------|
| `gen_ai.agent.id` | string | development | The unique identifier of the GenAI agent |
| `gen_ai.agent.name` | string | development | Human-readable name of the GenAI agent |
| `gen_ai.agent.description` | string | development | Free-form description of the GenAI agent |
| `gen_ai.agent.version` | string | development | The version of the GenAI agent |

### Current Span Types for Agents

1. **Create Agent Span** (`gen_ai.operation.name = "create_agent"`) - Agent creation, CLIENT kind
2. **Invoke Agent Client Span** (`gen_ai.operation.name = "invoke_agent"`) - Remote agent invocation, CLIENT kind
3. **Invoke Agent Internal Span** - Local framework-based agent operations
4. **Invoke Workflow Span** - GenAI workflow invocation operations
5. **Execute Tool Span** - Tool execution within agent operations

---

## 12. Referenced PR: #2502 - Prototyping Requirement

| Field | Value |
|-------|-------|
| **Title** | Add prototyping requirement for significant changes |
| **Author** | lmolkova |
| **State** | MERGED |
| **Merged by** | joaopgrassi (2025-07-14) |

This PR established that instrumentation implementations or prototypes must accompany substantial modifications to semantic conventions, regardless of stability level. Six reviewers approved (jsuereth, trask, joaopgrassi, arminru, AlexanderWert, ChrsMark).

**Key quote from the PR:**
> "Semantic conventions are intended to provide practical guidance for instrumentation authors and clear documentation for end users on what to expect and how to interpret telemetry."

**Impact on multi-agent work:** Any new multi-agent semantic conventions would now require an accompanying prototype/implementation demonstrating the attributes and spans in use.

---

## 13. Referenced PR: #2387 - Initial Implementation of Workflows

| Field | Value |
|-------|-------|
| **Title** | Initial implementation of workflows #1688 |
| **Author** | thompson-tomo |
| **State** | CLOSED (not merged) |
| **Created** | 2025-06-18T05:14:31Z |
| **Labels** | area:faas, area:k8s, area:deployment, area:aws, area:gcp, area:cicd, breaking, **triage:rejected:declined** |

This attempted to add broad `workflow.*` attributes encompassing CICD, cron, FaaS, deployments. It was auto-closed because the "workflow" area did not have an active SIG/project:

> "This PR contains changes to area(s) that do not have an active SIG/project and will be auto-closed: workflow. Such changes may be rejected or put on hold until a new SIG/project is established."

---

## 14. Related Active Issues (Current Landscape, April 2026)

### Issue #3602 - Proposal: `gen_ai.agent.name` on GenAI child spans and client metrics
**Author:** wrisa | **Created:** 2026-04-07 | **Status:** Open

Proposes adding `gen_ai.agent.name` to child spans (inference, embeddings, retrieval, execute_tool) and client metrics. Motivation:

> Multi-agent and orchestrated applications generate numerous inference, embeddings, retrieval, and execute_tool spans sharing identical `gen_ai.request.model` or `gen_ai.tool.name` attributes. These attributes alone cannot identify which logical agent (planner vs. retriever) initiated each operation.

This is directly relevant to multi-agent observability -- it proposes propagating agent identity down to child operations.

### Issue #3575 - Generic Grouping and Relationship Primitives for GenAI Semantic Conventions
**Author:** KazChe | **Status:** Open

Identifies the "N+1 span type problem" where multiple proposals (#3419, #2912, #2993, #3540) each introduce new span types. Proposes:
- `gen_ai.group.id` (string) - Identifier for logical span grouping
- `gen_ai.group.type` (open enum) - Type descriptor like "react_round", "task", "skill"
- Typed span links: `triggered_by`, `delegates_to`, `evaluates`

### Issue #3218 - Add semantic conventions for A2A (Agent-to-Agent) protocol
**Author:** xiaocang | **Created:** 2025-12-16 | **Status:** Open

Proposes `gen_ai.a2a.*` namespace for the Google A2A protocol with attributes for RPC method, task ID, task state, protocol version, and streaming.

### Issue #2993 - Add tool orchestration span to gen-ai spans
**Author:** TaoChenOSU | **Created:** 2025-10-28 | **Status:** Open

Originally proposed `orchestrate_tools` span. After discussion with lmolkova, narrowed to adding `gen_ai.agent.max_iterations` attribute to `invoke_agent` span.

### Issue #3540 - Add skill span
**Author:** clongbupt | **Status:** Open

### Issue #3419 - Adding ReAct Iterations Spans in Reasoning-Acting Agents
**Author:** Cirilla-zmh | **Status:** Open

### Issue #3318 - Add metrics for workflow
**Author:** wrisa | **Status:** Open

---

## 15. Referenced Issue: #1648 - CI/CD: Producing Long Running Traces

Related tangentially. Documents the challenge of producing spans for long-running workflows from Kubernetes controllers that may restart. Relevant because multi-agent workflows may also be long-running.

---

## 16. Referenced Paper

**"A Taxonomy of AgentOps for Enabling Observability of Foundation Model based Agents"**
- arXiv: https://arxiv.org/abs/2411.05285
- Referenced by both PRATIBHA-Moogi (in issue #1961) and drewby (in issue #1530)
- Provides a taxonomy for observability of AI agent systems
- Figure 7 generalizes the various steps that may appear in a Trace

---

## 17. Referenced: Google A2A Python SDK Telemetry

aabmass pointed out (2025-06-10) that Google's A2A Python SDK has telemetry:
- https://github.com/google-a2a/a2a-python/blob/main/src/a2a/utils/telemetry.py
- This represents real-world implementation of agent-to-agent telemetry

---

## 18. Key Participants & Their Positions

| Person | Affiliation | Position |
|--------|-------------|----------|
| **lmolkova** | Microsoft | Maintainer. Gate-keeper. Single-agent first; multi-agent needs general workflow thinking; attributes must have spans; prototyping required |
| **PRATIBHA-Moogi** | IBM? | PR author. Wants comprehensive multiagent attributes (topology, agent lists, etc.) |
| **gyliu513** | IBM | Co-author. Agrees with single-agent first approach. Distinguishes Agent vs Agent Framework semconv |
| **TaoChenOSU** | Microsoft (AutoGen) | Wants thin multi-agent layer. Key insight: multi-agent = message passing, not GenAI-specific |
| **karthikscale3** | Langtrace | Observability vendor. Identifies patterns: Sessions, Agents, Config, Tools, Tasks |
| **svrnm** | OTel maintainer | Proposed unified workflow attributes (#1688). Advocates cross-domain consistency |
| **drewby** | Microsoft? | Referenced the AgentOps taxonomy paper |
| **marklysze** | AG2/AutoGen | Implementing OTel support, wants alignment |
| **aabmass** | Google | Pointed to A2A SDK telemetry implementation |
| **horovits** | OTel | Warns against over-generalizing; scope-then-stabilize |
| **wrisa** | ? | Recent proposals for agent.name propagation (#3602) and workflow metrics (#3318) |
| **KazChe** | ? | Proposed generic grouping primitives (#3575) to avoid N+1 span types |
| **xiaocang** | ? | Proposed A2A protocol semconv (#3218) |
| **thompson-tomo** | ? | Attempted workflow PR (#2387), rejected for lack of active SIG |

---

## 19. Key Takeaways for Our Delegation Attribute PR

### 1. Maintainer Consensus: Single-Agent First, Then Multi-Agent
lmolkova's review (the authoritative voice) is unambiguous: finalize single-agent conventions before defining multi-agent ones. PR #2014 was rejected precisely because it jumped ahead.

### 2. Attributes Must Have Corresponding Signals
The semconv community explicitly rejects "attribute-only" PRs. Every attribute must be attached to a span, event, or metric. Our delegation attributes must be tied to specific spans (e.g., `invoke_agent` for the delegating agent, with span links to the delegated-to agent's `invoke_agent` span).

### 3. Prototyping Is Now Mandatory (PR #2502)
Since July 2025, all significant semconv changes require an accompanying prototype or instrumentation implementation. Any delegation attribute PR must include or reference working instrumentation code.

### 4. Multi-Agent = Workflow (Issue #1688 Connection)
lmolkova explicitly tied multi-agent to the general workflow discussion (#1688). The implication: multi-agent delegation should use workflow-like patterns that work for agents, humans, and bots alike. However, the workflow PR (#2387) was rejected for lacking an active SIG, so this path is currently blocked.

### 5. The "Thin Layer" Approach Is Preferred
TaoChenOSU's insight (from issue #1961) is widely supported: multi-agent needs only a "thin layer" because the underlying mechanism is message passing. The specific things to trace:
- Agents in a team
- Pattern employed (round robin, group chat, etc.)
- Transfer events (from one agent to another)
- Start/termination events

### 6. Risk of Over-Generalization
horovits (2026-04-01) explicitly warned against widening scope too much, citing OTel's track record of over-general approaches dwelling in Development status indefinitely. Any delegation PR should be narrowly scoped.

### 7. Active Related Proposals to Monitor
- **#3602** (agent.name on child spans) - Directly complementary to delegation work
- **#3575** (grouping primitives) - Could subsume delegation via `gen_ai.group.type = "delegation"` and typed span links
- **#3218** (A2A protocol) - Agent-to-agent communication is a superset that includes delegation
- **#2993** (tool orchestration) - Narrowed to `max_iterations`; shows how overly broad proposals get scoped down

### 8. Delegation-Specific Design Implications
Based on the full discussion landscape:
- **DO:** Use existing `gen_ai.agent.*` attributes on `invoke_agent` spans
- **DO:** Use span links with relationship types (per #3575's `delegates_to` concept)
- **DO:** Provide a working prototype with at least one agent framework
- **DO:** Keep the scope narrow -- just delegation, not full multi-agent topology
- **DON'T:** Create a new `gen_ai.multiagent.*` namespace (PR #2014's approach was rejected)
- **DON'T:** Define attributes without corresponding spans/events
- **DON'T:** Try to generalize across all frameworks simultaneously
- **DON'T:** Propose workflow-level abstractions without an active SIG backing them

### 9. Recommended Approach for a Delegation PR
1. Frame delegation as a specific pattern within the existing `invoke_agent` span semantics
2. Add attributes like `gen_ai.agent.delegate.target_name` or use span links with a `delegates_to` relationship type
3. Build a prototype with one framework (e.g., OpenAI Agents SDK, AutoGen, or CrewAI)
4. Reference #3575's grouping primitives concept as complementary
5. Keep the PR focused -- delegation only, not full multi-agent orchestration
6. Engage with lmolkova and TaoChenOSU early (they are the most technically rigorous voices)
