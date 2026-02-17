"""LlamaIndex instrumentor for AgentTelemetry.

Automatically captures telemetry from LlamaIndex by monkey-patching
core classes: query engines, retrievers, LLM interfaces, and agent
step executors.

Span mapping:

    BaseQueryEngine.query()              -> TASK span
    BaseQueryEngine.aquery()             -> TASK span (async)
    BaseRetriever.retrieve()             -> RETRIEVAL span
    BaseRetriever.aretrieve()            -> RETRIEVAL span (async)
    LLM.complete() / LLM.chat()         -> LLM_CALL span
    LLM.acomplete() / LLM.achat()       -> LLM_CALL span (async)
    AgentRunner.chat() / .query()        -> TASK span
    Agent step execution                 -> REASONING span

Usage::

    from agenttelemetry.instrumentors.llamaindex import LlamaIndexInstrumentor

    instrumentor = LlamaIndexInstrumentor(capture_content=True)
    instrumentor.instrument()

    # ... use LlamaIndex normally — telemetry is captured automatically ...

    instrumentor.uninstrument()
"""

from __future__ import annotations

import functools
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from agenttelemetry.core.events import EventType
from agenttelemetry.core.trace import (
    ATTR_AGENT_TASK,
    ATTR_LLM_COMPLETION,
    ATTR_LLM_COST_USD,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_LATENCY_MS,
    ATTR_LLM_MODEL,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_PROMPT,
    ATTR_LLM_PROVIDER,
    ATTR_LLM_TEMPERATURE,
    ATTR_LLM_TOTAL_TOKENS,
    ATTR_TOOL_ERROR,
    ATTR_TOOL_INPUT,
    ATTR_TOOL_LATENCY_MS,
    ATTR_TOOL_NAME,
    ATTR_TOOL_OUTPUT,
    ATTR_TOOL_SUCCESS,
    AgentSpanKind,
    SpanStatus,
    estimate_cost,
)
from agenttelemetry.instrumentors.base import BaseInstrumentor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom attribute keys for LlamaIndex-specific metadata
# ---------------------------------------------------------------------------
ATTR_LI_QUERY = "llamaindex.query"
ATTR_LI_QUERY_ENGINE_TYPE = "llamaindex.query_engine.type"
ATTR_LI_RETRIEVER_TYPE = "llamaindex.retriever.type"
ATTR_LI_RETRIEVAL_QUERY = "llamaindex.retrieval.query"
ATTR_LI_RETRIEVAL_TOP_K = "llamaindex.retrieval.top_k"
ATTR_LI_RETRIEVAL_RESULTS_COUNT = "llamaindex.retrieval.results_count"
ATTR_LI_NODE_SCORE = "llamaindex.node.score"
ATTR_LI_NODE_SCORES = "llamaindex.node.scores"
ATTR_LI_NODE_IDS = "llamaindex.node.ids"
ATTR_LI_RESPONSE_TYPE = "llamaindex.response.type"
ATTR_LI_AGENT_TYPE = "llamaindex.agent.type"
ATTR_LI_AGENT_STEP = "llamaindex.agent.step"
ATTR_LI_AGENT_TOTAL_STEPS = "llamaindex.agent.total_steps"
ATTR_LI_AGENT_TOOLS = "llamaindex.agent.tools"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_str(obj: Any, max_len: int = 4096) -> str:
    """Convert an object to a truncated string, swallowing exceptions."""
    try:
        text = str(obj)
        if len(text) > max_len:
            return text[:max_len] + "...[truncated]"
        return text
    except Exception:
        return "<unserializable>"


def _safe_json(obj: Any, max_len: int = 4096) -> str:
    """Serialize to JSON with truncation, falling back to str()."""
    try:
        text = json.dumps(obj, default=str, ensure_ascii=False)
    except (TypeError, ValueError, OverflowError):
        text = str(obj)
    if len(text) > max_len:
        return text[:max_len] + "...[truncated]"
    return text


def _extract_query_str(query_bundle: Any) -> str:
    """Extract the query string from a LlamaIndex QueryBundle or raw string."""
    if isinstance(query_bundle, str):
        return query_bundle
    query_str = getattr(query_bundle, "query_str", None)
    if query_str:
        return str(query_str)
    return _safe_str(query_bundle, max_len=1024)


def _extract_node_info(nodes: Any) -> Dict[str, Any]:
    """Extract scores and IDs from a list of NodeWithScore objects.

    Returns a dict with 'scores', 'ids', and 'count' keys.
    """
    info: Dict[str, Any] = {"scores": [], "ids": [], "count": 0}
    if nodes is None:
        return info
    if not isinstance(nodes, (list, tuple)):
        return info

    for node_with_score in nodes:
        score = getattr(node_with_score, "score", None)
        if score is not None:
            try:
                info["scores"].append(float(score))
            except (TypeError, ValueError):
                pass

        # Extract node ID
        node = getattr(node_with_score, "node", node_with_score)
        node_id = getattr(node, "node_id", None) or getattr(node, "id_", None)
        if node_id:
            info["ids"].append(str(node_id))

    info["count"] = len(nodes)
    return info


def _extract_llm_model_name(llm_instance: Any) -> str:
    """Extract the model name from a LlamaIndex LLM instance."""
    for attr in ("model", "model_name", "model_id"):
        val = getattr(llm_instance, attr, None)
        if val and isinstance(val, str):
            return val
    return type(llm_instance).__name__


def _extract_llm_provider(llm_instance: Any) -> str:
    """Infer the LLM provider from a LlamaIndex LLM instance class name."""
    class_name = type(llm_instance).__name__.lower()
    if "openai" in class_name:
        return "openai"
    if "anthropic" in class_name or "claude" in class_name:
        return "anthropic"
    if "gemini" in class_name or "google" in class_name:
        return "google"
    if "cohere" in class_name:
        return "cohere"
    if "huggingface" in class_name or "hf" in class_name:
        return "huggingface"
    if "bedrock" in class_name:
        return "aws_bedrock"
    if "ollama" in class_name:
        return "ollama"
    if "azure" in class_name:
        return "azure_openai"
    return "unknown"


def _extract_token_usage_from_response(response: Any) -> Tuple[int, int]:
    """Extract token counts from a LlamaIndex LLM completion/chat response.

    LlamaIndex wraps raw LLM responses in CompletionResponse or
    ChatResponse objects that may carry ``additional_kwargs`` or
    ``raw`` response data with token usage.

    Returns (input_tokens, output_tokens).
    """
    input_tokens = 0
    output_tokens = 0

    # Check additional_kwargs
    additional = getattr(response, "additional_kwargs", None) or {}
    if isinstance(additional, dict):
        usage = additional.get("usage", {})
        if isinstance(usage, dict):
            input_tokens = usage.get("prompt_tokens", 0) or usage.get(
                "input_tokens", 0
            )
            output_tokens = usage.get("completion_tokens", 0) or usage.get(
                "output_tokens", 0
            )

    # Check raw response
    if input_tokens == 0 and output_tokens == 0:
        raw = getattr(response, "raw", None)
        if raw is not None:
            usage = getattr(raw, "usage", None)
            if usage is not None:
                if isinstance(usage, dict):
                    input_tokens = usage.get("prompt_tokens", 0) or usage.get(
                        "input_tokens", 0
                    )
                    output_tokens = usage.get(
                        "completion_tokens", 0
                    ) or usage.get("output_tokens", 0)
                else:
                    # Usage may be an object with attributes
                    input_tokens = getattr(usage, "prompt_tokens", 0) or getattr(
                        usage, "input_tokens", 0
                    )
                    output_tokens = getattr(
                        usage, "completion_tokens", 0
                    ) or getattr(usage, "output_tokens", 0)

    return int(input_tokens or 0), int(output_tokens or 0)


def _messages_to_text(messages: Any) -> str:
    """Convert LlamaIndex ChatMessage list to readable text."""
    if not messages:
        return ""
    parts: List[str] = []
    if isinstance(messages, (list, tuple)):
        for msg in messages:
            role = getattr(msg, "role", "unknown")
            content = getattr(msg, "content", str(msg))
            parts.append(f"[{role}] {content}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# LlamaIndexInstrumentor
# ---------------------------------------------------------------------------


class LlamaIndexInstrumentor(BaseInstrumentor):
    """Instruments LlamaIndex to capture execution telemetry.

    Monkey-patches query engines, retrievers, LLM classes, and agent
    runners to automatically record spans and metrics.

    Parameters
    ----------
    tracer : AgentTracer, optional
        Pre-configured tracer instance.  A default one is created if omitted.
    metrics : AgentMetrics, optional
        Pre-configured metrics collector.  A default one is created if omitted.
    capture_content : bool
        When ``True``, queries, retrieved content, prompts, completions,
        and tool I/O are recorded as span attributes.  Defaults to
        ``False`` for privacy.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._originals: Dict[str, Any] = {}

    @property
    def framework_name(self) -> str:  # noqa: D401
        return "llamaindex"

    # ------------------------------------------------------------------
    # instrument / uninstrument
    # ------------------------------------------------------------------

    def instrument(self) -> None:
        """Apply monkey-patches to LlamaIndex classes."""
        if self._instrumented:
            logger.debug("LlamaIndex instrumentor is already active; skipping.")
            return

        try:
            import llama_index.core
        except ImportError as exc:
            raise ImportError(
                "llama-index-core is not installed. "
                "Install it with: pip install llama-index-core"
            ) from exc

        # Record framework version
        li_version = getattr(llama_index.core, "__version__", "unknown")
        self._tracer._framework_version = li_version

        # --- Patch BaseQueryEngine.query / aquery ---
        self._patch_query_engine()

        # --- Patch BaseRetriever.retrieve / aretrieve ---
        self._patch_retriever()

        # --- Patch LLM.complete / chat / acomplete / achat ---
        self._patch_llm()

        # --- Patch Agent classes ---
        self._patch_agent()

        self._instrumented = True
        logger.info(
            "LlamaIndex instrumentor activated (version=%s, capture_content=%s)",
            li_version,
            self._capture_content,
        )

    def _patch_query_engine(self) -> None:
        """Patch BaseQueryEngine.query and .aquery."""
        try:
            from llama_index.core.query_engine import BaseQueryEngine

            # Sync query
            if hasattr(BaseQueryEngine, "query"):
                self._originals["BaseQueryEngine.query"] = BaseQueryEngine.query
                BaseQueryEngine.query = self._wrap_query(BaseQueryEngine.query)

            # Async query
            if hasattr(BaseQueryEngine, "aquery"):
                self._originals["BaseQueryEngine.aquery"] = BaseQueryEngine.aquery
                BaseQueryEngine.aquery = self._wrap_aquery(BaseQueryEngine.aquery)

        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch BaseQueryEngine: %s", exc)

    def _patch_retriever(self) -> None:
        """Patch BaseRetriever.retrieve and .aretrieve."""
        try:
            from llama_index.core.retrievers import BaseRetriever

            # Sync retrieve
            if hasattr(BaseRetriever, "retrieve"):
                self._originals["BaseRetriever.retrieve"] = (
                    BaseRetriever.retrieve
                )
                BaseRetriever.retrieve = self._wrap_retrieve(
                    BaseRetriever.retrieve
                )

            # Async retrieve
            if hasattr(BaseRetriever, "aretrieve"):
                self._originals["BaseRetriever.aretrieve"] = (
                    BaseRetriever.aretrieve
                )
                BaseRetriever.aretrieve = self._wrap_aretrieve(
                    BaseRetriever.aretrieve
                )

        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch BaseRetriever: %s", exc)

    def _patch_llm(self) -> None:
        """Patch LLM base class methods for complete/chat."""
        try:
            from llama_index.core.llms import LLM

            # Sync complete
            if hasattr(LLM, "complete"):
                self._originals["LLM.complete"] = LLM.complete
                LLM.complete = self._wrap_llm_complete(LLM.complete)

            # Sync chat
            if hasattr(LLM, "chat"):
                self._originals["LLM.chat"] = LLM.chat
                LLM.chat = self._wrap_llm_chat(LLM.chat)

            # Async complete
            if hasattr(LLM, "acomplete"):
                self._originals["LLM.acomplete"] = LLM.acomplete
                LLM.acomplete = self._wrap_async_llm_complete(LLM.acomplete)

            # Async chat
            if hasattr(LLM, "achat"):
                self._originals["LLM.achat"] = LLM.achat
                LLM.achat = self._wrap_async_llm_chat(LLM.achat)

        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch LLM: %s", exc)

    def _patch_agent(self) -> None:
        """Patch agent runner and step engine classes."""
        # --- AgentRunner.chat / query ---
        try:
            from llama_index.core.agent import AgentRunner

            if hasattr(AgentRunner, "chat"):
                self._originals["AgentRunner.chat"] = AgentRunner.chat
                AgentRunner.chat = self._wrap_agent_chat(AgentRunner.chat)

            if hasattr(AgentRunner, "query"):
                self._originals["AgentRunner.query"] = AgentRunner.query
                AgentRunner.query = self._wrap_agent_query(AgentRunner.query)

            if hasattr(AgentRunner, "achat"):
                self._originals["AgentRunner.achat"] = AgentRunner.achat
                AgentRunner.achat = self._wrap_async_agent_chat(
                    AgentRunner.achat
                )

        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch AgentRunner: %s", exc)

        # --- Agent step engine ---
        try:
            from llama_index.core.agent.runner import base as agent_base

            if hasattr(agent_base, "BaseAgentRunner"):
                runner_cls = agent_base.BaseAgentRunner
                if hasattr(runner_cls, "_run_step"):
                    self._originals["BaseAgentRunner._run_step"] = (
                        runner_cls._run_step
                    )
                    runner_cls._run_step = self._wrap_agent_step(
                        runner_cls._run_step
                    )
        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch BaseAgentRunner._run_step: %s", exc)

        # --- ReActAgent step (alternative path) ---
        try:
            from llama_index.core.agent.react.step import ReActAgentWorker

            if hasattr(ReActAgentWorker, "run_step"):
                self._originals["ReActAgentWorker.run_step"] = (
                    ReActAgentWorker.run_step
                )
                ReActAgentWorker.run_step = self._wrap_agent_step(
                    ReActAgentWorker.run_step
                )
        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch ReActAgentWorker.run_step: %s", exc)

    def uninstrument(self) -> None:
        """Remove all monkey-patches and restore original methods."""
        if not self._instrumented:
            logger.debug(
                "LlamaIndex instrumentor is not active; nothing to undo."
            )
            return

        try:
            import llama_index.core
        except ImportError:
            self._instrumented = False
            self._originals.clear()
            return

        # Build restore map
        restore_targets: Dict[str, Tuple[Any, str]] = {}

        try:
            from llama_index.core.query_engine import BaseQueryEngine

            restore_targets["BaseQueryEngine.query"] = (
                BaseQueryEngine,
                "query",
            )
            restore_targets["BaseQueryEngine.aquery"] = (
                BaseQueryEngine,
                "aquery",
            )
        except (ImportError, AttributeError):
            pass

        try:
            from llama_index.core.retrievers import BaseRetriever

            restore_targets["BaseRetriever.retrieve"] = (
                BaseRetriever,
                "retrieve",
            )
            restore_targets["BaseRetriever.aretrieve"] = (
                BaseRetriever,
                "aretrieve",
            )
        except (ImportError, AttributeError):
            pass

        try:
            from llama_index.core.llms import LLM

            restore_targets["LLM.complete"] = (LLM, "complete")
            restore_targets["LLM.chat"] = (LLM, "chat")
            restore_targets["LLM.acomplete"] = (LLM, "acomplete")
            restore_targets["LLM.achat"] = (LLM, "achat")
        except (ImportError, AttributeError):
            pass

        try:
            from llama_index.core.agent import AgentRunner

            restore_targets["AgentRunner.chat"] = (AgentRunner, "chat")
            restore_targets["AgentRunner.query"] = (AgentRunner, "query")
            restore_targets["AgentRunner.achat"] = (AgentRunner, "achat")
        except (ImportError, AttributeError):
            pass

        try:
            from llama_index.core.agent.runner import base as agent_base

            if hasattr(agent_base, "BaseAgentRunner"):
                restore_targets["BaseAgentRunner._run_step"] = (
                    agent_base.BaseAgentRunner,
                    "_run_step",
                )
        except (ImportError, AttributeError):
            pass

        try:
            from llama_index.core.agent.react.step import ReActAgentWorker

            restore_targets["ReActAgentWorker.run_step"] = (
                ReActAgentWorker,
                "run_step",
            )
        except (ImportError, AttributeError):
            pass

        for key, (cls, attr_name) in restore_targets.items():
            original = self._originals.get(key)
            if original is not None:
                setattr(cls, attr_name, original)

        self._originals.clear()
        self._instrumented = False
        logger.info(
            "LlamaIndex instrumentor deactivated -- original methods restored."
        )

    # ------------------------------------------------------------------
    # Query engine wrappers
    # ------------------------------------------------------------------

    def _wrap_query(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``BaseQueryEngine.query`` as a TASK span."""
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_query(engine_self: Any, *args: Any, **kwargs: Any) -> Any:
            engine_type = type(engine_self).__name__

            # Extract query string
            query_str = ""
            if args:
                query_str = _extract_query_str(args[0])
            elif "str_or_query_bundle" in kwargs:
                query_str = _extract_query_str(kwargs["str_or_query_bundle"])

            task_name = f"llamaindex.query.{engine_type}"

            with instrumentor._tracer.start_task(task_name=task_name) as span:
                span.set_attribute(ATTR_LI_QUERY_ENGINE_TYPE, engine_type)
                span.set_attribute(ATTR_AGENT_TASK, task_name)

                if instrumentor._capture_content and query_str:
                    span.set_attribute(ATTR_LI_QUERY, _safe_str(query_str, 2048))

                span.add_event(
                    "query_start",
                    EventType.AGENT_START,
                    engine_type=engine_type,
                )

                instrumentor._metrics.increment(
                    "agent.task.count", framework="llamaindex"
                )
                start_ns = time.time_ns()

                try:
                    result = original_fn(engine_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "query_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                # Extract response info
                response_type = type(result).__name__
                span.set_attribute(ATTR_LI_RESPONSE_TYPE, response_type)

                if instrumentor._capture_content and result is not None:
                    response_text = getattr(result, "response", None) or str(
                        result
                    )
                    span.set_attribute(
                        "llamaindex.response", _safe_str(response_text)
                    )

                # Extract source nodes if present
                source_nodes = getattr(result, "source_nodes", None)
                if source_nodes:
                    node_info = _extract_node_info(source_nodes)
                    span.set_attribute(
                        ATTR_LI_RETRIEVAL_RESULTS_COUNT, node_info["count"]
                    )
                    if node_info["scores"]:
                        span.set_attribute(
                            ATTR_LI_NODE_SCORES, node_info["scores"]
                        )
                    if node_info["ids"]:
                        span.set_attribute(ATTR_LI_NODE_IDS, node_info["ids"])

                span.add_event(
                    "query_end",
                    EventType.AGENT_END,
                    engine_type=engine_type,
                    duration_ms=duration_ms,
                )

                instrumentor._metrics.record(
                    "agent.task.duration_ms",
                    duration_ms,
                    framework="llamaindex",
                )

                return result

        return _patched_query

    def _wrap_aquery(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``BaseQueryEngine.aquery`` as an async TASK span."""
        instrumentor = self

        @functools.wraps(original_fn)
        async def _patched_aquery(
            engine_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            engine_type = type(engine_self).__name__
            query_str = ""
            if args:
                query_str = _extract_query_str(args[0])
            elif "str_or_query_bundle" in kwargs:
                query_str = _extract_query_str(kwargs["str_or_query_bundle"])

            task_name = f"llamaindex.query.{engine_type}"

            with instrumentor._tracer.start_task(task_name=task_name) as span:
                span.set_attribute(ATTR_LI_QUERY_ENGINE_TYPE, engine_type)
                span.set_attribute(ATTR_AGENT_TASK, task_name)

                if instrumentor._capture_content and query_str:
                    span.set_attribute(ATTR_LI_QUERY, _safe_str(query_str, 2048))

                span.add_event(
                    "query_start",
                    EventType.AGENT_START,
                    engine_type=engine_type,
                )

                instrumentor._metrics.increment(
                    "agent.task.count", framework="llamaindex"
                )
                start_ns = time.time_ns()

                try:
                    result = await original_fn(engine_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "query_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                response_type = type(result).__name__
                span.set_attribute(ATTR_LI_RESPONSE_TYPE, response_type)

                if instrumentor._capture_content and result is not None:
                    response_text = getattr(result, "response", None) or str(
                        result
                    )
                    span.set_attribute(
                        "llamaindex.response", _safe_str(response_text)
                    )

                source_nodes = getattr(result, "source_nodes", None)
                if source_nodes:
                    node_info = _extract_node_info(source_nodes)
                    span.set_attribute(
                        ATTR_LI_RETRIEVAL_RESULTS_COUNT, node_info["count"]
                    )
                    if node_info["scores"]:
                        span.set_attribute(
                            ATTR_LI_NODE_SCORES, node_info["scores"]
                        )
                    if node_info["ids"]:
                        span.set_attribute(ATTR_LI_NODE_IDS, node_info["ids"])

                span.add_event(
                    "query_end",
                    EventType.AGENT_END,
                    engine_type=engine_type,
                    duration_ms=duration_ms,
                )

                instrumentor._metrics.record(
                    "agent.task.duration_ms",
                    duration_ms,
                    framework="llamaindex",
                )

                return result

        return _patched_aquery

    # ------------------------------------------------------------------
    # Retriever wrappers
    # ------------------------------------------------------------------

    def _wrap_retrieve(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``BaseRetriever.retrieve`` as a RETRIEVAL span."""
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_retrieve(
            retriever_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            retriever_type = type(retriever_self).__name__

            # Extract query
            query_str = ""
            if args:
                query_str = _extract_query_str(args[0])
            elif "str_or_query_bundle" in kwargs:
                query_str = _extract_query_str(kwargs["str_or_query_bundle"])

            # Try to get top_k / similarity_top_k
            top_k = getattr(retriever_self, "similarity_top_k", None) or getattr(
                retriever_self, "_similarity_top_k", None
            )

            with instrumentor._tracer.start_retrieval(
                name=f"llamaindex.retrieve.{retriever_type}"
            ) as span:
                span.set_attribute(ATTR_LI_RETRIEVER_TYPE, retriever_type)
                span.set_attribute(ATTR_TOOL_NAME, f"llamaindex.{retriever_type}")

                if top_k is not None:
                    span.set_attribute(ATTR_LI_RETRIEVAL_TOP_K, int(top_k))

                if instrumentor._capture_content and query_str:
                    span.set_attribute(
                        ATTR_LI_RETRIEVAL_QUERY, _safe_str(query_str, 2048)
                    )

                span.add_event(
                    "retrieval_start",
                    EventType.TOOL_START,
                    retriever=retriever_type,
                    query=query_str[:256] if instrumentor._capture_content else "<redacted>",
                )

                start_ns = time.time_ns()

                try:
                    result = original_fn(retriever_self, *args, **kwargs)
                except Exception as exc:
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_TOOL_SUCCESS, False)
                    span.set_attribute(ATTR_TOOL_LATENCY_MS, latency_ms)
                    span.add_event(
                        "retrieval_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_TOOL_SUCCESS, True)
                span.set_attribute(ATTR_TOOL_LATENCY_MS, latency_ms)

                # Extract node scores and IDs
                node_info = _extract_node_info(result)
                span.set_attribute(
                    ATTR_LI_RETRIEVAL_RESULTS_COUNT, node_info["count"]
                )
                if node_info["scores"]:
                    span.set_attribute(ATTR_LI_NODE_SCORES, node_info["scores"])
                if node_info["ids"]:
                    span.set_attribute(ATTR_LI_NODE_IDS, node_info["ids"])

                # Capture retrieved text content
                if instrumentor._capture_content and result:
                    retrieved_texts = []
                    for nws in result:
                        node = getattr(nws, "node", nws)
                        text = getattr(node, "text", None) or getattr(
                            node, "get_content", lambda: ""
                        )
                        if callable(text):
                            try:
                                text = text()
                            except Exception:
                                text = ""
                        if text:
                            score = getattr(nws, "score", None)
                            score_str = f" (score={score:.4f})" if score is not None else ""
                            retrieved_texts.append(
                                f"[node{score_str}] {_safe_str(text, 512)}"
                            )
                    if retrieved_texts:
                        span.set_attribute(
                            ATTR_TOOL_OUTPUT,
                            "\n---\n".join(retrieved_texts[:10]),
                        )

                span.add_event(
                    "retrieval_end",
                    EventType.RETRIEVAL_HIT,
                    results_count=node_info["count"],
                    latency_ms=latency_ms,
                )

                instrumentor._record_tool_metrics(
                    tool_name=f"llamaindex.{retriever_type}",
                    latency_ms=latency_ms,
                    success=True,
                )

                return result

        return _patched_retrieve

    def _wrap_aretrieve(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``BaseRetriever.aretrieve`` as an async RETRIEVAL span."""
        instrumentor = self

        @functools.wraps(original_fn)
        async def _patched_aretrieve(
            retriever_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            retriever_type = type(retriever_self).__name__

            query_str = ""
            if args:
                query_str = _extract_query_str(args[0])
            elif "str_or_query_bundle" in kwargs:
                query_str = _extract_query_str(kwargs["str_or_query_bundle"])

            top_k = getattr(retriever_self, "similarity_top_k", None) or getattr(
                retriever_self, "_similarity_top_k", None
            )

            with instrumentor._tracer.start_retrieval(
                name=f"llamaindex.retrieve.{retriever_type}"
            ) as span:
                span.set_attribute(ATTR_LI_RETRIEVER_TYPE, retriever_type)
                span.set_attribute(ATTR_TOOL_NAME, f"llamaindex.{retriever_type}")

                if top_k is not None:
                    span.set_attribute(ATTR_LI_RETRIEVAL_TOP_K, int(top_k))

                if instrumentor._capture_content and query_str:
                    span.set_attribute(
                        ATTR_LI_RETRIEVAL_QUERY, _safe_str(query_str, 2048)
                    )

                span.add_event(
                    "retrieval_start",
                    EventType.TOOL_START,
                    retriever=retriever_type,
                )

                start_ns = time.time_ns()

                try:
                    result = await original_fn(
                        retriever_self, *args, **kwargs
                    )
                except Exception as exc:
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_TOOL_SUCCESS, False)
                    span.set_attribute(ATTR_TOOL_LATENCY_MS, latency_ms)
                    span.add_event(
                        "retrieval_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_TOOL_SUCCESS, True)
                span.set_attribute(ATTR_TOOL_LATENCY_MS, latency_ms)

                node_info = _extract_node_info(result)
                span.set_attribute(
                    ATTR_LI_RETRIEVAL_RESULTS_COUNT, node_info["count"]
                )
                if node_info["scores"]:
                    span.set_attribute(ATTR_LI_NODE_SCORES, node_info["scores"])
                if node_info["ids"]:
                    span.set_attribute(ATTR_LI_NODE_IDS, node_info["ids"])

                span.add_event(
                    "retrieval_end",
                    EventType.RETRIEVAL_HIT,
                    results_count=node_info["count"],
                    latency_ms=latency_ms,
                )

                instrumentor._record_tool_metrics(
                    tool_name=f"llamaindex.{retriever_type}",
                    latency_ms=latency_ms,
                    success=True,
                )

                return result

        return _patched_aretrieve

    # ------------------------------------------------------------------
    # LLM wrappers
    # ------------------------------------------------------------------

    def _wrap_llm_complete(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``LLM.complete`` as an LLM_CALL span."""
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_complete(
            llm_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            model = _extract_llm_model_name(llm_self)
            provider = _extract_llm_provider(llm_self)
            start_ns = time.time_ns()

            with instrumentor._tracer.start_llm_call(model=model) as span:
                span.set_attribute(ATTR_LLM_PROVIDER, provider)

                temperature = getattr(llm_self, "temperature", None)
                if temperature is not None:
                    try:
                        span.set_attribute(
                            ATTR_LLM_TEMPERATURE, float(temperature)
                        )
                    except (TypeError, ValueError):
                        pass

                # Capture prompt
                if instrumentor._capture_content:
                    prompt = args[0] if args else kwargs.get("prompt", "")
                    span.set_attribute(ATTR_LLM_PROMPT, _safe_str(prompt))

                span.add_event("llm_start", EventType.LLM_START, model=model)

                try:
                    result = original_fn(llm_self, *args, **kwargs)
                except Exception as exc:
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
                    span.add_event(
                        "llm_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)

                # Token usage
                input_tokens, output_tokens = (
                    _extract_token_usage_from_response(result)
                )
                span.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
                span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)
                span.set_attribute(
                    ATTR_LLM_TOTAL_TOKENS, input_tokens + output_tokens
                )

                # Completion text
                if instrumentor._capture_content and result is not None:
                    text = getattr(result, "text", None) or str(result)
                    span.set_attribute(ATTR_LLM_COMPLETION, _safe_str(text))

                span.add_event(
                    "llm_end",
                    EventType.LLM_END,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                cost = estimate_cost(model, input_tokens, output_tokens)
                instrumentor._record_llm_metrics(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                )

                return result

        return _patched_complete

    def _wrap_llm_chat(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``LLM.chat`` as an LLM_CALL span."""
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_chat(llm_self: Any, *args: Any, **kwargs: Any) -> Any:
            model = _extract_llm_model_name(llm_self)
            provider = _extract_llm_provider(llm_self)
            start_ns = time.time_ns()

            with instrumentor._tracer.start_llm_call(model=model) as span:
                span.set_attribute(ATTR_LLM_PROVIDER, provider)

                temperature = getattr(llm_self, "temperature", None)
                if temperature is not None:
                    try:
                        span.set_attribute(
                            ATTR_LLM_TEMPERATURE, float(temperature)
                        )
                    except (TypeError, ValueError):
                        pass

                # Capture messages
                if instrumentor._capture_content:
                    messages = args[0] if args else kwargs.get("messages", [])
                    span.set_attribute(
                        ATTR_LLM_PROMPT, _messages_to_text(messages)
                    )

                span.add_event("llm_start", EventType.LLM_START, model=model)

                try:
                    result = original_fn(llm_self, *args, **kwargs)
                except Exception as exc:
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
                    span.add_event(
                        "llm_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)

                # Token usage
                input_tokens, output_tokens = (
                    _extract_token_usage_from_response(result)
                )
                span.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
                span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)
                span.set_attribute(
                    ATTR_LLM_TOTAL_TOKENS, input_tokens + output_tokens
                )

                # Completion content
                if instrumentor._capture_content and result is not None:
                    msg = getattr(result, "message", None)
                    if msg is not None:
                        content = getattr(msg, "content", str(msg))
                    else:
                        content = str(result)
                    span.set_attribute(ATTR_LLM_COMPLETION, _safe_str(content))

                span.add_event(
                    "llm_end",
                    EventType.LLM_END,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                cost = estimate_cost(model, input_tokens, output_tokens)
                instrumentor._record_llm_metrics(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                )

                return result

        return _patched_chat

    def _wrap_async_llm_complete(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``LLM.acomplete`` as an async LLM_CALL span."""
        instrumentor = self

        @functools.wraps(original_fn)
        async def _patched_acomplete(
            llm_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            model = _extract_llm_model_name(llm_self)
            provider = _extract_llm_provider(llm_self)
            start_ns = time.time_ns()

            with instrumentor._tracer.start_llm_call(model=model) as span:
                span.set_attribute(ATTR_LLM_PROVIDER, provider)

                if instrumentor._capture_content:
                    prompt = args[0] if args else kwargs.get("prompt", "")
                    span.set_attribute(ATTR_LLM_PROMPT, _safe_str(prompt))

                span.add_event("llm_start", EventType.LLM_START, model=model)

                try:
                    result = await original_fn(llm_self, *args, **kwargs)
                except Exception as exc:
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
                    span.add_event(
                        "llm_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)

                input_tokens, output_tokens = (
                    _extract_token_usage_from_response(result)
                )
                span.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
                span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)
                span.set_attribute(
                    ATTR_LLM_TOTAL_TOKENS, input_tokens + output_tokens
                )

                if instrumentor._capture_content and result is not None:
                    text = getattr(result, "text", None) or str(result)
                    span.set_attribute(ATTR_LLM_COMPLETION, _safe_str(text))

                span.add_event(
                    "llm_end",
                    EventType.LLM_END,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                cost = estimate_cost(model, input_tokens, output_tokens)
                instrumentor._record_llm_metrics(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                )

                return result

        return _patched_acomplete

    def _wrap_async_llm_chat(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``LLM.achat`` as an async LLM_CALL span."""
        instrumentor = self

        @functools.wraps(original_fn)
        async def _patched_achat(
            llm_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            model = _extract_llm_model_name(llm_self)
            provider = _extract_llm_provider(llm_self)
            start_ns = time.time_ns()

            with instrumentor._tracer.start_llm_call(model=model) as span:
                span.set_attribute(ATTR_LLM_PROVIDER, provider)

                if instrumentor._capture_content:
                    messages = args[0] if args else kwargs.get("messages", [])
                    span.set_attribute(
                        ATTR_LLM_PROMPT, _messages_to_text(messages)
                    )

                span.add_event("llm_start", EventType.LLM_START, model=model)

                try:
                    result = await original_fn(llm_self, *args, **kwargs)
                except Exception as exc:
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
                    span.add_event(
                        "llm_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)

                input_tokens, output_tokens = (
                    _extract_token_usage_from_response(result)
                )
                span.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
                span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)
                span.set_attribute(
                    ATTR_LLM_TOTAL_TOKENS, input_tokens + output_tokens
                )

                if instrumentor._capture_content and result is not None:
                    msg = getattr(result, "message", None)
                    if msg is not None:
                        content = getattr(msg, "content", str(msg))
                    else:
                        content = str(result)
                    span.set_attribute(ATTR_LLM_COMPLETION, _safe_str(content))

                span.add_event(
                    "llm_end",
                    EventType.LLM_END,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                cost = estimate_cost(model, input_tokens, output_tokens)
                instrumentor._record_llm_metrics(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                )

                return result

        return _patched_achat

    # ------------------------------------------------------------------
    # Agent wrappers
    # ------------------------------------------------------------------

    def _wrap_agent_chat(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``AgentRunner.chat`` as a TASK span."""
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_agent_chat(
            agent_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            agent_type = type(agent_self).__name__

            # Extract message
            message = ""
            if args:
                message = _safe_str(args[0], max_len=1024)
            elif "message" in kwargs:
                message = _safe_str(kwargs["message"], max_len=1024)

            # Extract tool names
            tool_names = []
            tools = getattr(agent_self, "tools", None) or getattr(
                agent_self, "_tools", None
            )
            if tools:
                for tool in tools:
                    name = getattr(
                        tool, "name", getattr(tool, "__name__", type(tool).__name__)
                    )
                    tool_names.append(str(name))

            task_name = f"llamaindex.agent.{agent_type}"

            with instrumentor._tracer.start_task(task_name=task_name) as span:
                span.set_attribute(ATTR_LI_AGENT_TYPE, agent_type)
                span.set_attribute(ATTR_AGENT_TASK, task_name)

                if tool_names:
                    span.set_attribute(ATTR_LI_AGENT_TOOLS, tool_names)

                if instrumentor._capture_content and message:
                    span.set_attribute("llamaindex.agent.message", message)

                span.add_event(
                    "agent_chat_start",
                    EventType.AGENT_START,
                    agent_type=agent_type,
                    tools=tool_names,
                )

                instrumentor._metrics.increment(
                    "agent.task.count", framework="llamaindex"
                )
                start_ns = time.time_ns()

                try:
                    result = original_fn(agent_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "agent_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                # Extract total steps from the agent's task state
                total_steps = 0
                current_task = getattr(agent_self, "current_task", None)
                if current_task is not None:
                    completed_steps = getattr(
                        current_task, "completed_steps", None
                    )
                    if completed_steps:
                        total_steps = len(completed_steps)
                span.set_attribute(ATTR_LI_AGENT_TOTAL_STEPS, total_steps)

                if instrumentor._capture_content and result is not None:
                    response_text = getattr(result, "response", None) or str(
                        result
                    )
                    span.set_attribute(
                        "llamaindex.agent.response",
                        _safe_str(response_text),
                    )

                span.add_event(
                    "agent_chat_end",
                    EventType.AGENT_END,
                    agent_type=agent_type,
                    total_steps=total_steps,
                    duration_ms=duration_ms,
                )

                instrumentor._metrics.record(
                    "agent.task.duration_ms",
                    duration_ms,
                    framework="llamaindex",
                )

                return result

        return _patched_agent_chat

    def _wrap_agent_query(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``AgentRunner.query`` as a TASK span.

        Delegates to the same logic as agent chat wrapping.
        """
        return self._wrap_agent_chat(original_fn)

    def _wrap_async_agent_chat(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch ``AgentRunner.achat`` as an async TASK span."""
        instrumentor = self

        @functools.wraps(original_fn)
        async def _patched_async_agent_chat(
            agent_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            agent_type = type(agent_self).__name__

            message = ""
            if args:
                message = _safe_str(args[0], max_len=1024)
            elif "message" in kwargs:
                message = _safe_str(kwargs["message"], max_len=1024)

            tool_names = []
            tools = getattr(agent_self, "tools", None) or getattr(
                agent_self, "_tools", None
            )
            if tools:
                for tool in tools:
                    name = getattr(
                        tool, "name", getattr(tool, "__name__", type(tool).__name__)
                    )
                    tool_names.append(str(name))

            task_name = f"llamaindex.agent.{agent_type}"

            with instrumentor._tracer.start_task(task_name=task_name) as span:
                span.set_attribute(ATTR_LI_AGENT_TYPE, agent_type)
                span.set_attribute(ATTR_AGENT_TASK, task_name)

                if tool_names:
                    span.set_attribute(ATTR_LI_AGENT_TOOLS, tool_names)

                if instrumentor._capture_content and message:
                    span.set_attribute("llamaindex.agent.message", message)

                span.add_event(
                    "agent_chat_start",
                    EventType.AGENT_START,
                    agent_type=agent_type,
                )

                instrumentor._metrics.increment(
                    "agent.task.count", framework="llamaindex"
                )
                start_ns = time.time_ns()

                try:
                    result = await original_fn(agent_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "agent_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                if instrumentor._capture_content and result is not None:
                    response_text = getattr(result, "response", None) or str(
                        result
                    )
                    span.set_attribute(
                        "llamaindex.agent.response",
                        _safe_str(response_text),
                    )

                span.add_event(
                    "agent_chat_end",
                    EventType.AGENT_END,
                    agent_type=agent_type,
                    duration_ms=duration_ms,
                )

                instrumentor._metrics.record(
                    "agent.task.duration_ms",
                    duration_ms,
                    framework="llamaindex",
                )

                return result

        return _patched_async_agent_chat

    def _wrap_agent_step(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Patch agent step execution as a REASONING span.

        Wraps individual step execution within an agent runner to capture
        per-step reasoning telemetry.
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_step(
            step_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            agent_type = type(step_self).__name__

            # Try to determine step number
            step_number = None
            task = kwargs.get("task", None)
            if task is None and args:
                task = args[0]
            if task is not None:
                completed = getattr(task, "completed_steps", None)
                if completed is not None:
                    step_number = len(completed) + 1

            step_label = step_number or "?"

            with instrumentor._tracer.start_reasoning(
                name=f"llamaindex.agent.step_{step_label}"
            ) as span:
                span.set_attribute(ATTR_LI_AGENT_TYPE, agent_type)
                if step_number is not None:
                    span.set_attribute(ATTR_LI_AGENT_STEP, step_number)

                span.add_event(
                    "agent_step_start",
                    EventType.AGENT_MESSAGE,
                    agent_type=agent_type,
                    step=step_label,
                )

                start_ns = time.time_ns()

                try:
                    result = original_fn(step_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "agent_step_error",
                        EventType.ERROR,
                        error=str(exc),
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="llamaindex"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                # Extract step output info
                if result is not None:
                    # TaskStepOutput has output, is_last, etc.
                    is_last = getattr(result, "is_last", False)
                    span.set_attribute("llamaindex.agent.step.is_last", is_last)

                    output = getattr(result, "output", None)
                    if output is not None and instrumentor._capture_content:
                        response_text = getattr(
                            output, "response", None
                        ) or str(output)
                        span.set_attribute(
                            "llamaindex.agent.step.output",
                            _safe_str(response_text),
                        )

                    # Check for tool output within the step
                    sources = getattr(result, "sources", None) or getattr(
                        output, "source_nodes", None
                    )
                    if sources:
                        node_info = _extract_node_info(sources)
                        if node_info["scores"]:
                            span.set_attribute(
                                ATTR_LI_NODE_SCORES, node_info["scores"]
                            )

                span.add_event(
                    "agent_step_end",
                    EventType.AGENT_MESSAGE,
                    step=step_label,
                    duration_ms=duration_ms,
                )

                return result

        return _patched_step
