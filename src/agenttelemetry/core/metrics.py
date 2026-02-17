"""Metrics collection for agent telemetry.

Provides counters, histograms, and gauges for tracking agent behavior
at an aggregate level (complementing per-span trace data).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MetricType(Enum):
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"


@dataclass
class MetricPoint:
    name: str
    metric_type: MetricType
    value: float
    timestamp_ns: int
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "timestamp_ns": self.timestamp_ns,
            "labels": self.labels,
        }


class AgentMetrics:
    """Thread-safe metrics collector for agent telemetry.

    Pre-defined metrics::

        agent.task.count           — Tasks executed (counter)
        agent.llm.call.count       — LLM calls made (counter)
        agent.tool.call.count      — Tool calls made (counter)
        agent.error.count          — Errors encountered (counter)
        agent.llm.tokens.input     — Input tokens used (counter)
        agent.llm.tokens.output    — Output tokens used (counter)
        agent.cost.total_usd       — Total cost in USD (counter)
        agent.task.duration_ms     — Task duration histogram
        agent.llm.latency_ms       — LLM latency histogram
        agent.tool.latency_ms      — Tool latency histogram
    """

    def __init__(self, agent_name: str = ""):
        self._agent_name = agent_name
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._gauges: Dict[str, float] = {}
        self._points: List[MetricPoint] = []

    def increment(self, name: str, value: float = 1.0, **labels: str) -> None:
        """Increment a counter."""
        with self._lock:
            key = self._key(name, labels)
            self._counters[key] = self._counters.get(key, 0.0) + value
            self._points.append(
                MetricPoint(
                    name=name,
                    metric_type=MetricType.COUNTER,
                    value=self._counters[key],
                    timestamp_ns=time.time_ns(),
                    labels={"agent.name": self._agent_name, **labels},
                )
            )

    def record(self, name: str, value: float, **labels: str) -> None:
        """Record a value to a histogram."""
        with self._lock:
            key = self._key(name, labels)
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            self._points.append(
                MetricPoint(
                    name=name,
                    metric_type=MetricType.HISTOGRAM,
                    value=value,
                    timestamp_ns=time.time_ns(),
                    labels={"agent.name": self._agent_name, **labels},
                )
            )

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        """Set a gauge value."""
        with self._lock:
            key = self._key(name, labels)
            self._gauges[key] = value
            self._points.append(
                MetricPoint(
                    name=name,
                    metric_type=MetricType.GAUGE,
                    value=value,
                    timestamp_ns=time.time_ns(),
                    labels={"agent.name": self._agent_name, **labels},
                )
            )

    def get_counter(self, name: str, **labels: str) -> float:
        key = self._key(name, labels)
        return self._counters.get(key, 0.0)

    def get_histogram(self, name: str, **labels: str) -> List[float]:
        key = self._key(name, labels)
        return list(self._histograms.get(key, []))

    def get_gauge(self, name: str, **labels: str) -> Optional[float]:
        key = self._key(name, labels)
        return self._gauges.get(key)

    def get_points(self) -> List[MetricPoint]:
        with self._lock:
            return list(self._points)

    def summary(self) -> Dict[str, Any]:
        """Return a summary of all metrics."""
        with self._lock:
            result: Dict[str, Any] = {"counters": dict(self._counters)}
            hist_summary = {}
            for key, values in self._histograms.items():
                if values:
                    sorted_v = sorted(values)
                    hist_summary[key] = {
                        "count": len(values),
                        "min": sorted_v[0],
                        "max": sorted_v[-1],
                        "avg": sum(values) / len(values),
                        "p50": sorted_v[len(sorted_v) // 2],
                        "p95": sorted_v[int(len(sorted_v) * 0.95)],
                        "p99": sorted_v[int(len(sorted_v) * 0.99)],
                    }
            result["histograms"] = hist_summary
            result["gauges"] = dict(self._gauges)
            return result

    @staticmethod
    def _key(name: str, labels: Dict[str, str]) -> str:
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
