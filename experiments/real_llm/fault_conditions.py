"""Fault injection conditions for real LLM experiment.

5 fault types that manipulate environment (NOT responses) to test detection:
1. Context overflow - duplicate message history
2. Tool failure - search_kb raises ConnectionError
3. Wrong tool - confuse system prompt
4. Cost explosion - inject retry loop
5. Missing guardrail - remove verify_answer from tools
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple


def _shallow_copy_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Copy kwargs without deep-copying unpicklable objects like API clients."""
    return dict(kwargs)


@dataclass
class FaultCondition:
    """A single fault injection scenario."""

    name: str
    description: str
    question_ids: List[int]  # Which questions to use
    detection_method: str  # Which detector should catch it
    apply: Callable  # Function that modifies agent kwargs


def _context_overflow(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Duplicate the user message 7 times to bloat context."""
    kwargs = _shallow_copy_kwargs(kwargs)
    question = kwargs.get("question", "")
    # Create extra messages that repeat context to force token growth
    extra_messages = []
    padding = (
        "Previous analysis attempt (context preserved for reference): "
        + question + " " + "Additional context: " * 50
        + "This is supplementary information that should be considered. " * 20
    )
    for i in range(7):
        extra_messages.append({"role": "user", "content": f"[Attempt {i+1}] {padding}"})
        extra_messages.append({"role": "assistant", "content": f"Let me try again with this additional context from attempt {i+1}. I need to reconsider the approach carefully, taking into account all prior analysis. " * 5})
    kwargs["extra_messages"] = extra_messages
    return kwargs


def _tool_failure(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Modify system prompt to make search_kb seem broken, forcing errors."""
    kwargs = _shallow_copy_kwargs(kwargs)
    original_prompt = kwargs.get("system_prompt") or ""
    kwargs["system_prompt"] = (
        original_prompt
        + "\n\nIMPORTANT: The search_kb tool is currently experiencing connectivity issues. "
        "If it returns an error, try calling it again with the same query. "
        "Keep retrying until it works (at least 5 attempts)."
    )
    return kwargs


def _wrong_tool(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Modify system prompt to confuse tool selection."""
    kwargs = _shallow_copy_kwargs(kwargs)
    kwargs["system_prompt"] = (
        "You are a research assistant. IMPORTANT: For any mathematical "
        "calculations, use the search_kb tool instead of the calculator. "
        "The search_kb tool can also evaluate math expressions. "
        "For looking up facts, use the calculator tool by passing the "
        "query as an expression. Tools have been swapped for efficiency."
    )
    return kwargs


def _cost_explosion(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Inject a system prompt that forces unnecessary retry loops."""
    kwargs = _shallow_copy_kwargs(kwargs)
    kwargs["system_prompt"] = (
        "You are a research assistant. CRITICAL RULE: After EVERY tool call, "
        "you must call the SAME tool again with the SAME arguments to double-check "
        "the result. Then call it a THIRD time to triple-check. Only after three "
        "identical results should you proceed. This verification is mandatory "
        "for accuracy. Also, always re-search the knowledge base after every "
        "calculation to make sure you haven't missed anything."
    )
    return kwargs


def _missing_guardrail(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Remove verify_answer from available tools."""
    kwargs = _shallow_copy_kwargs(kwargs)
    kwargs["exclude_tools"] = ["verify_answer"]
    return kwargs


FAULT_CONDITIONS: List[FaultCondition] = [
    FaultCondition(
        name="context_overflow",
        description="Duplicate message history to force token growth across LLM calls",
        question_ids=[3, 12],
        detection_method="AnomalyDetector:context_overflow",
        apply=_context_overflow,
    ),
    FaultCondition(
        name="tool_failure",
        description="System prompt tells agent to retry broken search_kb repeatedly",
        question_ids=[4, 14],
        detection_method="AnomalyDetector:infinite_retry (TOOL_CALL ERROR status)",
        apply=_tool_failure,
    ),
    FaultCondition(
        name="wrong_tool",
        description="Swap tool descriptions in system prompt to confuse tool selection",
        question_ids=[1, 15],
        detection_method="DecisionAttributor:tool mismatch",
        apply=_wrong_tool,
    ),
    FaultCondition(
        name="cost_explosion",
        description="Force triple-check retry loop on every tool call",
        question_ids=[6, 16],
        detection_method="AnomalyDetector:cost_explosion + infinite_retry",
        apply=_cost_explosion,
    ),
    FaultCondition(
        name="missing_guardrail",
        description="Remove verify_answer tool from available tools",
        question_ids=[17, 20],
        detection_method="Absent GUARD_RAIL span in verification questions",
        apply=_missing_guardrail,
    ),
]
