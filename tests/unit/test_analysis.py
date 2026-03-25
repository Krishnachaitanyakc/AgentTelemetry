"""Unit tests for agenttelemetry.analysis modules."""

from __future__ import annotations

from typing import Optional

import pytest


# ---------------------------------------------------------------------------
# Helper: build mock span dicts for analysis tests
# ---------------------------------------------------------------------------

def _make_span(
    name: str,
    agent_span_kind: str,
    span_id: str = "0000000000000001",
    parent_span_id: Optional[str] = None,
    trace_id: str = "00000000000000000000000000000001",
    attributes: Optional[dict] = None,
    duration_ms: float = 100.0,
    start_time_ns: int = 1000000000,
    status_code: str = "OK",
):
    """Create a mock span dict matching the shape from exporters._span_to_dict."""
    base_attrs = {"agenttelemetry.span.kind": agent_span_kind}
    if attributes:
        base_attrs.update(attributes)
    end_time_ns = start_time_ns + int(duration_ms * 1_000_000)
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": parent_span_id,
        "name": name,
        "kind": "INTERNAL",
        "agent_span_kind": agent_span_kind,
        "start_time_ns": start_time_ns,
        "end_time_ns": end_time_ns,
        "duration_ms": duration_ms,
        "status": {"code": status_code, "description": ""},
        "attributes": base_attrs,
        "events": [],
        "resource": {"service.name": "test"},
    }


# ---------------------------------------------------------------------------
# CostAggregator tests
# ---------------------------------------------------------------------------

class TestCostAggregator:
    @pytest.fixture(autouse=True)
    def _import_module(self):
        from agenttelemetry.analysis.cost_aggregation import CostAggregator
        self.CostAggregator = CostAggregator

    def _sample_spans(self):
        return [
            _make_span("llm-1", "LLM_CALL", span_id="0001", attributes={
                "llm.model": "gpt-4o",
                "llm.input_tokens": 1000,
                "llm.output_tokens": 500,
                "llm.cost": 0.0075,
                "agent.name": "planner",
            }),
            _make_span("llm-2", "LLM_CALL", span_id="0002", attributes={
                "llm.model": "gpt-4o",
                "llm.input_tokens": 2000,
                "llm.output_tokens": 800,
                "llm.cost": 0.013,
                "agent.name": "executor",
            }),
            _make_span("llm-3", "LLM_CALL", span_id="0003", attributes={
                "llm.model": "claude-3-5-sonnet",
                "llm.input_tokens": 500,
                "llm.output_tokens": 200,
                "llm.cost": 0.0045,
                "agent.name": "planner",
            }),
            _make_span("tool-1", "TOOL_CALL", span_id="0004", attributes={
                "tool.name": "search",
            }),
        ]

    def test_total_cost(self):
        aggregator = self.CostAggregator()
        report = aggregator.analyze(self._sample_spans())
        assert report.total_cost == pytest.approx(0.0075 + 0.013 + 0.0045)

    def test_cost_by_model(self):
        aggregator = self.CostAggregator()
        report = aggregator.analyze(self._sample_spans())
        assert "gpt-4o" in report.by_model
        assert report.by_model["gpt-4o"].cost == pytest.approx(0.0075 + 0.013)
        assert "claude-3-5-sonnet" in report.by_model
        assert report.by_model["claude-3-5-sonnet"].cost == pytest.approx(0.0045)

    def test_cost_by_agent(self):
        aggregator = self.CostAggregator()
        report = aggregator.analyze(self._sample_spans())
        assert "planner" in report.by_agent
        assert report.by_agent["planner"] == pytest.approx(0.0075 + 0.0045)
        assert "executor" in report.by_agent
        assert report.by_agent["executor"] == pytest.approx(0.013)

    def test_ignores_non_llm_spans(self):
        spans = [
            _make_span("tool", "TOOL_CALL", attributes={"tool.name": "x"}),
        ]
        aggregator = self.CostAggregator()
        report = aggregator.analyze(spans)
        assert report.total_cost == 0.0

    def test_empty_spans(self):
        aggregator = self.CostAggregator()
        report = aggregator.analyze([])
        assert report.total_cost == 0.0
        assert report.by_model == {}
        assert report.by_agent == {}

    def test_token_counts(self):
        aggregator = self.CostAggregator()
        report = aggregator.analyze(self._sample_spans())
        assert report.total_input_tokens == 3500
        assert report.total_output_tokens == 1500

    def test_model_call_count(self):
        aggregator = self.CostAggregator()
        report = aggregator.analyze(self._sample_spans())
        assert report.by_model["gpt-4o"].call_count == 2
        assert report.by_model["claude-3-5-sonnet"].call_count == 1


# ---------------------------------------------------------------------------
# DecisionAttributor tests
# ---------------------------------------------------------------------------

class TestDecisionAttributor:
    @pytest.fixture(autouse=True)
    def _import_module(self):
        from agenttelemetry.analysis.decision_attribution import DecisionAttributor
        self.DecisionAttributor = DecisionAttributor

    def test_links_tool_call_to_parent_llm(self):
        spans = [
            _make_span("llm-decide", "LLM_CALL", span_id="0001", attributes={
                "llm.model": "gpt-4o", "agent.name": "planner",
            }),
            _make_span("tool-exec", "TOOL_CALL", span_id="0002", parent_span_id="0001",
                        attributes={"tool.name": "search"}),
        ]
        attributor = self.DecisionAttributor()
        decisions = attributor.analyze(spans)
        assert len(decisions) == 1
        assert decisions[0].tool_span_id == "0002"
        assert decisions[0].llm_span_id == "0001"
        assert decisions[0].tool_name == "search"

    def test_no_links_when_no_tool_calls(self):
        spans = [
            _make_span("llm-1", "LLM_CALL", span_id="0001"),
        ]
        attributor = self.DecisionAttributor()
        decisions = attributor.analyze(spans)
        assert len(decisions) == 0

    def test_multiple_tools_from_same_llm(self):
        spans = [
            _make_span("llm", "LLM_CALL", span_id="0001", attributes={
                "llm.model": "gpt-4o",
            }),
            _make_span("tool-1", "TOOL_CALL", span_id="0002", parent_span_id="0001",
                        attributes={"tool.name": "search"}),
            _make_span("tool-2", "TOOL_CALL", span_id="0003", parent_span_id="0001",
                        attributes={"tool.name": "calculate"}),
        ]
        attributor = self.DecisionAttributor()
        decisions = attributor.analyze(spans)
        assert len(decisions) == 2
        tool_names = {d.tool_name for d in decisions}
        assert tool_names == {"search", "calculate"}


# ---------------------------------------------------------------------------
# AnomalyDetector tests
# ---------------------------------------------------------------------------

class TestAnomalyDetector:
    @pytest.fixture(autouse=True)
    def _import_module(self):
        from agenttelemetry.analysis.anomaly_detection import AnomalyDetector, AnomalyType
        self.AnomalyDetector = AnomalyDetector
        self.AnomalyType = AnomalyType

    def test_detects_circular_delegation(self):
        spans = [
            _make_span("delegate-A-to-B", "DELEGATION", span_id="0001", attributes={
                "delegation.source_agent": "A",
                "delegation.target_agent": "B",
            }),
            _make_span("delegate-B-to-A", "DELEGATION", span_id="0002", attributes={
                "delegation.source_agent": "B",
                "delegation.target_agent": "A",
            }),
        ]
        detector = self.AnomalyDetector()
        anomalies = detector.detect(spans)
        circular = [a for a in anomalies if a.anomaly_type == self.AnomalyType.CIRCULAR_DELEGATION]
        assert len(circular) >= 1

    def test_no_circular_delegation_in_linear_chain(self):
        spans = [
            _make_span("delegate-A-to-B", "DELEGATION", span_id="0001", attributes={
                "delegation.source_agent": "A",
                "delegation.target_agent": "B",
            }),
            _make_span("delegate-B-to-C", "DELEGATION", span_id="0002", attributes={
                "delegation.source_agent": "B",
                "delegation.target_agent": "C",
            }),
        ]
        detector = self.AnomalyDetector()
        anomalies = detector.detect(spans)
        circular = [a for a in anomalies if a.anomaly_type == self.AnomalyType.CIRCULAR_DELEGATION]
        assert len(circular) == 0

    def test_detects_infinite_retries(self):
        spans = [
            _make_span(f"tool-retry-{i}", "TOOL_CALL", span_id=f"{i:04d}", attributes={
                "tool.name": "flaky_api",
                "tool.status": "error",
            })
            for i in range(20)
        ]
        detector = self.AnomalyDetector(max_retries=5)
        anomalies = detector.detect(spans)
        retry = [a for a in anomalies if a.anomaly_type == self.AnomalyType.INFINITE_RETRY]
        assert len(retry) >= 1

    def test_no_retry_anomaly_for_few_calls(self):
        spans = [
            _make_span("tool-1", "TOOL_CALL", span_id="0001", attributes={
                "tool.name": "api", "tool.status": "error",
            }),
            _make_span("tool-2", "TOOL_CALL", span_id="0002", attributes={
                "tool.name": "api", "tool.status": "success",
            }),
        ]
        detector = self.AnomalyDetector(max_retries=5)
        anomalies = detector.detect(spans)
        retry = [a for a in anomalies if a.anomaly_type == self.AnomalyType.INFINITE_RETRY]
        assert len(retry) == 0

    def test_detects_cost_explosion(self):
        spans = [
            _make_span("expensive", "LLM_CALL", span_id="0001", attributes={
                "llm.cost": 50.0,
                "llm.model": "gpt-4",
            }),
        ]
        detector = self.AnomalyDetector(cost_threshold=10.0)
        anomalies = detector.detect(spans)
        cost = [a for a in anomalies if a.anomaly_type == self.AnomalyType.COST_EXPLOSION]
        assert len(cost) >= 1

    def test_no_cost_anomaly_under_threshold(self):
        spans = [
            _make_span("cheap", "LLM_CALL", span_id="0001", attributes={
                "llm.cost": 0.01,
                "llm.model": "gpt-4o-mini",
            }),
        ]
        detector = self.AnomalyDetector(cost_threshold=10.0)
        anomalies = detector.detect(spans)
        cost = [a for a in anomalies if a.anomaly_type == self.AnomalyType.COST_EXPLOSION]
        assert len(cost) == 0

    def test_detects_context_overflow(self):
        spans = [
            _make_span(f"llm-{i}", "LLM_CALL", span_id=f"{i:04d}",
                       start_time_ns=1000000000 + i * 100000000,
                       attributes={
                           "llm.input_tokens": 100 * (2 ** i),
                           "llm.model": "gpt-4o",
                       })
            for i in range(4)
        ]
        detector = self.AnomalyDetector(token_growth_factor=1.5)
        anomalies = detector.detect(spans)
        overflow = [a for a in anomalies if a.anomaly_type == self.AnomalyType.CONTEXT_OVERFLOW]
        assert len(overflow) >= 1


# ---------------------------------------------------------------------------
# HallucinationTracer tests
# ---------------------------------------------------------------------------

class TestHallucinationTracer:
    @pytest.fixture(autouse=True)
    def _import_module(self):
        from agenttelemetry.analysis.hallucination_tracing import HallucinationTracer
        self.HallucinationTracer = HallucinationTracer

    def test_finds_ungrounded_claims(self):
        spans = [
            _make_span("agent", "AGENT", span_id="0000"),
            _make_span("retrieval", "RETRIEVAL", span_id="0001", parent_span_id="0000",
                        attributes={
                            "retrieval.source": "docs",
                            "retrieval.query": "population of Paris",
                            "tool.output": "Paris has a population of 2.1 million in the city proper.",
                        }),
            _make_span("llm-response", "LLM_CALL", span_id="0002", parent_span_id="0000",
                        attributes={
                            "llm.completion": "The magnificent city of Zarqon has exactly 47 billion inhabitants across its seventeen dimensions.",
                            "llm.model": "gpt-4o",
                        }),
        ]
        tracer = self.HallucinationTracer(min_confidence=0.3)
        findings = tracer.analyze(spans)
        assert isinstance(findings, list)
        assert len(findings) >= 1

    def test_empty_spans_returns_empty(self):
        tracer = self.HallucinationTracer()
        findings = tracer.analyze([])
        assert findings == []

    def test_no_hallucination_when_grounded(self):
        spans = [
            _make_span("agent", "AGENT", span_id="0000"),
            _make_span("retrieval", "RETRIEVAL", span_id="0001", parent_span_id="0000",
                        attributes={
                            "tool.output": "Paris has a population of 2.1 million people in the city proper.",
                        }),
            _make_span("llm-response", "LLM_CALL", span_id="0002", parent_span_id="0000",
                        attributes={
                            "llm.completion": "Paris has a population of 2.1 million people in the city proper.",
                            "llm.model": "gpt-4o",
                        }),
        ]
        tracer = self.HallucinationTracer(min_confidence=0.5)
        findings = tracer.analyze(spans)
        assert len(findings) == 0

    def test_no_findings_without_retrieval(self):
        spans = [
            _make_span("llm-response", "LLM_CALL", span_id="0001", attributes={
                "llm.completion": "Paris is the capital of France.",
                "llm.model": "gpt-4o",
            }),
        ]
        tracer = self.HallucinationTracer()
        findings = tracer.analyze(spans)
        assert len(findings) == 0
