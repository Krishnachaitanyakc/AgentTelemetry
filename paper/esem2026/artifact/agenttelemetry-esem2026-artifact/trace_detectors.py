"""Executable detector predicates over benchmark span traces."""

from __future__ import annotations

from collections import Counter
from typing import Any


EASY_FAULTS = {
    "wrong_tool",
    "tool_failure",
    "timeout",
    "infinite_loop",
    "context_overflow",
    "cost_explosion",
}


def attrs(span: dict[str, Any]) -> dict[str, Any]:
    return span.get("attributes", {})


def detect_easy(spans: list[dict[str, Any]], fault: str) -> bool:
    if fault == "wrong_tool":
        return any(attrs(s).get("tool.name") and attrs(s).get("expected_tool") and attrs(s).get("tool.name") != attrs(s).get("expected_tool") for s in spans)
    if fault == "tool_failure":
        return any(attrs(s).get("status") == "ERROR" or "error.type" in attrs(s) for s in spans)
    if fault == "timeout":
        return any(attrs(s).get("status") == "TIMEOUT" or attrs(s).get("duration_ms", 0) > attrs(s).get("timeout_ms", 10**9) for s in spans)
    if fault == "infinite_loop":
        calls = Counter(attrs(s).get("tool.name") for s in spans if attrs(s).get("tool.name"))
        return any(count >= 3 for count in calls.values())
    if fault == "context_overflow":
        return any(attrs(s).get("llm.input_tokens", 0) > attrs(s).get("llm.context_limit", 10**12) for s in spans)
    if fault == "cost_explosion":
        return any(attrs(s).get("llm.cost", 0) > attrs(s).get("llm.cost_budget", 10**12) for s in spans)
    return False


def detect_dsm(spans: list[dict[str, Any]], fault: str) -> bool:
    if fault in EASY_FAULTS:
        return detect_easy(spans, fault)
    if fault == "circular_delegation":
        edges = {
            (attrs(s).get("delegation.source_agent"), attrs(s).get("delegation.target_agent"))
            for s in spans
            if s.get("kind") == "DELEGATION"
        }
        return any((target, source) in edges for source, target in edges if source and target)
    if fault == "agent_misroute":
        return any(s.get("kind") == "MEMORY" and attrs(s).get("memory.owner_agent") != attrs(s).get("agent.id") for s in spans if "memory.owner_agent" in attrs(s))
    if fault == "planning_failure":
        return any(s.get("kind") == "PLANNING" and (attrs(s).get("plan.status") == "failed" or attrs(s).get("plan.executable_steps") == 0) for s in spans)
    if fault == "reasoning_loop":
        hashes = Counter(attrs(s).get("reasoning.step_hash") for s in spans if s.get("kind") == "REASONING")
        return any(count >= 4 for count in hashes.values())
    if fault == "guardrail_bypass":
        return any(s.get("kind") == "GUARD_RAIL" and attrs(s).get("guardrail.result") == "bypass" for s in spans)
    if fault == "hallucination":
        return any(s.get("kind") == "AGENT" and attrs(s).get("agent.role") == "verifier" and attrs(s).get("verification.result") == "false_positive" for s in spans)
    if fault == "memory_corruption":
        return any(s.get("kind") == "MEMORY" and attrs(s).get("memory.corrupt") is True for s in spans)
    if fault == "stale_retrieval":
        return any(s.get("kind") == "RETRIEVAL" and attrs(s).get("retrieval.staleness_seconds", 0) > 86400 for s in spans)
    return False


def fires_any(condition: str, spans: list[dict[str, Any]]) -> bool:
    faults = [
        "wrong_tool",
        "tool_failure",
        "timeout",
        "infinite_loop",
        "context_overflow",
        "cost_explosion",
        "circular_delegation",
        "agent_misroute",
        "planning_failure",
        "reasoning_loop",
        "guardrail_bypass",
        "hallucination",
        "memory_corruption",
        "stale_retrieval",
    ]
    return any(detect(condition, spans, fault) for fault in faults)


def detect(condition: str, spans: list[dict[str, Any]], fault: str) -> bool:
    if condition == "no_telemetry":
        return False
    if condition in {"vanilla_otel", "otel_genai", "openinference"}:
        return fault in EASY_FAULTS and detect_easy(spans, fault)
    if condition in {"metadata_only", "full_capture"}:
        return detect_dsm(spans, fault)
    raise ValueError(f"unknown condition: {condition}")


def detect_permissive(condition: str, spans: list[dict[str, Any]], fault: str) -> bool:
    if detect(condition, spans, fault):
        return True
    name_tokens = {
        "reasoning_loop": ("reason",),
        "guardrail_bypass": ("guardrail",),
        "planning_failure": ("plan",),
        "memory_corruption": ("memory",),
    }
    allowed = {
        "otel_genai": {"planning_failure"},
        "openinference": {"guardrail_bypass"},
    }
    if fault not in allowed.get(condition, set()):
        return False
    tokens = name_tokens[fault]
    return any(any(token in str(span.get("name", "")).lower() for token in tokens) for span in spans)


def detect_extended(condition: str, spans: list[dict[str, Any]], fault: str) -> bool:
    if detect(condition, spans, fault):
        return True
    if condition == "otel_genai" and fault == "reasoning_loop":
        return any(attrs(span).get("gen_ai.usage.reasoning.output_tokens", 0) > 0 for span in spans)
    if condition == "openinference" and fault == "reasoning_loop":
        for span in spans:
            values = [
                value for key, value in attrs(span).items()
                if key.startswith("llm.output_messages.") and key.endswith(".message.content")
            ]
            if len(values) != len(set(values)):
                return True
    return False


def fires_any_permissive(condition: str, spans: list[dict[str, Any]]) -> bool:
    faults = [
        "wrong_tool",
        "tool_failure",
        "timeout",
        "infinite_loop",
        "context_overflow",
        "cost_explosion",
        "circular_delegation",
        "agent_misroute",
        "planning_failure",
        "reasoning_loop",
        "guardrail_bypass",
        "hallucination",
        "memory_corruption",
        "stale_retrieval",
    ]
    return any(detect_permissive(condition, spans, fault) for fault in faults)


def fires_any_extended(condition: str, spans: list[dict[str, Any]]) -> bool:
    faults = [
        "wrong_tool",
        "tool_failure",
        "timeout",
        "infinite_loop",
        "context_overflow",
        "cost_explosion",
        "circular_delegation",
        "agent_misroute",
        "planning_failure",
        "reasoning_loop",
        "guardrail_bypass",
        "hallucination",
        "memory_corruption",
        "stale_retrieval",
    ]
    return any(detect_extended(condition, spans, fault) for fault in faults)
