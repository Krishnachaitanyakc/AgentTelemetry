"""DSPy instrumentor for AgentTelemetry.

Automatically captures telemetry from DSPy programs by monkey-patching
core classes: ``dspy.Predict``, ``dspy.Module``, ``dspy.Retrieve``,
``dspy.ChainOfThought``, and ``dspy.ReAct``.

Span mapping:

    dspy.Module.__call__       -> TASK span
    dspy.Predict.__call__      -> LLM_CALL span
    dspy.Retrieve.__call__     -> RETRIEVAL span
    dspy.ChainOfThought        -> REASONING span (wrapping inner LLM_CALL)
    dspy.ReAct agent steps     -> REASONING spans for thought/action/observation

Usage::

    from agenttelemetry.instrumentors.dspy import DSPyInstrumentor

    instrumentor = DSPyInstrumentor(capture_content=True)
    instrumentor.instrument()

    # ... use DSPy normally — telemetry is captured automatically ...

    instrumentor.uninstrument()
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from agenttelemetry.core.events import EventType
from agenttelemetry.core.trace import (
    ATTR_AGENT_TASK,
    ATTR_LLM_COMPLETION,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_LATENCY_MS,
    ATTR_LLM_MODEL,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_PROMPT,
    ATTR_LLM_TOTAL_TOKENS,
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
# Custom attribute keys for DSPy-specific metadata
# ---------------------------------------------------------------------------
ATTR_DSPY_SIGNATURE = "dspy.signature"
ATTR_DSPY_SIGNATURE_INPUT_FIELDS = "dspy.signature.input_fields"
ATTR_DSPY_SIGNATURE_OUTPUT_FIELDS = "dspy.signature.output_fields"
ATTR_DSPY_SIGNATURE_INSTRUCTIONS = "dspy.signature.instructions"
ATTR_DSPY_MODULE_TYPE = "dspy.module.type"
ATTR_DSPY_PREDICTOR_NAME = "dspy.predictor.name"
ATTR_DSPY_DEMOS_COUNT = "dspy.demos.count"
ATTR_DSPY_REACT_STEP = "dspy.react.step"
ATTR_DSPY_REACT_PHASE = "dspy.react.phase"
ATTR_DSPY_RETRIEVAL_QUERY = "dspy.retrieval.query"
ATTR_DSPY_RETRIEVAL_K = "dspy.retrieval.k"
ATTR_DSPY_RETRIEVAL_RESULTS_COUNT = "dspy.retrieval.results_count"


def _safe_str(obj: Any, max_len: int = 4096) -> str:
    """Convert an object to a truncated string, swallowing exceptions."""
    try:
        text = str(obj)
        if len(text) > max_len:
            return text[:max_len] + "...[truncated]"
        return text
    except Exception:
        return "<unserializable>"


def _extract_signature_info(predict_instance: Any) -> Dict[str, Any]:
    """Extract signature metadata from a dspy.Predict instance.

    Returns a dict of span attributes describing the signature, input
    fields, output fields, and instructions (if present).
    """
    attrs: Dict[str, Any] = {}
    try:
        sig = getattr(predict_instance, "signature", None)
        if sig is None:
            return attrs

        # Signature string representation (e.g. "question -> answer")
        attrs[ATTR_DSPY_SIGNATURE] = _safe_str(sig, max_len=512)

        # Input and output field names
        if hasattr(sig, "input_fields"):
            input_fields = sig.input_fields
            if isinstance(input_fields, dict):
                attrs[ATTR_DSPY_SIGNATURE_INPUT_FIELDS] = list(input_fields.keys())
            elif isinstance(input_fields, (list, tuple)):
                attrs[ATTR_DSPY_SIGNATURE_INPUT_FIELDS] = list(input_fields)

        if hasattr(sig, "output_fields"):
            output_fields = sig.output_fields
            if isinstance(output_fields, dict):
                attrs[ATTR_DSPY_SIGNATURE_OUTPUT_FIELDS] = list(output_fields.keys())
            elif isinstance(output_fields, (list, tuple)):
                attrs[ATTR_DSPY_SIGNATURE_OUTPUT_FIELDS] = list(output_fields)

        # Instructions / docstring
        instructions = getattr(sig, "instructions", None) or getattr(
            sig, "__doc__", None
        )
        if instructions:
            attrs[ATTR_DSPY_SIGNATURE_INSTRUCTIONS] = _safe_str(
                instructions, max_len=1024
            )
    except Exception:
        logger.debug("Failed to extract DSPy signature info", exc_info=True)

    return attrs


def _extract_model_name() -> str:
    """Resolve the current DSPy LM model name at call time."""
    try:
        import dspy

        # DSPy >= 2.5: dspy.settings.lm is the active language model
        lm = getattr(dspy.settings, "lm", None)
        if lm is None:
            return "unknown"

        # The LM object typically exposes .model or .model_name
        model = getattr(lm, "model", None) or getattr(lm, "model_name", None)
        if model:
            return str(model)

        # Fallback: class name
        return type(lm).__name__
    except Exception:
        return "unknown"


def _extract_token_usage(result: Any) -> Tuple[int, int]:
    """Attempt to extract token usage from a DSPy prediction result.

    DSPy stores LM call history on the LM object.  We peek at the most
    recent entry to pull input/output token counts.

    Returns (input_tokens, output_tokens).
    """
    try:
        import dspy

        lm = getattr(dspy.settings, "lm", None)
        if lm is None:
            return 0, 0

        # DSPy >= 2.5 stores history as a list of dicts
        history = getattr(lm, "history", None)
        if history and isinstance(history, list) and len(history) > 0:
            last_entry = history[-1]
            usage = (
                last_entry.get("usage")
                or last_entry.get("response", {}).get("usage")
                or {}
            )
            if isinstance(usage, dict):
                inp = usage.get("prompt_tokens", 0) or usage.get("input_tokens", 0)
                out = (
                    usage.get("completion_tokens", 0)
                    or usage.get("output_tokens", 0)
                )
                return int(inp), int(out)

        # Alternative: some LM wrappers expose .total_tokens etc.
        inp = getattr(lm, "total_prompt_tokens", 0) or 0
        out = getattr(lm, "total_completion_tokens", 0) or 0
        return int(inp), int(out)
    except Exception:
        return 0, 0


# ---------------------------------------------------------------------------
# DSPyInstrumentor
# ---------------------------------------------------------------------------


class DSPyInstrumentor(BaseInstrumentor):
    """Instruments DSPy to capture execution telemetry.

    Monkey-patches ``dspy.Predict.__call__``, ``dspy.Module.__call__``,
    ``dspy.Retrieve.__call__``, ``dspy.ChainOfThought.__call__``, and
    ``dspy.ReAct.__call__`` to automatically record spans and metrics.

    Parameters
    ----------
    tracer : AgentTracer, optional
        Pre-configured tracer instance.  A default one is created if omitted.
    metrics : AgentMetrics, optional
        Pre-configured metrics collector.  A default one is created if omitted.
    capture_content : bool
        When ``True``, prompts, completions, and retrieval content are
        recorded as span attributes.  Defaults to ``False`` for privacy.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Stash for original (unpatched) methods so uninstrument() can restore them.
        # Instance variable — not shared across instrumentor instances.
        self._originals: Dict[str, Any] = {}

    @property
    def framework_name(self) -> str:  # noqa: D401
        return "dspy"

    # ------------------------------------------------------------------
    # instrument / uninstrument
    # ------------------------------------------------------------------

    def instrument(self) -> None:
        """Apply monkey-patches to DSPy classes."""
        if self._instrumented:
            logger.debug("DSPy instrumentor is already active; skipping.")
            return

        try:
            import dspy
        except ImportError as exc:
            raise ImportError(
                "DSPy is not installed.  Install it with: pip install dspy-ai"
            ) from exc

        # Record framework version
        dspy_version = getattr(dspy, "__version__", "unknown")
        self._tracer._framework_version = dspy_version

        # --- Predict.__call__ ---
        self._originals["Predict.__call__"] = dspy.Predict.__call__
        dspy.Predict.__call__ = self._wrap_predict_call(dspy.Predict.__call__)

        # --- Module.__call__ ---
        self._originals["Module.__call__"] = dspy.Module.__call__
        dspy.Module.__call__ = self._wrap_module_call(dspy.Module.__call__)

        # --- Retrieve.__call__ ---
        if hasattr(dspy, "Retrieve"):
            self._originals["Retrieve.__call__"] = dspy.Retrieve.__call__
            dspy.Retrieve.__call__ = self._wrap_retrieve_call(
                dspy.Retrieve.__call__
            )

        # --- ChainOfThought.__call__ ---
        if hasattr(dspy, "ChainOfThought"):
            self._originals["ChainOfThought.__call__"] = (
                dspy.ChainOfThought.__call__
            )
            dspy.ChainOfThought.__call__ = self._wrap_chain_of_thought_call(
                dspy.ChainOfThought.__call__
            )

        # --- ReAct.__call__ ---
        if hasattr(dspy, "ReAct"):
            self._originals["ReAct.__call__"] = dspy.ReAct.__call__
            dspy.ReAct.__call__ = self._wrap_react_call(dspy.ReAct.__call__)

        self._instrumented = True
        logger.info(
            "DSPy instrumentor activated (version=%s, capture_content=%s)",
            dspy_version,
            self._capture_content,
        )

    def uninstrument(self) -> None:
        """Remove all monkey-patches and restore original methods."""
        if not self._instrumented:
            logger.debug("DSPy instrumentor is not active; nothing to undo.")
            return

        try:
            import dspy
        except ImportError:
            self._instrumented = False
            self._originals.clear()
            return

        _class_map: Dict[str, Any] = {
            "Predict.__call__": dspy.Predict,
            "Module.__call__": dspy.Module,
        }
        if hasattr(dspy, "Retrieve"):
            _class_map["Retrieve.__call__"] = dspy.Retrieve
        if hasattr(dspy, "ChainOfThought"):
            _class_map["ChainOfThought.__call__"] = dspy.ChainOfThought
        if hasattr(dspy, "ReAct"):
            _class_map["ReAct.__call__"] = dspy.ReAct

        for key, cls in _class_map.items():
            original = self._originals.get(key)
            if original is not None:
                setattr(cls, "__call__", original)

        self._originals.clear()
        self._instrumented = False
        logger.info("DSPy instrumentor deactivated — original methods restored.")

    # ------------------------------------------------------------------
    # Wrapper factories
    # ------------------------------------------------------------------

    def _wrap_predict_call(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched ``Predict.__call__`` method.

        Each invocation is wrapped in an ``LLM_CALL`` span that captures
        model name, token usage, cost, latency, and (optionally) content.
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_predict_call(predict_self: Any, *args: Any, **kwargs: Any) -> Any:
            model = _extract_model_name()
            span_name = f"dspy.predict"

            # Build a meaningful predictor name from the Predict instance
            predictor_name = getattr(predict_self, "name", None) or type(
                predict_self
            ).__name__

            sig_attrs = _extract_signature_info(predict_self)

            # Capture the number of few-shot demos if available
            demos = getattr(predict_self, "demos", None)
            demo_count = len(demos) if demos is not None else 0

            start_ns = time.time_ns()

            with instrumentor._tracer.start_llm_call(model=model) as span:
                span.set_attribute(ATTR_DSPY_PREDICTOR_NAME, predictor_name)
                span.set_attribute(ATTR_DSPY_MODULE_TYPE, "Predict")
                span.set_attribute(ATTR_DSPY_DEMOS_COUNT, demo_count)

                for attr_key, attr_val in sig_attrs.items():
                    span.set_attribute(attr_key, attr_val)

                # Capture prompt content (the kwargs passed to __call__)
                if instrumentor._capture_content and kwargs:
                    span.set_attribute(ATTR_LLM_PROMPT, _safe_str(kwargs))

                span.add_event("llm_start", EventType.LLM_START, model=model)

                try:
                    result = original_fn(predict_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "predict_error", EventType.ERROR, error=str(exc)
                    )
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="dspy"
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)

                # Token usage
                input_tokens, output_tokens = _extract_token_usage(result)
                span.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
                span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)
                span.set_attribute(
                    ATTR_LLM_TOTAL_TOKENS, input_tokens + output_tokens
                )

                # Completion content (opt-in)
                if instrumentor._capture_content and result is not None:
                    span.set_attribute(ATTR_LLM_COMPLETION, _safe_str(result))

                span.add_event(
                    "llm_end",
                    EventType.LLM_END,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                # Record aggregate metrics
                cost = estimate_cost(model, input_tokens, output_tokens)
                instrumentor._record_llm_metrics(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    cost_usd=cost,
                )

                return result

        return _patched_predict_call

    def _wrap_module_call(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched ``Module.__call__`` method.

        Each invocation is wrapped in a ``TASK`` span that represents the
        full module execution (which may contain nested Predict / Retrieve
        calls tracked as child spans).
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_module_call(module_self: Any, *args: Any, **kwargs: Any) -> Any:
            module_type = type(module_self).__name__
            module_name = getattr(module_self, "name", None) or module_type
            task_name = f"dspy.module.{module_name}"

            # Avoid double-wrapping: if this Module is also a ChainOfThought
            # or ReAct that has its own wrapper, let the more specific wrapper
            # create the outer span.  We detect this by checking whether the
            # class already has a patched __call__ other than Module.__call__.
            # The more specific patches (ChainOfThought, ReAct) take precedence
            # via MRO, so this Module wrapper only fires for plain Module
            # subclasses.
            try:
                import dspy

                if isinstance(module_self, getattr(dspy, "ChainOfThought", type(None))):
                    return original_fn(module_self, *args, **kwargs)
                if isinstance(module_self, getattr(dspy, "ReAct", type(None))):
                    return original_fn(module_self, *args, **kwargs)
            except Exception:
                pass

            with instrumentor._tracer.start_task(task_name) as span:
                span.set_attribute(ATTR_DSPY_MODULE_TYPE, module_type)
                span.set_attribute(ATTR_AGENT_TASK, task_name)

                if instrumentor._capture_content and kwargs:
                    span.set_attribute("dspy.module.input", _safe_str(kwargs))

                span.add_event(
                    "module_start",
                    EventType.AGENT_START,
                    module=module_type,
                )

                instrumentor._metrics.increment("agent.task.count", framework="dspy")
                start_ns = time.time_ns()

                try:
                    result = original_fn(module_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "module_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="dspy"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                if instrumentor._capture_content and result is not None:
                    span.set_attribute("dspy.module.output", _safe_str(result))

                span.add_event(
                    "module_end",
                    EventType.AGENT_END,
                    module=module_type,
                    duration_ms=duration_ms,
                )

                instrumentor._metrics.record(
                    "agent.task.duration_ms", duration_ms, framework="dspy"
                )

                return result

        return _patched_module_call

    def _wrap_retrieve_call(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched ``Retrieve.__call__`` method.

        Each invocation is wrapped in a ``RETRIEVAL`` span that captures
        the query, number of results requested (k), and result count.
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_retrieve_call(
            retrieve_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            # Extract query — first positional arg or 'query' kwarg
            query = ""
            if args:
                query = _safe_str(args[0], max_len=1024)
            elif "query" in kwargs:
                query = _safe_str(kwargs["query"], max_len=1024)

            k = getattr(retrieve_self, "k", kwargs.get("k", None))

            with instrumentor._tracer.start_retrieval(
                name="dspy.retrieve"
            ) as span:
                span.set_attribute(ATTR_DSPY_MODULE_TYPE, "Retrieve")
                span.set_attribute(ATTR_TOOL_NAME, "dspy.Retrieve")

                if k is not None:
                    span.set_attribute(ATTR_DSPY_RETRIEVAL_K, int(k))

                if instrumentor._capture_content and query:
                    span.set_attribute(ATTR_DSPY_RETRIEVAL_QUERY, query)

                span.add_event(
                    "retrieval_start",
                    EventType.TOOL_START,
                    query=query if instrumentor._capture_content else "<redacted>",
                )

                start_ns = time.time_ns()

                try:
                    result = original_fn(retrieve_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_TOOL_SUCCESS, False)
                    span.add_event(
                        "retrieval_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="dspy"
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_TOOL_SUCCESS, True)

                # Count returned passages
                results_count = 0
                if result is not None:
                    passages = getattr(result, "passages", None)
                    if passages is not None and hasattr(passages, "__len__"):
                        results_count = len(passages)
                    elif isinstance(result, (list, tuple)):
                        results_count = len(result)

                span.set_attribute(
                    ATTR_DSPY_RETRIEVAL_RESULTS_COUNT, results_count
                )

                if instrumentor._capture_content and result is not None:
                    span.set_attribute(ATTR_TOOL_OUTPUT, _safe_str(result))

                span.add_event(
                    "retrieval_end",
                    EventType.RETRIEVAL_HIT,
                    results_count=results_count,
                    latency_ms=latency_ms,
                )

                instrumentor._record_tool_metrics(
                    tool_name="dspy.Retrieve",
                    latency_ms=latency_ms,
                    success=True,
                )

                return result

        return _patched_retrieve_call

    def _wrap_chain_of_thought_call(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched ``ChainOfThought.__call__`` method.

        Wraps the call in a ``REASONING`` span.  The inner Predict calls
        (already patched) will appear as ``LLM_CALL`` child spans under
        this reasoning span.
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_cot_call(cot_self: Any, *args: Any, **kwargs: Any) -> Any:
            sig_attrs = _extract_signature_info(cot_self)
            predictor_name = getattr(cot_self, "name", None) or "ChainOfThought"

            with instrumentor._tracer.start_reasoning(
                name=f"dspy.chain_of_thought.{predictor_name}"
            ) as span:
                span.set_attribute(ATTR_DSPY_MODULE_TYPE, "ChainOfThought")
                span.set_attribute(ATTR_DSPY_PREDICTOR_NAME, predictor_name)

                for attr_key, attr_val in sig_attrs.items():
                    span.set_attribute(attr_key, attr_val)

                if instrumentor._capture_content and kwargs:
                    span.set_attribute("dspy.cot.input", _safe_str(kwargs))

                span.add_event(
                    "cot_start",
                    EventType.AGENT_START,
                    predictor=predictor_name,
                )

                start_ns = time.time_ns()

                try:
                    result = original_fn(cot_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "cot_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="dspy"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                # Capture the rationale if present
                if instrumentor._capture_content and result is not None:
                    rationale = getattr(result, "rationale", None)
                    if rationale:
                        span.set_attribute(
                            "dspy.cot.rationale", _safe_str(rationale)
                        )
                    span.set_attribute(
                        "dspy.cot.output", _safe_str(result)
                    )

                span.add_event(
                    "cot_end",
                    EventType.AGENT_END,
                    predictor=predictor_name,
                    duration_ms=duration_ms,
                )

                return result

        return _patched_cot_call

    def _wrap_react_call(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched ``ReAct.__call__`` method.

        Wraps the entire ReAct execution in a ``TASK`` span and intercepts
        the internal thought/action/observation cycle to emit ``REASONING``
        child spans for each step.

        DSPy's ReAct module internally calls Predict multiple times in a
        loop.  Those Predict calls are already instrumented as LLM_CALL
        spans.  This wrapper adds the higher-level structure:

        - TASK span for the full ReAct execution
        - REASONING spans annotated with ``dspy.react.phase`` to mark
          thought, action, and observation phases when discernible from
          the result attributes.
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_react_call(
            react_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            module_name = getattr(react_self, "name", None) or "ReAct"
            sig_attrs = _extract_signature_info(react_self)

            # Collect tool names registered on the ReAct module
            tools = getattr(react_self, "tools", None)
            tool_names: List[str] = []
            if tools:
                for tool in tools:
                    name = (
                        getattr(tool, "name", None)
                        or getattr(tool, "__name__", None)
                        or type(tool).__name__
                    )
                    tool_names.append(str(name))

            max_iters = getattr(react_self, "max_iters", None) or kwargs.get(
                "max_iters", None
            )

            with instrumentor._tracer.start_task(
                task_name=f"dspy.react.{module_name}"
            ) as task_span:
                task_span.set_attribute(ATTR_DSPY_MODULE_TYPE, "ReAct")
                task_span.set_attribute(ATTR_AGENT_TASK, f"dspy.react.{module_name}")

                if tool_names:
                    task_span.set_attribute("dspy.react.tools", tool_names)
                if max_iters is not None:
                    task_span.set_attribute("dspy.react.max_iters", int(max_iters))

                for attr_key, attr_val in sig_attrs.items():
                    task_span.set_attribute(attr_key, attr_val)

                if instrumentor._capture_content and kwargs:
                    task_span.set_attribute("dspy.react.input", _safe_str(kwargs))

                task_span.add_event(
                    "react_start",
                    EventType.AGENT_START,
                    module=module_name,
                    tools=tool_names,
                )

                instrumentor._metrics.increment(
                    "agent.task.count", framework="dspy"
                )
                start_ns = time.time_ns()

                try:
                    result = original_fn(react_self, *args, **kwargs)
                except Exception as exc:
                    task_span.set_status(SpanStatus.ERROR, str(exc))
                    task_span.add_event(
                        "react_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="dspy"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                # ----------------------------------------------------------
                # Post-hoc extraction of thought/action/observation steps
                # from the result object.  DSPy ReAct stores the trajectory
                # in numbered attributes (e.g. result.action_1,
                # result.thought_1, result.observation_1).
                # ----------------------------------------------------------
                step = 1
                while True:
                    thought = getattr(result, f"thought_{step}", None)
                    action = getattr(result, f"action_{step}", None)
                    observation = getattr(result, f"observation_{step}", None)

                    if thought is None and action is None and observation is None:
                        break

                    # Emit a REASONING span for each complete step
                    with instrumentor._tracer.start_reasoning(
                        name=f"dspy.react.step_{step}"
                    ) as step_span:
                        step_span.set_attribute(ATTR_DSPY_REACT_STEP, step)
                        step_span.set_attribute(ATTR_DSPY_MODULE_TYPE, "ReAct")

                        if thought is not None:
                            step_span.set_attribute(
                                ATTR_DSPY_REACT_PHASE, "thought"
                            )
                            if instrumentor._capture_content:
                                step_span.set_attribute(
                                    "dspy.react.thought", _safe_str(thought)
                                )
                            step_span.add_event(
                                "react_thought",
                                EventType.AGENT_MESSAGE,
                                step=step,
                                phase="thought",
                            )

                        if action is not None:
                            step_span.set_attribute(
                                ATTR_DSPY_REACT_PHASE, "action"
                            )
                            if instrumentor._capture_content:
                                step_span.set_attribute(
                                    "dspy.react.action", _safe_str(action)
                                )
                            step_span.add_event(
                                "react_action",
                                EventType.TOOL_START,
                                step=step,
                                phase="action",
                            )

                        if observation is not None:
                            step_span.set_attribute(
                                ATTR_DSPY_REACT_PHASE, "observation"
                            )
                            if instrumentor._capture_content:
                                step_span.set_attribute(
                                    "dspy.react.observation",
                                    _safe_str(observation),
                                )
                            step_span.add_event(
                                "react_observation",
                                EventType.TOOL_END,
                                step=step,
                                phase="observation",
                            )

                    step += 1

                if instrumentor._capture_content and result is not None:
                    task_span.set_attribute(
                        "dspy.react.output", _safe_str(result)
                    )

                task_span.set_attribute(
                    "dspy.react.total_steps", step - 1
                )

                task_span.add_event(
                    "react_end",
                    EventType.AGENT_END,
                    module=module_name,
                    total_steps=step - 1,
                    duration_ms=duration_ms,
                )

                instrumentor._metrics.record(
                    "agent.task.duration_ms", duration_ms, framework="dspy"
                )

                return result

        return _patched_react_call
