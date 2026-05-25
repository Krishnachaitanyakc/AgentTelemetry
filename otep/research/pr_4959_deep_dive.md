# Deep Dive: opentelemetry-specification PR #4959 — OTEP: Agent Telemetry Semantic Conventions (ATSC)

## PR Summary

| Field | Value |
|-------|-------|
| **Title** | OTEP: Agent Telemetry Semantic Conventions (ATSC) |
| **Author** | `thegoo` (Jesse Williams) |
| **State** | Closed (NOT merged) |
| **Created** | 2026-03-18 |
| **Closed** | 2026-04-01 |

## What ATSC Proposed

ATSC is a vendor-neutral semantic layer for AI agent observability sitting above OTel GenAI SemConv. It defines 21 span kinds, 40+ span events, 14 domain objects, and a three-tier conformance model (Core/Standard/Full). Every ATSC span is a valid OTel span ingestible by any OTLP receiver. The spec lives at https://github.com/agent-telemetry-spec/atsc.

## Why It Was Closed — CRITICAL PRECEDENT

**@trask** responded within 2 hours showing most ATSC concepts already exist or have active proposals:

**Already standardized:** Agent invocation/creation (`invoke_agent`, `create_agent`), tool execution (`execute_tool`), MCP spans, retrieval/RAG, conversation tracking, token usage metrics, evaluation attributes, embeddings.

**Active open proposals covering the rest:**
- **Reasoning steps/turns:** #3419 (ReAct iterations), #3418 (entry span)
- **Multi-agent handoffs:** #3218 (A2A protocol), #1961 (multi-agent semconv)
- **Guardrails:** PR #3233 (apply_guardrail)
- **Agent memory:** PR #3250 (memory CRUD)
- **Workflows/tasks:** #2912, #2665, #1530

**@lmolkova** closed the PR, redirecting to `open-telemetry/semantic-conventions` as the correct venue.

## Key Takeaways for Our Work

### What exists today:
Agent/tool/LLM/MCP/retrieval/evaluation spans and metrics are standardized.

### Genuine remaining gaps (per trask's analysis):
- Multi-agent handoff semantics (A2A issue has zero engagement)
- Agent context propagation through OTel context
- **Planning/reasoning phase distinction** — our PR #3594
- **Delegation trigger identification** — our PR #3614

### Contribution rules (explicitly stated):
- Correct venue: `open-telemetry/semantic-conventions` (NOT `opentelemetry-specification`)
- GenAI SemConv SIG: Tuesdays 9am Pacific + Mondays for agent topics
- Do NOT propose monolithic specs; contribute focused PRs
- Bring real-world data and cross-framework validation

### Impact on our delegation attribute PR:
- trask's response validates that **focused, incremental** PRs are preferred
- The ATSC rejection for being too broad confirms our approach of single-attribute PRs
- trask explicitly listed the active proposals — our delegation attribute fills a gap not covered by any of them
- The 2-hour turnaround from trask shows he IS paying attention to agent proposals — the silence on #3594 may be a content/priority signal
