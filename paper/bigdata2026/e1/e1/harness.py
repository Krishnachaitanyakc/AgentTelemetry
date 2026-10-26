"""Recording transport, ground-truth log, span export and the shared model call."""

from __future__ import annotations

import contextlib
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import anthropic
import httpx2
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from e1.domain import EFFORT, MAX_TOKENS, MODEL

# claude-opus-5-5 list prices, USD per million tokens.
PRICE_INPUT = 4.00
PRICE_OUTPUT = 20.00
PRICE_CACHE_READ = 0.20
PRICE_CACHE_WRITE = 5.00


class ReplayMismatch(RuntimeError):
    pass


def _canonical(body: bytes) -> str:
    return json.dumps(json.loads(body), sort_keys=True, separators=(",", ":"))


class RecordReplayTransport(httpx2.BaseTransport):
    """Records successful Anthropic API exchanges, or replays them in order.

    Instrumentation libraries wrap the SDK above this layer, so in replay they
    observe ordinary SDK calls while the agent's execution stays identical.
    """

    def __init__(self, mode: str):
        assert mode in ("record", "replay")
        self.mode = mode
        self.inner = httpx2.HTTPTransport() if mode == "record" else None
        self.entries: list[dict] = []
        self.cursor = 0

    def load(self, path: Path) -> None:
        self.entries = [json.loads(line) for line in path.read_text().splitlines() if line]
        self.cursor = 0

    def reset(self) -> None:
        self.entries, self.cursor = [], 0

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        body = request.read()
        key = hashlib.sha256(f"{request.method} {request.url.path} ".encode()
                             + _canonical(body).encode()).hexdigest()
        if self.mode == "record":
            response = self.inner.handle_request(request)
            content = response.read()
            if response.status_code == 200:
                self.entries.append({
                    "key": key, "path": request.url.path, "status": 200,
                    "content_type": response.headers.get("content-type", "application/json"),
                    "request_id": response.headers.get("request-id", ""),
                    "body": content.decode(),
                })
            headers = {"content-type": response.headers.get("content-type", "application/json")}
            for name in ("request-id", "retry-after", "x-should-retry"):
                if name in response.headers:
                    headers[name] = response.headers[name]
            return httpx2.Response(response.status_code, headers=headers,
                                   content=content, request=request)
        if self.cursor >= len(self.entries):
            raise ReplayMismatch(f"request {self.cursor} was never recorded")
        entry = self.entries[self.cursor]
        if entry["key"] != key:
            raise ReplayMismatch(f"request {self.cursor} differs from the recording")
        self.cursor += 1
        return httpx2.Response(200, headers={"content-type": entry["content_type"],
                                             "request-id": entry["request_id"]},
                               content=entry["body"].encode(), request=request)


class JsonlSpanExporter(SpanExporter):
    """Writes each finished span as one JSON line to the current run's file."""

    def __init__(self) -> None:
        self._fh = None

    def set_output(self, path: Path | None) -> None:
        if self._fh:
            self._fh.close()
        self._fh = path.open("w") if path else None

    def export(self, spans) -> SpanExportResult:
        if self._fh is None:
            return SpanExportResult.SUCCESS
        for s in spans:
            record = {
                "trace_id": f"{s.context.trace_id:032x}",
                "span_id": f"{s.context.span_id:016x}",
                "parent_span_id": f"{s.parent.span_id:016x}" if s.parent else None,
                "name": s.name,
                "kind": s.kind.name,
                "start_ns": s.start_time,
                "end_ns": s.end_time,
                "status": s.status.status_code.name,
                "status_description": s.status.description,
                "scope": s.instrumentation_scope.name if s.instrumentation_scope else None,
                "scope_version": s.instrumentation_scope.version if s.instrumentation_scope else None,
                "attributes": {k: (list(v) if isinstance(v, tuple) else v)
                               for k, v in (s.attributes or {}).items()},
                "events": [{"name": e.name, "ts": e.timestamp,
                            "attributes": {k: (list(v) if isinstance(v, tuple) else v)
                                           for k, v in (e.attributes or {}).items()}}
                           for e in s.events],
            }
            self._fh.write(json.dumps(record, default=str) + "\n")
        self._fh.flush()
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        self.set_output(None)


@dataclass
class Event:
    seq: int
    kind: str
    name: str
    agent: str
    parent_seq: int | None
    start_ns: int = 0
    end_ns: int = 0
    attrs: dict[str, Any] = field(default_factory=dict)


class RunContext:
    """Per-run state: model client, ground-truth log and optional reference spans."""

    def __init__(self, client: anthropic.Anthropic, ref_tracer=None):
        self.client = client
        self.ref_tracer = ref_tracer
        self.events: list[Event] = []
        self._stack: list[Event] = []
        self.usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "calls": 0}
        self.stop_reasons: list[str] = []

    @contextlib.contextmanager
    def step(self, kind: str, name: str, agent: str, **attrs) -> Iterator[Event]:
        parent = self._stack[-1].seq if self._stack else None
        ev = Event(len(self.events), kind, name, agent, parent, attrs=dict(attrs))
        self.events.append(ev)
        self._stack.append(ev)
        span_cm = contextlib.nullcontext()
        if self.ref_tracer is not None:
            from agenttelemetry import start_agent_span
            span_cm = start_agent_span(name, kind, tracer=self.ref_tracer,
                                       attributes={"agent.name": agent})
        ev.start_ns = time.time_ns()
        try:
            with span_cm as span:
                yield ev
                if span is not None:
                    _apply_reference_attributes(span, ev)
        finally:
            ev.end_ns = time.time_ns()
            self._stack.pop()

    def call_model(self, *, agent: str, system: str, messages: list, tools: list | None = None):
        with self.step("LLM_CALL", "model_call", agent) as ev:
            kwargs: dict[str, Any] = dict(
                model=MODEL, max_tokens=MAX_TOKENS, system=system, messages=messages,
                output_config={"effort": EFFORT}, cache_control={"type": "ephemeral"},
            )
            if tools:
                kwargs["tools"] = tools
            response = self.client.messages.create(**kwargs)
            u = response.usage
            ev.attrs.update({
                "model": MODEL,
                "input_tokens": u.input_tokens,
                "output_tokens": u.output_tokens,
                "cache_read_input_tokens": u.cache_read_input_tokens or 0,
                "cache_creation_input_tokens": u.cache_creation_input_tokens or 0,
                "stop_reason": response.stop_reason,
                "tool_use_ids": [b.id for b in response.content if b.type == "tool_use"],
            })
            self.usage["input"] += u.input_tokens
            self.usage["output"] += u.output_tokens
            self.usage["cache_read"] += u.cache_read_input_tokens or 0
            self.usage["cache_write"] += u.cache_creation_input_tokens or 0
            self.usage["calls"] += 1
            self.stop_reasons.append(response.stop_reason)
            if response.stop_reason == "refusal":
                raise RefusalStop(getattr(response, "stop_details", None))
            return response

    def cost_usd(self) -> float:
        u = self.usage
        return (u["input"] * PRICE_INPUT + u["output"] * PRICE_OUTPUT
                + u["cache_read"] * PRICE_CACHE_READ + u["cache_write"] * PRICE_CACHE_WRITE) / 1e6

    def ground_truth(self) -> list[dict]:
        return [ev.__dict__ for ev in self.events]


class RefusalStop(RuntimeError):
    pass


def _apply_reference_attributes(span, ev: Event) -> None:
    """Map a ground-truth event onto AgentTelemetry's semantic attributes."""
    a = ev.attrs
    if ev.kind == "LLM_CALL":
        span.set_attribute("llm.model", a.get("model", ""))
        span.set_attribute("llm.provider", "anthropic")
        span.set_attribute("llm.input_tokens", a.get("input_tokens", 0))
        span.set_attribute("llm.output_tokens", a.get("output_tokens", 0))
        span.set_attribute("llm.total_tokens", a.get("input_tokens", 0) + a.get("output_tokens", 0))
    elif ev.kind == "TOOL_CALL":
        span.set_attribute("tool.name", a.get("tool_name", ev.name))
        span.set_attribute("tool.status", "error" if a.get("error") else "ok")
        span.set_attribute("tool.call_id", a.get("tool_call_id", ""))
        if a.get("error"):
            from opentelemetry.trace import StatusCode
            span.set_status(StatusCode.ERROR, a.get("error_message", "tool error"))
    elif ev.kind == "RETRIEVAL":
        span.set_attribute("retrieval.source", a.get("source", "policy_kb"))
        span.set_attribute("retrieval.doc_count", a.get("doc_count", 0))
    elif ev.kind == "MEMORY":
        span.set_attribute("memory.operation", a.get("operation", ""))
        span.set_attribute("memory.key", a.get("key", ""))
    elif ev.kind == "GUARD_RAIL":
        span.set_attribute("guardrail.name", a.get("guardrail_name", ev.name))
        span.set_attribute("guardrail.result", a.get("result", ""))
    elif ev.kind == "DELEGATION":
        span.set_attribute("delegation.source_agent", a.get("source_agent", ""))
        span.set_attribute("delegation.target_agent", a.get("target_agent", ""))
    elif ev.kind == "PLANNING":
        span.set_attribute("planning.step_count", a.get("step_count", 0))
    elif ev.kind == "AGENT":
        span.set_attribute("agent.role", a.get("role", ""))


def text_of(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text").strip()


def tool_uses(response) -> list:
    return [b for b in response.content if b.type == "tool_use"]


def count_plan_steps(plan_text: str) -> int:
    try:
        start, end = plan_text.index("{"), plan_text.rindex("}") + 1
        return len(json.loads(plan_text[start:end]).get("steps", []))
    except (ValueError, json.JSONDecodeError, AttributeError):
        return 0
