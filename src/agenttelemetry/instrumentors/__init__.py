"""Instrumentors for agent frameworks.

Each instrumentor monkey-patches or hooks into a specific agent framework
to automatically capture telemetry (spans and metrics) without requiring
changes to user code.

Available instrumentors:

    LangChainInstrumentor       — LangChain / LangGraph
    CrewAIInstrumentor          — CrewAI
    AutoGenInstrumentor         — Microsoft AutoGen
    DSPyInstrumentor            — Stanford DSPy
    ClaudeAgentInstrumentor     — Anthropic Claude Agent SDK
    SmolagentsInstrumentor      — HuggingFace smolagents
    LlamaIndexInstrumentor      — LlamaIndex
"""

from agenttelemetry.instrumentors.base import BaseInstrumentor

__all__ = [
    "BaseInstrumentor",
    "LangChainInstrumentor",
    "CrewAIInstrumentor",
    "AutoGenInstrumentor",
    "DSPyInstrumentor",
    "ClaudeAgentInstrumentor",
    "SmolagentsInstrumentor",
    "LlamaIndexInstrumentor",
]


def __getattr__(name: str):
    """Lazy-load instrumentors to avoid import errors when optional
    dependencies are not installed."""
    _lazy_map = {
        "LangChainInstrumentor": "agenttelemetry.instrumentors.langchain",
        "CrewAIInstrumentor": "agenttelemetry.instrumentors.crewai",
        "AutoGenInstrumentor": "agenttelemetry.instrumentors.autogen",
        "DSPyInstrumentor": "agenttelemetry.instrumentors.dspy",
        "ClaudeAgentInstrumentor": "agenttelemetry.instrumentors.claude_agent",
        "SmolagentsInstrumentor": "agenttelemetry.instrumentors.smolagents",
        "LlamaIndexInstrumentor": "agenttelemetry.instrumentors.llamaindex",
    }
    if name in _lazy_map:
        import importlib

        module = importlib.import_module(_lazy_map[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
