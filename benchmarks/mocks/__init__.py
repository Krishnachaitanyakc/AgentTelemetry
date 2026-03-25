"""Mock LLM clients for deterministic benchmarking."""

from benchmarks.mocks.mock_anthropic import (
    MockAnthropicClient,
    MockMessage,
    MockUsage,
    TextBlock,
    ToolUseBlock,
)
from benchmarks.mocks.mock_openai import (
    MockOpenAIClient,
    MockCompletion,
    MockCompletionUsage,
    MockChoice,
    MockChoiceMessage,
    MockToolCall,
    MockFunctionCall,
)

__all__ = [
    "MockAnthropicClient",
    "MockMessage",
    "MockUsage",
    "TextBlock",
    "ToolUseBlock",
    "MockOpenAIClient",
    "MockCompletion",
    "MockCompletionUsage",
    "MockChoice",
    "MockChoiceMessage",
    "MockToolCall",
    "MockFunctionCall",
]
