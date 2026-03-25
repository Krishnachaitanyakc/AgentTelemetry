"""Mock OpenAI SDK client for deterministic benchmarking.

Returns deterministic responses based on input hash.
Mimics the openai SDK interface (client.chat.completions.create).
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MockFunctionCall:
    """Mimics openai.types.chat.ChatCompletionMessageToolCall.Function."""

    name: str
    arguments: str  # JSON string


@dataclass
class MockToolCall:
    """Mimics openai.types.chat.ChatCompletionMessageToolCall."""

    id: str
    function: MockFunctionCall
    type: str = "function"


@dataclass
class MockChoiceMessage:
    """Mimics openai.types.chat.ChatCompletionMessage."""

    role: str = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[MockToolCall]] = None


@dataclass
class MockChoice:
    """Mimics openai.types.chat.Choice."""

    message: MockChoiceMessage
    finish_reason: str
    index: int = 0


@dataclass
class MockCompletionUsage:
    """Mimics openai.types.CompletionUsage."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class MockCompletion:
    """Mimics openai.types.chat.ChatCompletion."""

    id: str
    choices: List[MockChoice]
    usage: MockCompletionUsage
    model: str
    object: str = "chat.completion"
    created: int = 0


# -- Deterministic response templates ----------------------------------------

_TEXT_TEMPLATES = [
    "Based on my analysis, the answer is {seed}.",
    "I found that the key insight relates to {seed}.",
    "After reviewing the information, I conclude: result-{seed}.",
    "The data suggests that {seed} is the most relevant factor.",
    "Here is a summary of my findings regarding {seed}.",
]


def _hash_messages(messages: List[Dict[str, Any]]) -> str:
    """Create a deterministic hash from the message list."""
    content = json.dumps(messages, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def _estimate_prompt_tokens(messages: List[Dict[str, Any]], tools: Optional[List] = None) -> int:
    """Rough token estimate for prompt."""
    content = json.dumps(messages, default=str)
    tokens = len(content) // 4
    if tools:
        tokens += len(json.dumps(tools, default=str)) // 4
    return max(tokens, 50)


class MockCompletions:
    """Mimics openai.OpenAI().chat.completions with create method."""

    def __init__(
        self,
        default_model: str = "gpt-4o",
        fault_injector: Any = None,
        latency_ms: float = 0.0,
    ) -> None:
        self._default_model = default_model
        self._fault_injector = fault_injector
        self._latency_ms = latency_ms
        self.call_count = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.call_log: List[Dict[str, Any]] = []

    def _should_use_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """Decide whether to return tool calls based on messages and tools."""
        if not tools:
            return None

        # If the last message is a tool response, don't call tools again
        if messages and messages[-1].get("role") == "tool":
            return None

        msg_hash = _hash_messages(messages)
        hash_val = int(msg_hash, 16)

        # 60% chance of tool use when tools are available
        if hash_val % 10 < 6:
            tool_idx = hash_val % len(tools)
            selected_tool = tools[tool_idx]
            func = selected_tool.get("function", {})
            tool_name = func.get("name", "unknown_tool")

            # Generate deterministic arguments based on function schema
            arguments = {}
            params = func.get("parameters", {})
            properties = params.get("properties", {})
            for prop_name, prop_def in properties.items():
                prop_type = prop_def.get("type", "string")
                if prop_type == "string":
                    arguments[prop_name] = f"query-{msg_hash[:6]}"
                elif prop_type == "integer":
                    arguments[prop_name] = hash_val % 100
                elif prop_type == "boolean":
                    arguments[prop_name] = hash_val % 2 == 0
                elif prop_type == "number":
                    arguments[prop_name] = (hash_val % 1000) / 10.0

            return {"name": tool_name, "arguments": arguments}

        return None

    def create(
        self,
        model: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> MockCompletion:
        """Synchronous completion creation mimicking openai SDK."""
        if self._fault_injector:
            result = self._fault_injector.maybe_inject("openai", self, model, messages, tools, kwargs)
            if result is not None:
                return result

        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)

        messages = messages or [{"role": "user", "content": "Hello"}]
        model = model or self._default_model
        msg_hash = _hash_messages(messages)

        self.call_count += 1
        prompt_tokens = _estimate_prompt_tokens(messages, tools)
        max_out = max_tokens or 1024
        completion_tokens = min(max_out, 50 + (int(msg_hash, 16) % 200))

        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens

        # Decide content
        tool_decision = self._should_use_tools(messages, tools)
        if tool_decision:
            tool_call = MockToolCall(
                id=f"call_{msg_hash[:20]}",
                function=MockFunctionCall(
                    name=tool_decision["name"],
                    arguments=json.dumps(tool_decision["arguments"]),
                ),
            )
            choice_message = MockChoiceMessage(
                role="assistant",
                content=None,
                tool_calls=[tool_call],
            )
            finish_reason = "tool_calls"
        else:
            seed = msg_hash[:8]
            template_idx = int(msg_hash, 16) % len(_TEXT_TEMPLATES)
            text = _TEXT_TEMPLATES[template_idx].format(seed=seed)
            choice_message = MockChoiceMessage(
                role="assistant",
                content=text,
                tool_calls=None,
            )
            finish_reason = "stop"

        total_tokens = prompt_tokens + completion_tokens
        completion = MockCompletion(
            id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
            choices=[MockChoice(message=choice_message, finish_reason=finish_reason)],
            usage=MockCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
            ),
            model=model,
            created=int(time.time()),
        )

        self.call_log.append({
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "finish_reason": finish_reason,
            "tool_used": tool_decision["name"] if tool_decision else None,
        })

        return completion

    async def acreate(
        self,
        model: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs: Any,
    ) -> MockCompletion:
        """Async version of create."""
        return self.create(
            model=model, messages=messages, tools=tools,
            max_tokens=max_tokens, temperature=temperature, **kwargs,
        )


class MockChat:
    """Mimics openai.OpenAI().chat namespace."""

    def __init__(
        self,
        default_model: str = "gpt-4o",
        fault_injector: Any = None,
        latency_ms: float = 0.0,
    ) -> None:
        self.completions = MockCompletions(
            default_model=default_model,
            fault_injector=fault_injector,
            latency_ms=latency_ms,
        )


class _AnthropicAdapter:
    """Adapts MockOpenAIClient to accept Anthropic-style .messages.create() calls.

    Converts between Anthropic and OpenAI response formats so benchmark apps
    can use a single interface regardless of which mock client is provided.
    """

    def __init__(self, completions: "MockCompletions") -> None:
        self._completions = completions

    def create(
        self,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Any:
        # Convert Anthropic-style tools to OpenAI-style if needed
        openai_tools = None
        if tools:
            openai_tools = []
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name", "unknown"),
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {}),
                    },
                })

        completion = self._completions.create(
            model=model or self._completions._default_model,
            messages=messages or [],
            tools=openai_tools,
            max_tokens=max_tokens,
        )

        # Convert OpenAI response to Anthropic-compatible format
        from benchmarks.mocks.mock_anthropic import TextBlock, ToolUseBlock, MockUsage, MockMessage
        import uuid as _uuid

        choice = completion.choices[0]
        content: List[Any] = []
        stop_reason = "end_turn"

        if choice.message.content:
            content.append(TextBlock(text=choice.message.content))

        if choice.message.tool_calls:
            stop_reason = "tool_use"
            for tc in choice.message.tool_calls:
                try:
                    tool_input = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    tool_input = {"input": tc.function.arguments}
                content.append(ToolUseBlock(
                    id=tc.id,
                    name=tc.function.name,
                    input=tool_input,
                ))

        if not content:
            content.append(TextBlock(text="No response generated."))

        return MockMessage(
            id=f"msg_{_uuid.uuid4().hex[:24]}",
            model=completion.model,
            content=content,
            usage=MockUsage(
                input_tokens=completion.usage.prompt_tokens,
                output_tokens=completion.usage.completion_tokens,
            ),
            stop_reason=stop_reason,
        )


class MockOpenAIClient:
    """Drop-in replacement for openai.OpenAI() in benchmarks.

    Supports both OpenAI-style and Anthropic-style interfaces::

        # OpenAI-style
        response = client.chat.completions.create(model="gpt-4o", messages=[...])

        # Anthropic-style (via adapter)
        response = client.messages.create(model="gpt-4o", messages=[...])
    """

    def __init__(
        self,
        default_model: str = "gpt-4o",
        fault_injector: Any = None,
        latency_ms: float = 0.0,
    ) -> None:
        self.chat = MockChat(
            default_model=default_model,
            fault_injector=fault_injector,
            latency_ms=latency_ms,
        )
        self.messages = _AnthropicAdapter(self.chat.completions)

    def get_call_stats(self) -> Dict[str, Any]:
        """Return statistics about mock API calls."""
        completions = self.chat.completions
        return {
            "call_count": completions.call_count,
            "total_prompt_tokens": completions.total_prompt_tokens,
            "total_completion_tokens": completions.total_completion_tokens,
            "call_log": completions.call_log,
        }

    def reset_stats(self) -> None:
        """Reset call statistics."""
        completions = self.chat.completions
        completions.call_count = 0
        completions.total_prompt_tokens = 0
        completions.total_completion_tokens = 0
        completions.call_log.clear()
