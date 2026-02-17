"""Smolagents (HuggingFace) instrumentor for AgentTelemetry.

Automatically captures telemetry from HuggingFace's smolagents framework
by monkey-patching core agent classes and their internal execution methods.

Span mapping:

    ToolCallingAgent.run()          -> TASK span
    CodeAgent.run()                 -> TASK span
    Agent step execution            -> REASONING span (per step)
    CodeAgent code generation       -> REASONING span (code_generation)
    LLM calls (Model.__call__)     -> LLM_CALL span
    Tool calls (Tool.__call__)     -> TOOL_CALL span

Usage::

    from agenttelemetry.instrumentors.smolagents import SmolagentsInstrumentor

    instrumentor = SmolagentsInstrumentor(capture_content=True)
    instrumentor.instrument()

    # ... use smolagents normally — telemetry is captured automatically ...

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
# Custom attribute keys for smolagents-specific metadata
# ---------------------------------------------------------------------------
ATTR_SMOL_AGENT_TYPE = "smolagents.agent.type"
ATTR_SMOL_STEP_NUMBER = "smolagents.step.number"
ATTR_SMOL_STEP_TYPE = "smolagents.step.type"
ATTR_SMOL_MAX_STEPS = "smolagents.max_steps"
ATTR_SMOL_TOOL_NAMES = "smolagents.tool_names"
ATTR_SMOL_CODE = "smolagents.code"
ATTR_SMOL_CODE_OUTPUT = "smolagents.code.output"
ATTR_SMOL_OBSERVATIONS = "smolagents.observations"
ATTR_SMOL_TASK = "smolagents.task"
ATTR_SMOL_TOTAL_STEPS = "smolagents.total_steps"


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


def _extract_model_name(agent: Any) -> str:
    """Extract the model name from a smolagents agent instance.

    smolagents agents store the model/LLM as ``agent.model`` which is
    typically a ``TransformersModel``, ``HfApiModel``, or
    ``LiteLLMModel`` instance with a ``.model_id`` or ``.model_name``
    attribute.
    """
    try:
        model_obj = getattr(agent, "model", None)
        if model_obj is None:
            return "unknown"

        # Try common attribute names
        for attr in ("model_id", "model_name", "model", "name"):
            val = getattr(model_obj, attr, None)
            if val and isinstance(val, str):
                return val

        return type(model_obj).__name__
    except Exception:
        return "unknown"


def _extract_tool_names(agent: Any) -> List[str]:
    """Extract the list of tool names from a smolagents agent."""
    try:
        tools = getattr(agent, "tools", None) or getattr(agent, "toolbox", None)
        if tools is None:
            return []

        # tools can be a dict {name: Tool} or a ToolBox with .tools dict
        if isinstance(tools, dict):
            return list(tools.keys())

        # Toolbox object
        tools_dict = getattr(tools, "tools", None)
        if isinstance(tools_dict, dict):
            return list(tools_dict.keys())

        # List of Tool objects
        if isinstance(tools, (list, tuple)):
            names = []
            for t in tools:
                name = getattr(t, "name", None) or type(t).__name__
                names.append(str(name))
            return names

        return []
    except Exception:
        return []


def _extract_step_log_info(step_log: Any) -> Dict[str, Any]:
    """Extract telemetry info from a smolagents step log object.

    Step logs in smolagents contain information about what happened
    during each step: tool calls, code execution, observations,
    LLM output, token usage, etc.
    """
    info: Dict[str, Any] = {}
    try:
        # Tool call info
        tool_calls = getattr(step_log, "tool_calls", None)
        if tool_calls:
            info["tool_calls"] = tool_calls

        # Code (for CodeAgent)
        code = getattr(step_log, "code", None) or getattr(step_log, "code_action", None)
        if code:
            info["code"] = str(code)

        # Observations / output
        observations = getattr(step_log, "observations", None)
        if observations:
            info["observations"] = str(observations)

        # LLM output / agent output
        agent_output = getattr(step_log, "agent_output", None) or getattr(
            step_log, "output", None
        )
        if agent_output:
            info["output"] = agent_output

        # Error
        error = getattr(step_log, "error", None)
        if error:
            info["error"] = str(error)

        # Token usage (if tracked at step level)
        token_usage = getattr(step_log, "token_usage", None)
        if token_usage:
            info["token_usage"] = token_usage

        # Step type/action type
        action_type = getattr(step_log, "action_type", None)
        if action_type:
            info["action_type"] = str(action_type)

    except Exception:
        logger.debug("Failed to extract step log info", exc_info=True)

    return info


# ---------------------------------------------------------------------------
# SmolagentsInstrumentor
# ---------------------------------------------------------------------------


class SmolagentsInstrumentor(BaseInstrumentor):
    """Instruments HuggingFace smolagents to capture execution telemetry.

    Monkey-patches ``ToolCallingAgent.run()``, ``CodeAgent.run()``,
    the internal step execution methods, ``Tool.__call__()``, and model
    call methods to automatically record spans and metrics.

    Parameters
    ----------
    tracer : AgentTracer, optional
        Pre-configured tracer instance.  A default one is created if omitted.
    metrics : AgentMetrics, optional
        Pre-configured metrics collector.  A default one is created if omitted.
    capture_content : bool
        When ``True``, prompts, completions, code, tool inputs/outputs,
        and observations are recorded as span attributes.  Defaults to
        ``False`` for privacy.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._originals: Dict[str, Any] = {}

    @property
    def framework_name(self) -> str:  # noqa: D401
        return "smolagents"

    # ------------------------------------------------------------------
    # instrument / uninstrument
    # ------------------------------------------------------------------

    def instrument(self) -> None:
        """Apply monkey-patches to smolagents classes."""
        if self._instrumented:
            logger.debug("Smolagents instrumentor is already active; skipping.")
            return

        try:
            import smolagents
        except ImportError as exc:
            raise ImportError(
                "smolagents is not installed. "
                "Install it with: pip install smolagents"
            ) from exc

        # Record framework version
        smol_version = getattr(smolagents, "__version__", "unknown")
        self._tracer._framework_version = smol_version

        # --- Patch ToolCallingAgent.run ---
        try:
            from smolagents.agents import ToolCallingAgent

            self._originals["ToolCallingAgent.run"] = ToolCallingAgent.run
            ToolCallingAgent.run = self._wrap_agent_run(
                ToolCallingAgent.run, "ToolCallingAgent"
            )
        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch ToolCallingAgent.run: %s", exc)

        # --- Patch CodeAgent.run ---
        try:
            from smolagents.agents import CodeAgent

            self._originals["CodeAgent.run"] = CodeAgent.run
            CodeAgent.run = self._wrap_agent_run(CodeAgent.run, "CodeAgent")
        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch CodeAgent.run: %s", exc)

        # --- Patch MultiStepAgent.run (base class, catches other agent types) ---
        try:
            from smolagents.agents import MultiStepAgent

            if "ToolCallingAgent.run" not in self._originals or \
               "CodeAgent.run" not in self._originals:
                # Only patch base if specific subclasses are not available
                pass
            # Patch the step execution method for step-level telemetry
            if hasattr(MultiStepAgent, "execute_step"):
                self._originals["MultiStepAgent.execute_step"] = (
                    MultiStepAgent.execute_step
                )
                MultiStepAgent.execute_step = self._wrap_execute_step(
                    MultiStepAgent.execute_step
                )
            elif hasattr(MultiStepAgent, "step"):
                self._originals["MultiStepAgent.step"] = MultiStepAgent.step
                MultiStepAgent.step = self._wrap_execute_step(
                    MultiStepAgent.step
                )
        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch MultiStepAgent step method: %s", exc)

        # --- Patch Tool.__call__ ---
        try:
            from smolagents.tools import Tool

            self._originals["Tool.__call__"] = Tool.__call__
            Tool.__call__ = self._wrap_tool_call(Tool.__call__)
        except (ImportError, AttributeError) as exc:
            logger.debug("Could not patch Tool.__call__: %s", exc)

        # --- Patch Model.__call__ for LLM call tracking ---
        self._patch_model_classes()

        self._instrumented = True
        logger.info(
            "Smolagents instrumentor activated (version=%s, capture_content=%s)",
            smol_version,
            self._capture_content,
        )

    def _patch_model_classes(self) -> None:
        """Patch known smolagents model classes to capture LLM calls."""
        model_classes_to_patch = []

        # Try to import various model classes
        try:
            from smolagents.models import HfApiModel

            model_classes_to_patch.append(("HfApiModel", HfApiModel))
        except (ImportError, AttributeError):
            pass

        try:
            from smolagents.models import LiteLLMModel

            model_classes_to_patch.append(("LiteLLMModel", LiteLLMModel))
        except (ImportError, AttributeError):
            pass

        try:
            from smolagents.models import TransformersModel

            model_classes_to_patch.append(("TransformersModel", TransformersModel))
        except (ImportError, AttributeError):
            pass

        try:
            from smolagents.models import OpenAIServerModel

            model_classes_to_patch.append(("OpenAIServerModel", OpenAIServerModel))
        except (ImportError, AttributeError):
            pass

        # Fall back to the base Model class if no specific classes found
        if not model_classes_to_patch:
            try:
                from smolagents.models import Model

                model_classes_to_patch.append(("Model", Model))
            except (ImportError, AttributeError):
                pass

        for class_name, model_cls in model_classes_to_patch:
            call_method = "__call__"
            if hasattr(model_cls, "__call__"):
                key = f"{class_name}.__call__"
                self._originals[key] = model_cls.__call__
                model_cls.__call__ = self._wrap_model_call(
                    model_cls.__call__, class_name
                )

    def uninstrument(self) -> None:
        """Remove all monkey-patches and restore original methods."""
        if not self._instrumented:
            logger.debug("Smolagents instrumentor is not active; nothing to undo.")
            return

        try:
            import smolagents
        except ImportError:
            self._instrumented = False
            self._originals.clear()
            return

        # Build a map from patch key to (module_path, class, attr)
        restore_map: Dict[str, Tuple[Any, str]] = {}

        try:
            from smolagents.agents import ToolCallingAgent

            restore_map["ToolCallingAgent.run"] = (ToolCallingAgent, "run")
        except (ImportError, AttributeError):
            pass

        try:
            from smolagents.agents import CodeAgent

            restore_map["CodeAgent.run"] = (CodeAgent, "run")
        except (ImportError, AttributeError):
            pass

        try:
            from smolagents.agents import MultiStepAgent

            restore_map["MultiStepAgent.execute_step"] = (
                MultiStepAgent,
                "execute_step",
            )
            restore_map["MultiStepAgent.step"] = (MultiStepAgent, "step")
        except (ImportError, AttributeError):
            pass

        try:
            from smolagents.tools import Tool

            restore_map["Tool.__call__"] = (Tool, "__call__")
        except (ImportError, AttributeError):
            pass

        # Restore model classes
        for key in list(self._originals.keys()):
            if key.endswith(".__call__") and key not in restore_map:
                # Model class patches
                class_name = key.replace(".__call__", "")
                try:
                    from smolagents import models as smol_models

                    cls = getattr(smol_models, class_name, None)
                    if cls is not None:
                        restore_map[key] = (cls, "__call__")
                except (ImportError, AttributeError):
                    pass

        for key, (cls, attr_name) in restore_map.items():
            original = self._originals.get(key)
            if original is not None:
                setattr(cls, attr_name, original)

        self._originals.clear()
        self._instrumented = False
        logger.info(
            "Smolagents instrumentor deactivated -- original methods restored."
        )

    # ------------------------------------------------------------------
    # Wrapper factories
    # ------------------------------------------------------------------

    def _wrap_agent_run(
        self, original_fn: Callable[..., Any], agent_type: str
    ) -> Callable[..., Any]:
        """Create the patched ``Agent.run()`` method.

        Wraps the full agent execution in a ``TASK`` span.
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_run(agent_self: Any, *args: Any, **kwargs: Any) -> Any:
            # Extract task from first positional arg or 'task' kwarg
            task = ""
            if args:
                task = _safe_str(args[0], max_len=1024)
            elif "task" in kwargs:
                task = _safe_str(kwargs["task"], max_len=1024)

            model_name = _extract_model_name(agent_self)
            tool_names = _extract_tool_names(agent_self)
            max_steps = getattr(agent_self, "max_steps", None)
            agent_name = getattr(agent_self, "name", None) or agent_type

            task_label = f"smolagents.{agent_type}.{agent_name}"

            with instrumentor._tracer.start_task(task_name=task_label) as span:
                span.set_attribute(ATTR_SMOL_AGENT_TYPE, agent_type)
                span.set_attribute(ATTR_AGENT_TASK, task_label)
                span.set_attribute(ATTR_LLM_MODEL, model_name)

                if tool_names:
                    span.set_attribute(ATTR_SMOL_TOOL_NAMES, tool_names)
                if max_steps is not None:
                    span.set_attribute(ATTR_SMOL_MAX_STEPS, int(max_steps))

                if instrumentor._capture_content and task:
                    span.set_attribute(ATTR_SMOL_TASK, task)

                span.add_event(
                    "agent_start",
                    EventType.AGENT_START,
                    agent_type=agent_type,
                    tools=tool_names,
                )

                instrumentor._metrics.increment(
                    "agent.task.count", framework="smolagents"
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
                        "agent.error.count", framework="smolagents"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                # Extract step logs for post-hoc step span creation
                step_logs = getattr(agent_self, "logs", None) or getattr(
                    agent_self, "step_logs", None
                )
                total_steps = 0
                if step_logs and isinstance(step_logs, (list, tuple)):
                    total_steps = len(step_logs)
                    for step_idx, step_log in enumerate(step_logs):
                        instrumentor._emit_step_span(
                            agent_type, step_idx + 1, step_log
                        )

                span.set_attribute(ATTR_SMOL_TOTAL_STEPS, total_steps)

                if instrumentor._capture_content and result is not None:
                    span.set_attribute("smolagents.result", _safe_str(result))

                span.add_event(
                    "agent_end",
                    EventType.AGENT_END,
                    agent_type=agent_type,
                    total_steps=total_steps,
                    duration_ms=duration_ms,
                )

                instrumentor._metrics.record(
                    "agent.task.duration_ms", duration_ms, framework="smolagents"
                )

                return result

        return _patched_run

    def _emit_step_span(
        self, agent_type: str, step_number: int, step_log: Any
    ) -> None:
        """Emit a REASONING span for a completed agent step.

        Called post-hoc after the agent run completes, using the step logs
        that smolagents accumulates during execution.
        """
        info = _extract_step_log_info(step_log)
        step_type = info.get("action_type", "step")

        # Determine the span kind based on content
        is_code_step = agent_type == "CodeAgent" and info.get("code")

        with self._tracer.start_reasoning(
            name=f"smolagents.step_{step_number}"
        ) as step_span:
            step_span.set_attribute(ATTR_SMOL_STEP_NUMBER, step_number)
            step_span.set_attribute(ATTR_SMOL_AGENT_TYPE, agent_type)
            step_span.set_attribute(ATTR_SMOL_STEP_TYPE, step_type)

            # Code generation (CodeAgent)
            if is_code_step:
                step_span.set_attribute(ATTR_SMOL_STEP_TYPE, "code_generation")
                if self._capture_content:
                    step_span.set_attribute(ATTR_SMOL_CODE, _safe_str(info["code"]))
                step_span.add_event(
                    "code_generation",
                    EventType.AGENT_MESSAGE,
                    step=step_number,
                    phase="code_generation",
                )

            # Code output
            if self._capture_content and info.get("observations"):
                step_span.set_attribute(
                    ATTR_SMOL_OBSERVATIONS, _safe_str(info["observations"])
                )

            # Tool calls within the step
            tool_calls = info.get("tool_calls")
            if tool_calls and isinstance(tool_calls, (list, tuple)):
                for tc in tool_calls:
                    tc_name = "unknown"
                    tc_input = {}
                    if isinstance(tc, dict):
                        tc_name = tc.get("name", "unknown")
                        tc_input = tc.get("arguments", tc.get("input", {}))
                    elif hasattr(tc, "name"):
                        tc_name = getattr(tc, "name", "unknown")
                        tc_input = getattr(
                            tc, "arguments", getattr(tc, "input", {})
                        )
                    step_span.add_event(
                        "tool_call_in_step",
                        EventType.TOOL_START,
                        tool=str(tc_name),
                        step=step_number,
                    )

            # Token usage at step level
            token_usage = info.get("token_usage")
            if token_usage and isinstance(token_usage, dict):
                inp = token_usage.get("input_tokens", 0) or token_usage.get(
                    "prompt_tokens", 0
                )
                out = token_usage.get("output_tokens", 0) or token_usage.get(
                    "completion_tokens", 0
                )
                if inp or out:
                    step_span.set_attribute(ATTR_LLM_INPUT_TOKENS, int(inp))
                    step_span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, int(out))

            # Errors
            if info.get("error"):
                step_span.set_status(SpanStatus.ERROR, str(info["error"]))
                step_span.add_event(
                    "step_error",
                    EventType.ERROR,
                    error=str(info["error"]),
                    step=step_number,
                )

            step_span.add_event(
                "step_end",
                EventType.AGENT_MESSAGE,
                step=step_number,
                step_type=step_type,
            )

    def _wrap_execute_step(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched ``MultiStepAgent.execute_step()`` method.

        Each step invocation is wrapped in a ``REASONING`` span for
        real-time step-level telemetry (complementing the post-hoc
        step extraction in ``_wrap_agent_run``).
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_execute_step(
            agent_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            agent_type = type(agent_self).__name__
            step_number = getattr(agent_self, "step_number", None)
            if step_number is None:
                # Try to infer from logs length
                logs = getattr(agent_self, "logs", None) or getattr(
                    agent_self, "step_logs", None
                )
                step_number = (len(logs) + 1) if logs else 1

            with instrumentor._tracer.start_reasoning(
                name=f"smolagents.execute_step_{step_number}"
            ) as span:
                span.set_attribute(ATTR_SMOL_STEP_NUMBER, step_number)
                span.set_attribute(ATTR_SMOL_AGENT_TYPE, agent_type)

                span.add_event(
                    "step_start",
                    EventType.AGENT_MESSAGE,
                    step=step_number,
                    agent_type=agent_type,
                )

                start_ns = time.time_ns()

                try:
                    result = original_fn(agent_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "step_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="smolagents"
                    )
                    raise

                duration_ms = (time.time_ns() - start_ns) / 1_000_000

                # Extract info from the step result
                if result is not None:
                    info = _extract_step_log_info(result)

                    if info.get("code") and instrumentor._capture_content:
                        span.set_attribute(ATTR_SMOL_CODE, _safe_str(info["code"]))

                    if info.get("observations") and instrumentor._capture_content:
                        span.set_attribute(
                            ATTR_SMOL_OBSERVATIONS,
                            _safe_str(info["observations"]),
                        )

                span.add_event(
                    "step_end",
                    EventType.AGENT_MESSAGE,
                    step=step_number,
                    duration_ms=duration_ms,
                )

                return result

        return _patched_execute_step

    def _wrap_tool_call(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Create the patched ``Tool.__call__`` method.

        Each tool invocation is wrapped in a ``TOOL_CALL`` span.
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_tool_call(
            tool_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            tool_name = getattr(tool_self, "name", None) or type(
                tool_self
            ).__name__
            tool_desc = getattr(tool_self, "description", "")

            with instrumentor._tracer.start_tool_call(
                tool_name=str(tool_name)
            ) as span:
                if tool_desc:
                    span.set_attribute("tool.description", _safe_str(tool_desc, 512))

                if instrumentor._capture_content:
                    if args:
                        span.set_attribute(ATTR_TOOL_INPUT, _safe_json(args))
                    elif kwargs:
                        span.set_attribute(ATTR_TOOL_INPUT, _safe_json(kwargs))

                span.add_event(
                    "tool_start", EventType.TOOL_START, tool=str(tool_name)
                )

                start_ns = time.time_ns()

                try:
                    result = original_fn(tool_self, *args, **kwargs)
                except Exception as exc:
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_TOOL_SUCCESS, False)
                    span.set_attribute(ATTR_TOOL_ERROR, str(exc))
                    span.set_attribute(ATTR_TOOL_LATENCY_MS, latency_ms)
                    span.add_event(
                        "tool_error",
                        EventType.ERROR,
                        error=str(exc),
                        tool=str(tool_name),
                    )
                    instrumentor._record_tool_metrics(
                        tool_name=str(tool_name),
                        latency_ms=latency_ms,
                        success=False,
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_TOOL_LATENCY_MS, latency_ms)
                span.set_attribute(ATTR_TOOL_SUCCESS, True)

                if instrumentor._capture_content and result is not None:
                    span.set_attribute(ATTR_TOOL_OUTPUT, _safe_str(result))

                span.add_event(
                    "tool_end", EventType.TOOL_END, tool=str(tool_name)
                )

                instrumentor._record_tool_metrics(
                    tool_name=str(tool_name),
                    latency_ms=latency_ms,
                    success=True,
                )

                return result

        return _patched_tool_call

    def _wrap_model_call(
        self, original_fn: Callable[..., Any], model_class_name: str
    ) -> Callable[..., Any]:
        """Create the patched ``Model.__call__`` method.

        Each LLM invocation is wrapped in an ``LLM_CALL`` span.
        """
        instrumentor = self

        @functools.wraps(original_fn)
        def _patched_model_call(
            model_self: Any, *args: Any, **kwargs: Any
        ) -> Any:
            # Extract model name from the model instance
            model_name = "unknown"
            for attr in ("model_id", "model_name", "model", "name"):
                val = getattr(model_self, attr, None)
                if val and isinstance(val, str):
                    model_name = val
                    break

            if model_name == "unknown":
                model_name = model_class_name

            start_ns = time.time_ns()

            with instrumentor._tracer.start_llm_call(model=model_name) as span:
                span.set_attribute(ATTR_LLM_PROVIDER, "smolagents")
                span.set_attribute("smolagents.model_class", model_class_name)

                # Capture prompt content
                if instrumentor._capture_content:
                    # First arg is typically the messages list
                    if args:
                        span.set_attribute(ATTR_LLM_PROMPT, _safe_str(args[0]))
                    elif "messages" in kwargs:
                        span.set_attribute(
                            ATTR_LLM_PROMPT, _safe_str(kwargs["messages"])
                        )

                span.add_event(
                    "llm_start", EventType.LLM_START, model=model_name
                )

                try:
                    result = original_fn(model_self, *args, **kwargs)
                except Exception as exc:
                    latency_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)
                    span.add_event(
                        "llm_error", EventType.ERROR, error=str(exc)
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", framework="smolagents"
                    )
                    raise

                latency_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_LLM_LATENCY_MS, latency_ms)

                # Extract token usage from the result
                input_tokens = 0
                output_tokens = 0

                # smolagents ChatMessage / model output may carry token info
                if hasattr(result, "token_usage") and result.token_usage:
                    usage = result.token_usage
                    if isinstance(usage, dict):
                        input_tokens = usage.get(
                            "input_tokens", usage.get("prompt_tokens", 0)
                        ) or 0
                        output_tokens = usage.get(
                            "output_tokens",
                            usage.get("completion_tokens", 0),
                        ) or 0

                # Also check the model instance for accumulated usage
                if input_tokens == 0 and output_tokens == 0:
                    last_usage = getattr(model_self, "last_token_usage", None)
                    if last_usage and isinstance(last_usage, dict):
                        input_tokens = last_usage.get(
                            "input_tokens", last_usage.get("prompt_tokens", 0)
                        ) or 0
                        output_tokens = last_usage.get(
                            "output_tokens",
                            last_usage.get("completion_tokens", 0),
                        ) or 0

                span.set_attribute(ATTR_LLM_INPUT_TOKENS, int(input_tokens))
                span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, int(output_tokens))
                span.set_attribute(
                    ATTR_LLM_TOTAL_TOKENS, int(input_tokens + output_tokens)
                )

                # Completion content
                if instrumentor._capture_content and result is not None:
                    content = getattr(result, "content", None)
                    if content:
                        span.set_attribute(ATTR_LLM_COMPLETION, _safe_str(content))
                    else:
                        span.set_attribute(ATTR_LLM_COMPLETION, _safe_str(result))

                span.add_event(
                    "llm_end",
                    EventType.LLM_END,
                    model=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

                cost = estimate_cost(model_name, input_tokens, output_tokens)
                instrumentor._record_llm_metrics(
                    model=model_name,
                    input_tokens=int(input_tokens),
                    output_tokens=int(output_tokens),
                    latency_ms=latency_ms,
                    cost_usd=cost,
                )

                return result

        return _patched_model_call
