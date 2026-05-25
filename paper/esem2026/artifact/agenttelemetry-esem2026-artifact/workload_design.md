# Workload Design Freeze

The workload was frozen before detector authoring. Dates and commit identifiers are anonymized for review.

| event | anonymized timestamp |
|---|---|
| workload cases frozen | T0 |
| first taxonomy mapping commit | T0 + 32 days |
| DSM detector bank frozen | T0 + 41 days |
| third-party adapter scoring frozen | T0 + 44 days |

Blinded freeze-order digests, generated from the original repository commits
with an anonymizing salt retained for deanonymization after review:

| event | blinded digest |
|---|---:|
| workload cases frozen | `bf0d7b7a7e2c` |
| first taxonomy mapping commit | `7f8ce534e1bf` |
| DSM detector bank frozen | `b88410ad0a6d` |
| third-party adapter scoring frozen | `58c9d7ce42d8` |

Workload cases: no_fault, wrong_tool, tool_failure, timeout, infinite_loop, context_overflow, cost_explosion, circular_delegation, agent_misroute, planning_failure, reasoning_loop, guardrail_bypass, hallucination, memory_corruption, stale_retrieval.

The freeze order is workload -> MAST mapping -> DSM taxonomy mapping -> predicate banks. This file is included to make the circularity threat auditable without exposing repository identity during double-anonymous review.
