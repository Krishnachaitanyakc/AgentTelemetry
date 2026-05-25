"""Primary standardized-field predicate bank used for RQ1/RQ2."""

EASY_SIX = {
    "wrong_tool": ["span.kind", "tool.name"],
    "tool_failure": ["status", "error.type"],
    "timeout": ["duration_ms", "status"],
    "infinite_loop": ["tool.name", "retry_count"],
    "context_overflow": ["llm.input_tokens", "llm.context_limit"],
    "cost_explosion": ["llm.cost", "llm.input_tokens", "llm.output_tokens"],
}

DSM_ONLY = {
    "circular_delegation": ["DELEGATION", "delegation.source_agent", "delegation.target_agent"],
    "agent_misroute": ["MEMORY", "agent.id", "memory.owner_agent"],
    "planning_failure": ["PLANNING", "plan.step_status"],
    "reasoning_loop": ["REASONING", "reasoning.step_hash"],
    "guardrail_bypass": ["GUARD_RAIL", "guardrail.result"],
    "hallucination": ["AGENT", "agent.role", "verification.result"],
    "memory_corruption": ["MEMORY", "memory.key", "memory.version"],
    "stale_retrieval": ["RETRIEVAL", "retrieval.staleness_seconds"],
}

BASELINE_TCR = 6 / 14
DSM_CAPABILITY_TCR = 14 / 14
