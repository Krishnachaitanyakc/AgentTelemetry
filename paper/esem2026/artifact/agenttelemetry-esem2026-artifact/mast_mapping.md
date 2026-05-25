# MAST Mapping

The 14 benchmark faults map to the externally authored MAST taxonomy where applicable. cost_explosion is included as an independently motivated operational cost-runaway fault.

| benchmark fault | MAST label | rationale |
|---|---|---|
| wrong_tool | FM-2.6 Reasoning--Action Mismatch | wrong tool chosen for task |
| tool_failure | FM-3.2 No or Incomplete Verification | called tool returns failure without adequate verification |
| timeout | FM-3.1 Premature Termination | timeout terminates the task before completion |
| infinite_loop | FM-1.5 Unaware of Termination Conditions | repeated tool/action cycle |
| context_overflow | FM-1.4 Loss of Conversation History | context budget exceeded |
| cost_explosion | independent | cost-runaway operational fault |
| circular_delegation | FM-2.1 Conversation Reset (cyclic) | two-agent delegation cycle |
| agent_misroute | FM-2.5 Ignored Other Agent's Input | task routed to wrong agent |
| planning_failure | FM-1.1 Disobey Task Specification | planner produces no executable path |
| reasoning_loop | FM-1.3 Step Repetition | repeated reasoning state |
| guardrail_bypass | FM-3.2 No or Incomplete Verification | policy violation not blocked |
| hallucination | FM-3.3 Incorrect Verification | verification accepts false answer |
| memory_corruption | FM-2.3 Task Derailment | incorrect memory state used |
| stale_retrieval | FM-2.4 Information Withholding | stale retrieved document used |

Omitted MAST modes: FM-1.2 and FM-2.2. These omissions bound the paper's claim because they are plausible beneficiaries of typed AGENT.role and GUARD_RAIL telemetry.
