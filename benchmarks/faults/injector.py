"""Fault injection for AgentTelemetry benchmarks.

Provides configurable fault injection to test whether the telemetry system
can detect various failure modes in agent systems.
"""

from __future__ import annotations

import json
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class FaultType(Enum):
    """Fourteen fault types that AgentTelemetry should detect, plus NONE.

    NONE is used for false-positive analysis: the agent runs without any
    injected fault and all detectors are checked for spurious fires.

    The first 8 are LLM-response faults (injected via mock client).
    The last 6 are span-attribute faults (injected by app code based on
    the active fault type, requiring agent-specific span kinds).
    """

    NONE = "no_fault"  # No fault injected (for false-positive analysis)

    # LLM-response faults (original 8)
    WRONG_TOOL = "wrong_tool"                       # LLM selects wrong tool
    HALLUCINATION = "hallucination"                  # LLM generates ungrounded content
    INFINITE_LOOP = "infinite_loop"                  # Agent calls same tool repeatedly
    CONTEXT_OVERFLOW = "context_overflow"            # Progressive token growth
    COST_EXPLOSION = "cost_explosion"                # Excessive API calls
    CIRCULAR_DELEGATION = "circular_delegation"      # Agent A -> B -> A
    TOOL_FAILURE = "tool_failure"                    # Tool throws error
    TIMEOUT = "timeout"                              # LLM call times out

    # Span-attribute faults (new 6 -- require agent-specific span kinds)
    STALE_RETRIEVAL = "stale_retrieval"              # Retrieval returns stale data
    GUARDRAIL_BYPASS = "guardrail_bypass"            # Guardrail check bypassed
    PLANNING_FAILURE = "planning_failure"            # Excessive planning decomposition
    REASONING_LOOP = "reasoning_loop"                # Repeated identical reasoning chains
    AGENT_MISROUTE = "agent_misroute"                # Wrong agent handles the task
    MEMORY_CORRUPTION = "memory_corruption"          # Memory read returns corrupt data


@dataclass
class FaultEvent:
    """Record of an injected fault for ground truth comparison."""

    fault_type: FaultType
    timestamp: float
    call_index: int
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fault_type": self.fault_type.value,
            "timestamp": self.timestamp,
            "call_index": self.call_index,
            "details": self.details,
        }


class FaultInjector:
    """Injects faults into mock LLM client responses.

    Usage::

        injector = FaultInjector(FaultType.WRONG_TOOL, rate=0.3)
        client = MockAnthropicClient(fault_injector=injector)
        # 30% of calls will select wrong tool
        response = client.messages.create(...)
        # Check injector.injected_faults for ground truth
    """

    def __init__(
        self,
        fault_type: FaultType,
        rate: float = 1.0,
        seed: Optional[int] = None,
        **config: Any,
    ) -> None:
        if not 0.0 <= rate <= 1.0:
            raise ValueError(f"rate must be between 0 and 1, got {rate}")

        self.fault_type = fault_type
        self.rate = rate
        self.config = config
        self.injected_faults: List[FaultEvent] = []
        self._call_index = 0
        self._rng = random.Random(seed)

        # Fault-specific state
        self._loop_count = 0
        self._last_tool_name: Optional[str] = None
        self._token_growth_factor = config.get("token_growth_factor", 1.5)
        self._accumulated_tokens = config.get("base_tokens", 500)
        self._max_loop_iterations = config.get("max_loop_iterations", 10)
        self._timeout_seconds = config.get("timeout_seconds", 5.0)

    def should_inject(self) -> bool:
        """Determine whether to inject a fault on this call."""
        return self._rng.random() < self.rate

    def _record_fault(self, details: Dict[str, Any]) -> None:
        """Record a fault event for ground truth."""
        self.injected_faults.append(FaultEvent(
            fault_type=self.fault_type,
            timestamp=time.time(),
            call_index=self._call_index,
            details=details,
        ))

    def maybe_inject(
        self,
        provider: str,
        mock_client: Any,
        model: Optional[str],
        messages: Optional[List[Dict[str, Any]]],
        tools: Optional[List[Dict[str, Any]]],
        kwargs: Dict[str, Any],
    ) -> Any:
        """Called by mock clients. Returns a modified response if fault injected, else None.

        Args:
            provider: "anthropic" or "openai"
            mock_client: The MockMessages or MockCompletions instance
            model: Model name
            messages: The messages list
            tools: The tools list
            kwargs: Additional kwargs

        Returns:
            A fault-injected response object, or None to use normal response.
        """
        self._call_index += 1

        if not self.should_inject():
            return None

        handler = getattr(self, f"_inject_{self.fault_type.value}", None)
        if handler is None:
            return None

        return handler(provider, mock_client, model, messages or [], tools or [], kwargs)

    # -- Fault implementations ------------------------------------------------

    def _inject_no_fault(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        """No-fault pass-through: returns None so normal response flows."""
        return None

    def _inject_wrong_tool(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        """Select a tool that doesn't match the user's request."""
        if not tools:
            return None

        # Pick a random tool that's likely wrong
        available_tools = [t for t in tools]
        if len(available_tools) < 2:
            return None  # Can't pick a "wrong" tool with only one option

        # Deterministically pick a different tool than what would be expected
        wrong_idx = (self._call_index * 7) % len(available_tools)
        if provider == "anthropic":
            tool = available_tools[wrong_idx]
            tool_name = tool.get("name", "unknown")
            self._record_fault({"wrong_tool": tool_name, "available_tools": [t.get("name") for t in tools]})
            return _make_anthropic_tool_response(model or "claude-sonnet-4", tool_name, {"query": "wrong_input"})
        else:
            func = available_tools[wrong_idx].get("function", {})
            tool_name = func.get("name", "unknown")
            self._record_fault({"wrong_tool": tool_name, "available_tools": [f.get("function", {}).get("name") for f in tools]})
            return _make_openai_tool_response(model or "gpt-4o", tool_name, {"query": "wrong_input"})

    def _inject_hallucination(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        """Generate content not grounded in the input."""
        hallucinated_text = (
            "According to the latest research published in Nature (2025), "
            "the quantum coherence time of silicon-based qubits has reached "
            "47.3 milliseconds at room temperature, which represents a "
            "breakthrough that completely invalidates previous assumptions. "
            "Dr. Firstname Lastname of MIT confirmed these results."
        )
        self._record_fault({"hallucinated_content": hallucinated_text[:100]})

        if provider == "anthropic":
            return _make_anthropic_text_response(model or "claude-sonnet-4", hallucinated_text)
        else:
            return _make_openai_text_response(model or "gpt-4o", hallucinated_text)

    def _inject_infinite_loop(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        """Make the agent call the same tool repeatedly."""
        if not tools:
            return None

        # Always pick the same tool
        if provider == "anthropic":
            tool_name = tools[0].get("name", "loop_tool")
        else:
            tool_name = tools[0].get("function", {}).get("name", "loop_tool")

        self._loop_count += 1
        if self._loop_count > self._max_loop_iterations:
            self._loop_count = 0
            return None  # Stop eventually so benchmarks terminate

        self._record_fault({"tool_name": tool_name, "loop_iteration": self._loop_count})

        if provider == "anthropic":
            return _make_anthropic_tool_response(model or "claude-sonnet-4", tool_name, {"query": "same_query"})
        else:
            return _make_openai_tool_response(model or "gpt-4o", tool_name, {"query": "same_query"})

    def _inject_context_overflow(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        """Progressively increase token counts to simulate context overflow.

        Returns tool_use responses for the first several calls to keep the agent
        looping, so the progressive token growth can be observed in the trace.
        """
        self._accumulated_tokens = int(self._accumulated_tokens * self._token_growth_factor)

        self._record_fault({"accumulated_tokens": self._accumulated_tokens, "growth_factor": self._token_growth_factor})

        # Return tool_use for the first several calls to keep the agent looping.
        # After enough calls to establish the pattern, return text to terminate.
        if self._call_index <= 5 and tools:
            if provider == "anthropic":
                tool_name = tools[0].get("name", "web_search")
                return _make_anthropic_tool_response(
                    model or "claude-sonnet-4", tool_name,
                    {"query": f"overflow-query-{self._call_index}"},
                    input_tokens=self._accumulated_tokens,
                    output_tokens=min(self._accumulated_tokens // 2, 500),
                )
            else:
                tool_name = tools[0].get("function", {}).get("name", "web_search")
                return _make_openai_tool_response(
                    model or "gpt-4o", tool_name,
                    {"query": f"overflow-query-{self._call_index}"},
                    prompt_tokens=self._accumulated_tokens,
                    completion_tokens=min(self._accumulated_tokens // 2, 500),
                )

        # After enough calls, return text to terminate
        large_text = "Context overflow detected - response truncated."
        if provider == "anthropic":
            return _make_anthropic_text_response(
                model or "claude-sonnet-4", large_text,
                input_tokens=self._accumulated_tokens,
                output_tokens=100,
            )
        else:
            return _make_openai_text_response(
                model or "gpt-4o", large_text,
                prompt_tokens=self._accumulated_tokens,
                completion_tokens=100,
            )

    def _inject_cost_explosion(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        """Return normal response but with inflated token counts."""
        inflated_input = 50000
        inflated_output = 20000

        self._record_fault({"inflated_input_tokens": inflated_input, "inflated_output_tokens": inflated_output})

        if provider == "anthropic":
            return _make_anthropic_text_response(
                model or "claude-sonnet-4",
                "Here is my response.",
                input_tokens=inflated_input,
                output_tokens=inflated_output,
            )
        else:
            return _make_openai_text_response(
                model or "gpt-4o",
                "Here is my response.",
                prompt_tokens=inflated_input,
                completion_tokens=inflated_output,
            )

    def _inject_circular_delegation(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        """Simulate circular delegation: A->B->A cycle.

        Alternates delegation between two agents to create a detectable cycle.
        Uses delegate_task tool if available, falls back to text.
        After enough delegations to establish the cycle, returns text to terminate.
        """
        agents = self.config.get("agents", ["agent_b", "agent_a"])
        target = agents[self._call_index % len(agents)]

        self._record_fault({"target_agent": target, "delegation_cycle": self._call_index})

        # After 4 delegations, stop to let the agent terminate
        if self._call_index > 4:
            if provider == "anthropic":
                return _make_anthropic_text_response(model or "claude-sonnet-4", "Task completed after delegation.")
            else:
                return _make_openai_text_response(model or "gpt-4o", "Task completed after delegation.")

        # Look for a delegation tool
        delegate_tool = None
        for t in tools:
            name = t.get("name") or t.get("function", {}).get("name", "")
            if "delegate" in name.lower():
                delegate_tool = name
                break

        if delegate_tool:
            if provider == "anthropic":
                return _make_anthropic_tool_response(model or "claude-sonnet-4", delegate_tool, {"agent": target, "task": "continue processing"})
            else:
                return _make_openai_tool_response(model or "gpt-4o", delegate_tool, {"agent": target, "task": "continue processing"})
        else:
            delegation_text = f"I need to delegate this task to {target} for further processing."
            if provider == "anthropic":
                return _make_anthropic_text_response(model or "claude-sonnet-4", delegation_text)
            else:
                return _make_openai_text_response(model or "gpt-4o", delegation_text)

    def _inject_tool_failure(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        """Make the response trigger a tool that will fail."""
        if not tools:
            return None

        if provider == "anthropic":
            tool_name = tools[0].get("name", "failing_tool")
        else:
            tool_name = tools[0].get("function", {}).get("name", "failing_tool")

        self._record_fault({"failing_tool": tool_name})

        # Return a tool call — the app layer should simulate the tool raising an error
        if provider == "anthropic":
            return _make_anthropic_tool_response(model or "claude-sonnet-4", tool_name, {"__fault__": "tool_failure"})
        else:
            return _make_openai_tool_response(model or "gpt-4o", tool_name, {"__fault__": "tool_failure"})

    def _inject_timeout(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        """Simulate a timeout by sleeping (capped for benchmarks)."""
        actual_delay = min(self._timeout_seconds, 0.1)  # Cap at 100ms for benchmarks
        time.sleep(actual_delay)

        self._record_fault({"timeout_seconds": self._timeout_seconds, "actual_delay": actual_delay})
        raise TimeoutError(f"Mock LLM call timed out after {self._timeout_seconds}s")

    # -- Span-attribute faults ------------------------------------------------
    # These 6 faults do NOT modify the LLM response.  Instead, the app code
    # checks ``fault_injector.fault_type`` and modifies span attributes.
    # The handlers below simply record ground truth and return None so the
    # normal mock-client response flows through.

    def _inject_stale_retrieval(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        self._record_fault({"staleness_seconds": 7200, "source": "stale_cache"})
        return None

    def _inject_guardrail_bypass(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        self._record_fault({"guardrail_result": "bypass"})
        return None

    def _inject_planning_failure(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        self._record_fault({"step_count": 15, "excessive_decomposition": True})
        return None

    def _inject_reasoning_loop(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        self._record_fault({"chain": "stuck-in-loop", "repeated": True})
        return None

    def _inject_agent_misroute(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        self._record_fault({"agent_name": "researcher", "expected_name": "specialist", "misrouted": True})
        return None

    def _inject_memory_corruption(
        self, provider: str, client: Any, model: Optional[str],
        messages: List, tools: List, kwargs: Dict,
    ) -> Any:
        self._record_fault({"operation": "read", "corrupted": True})
        return None

    def get_ground_truth(self) -> List[Dict[str, Any]]:
        """Return all injected faults as dicts for analysis."""
        return [f.to_dict() for f in self.injected_faults]

    def reset(self) -> None:
        """Reset injector state."""
        self.injected_faults.clear()
        self._call_index = 0
        self._loop_count = 0
        self._accumulated_tokens = self.config.get("base_tokens", 500)


# -- Response factory helpers ------------------------------------------------

def _make_anthropic_text_response(
    model: str,
    text: str,
    input_tokens: int = 500,
    output_tokens: int = 200,
) -> Any:
    """Create a MockMessage with text content."""
    from benchmarks.mocks.mock_anthropic import MockMessage, MockUsage, TextBlock

    return MockMessage(
        id=f"msg_{uuid.uuid4().hex[:24]}",
        model=model,
        content=[TextBlock(text=text)],
        usage=MockUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        stop_reason="end_turn",
    )


def _make_anthropic_tool_response(
    model: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    input_tokens: int = 500,
    output_tokens: int = 200,
) -> Any:
    """Create a MockMessage with tool_use content."""
    from benchmarks.mocks.mock_anthropic import MockMessage, MockUsage, TextBlock, ToolUseBlock

    return MockMessage(
        id=f"msg_{uuid.uuid4().hex[:24]}",
        model=model,
        content=[
            TextBlock(text=f"I'll use {tool_name}."),
            ToolUseBlock(
                id=f"toolu_{uuid.uuid4().hex[:20]}",
                name=tool_name,
                input=tool_input,
            ),
        ],
        usage=MockUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        stop_reason="tool_use",
    )


def _make_openai_text_response(
    model: str,
    text: str,
    prompt_tokens: int = 500,
    completion_tokens: int = 200,
) -> Any:
    """Create a MockCompletion with text content."""
    from benchmarks.mocks.mock_openai import (
        MockCompletion, MockCompletionUsage, MockChoice, MockChoiceMessage,
    )

    return MockCompletion(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        choices=[MockChoice(
            message=MockChoiceMessage(role="assistant", content=text),
            finish_reason="stop",
        )],
        usage=MockCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
        model=model,
    )


def _make_openai_tool_response(
    model: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    prompt_tokens: int = 500,
    completion_tokens: int = 200,
) -> Any:
    """Create a MockCompletion with tool_calls."""
    from benchmarks.mocks.mock_openai import (
        MockCompletion, MockCompletionUsage, MockChoice, MockChoiceMessage,
        MockToolCall, MockFunctionCall,
    )

    return MockCompletion(
        id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
        choices=[MockChoice(
            message=MockChoiceMessage(
                role="assistant",
                content=None,
                tool_calls=[MockToolCall(
                    id=f"call_{uuid.uuid4().hex[:20]}",
                    function=MockFunctionCall(
                        name=tool_name,
                        arguments=json.dumps(tool_input),
                    ),
                )],
            ),
            finish_reason="tool_calls",
        )],
        usage=MockCompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
        model=model,
    )
