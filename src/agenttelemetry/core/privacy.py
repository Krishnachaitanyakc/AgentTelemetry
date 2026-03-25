"""Privacy controls for AgentTelemetry.

Controls what level of detail is captured in span attributes.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from agenttelemetry.core.spans import (
    LLM_PROMPT,
    LLM_COMPLETION,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_INPUT_TOKENS,
    LLM_OUTPUT_TOKENS,
    LLM_TOTAL_TOKENS,
    LLM_COST,
    LLM_TEMPERATURE,
    LLM_LATENCY_MS,
    TOOL_NAME,
    TOOL_INPUT,
    TOOL_OUTPUT,
    TOOL_STATUS,
    TOOL_DESCRIPTION,
    TOOL_LATENCY_MS,
    RETRIEVAL_SOURCE,
    RETRIEVAL_QUERY,
    RETRIEVAL_DOC_COUNT,
    AGENT_SPAN_KIND,
    AGENT_NAME,
    AGENT_FRAMEWORK,
    AGENT_FRAMEWORK_VERSION,
)


class PrivacyLevel(Enum):
    """Controls what data is captured in spans.

    NONE: Only structural info — span kind, timing, status. No model names,
          token counts, or content.
    METADATA_ONLY: Add model name, token counts, tool names, costs — but no
                   prompt/completion content or tool I/O content. This is the
                   default.
    FULL: Capture everything including prompt content, completions, tool
          inputs/outputs. Opt-in only.
    """

    NONE = "none"
    METADATA_ONLY = "metadata_only"
    FULL = "full"


# Attributes always allowed (structural)
_STRUCTURAL_ATTRS = {
    AGENT_SPAN_KIND,
    AGENT_NAME,
    AGENT_FRAMEWORK,
    AGENT_FRAMEWORK_VERSION,
    TOOL_STATUS,
    TOOL_LATENCY_MS,
    LLM_LATENCY_MS,
}

# Attributes allowed at METADATA_ONLY level
_METADATA_ATTRS = _STRUCTURAL_ATTRS | {
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_INPUT_TOKENS,
    LLM_OUTPUT_TOKENS,
    LLM_TOTAL_TOKENS,
    LLM_COST,
    LLM_TEMPERATURE,
    TOOL_NAME,
    TOOL_DESCRIPTION,
    RETRIEVAL_SOURCE,
    RETRIEVAL_DOC_COUNT,
}

# Attributes that contain content (only at FULL level)
_CONTENT_ATTRS = {
    LLM_PROMPT,
    LLM_COMPLETION,
    TOOL_INPUT,
    TOOL_OUTPUT,
    RETRIEVAL_QUERY,
}


def filter_attributes(
    attributes: Dict[str, Any],
    privacy_level: PrivacyLevel,
) -> Dict[str, Any]:
    """Filter span attributes according to the privacy level.

    Attributes not in any known set are passed through at METADATA_ONLY
    and FULL levels (they are custom user attributes).
    """
    if privacy_level == PrivacyLevel.FULL:
        return attributes

    if privacy_level == PrivacyLevel.NONE:
        return {k: v for k, v in attributes.items() if k in _STRUCTURAL_ATTRS}

    # METADATA_ONLY: allow structural + metadata, block content
    return {
        k: v
        for k, v in attributes.items()
        if k not in _CONTENT_ATTRS
    }


def should_capture_content(privacy_level: PrivacyLevel) -> bool:
    """Whether to capture prompt/completion content at this privacy level."""
    return privacy_level == PrivacyLevel.FULL
