"""Comprehensive tests for AgentMetrics."""

import threading
import time

import pytest

from agenttelemetry.core.metrics import AgentMetrics, MetricPoint, MetricType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def metrics():
    """Return a fresh AgentMetrics instance."""
    return AgentMetrics(agent_name="test-agent")


@pytest.fixture
def metrics_no_name():
    """AgentMetrics with empty agent name."""
    return AgentMetrics()


# ===================================================================
# MetricPoint tests
# ===================================================================


class TestMetricPoint:
    """Tests for the MetricPoint dataclass."""

    def test_to_dict(self):
        mp = MetricPoint(
            name="agent.task.count",
            metric_type=MetricType.COUNTER,
            value=5.0,
            timestamp_ns=1000,
            labels={"agent.name": "a"},
        )
        d = mp.to_dict()
        assert d["name"] == "agent.task.count"
        assert d["type"] == "counter"
        assert d["value"] == 5.0
        assert d["timestamp_ns"] == 1000
        assert d["labels"] == {"agent.name": "a"}

    def test_to_dict_histogram_type(self):
        mp = MetricPoint(
            name="latency",
            metric_type=MetricType.HISTOGRAM,
            value=42.0,
            timestamp_ns=2000,
        )
        assert mp.to_dict()["type"] == "histogram"

    def test_to_dict_gauge_type(self):
        mp = MetricPoint(
            name="active",
            metric_type=MetricType.GAUGE,
            value=3.0,
            timestamp_ns=3000,
        )
        assert mp.to_dict()["type"] == "gauge"

    def test_default_empty_labels(self):
        mp = MetricPoint(
            name="x", metric_type=MetricType.COUNTER, value=1.0, timestamp_ns=0
        )
        assert mp.labels == {}


# ===================================================================
# Counter tests
# ===================================================================


class TestCounters:
    """Tests for counter operations."""

    def test_increment_default_value(self, metrics):
        metrics.increment("agent.task.count")
        assert metrics.get_counter("agent.task.count") == 1.0

    def test_increment_custom_value(self, metrics):
        metrics.increment("agent.llm.tokens.input", value=500)
        assert metrics.get_counter("agent.llm.tokens.input") == 500.0

    def test_increment_accumulates(self, metrics):
        metrics.increment("agent.task.count")
        metrics.increment("agent.task.count")
        metrics.increment("agent.task.count")
        assert metrics.get_counter("agent.task.count") == 3.0

    def test_increment_accumulates_custom_values(self, metrics):
        metrics.increment("agent.cost.total_usd", value=0.01)
        metrics.increment("agent.cost.total_usd", value=0.02)
        metrics.increment("agent.cost.total_usd", value=0.03)
        assert metrics.get_counter("agent.cost.total_usd") == pytest.approx(0.06)

    def test_counter_starts_at_zero(self, metrics):
        assert metrics.get_counter("nonexistent") == 0.0

    def test_counter_with_labels(self, metrics):
        metrics.increment("agent.llm.call.count", model="gpt-4o")
        metrics.increment("agent.llm.call.count", model="claude-3-opus")
        metrics.increment("agent.llm.call.count", model="gpt-4o")
        assert metrics.get_counter("agent.llm.call.count", model="gpt-4o") == 2.0
        assert metrics.get_counter("agent.llm.call.count", model="claude-3-opus") == 1.0

    def test_counter_different_labels_are_independent(self, metrics):
        metrics.increment("errors", severity="warn")
        metrics.increment("errors", severity="critical")
        assert metrics.get_counter("errors", severity="warn") == 1.0
        assert metrics.get_counter("errors", severity="critical") == 1.0

    def test_counter_no_label_vs_with_label(self, metrics):
        metrics.increment("agent.task.count")
        metrics.increment("agent.task.count", env="prod")
        assert metrics.get_counter("agent.task.count") == 1.0
        assert metrics.get_counter("agent.task.count", env="prod") == 1.0

    def test_increment_records_metric_point(self, metrics):
        metrics.increment("agent.task.count")
        points = metrics.get_points()
        assert len(points) == 1
        assert points[0].name == "agent.task.count"
        assert points[0].metric_type is MetricType.COUNTER
        assert points[0].value == 1.0
        assert points[0].labels["agent.name"] == "test-agent"
        assert points[0].timestamp_ns > 0


# ===================================================================
# Histogram tests
# ===================================================================


class TestHistograms:
    """Tests for histogram operations."""

    def test_record_single_value(self, metrics):
        metrics.record("agent.llm.latency_ms", 150.0)
        values = metrics.get_histogram("agent.llm.latency_ms")
        assert values == [150.0]

    def test_record_multiple_values(self, metrics):
        metrics.record("agent.llm.latency_ms", 100.0)
        metrics.record("agent.llm.latency_ms", 200.0)
        metrics.record("agent.llm.latency_ms", 150.0)
        values = metrics.get_histogram("agent.llm.latency_ms")
        assert values == [100.0, 200.0, 150.0]

    def test_empty_histogram(self, metrics):
        values = metrics.get_histogram("nonexistent")
        assert values == []

    def test_histogram_returns_copy(self, metrics):
        metrics.record("h", 1.0)
        values = metrics.get_histogram("h")
        values.append(999.0)
        assert metrics.get_histogram("h") == [1.0]

    def test_histogram_with_labels(self, metrics):
        metrics.record("latency", 100.0, model="gpt-4o")
        metrics.record("latency", 200.0, model="claude")
        assert metrics.get_histogram("latency", model="gpt-4o") == [100.0]
        assert metrics.get_histogram("latency", model="claude") == [200.0]

    def test_record_creates_metric_point(self, metrics):
        metrics.record("agent.task.duration_ms", 42.5)
        points = metrics.get_points()
        assert len(points) == 1
        assert points[0].metric_type is MetricType.HISTOGRAM
        assert points[0].value == 42.5


# ===================================================================
# Gauge tests
# ===================================================================


class TestGauges:
    """Tests for gauge operations."""

    def test_set_gauge(self, metrics):
        metrics.set_gauge("active_agents", 3.0)
        assert metrics.get_gauge("active_agents") == 3.0

    def test_gauge_overwrite(self, metrics):
        metrics.set_gauge("active_agents", 3.0)
        metrics.set_gauge("active_agents", 5.0)
        assert metrics.get_gauge("active_agents") == 5.0

    def test_gauge_returns_none_when_missing(self, metrics):
        assert metrics.get_gauge("nonexistent") is None

    def test_gauge_with_labels(self, metrics):
        metrics.set_gauge("queue_depth", 10.0, priority="high")
        metrics.set_gauge("queue_depth", 50.0, priority="low")
        assert metrics.get_gauge("queue_depth", priority="high") == 10.0
        assert metrics.get_gauge("queue_depth", priority="low") == 50.0

    def test_gauge_creates_metric_point(self, metrics):
        metrics.set_gauge("g", 7.0)
        points = metrics.get_points()
        assert len(points) == 1
        assert points[0].metric_type is MetricType.GAUGE
        assert points[0].value == 7.0

    def test_gauge_can_decrease(self, metrics):
        metrics.set_gauge("memory_mb", 100.0)
        metrics.set_gauge("memory_mb", 50.0)
        assert metrics.get_gauge("memory_mb") == 50.0


# ===================================================================
# Summary statistics tests
# ===================================================================


class TestSummary:
    """Tests for the summary() method and histogram statistics."""

    def test_summary_empty(self, metrics):
        s = metrics.summary()
        assert s["counters"] == {}
        assert s["histograms"] == {}
        assert s["gauges"] == {}

    def test_summary_counters(self, metrics):
        metrics.increment("a", value=10)
        metrics.increment("b", value=20)
        s = metrics.summary()
        assert s["counters"]["a"] == 10.0
        assert s["counters"]["b"] == 20.0

    def test_summary_gauges(self, metrics):
        metrics.set_gauge("g1", 3.14)
        s = metrics.summary()
        assert s["gauges"]["g1"] == 3.14

    def test_summary_histogram_stats_single_value(self, metrics):
        metrics.record("h", 42.0)
        s = metrics.summary()
        stats = s["histograms"]["h"]
        assert stats["count"] == 1
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0
        assert stats["avg"] == 42.0
        assert stats["p50"] == 42.0
        assert stats["p95"] == 42.0
        assert stats["p99"] == 42.0

    def test_summary_histogram_stats_multiple_values(self, metrics):
        # Insert 100 values: 1..100
        for i in range(1, 101):
            metrics.record("latency", float(i))
        s = metrics.summary()
        stats = s["histograms"]["latency"]
        assert stats["count"] == 100
        assert stats["min"] == 1.0
        assert stats["max"] == 100.0
        assert stats["avg"] == pytest.approx(50.5)
        assert stats["p50"] == 51.0  # index 50 of sorted [1..100] (0-indexed)
        assert stats["p95"] == 96.0  # index 95
        assert stats["p99"] == 100.0  # index 99

    def test_summary_histogram_with_labels(self, metrics):
        metrics.record("h", 10.0, region="us")
        metrics.record("h", 20.0, region="us")
        s = metrics.summary()
        key = "h{region=us}"
        assert key in s["histograms"]
        assert s["histograms"][key]["count"] == 2
        assert s["histograms"][key]["avg"] == 15.0

    def test_summary_does_not_include_empty_histograms(self, metrics):
        """No histogram key should appear if no values were recorded for it."""
        s = metrics.summary()
        assert "histograms" in s
        assert s["histograms"] == {}


# ===================================================================
# Thread safety tests
# ===================================================================


class TestThreadSafety:
    """Tests that verify thread-safe behavior of AgentMetrics."""

    def test_concurrent_counter_increments(self):
        metrics = AgentMetrics(agent_name="thread-test")
        num_threads = 10
        increments_per_thread = 1000
        barrier = threading.Barrier(num_threads)

        def worker():
            barrier.wait()
            for _ in range(increments_per_thread):
                metrics.increment("concurrent.counter")

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * increments_per_thread
        assert metrics.get_counter("concurrent.counter") == float(expected)

    def test_concurrent_histogram_records(self):
        metrics = AgentMetrics(agent_name="thread-test")
        num_threads = 10
        records_per_thread = 100
        barrier = threading.Barrier(num_threads)

        def worker(thread_id):
            barrier.wait()
            for i in range(records_per_thread):
                metrics.record("concurrent.hist", float(thread_id * 1000 + i))

        threads = [
            threading.Thread(target=worker, args=(tid,))
            for tid in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        values = metrics.get_histogram("concurrent.hist")
        assert len(values) == num_threads * records_per_thread

    def test_concurrent_gauge_sets(self):
        metrics = AgentMetrics(agent_name="thread-test")
        num_threads = 10
        sets_per_thread = 100
        barrier = threading.Barrier(num_threads)

        def worker(tid):
            barrier.wait()
            for i in range(sets_per_thread):
                metrics.set_gauge("concurrent.gauge", float(tid * 100 + i))

        threads = [
            threading.Thread(target=worker, args=(tid,))
            for tid in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Gauge should hold some valid float value (we cannot predict which
        # thread wrote last, but it must not have crashed)
        val = metrics.get_gauge("concurrent.gauge")
        assert val is not None
        assert isinstance(val, float)

    def test_concurrent_mixed_operations(self):
        metrics = AgentMetrics(agent_name="mixed")
        barrier = threading.Barrier(3)

        def counter_worker():
            barrier.wait()
            for _ in range(500):
                metrics.increment("mixed.counter")

        def histogram_worker():
            barrier.wait()
            for i in range(500):
                metrics.record("mixed.hist", float(i))

        def gauge_worker():
            barrier.wait()
            for i in range(500):
                metrics.set_gauge("mixed.gauge", float(i))

        threads = [
            threading.Thread(target=counter_worker),
            threading.Thread(target=histogram_worker),
            threading.Thread(target=gauge_worker),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert metrics.get_counter("mixed.counter") == 500.0
        assert len(metrics.get_histogram("mixed.hist")) == 500
        assert metrics.get_gauge("mixed.gauge") is not None


# ===================================================================
# get_points tests
# ===================================================================


class TestGetPoints:
    """Tests for the get_points() method."""

    def test_empty_points(self, metrics):
        assert metrics.get_points() == []

    def test_points_from_all_operations(self, metrics):
        metrics.increment("c")
        metrics.record("h", 1.0)
        metrics.set_gauge("g", 2.0)
        points = metrics.get_points()
        assert len(points) == 3
        types = [p.metric_type for p in points]
        assert MetricType.COUNTER in types
        assert MetricType.HISTOGRAM in types
        assert MetricType.GAUGE in types

    def test_points_returns_copy(self, metrics):
        metrics.increment("c")
        pts = metrics.get_points()
        pts.clear()
        assert len(metrics.get_points()) == 1

    def test_points_include_agent_name_label(self, metrics):
        metrics.increment("c")
        points = metrics.get_points()
        assert points[0].labels["agent.name"] == "test-agent"

    def test_points_include_custom_labels(self, metrics):
        metrics.increment("c", env="prod", region="us-west")
        points = metrics.get_points()
        assert points[0].labels["env"] == "prod"
        assert points[0].labels["region"] == "us-west"


# ===================================================================
# Key generation tests
# ===================================================================


class TestKeyGeneration:
    """Tests for the internal _key static method."""

    def test_key_no_labels(self):
        assert AgentMetrics._key("metric", {}) == "metric"

    def test_key_single_label(self):
        assert AgentMetrics._key("metric", {"a": "1"}) == "metric{a=1}"

    def test_key_multiple_labels_sorted(self):
        key = AgentMetrics._key("metric", {"z": "2", "a": "1"})
        assert key == "metric{a=1,z=2}"

    def test_key_deterministic(self):
        labels = {"b": "2", "a": "1", "c": "3"}
        k1 = AgentMetrics._key("m", labels)
        k2 = AgentMetrics._key("m", labels)
        assert k1 == k2


# ===================================================================
# Agent name handling
# ===================================================================


class TestAgentNameInMetrics:
    """Test that agent_name flows correctly into metric labels."""

    def test_empty_agent_name(self, metrics_no_name):
        metrics_no_name.increment("c")
        points = metrics_no_name.get_points()
        assert points[0].labels["agent.name"] == ""

    def test_agent_name_in_counter(self, metrics):
        metrics.increment("c")
        points = metrics.get_points()
        assert points[0].labels["agent.name"] == "test-agent"

    def test_agent_name_in_histogram(self, metrics):
        metrics.record("h", 1.0)
        points = metrics.get_points()
        assert points[0].labels["agent.name"] == "test-agent"

    def test_agent_name_in_gauge(self, metrics):
        metrics.set_gauge("g", 1.0)
        points = metrics.get_points()
        assert points[0].labels["agent.name"] == "test-agent"
