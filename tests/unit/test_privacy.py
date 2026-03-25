"""Unit tests for agenttelemetry.core.privacy."""

import pytest

from agenttelemetry.core.privacy import (
    PrivacyLevel,
    filter_attributes,
    should_capture_content,
    _STRUCTURAL_ATTRS,
    _METADATA_ATTRS,
    _CONTENT_ATTRS,
)
from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND,
    AGENT_NAME,
    LLM_MODEL,
    LLM_INPUT_TOKENS,
    LLM_COST,
    LLM_PROMPT,
    LLM_COMPLETION,
    TOOL_NAME,
    TOOL_INPUT,
    TOOL_OUTPUT,
    TOOL_STATUS,
    TOOL_LATENCY_MS,
    LLM_LATENCY_MS,
)


@pytest.fixture()
def full_attributes():
    """A representative set of span attributes spanning all categories."""
    return {
        # Structural
        AGENT_SPAN_KIND: "LLM_CALL",
        AGENT_NAME: "my-agent",
        TOOL_STATUS: "success",
        TOOL_LATENCY_MS: 150,
        LLM_LATENCY_MS: 800,
        # Metadata
        LLM_MODEL: "gpt-4o",
        LLM_INPUT_TOKENS: 100,
        LLM_COST: 0.001,
        TOOL_NAME: "search",
        # Content
        LLM_PROMPT: "What is the weather?",
        LLM_COMPLETION: "The weather is sunny.",
        TOOL_INPUT: '{"query": "weather"}',
        TOOL_OUTPUT: '{"result": "sunny"}',
        # Custom user attribute
        "custom.user_id": "user-123",
    }


class TestPrivacyLevelEnum:
    """Tests for the PrivacyLevel enum."""

    def test_has_three_levels(self):
        assert len(PrivacyLevel) == 3

    def test_values(self):
        assert PrivacyLevel.NONE.value == "none"
        assert PrivacyLevel.METADATA_ONLY.value == "metadata_only"
        assert PrivacyLevel.FULL.value == "full"


class TestFilterAttributesNone:
    """PrivacyLevel.NONE should keep only structural attributes."""

    def test_keeps_structural_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.NONE)
        for key in _STRUCTURAL_ATTRS:
            if key in full_attributes:
                assert key in filtered

    def test_strips_metadata_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.NONE)
        assert LLM_MODEL not in filtered
        assert LLM_INPUT_TOKENS not in filtered
        assert LLM_COST not in filtered
        assert TOOL_NAME not in filtered

    def test_strips_content_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.NONE)
        assert LLM_PROMPT not in filtered
        assert LLM_COMPLETION not in filtered
        assert TOOL_INPUT not in filtered
        assert TOOL_OUTPUT not in filtered

    def test_strips_custom_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.NONE)
        assert "custom.user_id" not in filtered


class TestFilterAttributesMetadataOnly:
    """PrivacyLevel.METADATA_ONLY keeps metadata but strips content."""

    def test_keeps_structural_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.METADATA_ONLY)
        for key in _STRUCTURAL_ATTRS:
            if key in full_attributes:
                assert key in filtered

    def test_keeps_metadata_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.METADATA_ONLY)
        assert filtered[LLM_MODEL] == "gpt-4o"
        assert filtered[LLM_INPUT_TOKENS] == 100
        assert filtered[LLM_COST] == 0.001
        assert filtered[TOOL_NAME] == "search"

    def test_strips_content_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.METADATA_ONLY)
        assert LLM_PROMPT not in filtered
        assert LLM_COMPLETION not in filtered
        assert TOOL_INPUT not in filtered
        assert TOOL_OUTPUT not in filtered

    def test_passes_through_custom_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.METADATA_ONLY)
        assert filtered["custom.user_id"] == "user-123"


class TestFilterAttributesFull:
    """PrivacyLevel.FULL keeps everything."""

    def test_keeps_all_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.FULL)
        assert filtered == full_attributes

    def test_keeps_content_attrs(self, full_attributes):
        filtered = filter_attributes(full_attributes, PrivacyLevel.FULL)
        assert filtered[LLM_PROMPT] == "What is the weather?"
        assert filtered[LLM_COMPLETION] == "The weather is sunny."
        assert filtered[TOOL_INPUT] == '{"query": "weather"}'
        assert filtered[TOOL_OUTPUT] == '{"result": "sunny"}'


class TestShouldCaptureContent:
    """Tests for should_capture_content."""

    def test_none_returns_false(self):
        assert should_capture_content(PrivacyLevel.NONE) is False

    def test_metadata_only_returns_false(self):
        assert should_capture_content(PrivacyLevel.METADATA_ONLY) is False

    def test_full_returns_true(self):
        assert should_capture_content(PrivacyLevel.FULL) is True
