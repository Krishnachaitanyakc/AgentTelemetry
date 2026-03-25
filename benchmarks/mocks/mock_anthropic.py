"""Mock Anthropic SDK client for deterministic benchmarking.

Returns deterministic responses based on input hash.
Mimics the anthropic SDK interface (client.messages.create).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TextBlock:
    """Mimics anthropic.types.TextBlock."""

    text: str
    type: str = "text"


@dataclass
class ToolUseBlock:
    """Mimics anthropic.types.ToolUseBlock."""

    id: str
    name: str
    input: Dict[str, Any]
    type: str = "tool_use"


@dataclass
class MockUsage:
    """Mimics anthropic.types.Usage."""

    input_tokens: int
    output_tokens: int


@dataclass
class MockMessage:
    """Mimics anthropic.types.Message."""

    id: str
    model: str
    content: List[Any]  # TextBlock or ToolUseBlock
    usage: MockUsage
    stop_reason: str
    role: str = "assistant"
    type: str = "message"


# -- Deterministic response templates ----------------------------------------

_TEXT_TEMPLATES = [
    "Based on my analysis, the answer is {seed}.",
    "I found that the key insight relates to {seed}.",
    "After reviewing the information, I conclude: result-{seed}.",
    "The data suggests that {seed} is the most relevant factor.",
    "Here is a summary of my findings regarding {seed}.",
]

_TOOL_RESPONSES = {
    "web_search": {"results": [{"title": "Result", "url": "https://example.com", "snippet": "Found info"}]},
    "calculator": {"result": 42},
    "code_interpreter": {"output": "Execution successful", "exit_code": 0},
    "file_reader": {"content": "File content here", "lines": 10},
    "database_query": {"rows": [{"id": 1, "value": "data"}], "count": 1},
}


def _hash_messages(messages: List[Dict[str, Any]]) -> str:
    """Create a deterministic hash from the message list."""
    content = json.dumps(messages, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def _estimate_input_tokens(messages: List[Dict[str, Any]], tools: Optional[List] = None) -> int:
    """Rough token estimate for input."""
    content = json.dumps(messages, default=str)
    tokens = len(content) // 4  # rough char-to-token ratio
    if tools:
        tokens += len(json.dumps(tools, default=str)) // 4
    return max(tokens, 50)


class MockMessages:
    """Mimics anthropic.Anthropic().messages with sync and async create methods."""

    def __init__(
        self,
        default_model: str = "claude-sonnet-4",
        fault_injector: Any = None,
        latency_ms: float = 0.0,
    ) -> None:
        self._default_model = default_model
        self._fault_injector = fault_injector
        self._latency_ms = latency_ms
        self.call_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_log: List[Dict[str, Any]] = []

    def _should_use_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """Decide whether to return a tool use block based on messages and tools."""
        if not tools:
            return None

        # Look at the last user message for tool-trigger keywords
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                last_user_msg = content if isinstance(content, str) else str(content)
                break

        # If a tool_result was just provided, don't call tools again
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            return None
                break

        # Use deterministic selection based on hash
        msg_hash = _hash_messages(messages)
        hash_val = int(msg_hash, 16)

        # 60% chance of tool use when tools are available and no recent tool_result
        if hash_val % 10 < 6:
            tool_idx = hash_val % len(tools)
            selected_tool = tools[tool_idx]
            tool_name = selected_tool.get("name", "unknown_tool")

            # Generate deterministic input based on tool schema
            tool_input = {}
            schema = selected_tool.get("input_schema", {})
            properties = schema.get("properties", {})
            for prop_name, prop_def in properties.items():
                prop_type = prop_def.get("type", "string")
                if prop_type == "string":
                    tool_input[prop_name] = f"query-{msg_hash[:6]}"
                elif prop_type == "integer":
                    tool_input[prop_name] = hash_val % 100
                elif prop_type == "boolean":
                    tool_input[prop_name] = hash_val % 2 == 0
                elif prop_type == "number":
                    tool_input[prop_name] = (hash_val % 1000) / 10.0

            return {"name": tool_name, "input": tool_input}

        return None

    def create(
        self,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> MockMessage:
        """Synchronous message creation mimicking anthropic SDK."""
        if self._fault_injector:
            result = self._fault_injector.maybe_inject("anthropic", self, model, messages, tools, kwargs)
            if result is not None:
                return result

        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)

        messages = messages or [{"role": "user", "content": "Hello"}]
        model = model or self._default_model
        msg_hash = _hash_messages(messages)

        self.call_count += 1
        input_tokens = _estimate_input_tokens(messages, tools)
        output_tokens = min(max_tokens, 50 + (int(msg_hash, 16) % 200))

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # Decide content
        tool_decision = self._should_use_tools(messages, tools)
        if tool_decision:
            tool_use_id = f"toolu_{msg_hash[:20]}"
            content = [
                TextBlock(text=f"I'll use the {tool_decision['name']} tool."),
                ToolUseBlock(
                    id=tool_use_id,
                    name=tool_decision["name"],
                    input=tool_decision["input"],
                ),
            ]
            stop_reason = "tool_use"
        else:
            seed = msg_hash[:8]
            template_idx = int(msg_hash, 16) % len(_TEXT_TEMPLATES)
            text = _TEXT_TEMPLATES[template_idx].format(seed=seed)
            content = [TextBlock(text=text)]
            stop_reason = "end_turn"

        message = MockMessage(
            id=f"msg_{uuid.uuid4().hex[:24]}",
            model=model,
            content=content,
            usage=MockUsage(input_tokens=input_tokens, output_tokens=output_tokens),
            stop_reason=stop_reason,
        )

        self.call_log.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "stop_reason": stop_reason,
            "tool_used": tool_decision["name"] if tool_decision else None,
        })

        return message

    async def acreate(
        self,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> MockMessage:
        """Async version of create."""
        return self.create(model=model, max_tokens=max_tokens, messages=messages, tools=tools, **kwargs)


class MockAnthropicClient:
    """Drop-in replacement for anthropic.Anthropic() in benchmarks.

    Usage::

        client = MockAnthropicClient()
        response = client.messages.create(
            model="claude-sonnet-4",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(response.content[0].text)
    """

    def __init__(
        self,
        default_model: str = "claude-sonnet-4",
        fault_injector: Any = None,
        latency_ms: float = 0.0,
    ) -> None:
        self.messages = MockMessages(
            default_model=default_model,
            fault_injector=fault_injector,
            latency_ms=latency_ms,
        )

    def get_call_stats(self) -> Dict[str, Any]:
        """Return statistics about mock API calls."""
        return {
            "call_count": self.messages.call_count,
            "total_input_tokens": self.messages.total_input_tokens,
            "total_output_tokens": self.messages.total_output_tokens,
            "call_log": self.messages.call_log,
        }

    def reset_stats(self) -> None:
        """Reset call statistics."""
        self.messages.call_count = 0
        self.messages.total_input_tokens = 0
        self.messages.total_output_tokens = 0
        self.messages.call_log.clear()
