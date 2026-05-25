# MAST → AgentTelemetry Fault Mapping

Source: Cemri et al., "Why Do Multi-Agent LLM Systems Fail?", arXiv:2503.13657
MAST = Multi-Agent System Failure Taxonomy
Generated: 2026-05-05

MAST defines 14 fine-grained failure modes (FM-1.1 through FM-3.3) clustered
into 3 categories: (i) system design issues (FM-1.x), (ii) inter-agent
misalignment (FM-2.x), (iii) task verification (FM-3.x).

| AgentTelemetry fault    | MAST mode (Cemri et al.)                              | MAST category               |
|-------------------------|-------------------------------------------------------|-----------------------------|
| `WRONG_TOOL`            | FM-2.6 Reasoning-Action Mismatch                      | Inter-agent misalignment    |
| `HALLUCINATION`         | FM-3.3 Incorrect Verification (fabricated content)    | Task verification           |
| `INFINITE_LOOP`         | FM-1.5 Unaware of Termination Conditions              | System design issues        |
| `CONTEXT_OVERFLOW`      | FM-1.4 Loss of Conversation History                   | System design issues        |
| `CIRCULAR_DELEGATION`   | FM-2.1 Conversation Reset (cyclic re-handoff)         | Inter-agent misalignment    |
| `TOOL_FAILURE`          | FM-3.2 No or Incomplete Verification (tool-level)     | Task verification           |
| `TIMEOUT`               | FM-3.1 Premature Termination                          | Task verification           |
| `STALE_RETRIEVAL`       | FM-2.4 Information Withholding (outdated grounding)   | Inter-agent misalignment    |
| `GUARDRAIL_BYPASS`      | FM-3.2 No or Incomplete Verification (policy-level)   | Task verification           |
| `PLANNING_FAILURE`      | FM-1.1 Disobey Task Specification                     | System design issues        |
| `REASONING_LOOP`        | FM-1.3 Step Repetition                                | System design issues        |
| `AGENT_MISROUTE`        | FM-2.5 Ignored Other Agent's Input                    | Inter-agent misalignment    |
| `MEMORY_CORRUPTION`     | FM-2.3 Task Derailment (state-corruption variant)     | Inter-agent misalignment    |
| `COST_EXPLOSION`        | (independent; production cost-incident reports)       | (not in MAST)               |

13 of 14 AgentTelemetry faults map to MAST modes. `COST_EXPLOSION` is
independently motivated by production cost-incident reports rather than
agent-task failures.

## Coverage of MAST by AgentTelemetry

The 14 AgentTelemetry faults map to 12 distinct MAST modes (FM-3.2 is mapped
twice: tool-level for `TOOL_FAILURE` and policy-level for `GUARDRAIL_BYPASS`).
Two MAST modes are not yet mapped:
- FM-1.2 Disobey Role Specification — a design-time role-mismatch fault
  not observable from runtime telemetry alone.
- FM-2.2 Fail to Ask for Clarification — a turn-level dialogue fault not
  observable from runtime telemetry alone without full payload analysis.
Both unmapped MAST modes are out of scope for telemetry-only diagnosis.
