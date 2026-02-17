"""CrewAI instrumentor for AgentTelemetry.

Monkey-patches CrewAI's core classes to automatically capture telemetry:

    - ``Crew.kickoff()`` is wrapped in a TASK span (root of the trace).
    - ``Agent.execute_task()`` is wrapped in REASONING spans with agent metadata.
    - ``Task.execute()`` is wrapped to track per-task execution.
    - Delegation between agents is tracked with AGENT_COMM spans.
    - LLM calls made by agents are captured as LLM_CALL spans.

Usage::

    from agenttelemetry.instrumentors.crewai import CrewAIInstrumentor

    instrumentor = CrewAIInstrumentor(capture_content=True)
    instrumentor.instrument()

    # ... use CrewAI normally — telemetry is captured automatically ...

    instrumentor.uninstrument()
"""

from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple

from agenttelemetry.core.events import EventType
from agenttelemetry.core.trace import (
    ATTR_AGENT_NAME,
    ATTR_AGENT_ROLE,
    ATTR_AGENT_TASK,
    ATTR_INTERACTION_SOURCE,
    ATTR_INTERACTION_TARGET,
    ATTR_INTERACTION_TYPE,
    ATTR_LLM_COMPLETION,
    ATTR_LLM_COST_USD,
    ATTR_LLM_INPUT_TOKENS,
    ATTR_LLM_LATENCY_MS,
    ATTR_LLM_MODEL,
    ATTR_LLM_OUTPUT_TOKENS,
    ATTR_LLM_PROMPT,
    ATTR_LLM_TOTAL_TOKENS,
    ATTR_TOOL_NAME,
    ATTR_TOOL_SUCCESS,
    AgentSpanKind,
    SpanStatus,
    estimate_cost,
)
from agenttelemetry.instrumentors.base import BaseInstrumentor

logger = logging.getLogger(__name__)

# Custom attribute keys specific to CrewAI
ATTR_AGENT_GOAL = "agent.goal"
ATTR_AGENT_BACKSTORY = "agent.backstory"
ATTR_CREW_NAME = "crewai.crew.name"
ATTR_CREW_PROCESS = "crewai.crew.process"
ATTR_CREW_NUM_AGENTS = "crewai.crew.num_agents"
ATTR_CREW_NUM_TASKS = "crewai.crew.num_tasks"
ATTR_TASK_DESCRIPTION = "crewai.task.description"
ATTR_TASK_EXPECTED_OUTPUT = "crewai.task.expected_output"
ATTR_TASK_AGENT_ROLE = "crewai.task.agent_role"
ATTR_DELEGATION_FROM = "crewai.delegation.from_agent"
ATTR_DELEGATION_TO = "crewai.delegation.to_agent"
ATTR_DELEGATION_TASK = "crewai.delegation.task_description"


def _safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely retrieve an attribute, returning *default* on any error."""
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default


def _safe_str(value: Any, max_length: int = 4096) -> str:
    """Convert a value to a truncated string, never raising."""
    try:
        text = str(value)
        if len(text) > max_length:
            return text[:max_length] + "...[truncated]"
        return text
    except Exception:
        return "<unserializable>"


def _extract_agent_role(agent: Any) -> str:
    """Extract the role string from a CrewAI Agent object."""
    return _safe_str(_safe_getattr(agent, "role", "unknown_agent"))


def _extract_agent_goal(agent: Any) -> str:
    """Extract the goal string from a CrewAI Agent object."""
    return _safe_str(_safe_getattr(agent, "goal", ""))


def _extract_agent_backstory(agent: Any) -> str:
    """Extract the backstory string from a CrewAI Agent object."""
    return _safe_str(_safe_getattr(agent, "backstory", ""))


def _extract_llm_model(agent: Any) -> str:
    """Best-effort extraction of the model name from a CrewAI agent's LLM."""
    llm = _safe_getattr(agent, "llm", None)
    if llm is None:
        return "unknown"
    # CrewAI stores the model name in several possible locations depending on
    # version and LLM backend.
    for attr in ("model_name", "model", "model_id"):
        name = _safe_getattr(llm, attr, None)
        if name:
            return _safe_str(name)
    return "unknown"


# ---------------------------------------------------------------------------
# Stored originals type alias for readability
# ---------------------------------------------------------------------------
_OriginalMethods = Dict[str, Tuple[Any, str, Callable[..., Any]]]


class CrewAIInstrumentor(BaseInstrumentor):
    """Instruments CrewAI to emit AgentTelemetry spans and metrics.

    Patches applied:
        1. ``Crew.kickoff`` -- TASK span wrapping the entire crew execution.
        2. ``Agent.execute_task`` -- REASONING span per agent/task execution.
        3. ``Task.execute`` -- lightweight wrapper that captures task metadata
           and detects delegation (AGENT_COMM spans).

    All patches are reversible via :meth:`uninstrument`.
    """

    # --------------------------------------------------------------------- #
    # BaseInstrumentor interface
    # --------------------------------------------------------------------- #

    @property
    def framework_name(self) -> str:  # noqa: D401
        return "crewai"

    def instrument(self) -> None:
        """Apply monkey-patches to CrewAI classes."""
        if self._instrumented:
            logger.debug("CrewAI is already instrumented; skipping.")
            return

        try:
            import crewai  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "crewai package is required for CrewAIInstrumentor. "
                "Install it with: pip install crewai"
            ) from exc

        # Store framework version for span attributes
        crewai_version = _safe_str(_safe_getattr(crewai, "__version__", ""))
        if crewai_version:
            self._tracer._framework_version = crewai_version

        # Resolve classes -- imported here so the instrumentor module can be
        # loaded even when crewai is not installed.
        from crewai import Agent, Crew, Task

        self._originals: _OriginalMethods = {}

        # ---- Crew.kickoff ------------------------------------------------
        self._patch_method(Crew, "kickoff", self._wrap_crew_kickoff)

        # ---- Agent.execute_task ------------------------------------------
        self._patch_method(Agent, "execute_task", self._wrap_agent_execute_task)

        # ---- Task.execute ------------------------------------------------
        self._patch_method(Task, "execute", self._wrap_task_execute)

        # ---- LLM call interception ---------------------------------------
        self._patch_llm_calls()

        self._instrumented = True
        logger.info("CrewAI instrumentation applied (crewai %s).", crewai_version)

    def uninstrument(self) -> None:
        """Remove all monkey-patches and restore original methods."""
        if not self._instrumented:
            logger.debug("CrewAI is not instrumented; nothing to remove.")
            return

        for key, (cls, method_name, original_fn) in self._originals.items():
            try:
                setattr(cls, method_name, original_fn)
            except Exception:
                logger.warning("Failed to restore %s.%s", cls.__name__, method_name)

        self._originals.clear()
        self._instrumented = False
        logger.info("CrewAI instrumentation removed.")

    # --------------------------------------------------------------------- #
    # Internal patching helpers
    # --------------------------------------------------------------------- #

    def _patch_method(
        self,
        cls: type,
        method_name: str,
        wrapper_factory: Callable[..., Callable[..., Any]],
    ) -> None:
        """Replace *cls.method_name* with a wrapped version.

        The original is stored in ``self._originals`` for later restoration.
        *wrapper_factory* is called with ``(original_fn,)`` and must return
        the replacement function.
        """
        original = getattr(cls, method_name)
        key = f"{cls.__name__}.{method_name}"
        self._originals[key] = (cls, method_name, original)

        wrapped = wrapper_factory(original)
        # Preserve docstring / introspection
        functools.update_wrapper(wrapped, original)
        setattr(cls, method_name, wrapped)

    # --------------------------------------------------------------------- #
    # Wrapper factories
    # --------------------------------------------------------------------- #

    def _wrap_crew_kickoff(self, original_fn: Callable[..., Any]) -> Callable[..., Any]:
        """Return a patched ``Crew.kickoff`` that wraps execution in a TASK span."""
        instrumentor = self

        def patched_kickoff(crew_self: Any, *args: Any, **kwargs: Any) -> Any:
            crew_name = _safe_str(
                _safe_getattr(crew_self, "name", None)
                or _safe_getattr(crew_self, "crew_name", None)
                or "crew"
            )
            agents = _safe_getattr(crew_self, "agents", []) or []
            tasks = _safe_getattr(crew_self, "tasks", []) or []
            process = _safe_str(_safe_getattr(crew_self, "process", "sequential"))

            task_attrs = {
                ATTR_CREW_NAME: crew_name,
                ATTR_CREW_PROCESS: process,
                ATTR_CREW_NUM_AGENTS: len(agents),
                ATTR_CREW_NUM_TASKS: len(tasks),
            }

            # Record agent roles participating in the crew
            agent_roles = [_extract_agent_role(a) for a in agents]
            task_attrs["crewai.crew.agent_roles"] = ", ".join(agent_roles)

            instrumentor._metrics.increment("agent.task.count")

            with instrumentor._tracer.start_task(
                f"crew.{crew_name}", **task_attrs
            ) as span:
                span.add_event("crew_kickoff_start", EventType.AGENT_START)
                start_ns = time.time_ns()
                try:
                    result = original_fn(crew_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "crew_kickoff_error",
                        EventType.ERROR,
                        error=_safe_str(exc),
                    )
                    instrumentor._metrics.increment("agent.error.count")
                    raise
                finally:
                    elapsed_ms = (time.time_ns() - start_ns) / 1_000_000
                    instrumentor._metrics.record("agent.task.duration_ms", elapsed_ms)
                    span.add_event("crew_kickoff_end", EventType.AGENT_END)

                if instrumentor._capture_content and result is not None:
                    span.set_attribute("crewai.crew.result", _safe_str(result))

                return result

        return patched_kickoff

    def _wrap_agent_execute_task(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Return a patched ``Agent.execute_task`` wrapped in a REASONING span."""
        instrumentor = self

        def patched_execute_task(agent_self: Any, *args: Any, **kwargs: Any) -> Any:
            role = _extract_agent_role(agent_self)
            goal = _extract_agent_goal(agent_self)
            backstory = _extract_agent_backstory(agent_self)
            model = _extract_llm_model(agent_self)

            reasoning_attrs: Dict[str, Any] = {
                ATTR_AGENT_NAME: role,
                ATTR_AGENT_ROLE: role,
            }
            if goal:
                reasoning_attrs[ATTR_AGENT_GOAL] = goal
            if backstory:
                reasoning_attrs[ATTR_AGENT_BACKSTORY] = backstory
            if model != "unknown":
                reasoning_attrs[ATTR_LLM_MODEL] = model

            # Try to extract the task description from the first positional arg
            task_obj = args[0] if args else kwargs.get("task", None)
            task_description = ""
            if task_obj is not None:
                task_description = _safe_str(
                    _safe_getattr(task_obj, "description", "")
                )
                if task_description:
                    reasoning_attrs[ATTR_AGENT_TASK] = task_description

            # Capture content (prompt) only when allowed
            if instrumentor._capture_content and task_description:
                reasoning_attrs[ATTR_TASK_DESCRIPTION] = task_description

            span_name = f"agent.{role}.execute_task"
            with instrumentor._tracer.start_reasoning(
                span_name, **reasoning_attrs
            ) as span:
                span.add_event(
                    "agent_execute_task_start",
                    EventType.AGENT_START,
                    agent_role=role,
                )

                start_ns = time.time_ns()
                try:
                    result = original_fn(agent_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "agent_execute_task_error",
                        EventType.ERROR,
                        agent_role=role,
                        error=_safe_str(exc),
                    )
                    instrumentor._metrics.increment(
                        "agent.error.count", agent=role
                    )
                    raise
                finally:
                    elapsed_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.add_event(
                        "agent_execute_task_end",
                        EventType.AGENT_END,
                        agent_role=role,
                        duration_ms=elapsed_ms,
                    )

                # Capture output content when allowed
                if instrumentor._capture_content and result is not None:
                    span.set_attribute(
                        "crewai.agent.output", _safe_str(result)
                    )

                # Detect delegation: if the result comes from a different agent,
                # record an AGENT_COMM span.  CrewAI's TaskOutput/AgentFinish
                # sometimes carries metadata about delegation.
                instrumentor._detect_delegation(
                    span, agent_self, result
                )

                return result

        return patched_execute_task

    def _wrap_task_execute(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Return a patched ``Task.execute`` that adds task-level metadata."""
        instrumentor = self

        def patched_task_execute(task_self: Any, *args: Any, **kwargs: Any) -> Any:
            description = _safe_str(
                _safe_getattr(task_self, "description", "task")
            )
            expected_output = _safe_str(
                _safe_getattr(task_self, "expected_output", "")
            )
            agent = _safe_getattr(task_self, "agent", None)
            agent_role = _extract_agent_role(agent) if agent else "unassigned"

            reasoning_attrs: Dict[str, Any] = {
                ATTR_TASK_AGENT_ROLE: agent_role,
                ATTR_AGENT_NAME: agent_role,
            }
            if instrumentor._capture_content:
                reasoning_attrs[ATTR_TASK_DESCRIPTION] = description
                if expected_output:
                    reasoning_attrs[ATTR_TASK_EXPECTED_OUTPUT] = expected_output

            span_name = f"task.{agent_role}.execute"
            with instrumentor._tracer.start_reasoning(
                span_name, **reasoning_attrs
            ) as span:
                span.add_event(
                    "task_execute_start",
                    EventType.AGENT_START,
                    task_description=description[:256],
                    agent_role=agent_role,
                )

                # Check for delegation: if the task's agent differs from the
                # agent that was *originally* assigned, record delegation.
                context_agents = _safe_getattr(task_self, "context", None)
                delegated_agent = kwargs.get("agent", None)
                if delegated_agent is not None and agent is not None:
                    delegated_role = _extract_agent_role(delegated_agent)
                    if delegated_role != agent_role:
                        instrumentor._record_delegation(
                            span,
                            source_role=agent_role,
                            target_role=delegated_role,
                            task_description=description,
                        )

                start_ns = time.time_ns()
                try:
                    result = original_fn(task_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "task_execute_error",
                        EventType.ERROR,
                        error=_safe_str(exc),
                    )
                    instrumentor._metrics.increment("agent.error.count")
                    raise
                finally:
                    elapsed_ms = (time.time_ns() - start_ns) / 1_000_000
                    span.add_event(
                        "task_execute_end",
                        EventType.AGENT_END,
                        duration_ms=elapsed_ms,
                    )

                if instrumentor._capture_content and result is not None:
                    span.set_attribute(
                        "crewai.task.output", _safe_str(result)
                    )

                return result

        return patched_task_execute

    # --------------------------------------------------------------------- #
    # LLM call patching
    # --------------------------------------------------------------------- #

    def _patch_llm_calls(self) -> None:
        """Patch CrewAI's internal LLM invocation path to capture LLM_CALL spans.

        CrewAI wraps LLM calls through ``crewai.llm.LLM.call`` (v0.30+) or
        through LiteLLM's ``completion`` function (older versions).  We try
        both paths so the instrumentor works across versions.
        """
        # Strategy 1: patch crewai.llm.LLM.call (CrewAI >= 0.30)
        try:
            from crewai.llm import LLM as CrewLLM

            if hasattr(CrewLLM, "call"):
                self._patch_method(CrewLLM, "call", self._wrap_llm_call)
                logger.debug("Patched crewai.llm.LLM.call for LLM tracing.")
                return
        except (ImportError, AttributeError):
            pass

        # Strategy 2: patch litellm.completion used by CrewAI
        try:
            import litellm

            if hasattr(litellm, "completion"):
                self._patch_method(
                    litellm,  # type: ignore[arg-type]
                    "completion",
                    self._wrap_litellm_completion,
                )
                logger.debug("Patched litellm.completion for LLM tracing.")
                return
        except (ImportError, AttributeError):
            pass

        logger.debug(
            "Could not locate CrewAI LLM call path; LLM spans will not be "
            "captured.  Agent and task spans are still active."
        )

    def _wrap_llm_call(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Wrap ``crewai.llm.LLM.call`` in an LLM_CALL span."""
        instrumentor = self

        def patched_llm_call(llm_self: Any, *args: Any, **kwargs: Any) -> Any:
            model = _safe_str(
                _safe_getattr(llm_self, "model", None)
                or _safe_getattr(llm_self, "model_name", "unknown")
            )

            # Extract prompt content when capture is enabled
            prompt_messages = args[0] if args else kwargs.get("messages", None)

            with instrumentor._tracer.start_llm_call(model=model) as span:
                if instrumentor._capture_content and prompt_messages is not None:
                    span.set_attribute(ATTR_LLM_PROMPT, _safe_str(prompt_messages))

                span.add_event("llm_call_start", EventType.LLM_START, model=model)
                start_ns = time.time_ns()

                try:
                    response = original_fn(llm_self, *args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "llm_call_error", EventType.ERROR, error=_safe_str(exc)
                    )
                    instrumentor._metrics.increment("agent.error.count")
                    raise

                elapsed_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_LLM_LATENCY_MS, elapsed_ms)

                # Extract token usage from the response
                instrumentor._extract_llm_usage(span, response, model, elapsed_ms)

                if instrumentor._capture_content and response is not None:
                    completion_text = instrumentor._extract_completion_text(response)
                    if completion_text:
                        span.set_attribute(ATTR_LLM_COMPLETION, completion_text)

                span.add_event("llm_call_end", EventType.LLM_END, model=model)
                return response

        return patched_llm_call

    def _wrap_litellm_completion(
        self, original_fn: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Wrap ``litellm.completion`` in an LLM_CALL span."""
        instrumentor = self

        def patched_completion(*args: Any, **kwargs: Any) -> Any:
            model = _safe_str(kwargs.get("model", args[0] if args else "unknown"))

            messages = kwargs.get("messages", None)

            with instrumentor._tracer.start_llm_call(model=model) as span:
                if instrumentor._capture_content and messages is not None:
                    span.set_attribute(ATTR_LLM_PROMPT, _safe_str(messages))

                span.add_event("llm_call_start", EventType.LLM_START, model=model)
                start_ns = time.time_ns()

                try:
                    response = original_fn(*args, **kwargs)
                except Exception as exc:
                    span.set_status(SpanStatus.ERROR, str(exc))
                    span.add_event(
                        "llm_call_error", EventType.ERROR, error=_safe_str(exc)
                    )
                    instrumentor._metrics.increment("agent.error.count")
                    raise

                elapsed_ms = (time.time_ns() - start_ns) / 1_000_000
                span.set_attribute(ATTR_LLM_LATENCY_MS, elapsed_ms)

                instrumentor._extract_llm_usage(span, response, model, elapsed_ms)

                if instrumentor._capture_content and response is not None:
                    completion_text = instrumentor._extract_completion_text(response)
                    if completion_text:
                        span.set_attribute(ATTR_LLM_COMPLETION, completion_text)

                span.add_event("llm_call_end", EventType.LLM_END, model=model)
                return response

        return patched_completion

    # --------------------------------------------------------------------- #
    # LLM usage extraction
    # --------------------------------------------------------------------- #

    def _extract_llm_usage(
        self,
        span: Any,
        response: Any,
        model: str,
        latency_ms: float,
    ) -> None:
        """Extract token counts from an LLM response and record metrics."""
        usage = _safe_getattr(response, "usage", None)
        if usage is None:
            # Some responses nest usage inside a dict
            if isinstance(response, dict):
                usage = response.get("usage", None)
            if usage is None:
                return

        if isinstance(usage, dict):
            input_tokens = usage.get("prompt_tokens", 0) or 0
            output_tokens = usage.get("completion_tokens", 0) or 0
            total_tokens = usage.get("total_tokens", 0) or (
                input_tokens + output_tokens
            )
        else:
            input_tokens = _safe_getattr(usage, "prompt_tokens", 0) or 0
            output_tokens = _safe_getattr(usage, "completion_tokens", 0) or 0
            total_tokens = _safe_getattr(usage, "total_tokens", 0) or (
                input_tokens + output_tokens
            )

        span.set_attribute(ATTR_LLM_INPUT_TOKENS, input_tokens)
        span.set_attribute(ATTR_LLM_OUTPUT_TOKENS, output_tokens)
        span.set_attribute(ATTR_LLM_TOTAL_TOKENS, total_tokens)

        cost = estimate_cost(model, input_tokens, output_tokens)
        if cost > 0:
            span.set_attribute(ATTR_LLM_COST_USD, cost)

        # Record aggregate metrics
        self._record_llm_metrics(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )

    @staticmethod
    def _extract_completion_text(response: Any) -> str:
        """Best-effort extraction of the completion text from an LLM response."""
        # LiteLLM / OpenAI-style response object
        choices = _safe_getattr(response, "choices", None)
        if choices and len(choices) > 0:
            message = _safe_getattr(choices[0], "message", None)
            if message:
                content = _safe_getattr(message, "content", None)
                if content:
                    return _safe_str(content)
        # Plain string response (some CrewAI versions return str directly)
        if isinstance(response, str):
            return _safe_str(response)
        # Dict-style response
        if isinstance(response, dict):
            choices_list = response.get("choices", [])
            if choices_list:
                msg = choices_list[0].get("message", {})
                return _safe_str(msg.get("content", ""))
        return ""

    # --------------------------------------------------------------------- #
    # Delegation detection
    # --------------------------------------------------------------------- #

    def _detect_delegation(
        self,
        parent_span: Any,
        agent: Any,
        result: Any,
    ) -> None:
        """Detect if a delegation occurred during agent execution.

        CrewAI's delegation mechanism lets one agent hand off work to another.
        When this happens, the result or internal state may reference the
        delegated agent.  We inspect known patterns to emit an AGENT_COMM span.
        """
        if result is None:
            return

        source_role = _extract_agent_role(agent)

        # Pattern 1: result has a ``delegations`` attribute (CrewAI >= 0.40)
        delegations = _safe_getattr(result, "delegations", None)
        if delegations and isinstance(delegations, (list, tuple)):
            for delegation in delegations:
                target_role = _safe_str(
                    _safe_getattr(delegation, "agent_role", None)
                    or _safe_getattr(delegation, "coworker", "unknown")
                )
                task_desc = _safe_str(
                    _safe_getattr(delegation, "task", "delegated task")
                )
                self._record_delegation(
                    parent_span,
                    source_role=source_role,
                    target_role=target_role,
                    task_description=task_desc,
                )
            return

        # Pattern 2: result is a string containing delegation markers
        result_str = _safe_str(result) if not isinstance(result, str) else result
        if "delegate" in result_str.lower() or "coworker" in result_str.lower():
            # CrewAI often formats delegation as:
            #   "Action: Delegate work to co-worker"
            #   "Action Input: {coworker: ..., task: ...}"
            # We mark this as a delegation event even if we can't parse
            # the exact target.
            parent_span.add_event(
                "delegation_detected",
                EventType.AGENT_MESSAGE,
                source_agent=source_role,
            )

    def _record_delegation(
        self,
        parent_span: Any,
        source_role: str,
        target_role: str,
        task_description: str = "",
    ) -> None:
        """Record a delegation between agents as an AGENT_COMM span."""
        comm_attrs: Dict[str, Any] = {
            ATTR_INTERACTION_TYPE: "delegation",
            ATTR_DELEGATION_FROM: source_role,
            ATTR_DELEGATION_TO: target_role,
        }
        if self._capture_content and task_description:
            comm_attrs[ATTR_DELEGATION_TASK] = task_description

        with self._tracer.start_agent_comm(
            target_agent=target_role, **comm_attrs
        ) as comm_span:
            comm_span.set_attribute(ATTR_INTERACTION_SOURCE, source_role)
            comm_span.add_event(
                "delegation",
                EventType.AGENT_MESSAGE,
                source_agent=source_role,
                target_agent=target_role,
            )
            self._metrics.increment(
                "agent.delegation.count",
                source=source_role,
                target=target_role,
            )

        # Also annotate the parent span
        parent_span.add_event(
            "delegation",
            EventType.AGENT_MESSAGE,
            source_agent=source_role,
            target_agent=target_role,
        )
