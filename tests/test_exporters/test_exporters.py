"""Comprehensive tests for ConsoleExporter and JSONFileExporter."""

import json
import os
import tempfile
import time

import pytest

from agenttelemetry.core.trace import (
    AgentSpan,
    AgentSpanKind,
    AgentTracer,
    SpanStatus,
    ATTR_AGENT_NAME,
    ATTR_LLM_MODEL,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_COST_USD,
    ATTR_TOOL_NAME,
    ATTR_TOOL_SUCCESS,
)
from agenttelemetry.core.events import EventType
from agenttelemetry.exporters.console import ConsoleExporter
from agenttelemetry.exporters.json_file import JSONFileExporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_span(
    name="test-span",
    kind=AgentSpanKind.TASK,
    status=SpanStatus.OK,
    duration_ms=100.0,
    **attrs,
):
    """Create a finished span for testing exporters."""
    start = time.time_ns()
    span = AgentSpan(
        trace_id="aaaa1111bbbb2222",
        span_id="cccc3333",
        parent_span_id=None,
        name=name,
        kind=kind,
        start_time_ns=start,
        end_time_ns=start + int(duration_ms * 1_000_000),
        status=status,
        attributes=dict(attrs),
    )
    return span


# ===================================================================
# ConsoleExporter tests
# ===================================================================


class TestConsoleExporter:
    """Tests for ConsoleExporter."""

    # -- Non-verbose (compact) output --

    def test_compact_output_contains_status(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span(status=SpanStatus.OK)
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "[OK]" in output

    def test_compact_output_contains_error_status(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span(status=SpanStatus.ERROR)
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "[ERROR]" in output

    def test_compact_output_contains_kind(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span(kind=AgentSpanKind.LLM_CALL)
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "llm_call" in output

    def test_compact_output_contains_name(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span(name="llm.gpt-4o")
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "llm.gpt-4o" in output

    def test_compact_output_contains_duration(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span(duration_ms=123.4)
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "123.4ms" in output

    def test_compact_output_shows_tokens_for_llm(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span(
            kind=AgentSpanKind.LLM_CALL,
            **{ATTR_LLM_INPUT_TOKENS: 500, ATTR_LLM_OUTPUT_TOKENS: 200},
        )
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "500" in output
        assert "200" in output
        assert "tokens" in output

    def test_compact_output_shows_cost(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span(
            kind=AgentSpanKind.LLM_CALL,
            **{ATTR_LLM_COST_USD: 0.001234},
        )
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "$0.001234" in output

    def test_compact_output_shows_tool_success(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span(
            kind=AgentSpanKind.TOOL_CALL,
            **{ATTR_TOOL_NAME: "search", ATTR_TOOL_SUCCESS: True},
        )
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "success=True" in output

    def test_compact_output_no_tokens_for_task_span(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span(kind=AgentSpanKind.TASK)
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "tokens" not in output

    def test_compact_output_no_cost_when_zero(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span()
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert "$" not in output

    def test_compact_output_pipe_separated(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        span = _make_span()
        exporter.export_span(span)
        output = capsys.readouterr().out
        assert " | " in output

    # -- Verbose (JSON) output --

    def test_verbose_output_is_valid_json(self, capsys):
        exporter = ConsoleExporter(verbose=True)
        span = _make_span()
        exporter.export_span(span)
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_verbose_output_has_all_keys(self, capsys):
        exporter = ConsoleExporter(verbose=True)
        span = _make_span(name="verbose-span")
        exporter.export_span(span)
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert parsed["name"] == "verbose-span"
        assert parsed["trace_id"] == "aaaa1111bbbb2222"
        assert parsed["span_id"] == "cccc3333"
        assert "start_time_ns" in parsed
        assert "end_time_ns" in parsed
        assert "duration_ms" in parsed
        assert "status" in parsed
        assert "kind" in parsed
        assert "attributes" in parsed
        assert "events" in parsed

    def test_verbose_output_includes_attributes(self, capsys):
        exporter = ConsoleExporter(verbose=True)
        span = _make_span(**{ATTR_AGENT_NAME: "my-agent", "custom": "value"})
        exporter.export_span(span)
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert parsed["attributes"]["agent.name"] == "my-agent"
        assert parsed["attributes"]["custom"] == "value"

    def test_verbose_output_includes_events(self, capsys):
        exporter = ConsoleExporter(verbose=True)
        span = _make_span()
        span.add_event("test_event", EventType.CUSTOM, detail="hello")
        exporter.export_span(span)
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert len(parsed["events"]) == 1
        assert parsed["events"][0]["name"] == "test_event"
        assert parsed["events"][0]["event_type"] == "custom"

    def test_verbose_is_indented(self, capsys):
        exporter = ConsoleExporter(verbose=True)
        span = _make_span()
        exporter.export_span(span)
        output = capsys.readouterr().out
        # indent=2 means there should be lines starting with "  "
        lines = output.strip().split("\n")
        indented_lines = [l for l in lines if l.startswith("  ")]
        assert len(indented_lines) > 0

    # -- Multiple spans --

    def test_export_multiple_spans(self, capsys):
        exporter = ConsoleExporter(verbose=False)
        for i in range(3):
            span = _make_span(name=f"span-{i}")
            exporter.export_span(span)
        output = capsys.readouterr().out
        assert "span-0" in output
        assert "span-1" in output
        assert "span-2" in output


# ===================================================================
# JSONFileExporter tests
# ===================================================================


class TestJSONFileExporter:
    """Tests for JSONFileExporter."""

    @pytest.fixture
    def tmp_file(self, tmp_path):
        """Return a path to a temporary JSONL file."""
        return str(tmp_path / "traces.jsonl")

    @pytest.fixture
    def exporter(self, tmp_file):
        """Return a JSONFileExporter writing to tmp_file."""
        return JSONFileExporter(file_path=tmp_file)

    # -- File creation --

    def test_file_created_on_first_export(self, tmp_file):
        exporter = JSONFileExporter(file_path=tmp_file)
        assert not os.path.exists(tmp_file)
        span = _make_span()
        exporter.export_span(span)
        assert os.path.exists(tmp_file)

    def test_parent_directory_created(self, tmp_path):
        nested_path = str(tmp_path / "sub" / "dir" / "traces.jsonl")
        exporter = JSONFileExporter(file_path=nested_path)
        span = _make_span()
        exporter.export_span(span)
        assert os.path.exists(nested_path)

    # -- Writing --

    def test_single_span_written(self, exporter, tmp_file):
        span = _make_span(name="first")
        exporter.export_span(span)
        with open(tmp_file) as f:
            lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["name"] == "first"

    def test_multiple_spans_appended(self, exporter, tmp_file):
        for i in range(5):
            exporter.export_span(_make_span(name=f"span-{i}"))
        with open(tmp_file) as f:
            lines = f.readlines()
        assert len(lines) == 5

    def test_each_line_is_valid_json(self, exporter, tmp_file):
        for _ in range(3):
            exporter.export_span(_make_span())
        with open(tmp_file) as f:
            for line in f:
                parsed = json.loads(line.strip())
                assert isinstance(parsed, dict)

    def test_span_data_integrity(self, exporter, tmp_file):
        span = _make_span(
            name="integrity-check",
            kind=AgentSpanKind.LLM_CALL,
            status=SpanStatus.OK,
            duration_ms=55.5,
            **{
                ATTR_LLM_MODEL: "gpt-4o",
                ATTR_LLM_INPUT_TOKENS: 100,
                ATTR_LLM_OUTPUT_TOKENS: 50,
            },
        )
        exporter.export_span(span)
        with open(tmp_file) as f:
            data = json.loads(f.readline())
        assert data["name"] == "integrity-check"
        assert data["kind"] == "llm_call"
        assert data["status"] == "ok"
        assert data["trace_id"] == "aaaa1111bbbb2222"
        assert data["span_id"] == "cccc3333"
        assert data["attributes"]["llm.model"] == "gpt-4o"
        assert data["attributes"]["llm.input_tokens"] == 100
        assert data["attributes"]["llm.output_tokens"] == 50
        assert data["duration_ms"] == pytest.approx(55.5)

    def test_events_written(self, exporter, tmp_file):
        span = _make_span()
        span.add_event("error", EventType.ERROR, msg="oops")
        exporter.export_span(span)
        with open(tmp_file) as f:
            data = json.loads(f.readline())
        assert len(data["events"]) == 1
        assert data["events"][0]["event_type"] == "error"
        assert data["events"][0]["attributes"]["msg"] == "oops"

    # -- Reading --

    def test_read_traces_empty_file(self, exporter, tmp_file):
        # File does not exist yet
        result = exporter.read_traces()
        assert result == []

    def test_read_traces_returns_all_spans(self, exporter):
        for i in range(4):
            exporter.export_span(_make_span(name=f"s{i}"))
        traces = exporter.read_traces()
        assert len(traces) == 4
        names = [t["name"] for t in traces]
        assert names == ["s0", "s1", "s2", "s3"]

    def test_read_traces_returns_dicts(self, exporter):
        exporter.export_span(_make_span())
        traces = exporter.read_traces()
        assert isinstance(traces[0], dict)

    def test_read_traces_data_matches_written(self, exporter):
        span = _make_span(
            name="match-test",
            kind=AgentSpanKind.TOOL_CALL,
            **{ATTR_TOOL_NAME: "calculator", ATTR_TOOL_SUCCESS: True},
        )
        exporter.export_span(span)
        traces = exporter.read_traces()
        assert traces[0]["name"] == "match-test"
        assert traces[0]["kind"] == "tool_call"
        assert traces[0]["attributes"]["tool.name"] == "calculator"
        assert traces[0]["attributes"]["tool.success"] is True

    # -- Write-read round trip --

    def test_write_read_round_trip(self, exporter):
        original_span = _make_span(
            name="round-trip",
            kind=AgentSpanKind.REASONING,
            status=SpanStatus.OK,
            duration_ms=75.0,
            **{ATTR_AGENT_NAME: "agent-1", "custom.attr": "hello"},
        )
        exporter.export_span(original_span)
        traces = exporter.read_traces()
        assert len(traces) == 1
        t = traces[0]
        assert t["name"] == "round-trip"
        assert t["kind"] == "reasoning"
        assert t["status"] == "ok"
        assert t["attributes"]["agent.name"] == "agent-1"
        assert t["attributes"]["custom.attr"] == "hello"
        assert t["trace_id"] == original_span.trace_id
        assert t["span_id"] == original_span.span_id

    # -- Blank lines / resilience --

    def test_read_traces_ignores_blank_lines(self, tmp_file):
        with open(tmp_file, "w") as f:
            span_dict = _make_span(name="valid").to_dict()
            f.write(json.dumps(span_dict, default=str) + "\n")
            f.write("\n")  # blank line
            f.write("   \n")  # whitespace-only line
            f.write(json.dumps(_make_span(name="also-valid").to_dict(), default=str) + "\n")
        exporter = JSONFileExporter(file_path=tmp_file)
        traces = exporter.read_traces()
        assert len(traces) == 2
        assert traces[0]["name"] == "valid"
        assert traces[1]["name"] == "also-valid"


# ===================================================================
# Integration: Tracer + Exporter
# ===================================================================


class TestTracerExporterIntegration:
    """Tests that validate tracers work end-to-end with exporters."""

    def test_tracer_with_console_exporter(self, capsys):
        tracer = AgentTracer(agent_name="demo")
        tracer.add_exporter(ConsoleExporter(verbose=False))
        with tracer.start_task("task"):
            with tracer.start_llm_call("gpt-4o") as llm:
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 100)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 50)
        output = capsys.readouterr().out
        # Should have two lines of output (LLM + Task)
        lines = [l for l in output.strip().split("\n") if l.strip()]
        assert len(lines) == 2
        # LLM span should mention tokens
        assert "tokens" in lines[0]

    def test_tracer_with_json_exporter(self, tmp_path):
        filepath = str(tmp_path / "integration.jsonl")
        tracer = AgentTracer(agent_name="demo")
        exporter = JSONFileExporter(file_path=filepath)
        tracer.add_exporter(exporter)

        with tracer.start_task("Summarize") as task:
            with tracer.start_llm_call("gpt-4o") as llm:
                llm.set_attribute(ATTR_LLM_INPUT_TOKENS, 1000)
                llm.set_attribute(ATTR_LLM_OUTPUT_TOKENS, 500)
            with tracer.start_tool_call("save") as tool:
                pass

        traces = exporter.read_traces()
        assert len(traces) == 3

        # Verify parent-child relationships in exported data
        task_data = next(t for t in traces if t["kind"] == "task")
        llm_data = next(t for t in traces if t["kind"] == "llm_call")
        tool_data = next(t for t in traces if t["kind"] == "tool_call")

        assert llm_data["parent_span_id"] == task_data["span_id"]
        assert tool_data["parent_span_id"] == task_data["span_id"]
        assert task_data["parent_span_id"] is None

        # All share trace_id
        assert llm_data["trace_id"] == task_data["trace_id"]
        assert tool_data["trace_id"] == task_data["trace_id"]

    def test_tracer_with_both_exporters(self, capsys, tmp_path):
        filepath = str(tmp_path / "both.jsonl")
        tracer = AgentTracer(agent_name="multi-export")
        tracer.add_exporter(ConsoleExporter(verbose=False))
        tracer.add_exporter(JSONFileExporter(file_path=filepath))

        with tracer.start_task("job"):
            pass

        # Console should have output
        output = capsys.readouterr().out
        assert "[OK]" in output

        # File should have one span
        file_exporter = JSONFileExporter(file_path=filepath)
        traces = file_exporter.read_traces()
        assert len(traces) == 1

    def test_error_propagates_through_exporter_flow(self, tmp_path):
        filepath = str(tmp_path / "errors.jsonl")
        tracer = AgentTracer(agent_name="error-test")
        exporter = JSONFileExporter(file_path=filepath)
        tracer.add_exporter(exporter)

        with pytest.raises(RuntimeError):
            with tracer.start_task("fail"):
                raise RuntimeError("boom")

        traces = exporter.read_traces()
        assert len(traces) == 1
        assert traces[0]["status"] == "error"
