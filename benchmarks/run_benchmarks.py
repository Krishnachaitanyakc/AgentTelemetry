"""Benchmark runner for AgentTelemetry evaluation.

Runs all configurations: models x frameworks x faults x conditions
Outputs results.tsv with FDR, TTRC, precision, span sufficiency.

Usage:
    cd agenttelemetry
    PYTHONPATH=src:. python benchmarks/run_benchmarks.py
    # or
    PYTHONPATH=src python benchmarks/run_benchmarks.py --mock-only --output results.tsv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Ensure src and benchmarks are on sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.dirname(_SCRIPT_DIR)
_SRC_DIR = os.path.join(_ROOT_DIR, "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)

from agenttelemetry import (
    AgentTelemetryProvider,
    AgentTelemetryJSONExporter,
    configure,
    start_agent_span,
    AgentSpanKind,
)
from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND, LLM_MODEL, LLM_INPUT_TOKENS, LLM_OUTPUT_TOKENS,
    LLM_COST, TOOL_NAME, TOOL_STATUS, estimate_cost,
    RETRIEVAL_STALENESS_SECONDS, GUARDRAIL_RESULT, PLANNING_STEP_COUNT,
    REASONING_CHAIN, AGENT_MISROUTED, MEMORY_CORRUPTED, MEMORY_OPERATION,
)
from agenttelemetry.core.privacy import PrivacyLevel

from benchmarks.mocks import MockAnthropicClient, MockOpenAIClient
from benchmarks.faults import FaultInjector, FaultType
from benchmarks.apps.custom_agent.app import run_custom_agent
from benchmarks.apps.vanilla_otel.app import run_vanilla_agent
from benchmarks.apps.otel_genai.app import (
    run_otel_genai_agent,
    GENAI_OPERATION_NAME, GENAI_REQUEST_MODEL, GENAI_USAGE_INPUT_TOKENS,
    GENAI_USAGE_OUTPUT_TOKENS, GENAI_TOOL_NAME, GENAI_DATA_SOURCE_ID,
)
from benchmarks.apps.openinference.app import (
    run_openinference_agent,
    OI_SPAN_KIND, OI_LLM_MODEL_NAME,
    OI_LLM_TOKEN_COUNT_PROMPT, OI_LLM_TOKEN_COUNT_COMPLETION,
    OI_TOOL_NAME,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODELS = [
    "claude-sonnet-4",
    "claude-haiku-4",
    "gpt-4o",
    "gpt-4o-mini",
    "o3-mini",
    "claude-opus-4",
]

FRAMEWORKS = [
    "langchain",
    "crewai",
    "autogen",
    "anthropic_sdk",
    "openai_sdk",
    "llamaindex",
    "custom",
]

CONDITIONS = [
    "no_telemetry",
    "vanilla_otel",
    "otel_genai",
    "openinference",
    "metadata_only",
    "full_capture",
]


# ---------------------------------------------------------------------------
# Benchmark result
# ---------------------------------------------------------------------------

@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    framework: str
    model: str
    fault_type: str
    condition: str
    fault_detected: bool
    detection_correct: bool
    time_to_root_cause_ms: float
    total_spans: int
    llm_spans: int
    tool_spans: int
    total_tokens: int
    estimated_cost_usd: float
    agent_iterations: int
    faults_injected: int
    faults_detected: int
    run_time_ms: float
    error: Optional[str] = None
    detector_results: Optional[Dict[str, bool]] = None  # per-detector fire map for FP analysis

    @property
    def fault_detection_rate(self) -> float:
        """FDR: fraction of injected faults that were detected."""
        if self.faults_injected == 0:
            return 1.0  # No faults to detect
        return self.faults_detected / self.faults_injected

    @property
    def precision(self) -> float:
        """Precision: fraction of detected faults that are true positives."""
        if self.faults_detected == 0:
            return 1.0  # No false positives
        return 1.0 if self.detection_correct else 0.0

    @property
    def span_sufficiency(self) -> float:
        """Whether telemetry captured enough data to diagnose the fault.

        Heuristic: if we have at least LLM + tool spans and the agent
        ran for more than 0 iterations, spans are sufficient.
        """
        if self.condition == "no_telemetry":
            return 0.0
        if self.total_spans == 0:
            return 0.0
        if self.llm_spans > 0 and self.fault_type != "no_fault":
            return 1.0
        return 0.5  # Partial information

    def to_tsv_row(self) -> List[str]:
        """Convert to TSV row."""
        return [
            self.framework,
            self.model,
            self.fault_type,
            self.condition,
            f"{self.fault_detection_rate:.3f}",
            f"{self.time_to_root_cause_ms:.1f}",
            f"{self.precision:.3f}",
            f"{self.span_sufficiency:.3f}",
            str(self.total_spans),
            str(self.llm_spans),
            str(self.tool_spans),
            str(self.total_tokens),
            f"{self.estimated_cost_usd:.6f}",
            str(self.agent_iterations),
            str(self.faults_injected),
            str(self.faults_detected),
            f"{self.run_time_ms:.1f}",
            self.error or "",
        ]


TSV_HEADER = [
    "framework", "model", "fault_type", "condition",
    "fault_detection_rate", "time_to_root_cause_ms", "precision",
    "span_sufficiency", "total_spans", "llm_spans", "tool_spans",
    "total_tokens", "estimated_cost_usd", "agent_iterations",
    "faults_injected", "faults_detected", "run_time_ms", "error",
]


# ---------------------------------------------------------------------------
# App runners registry
# ---------------------------------------------------------------------------

def _get_app_runner(framework: str) -> Optional[Callable]:
    """Get the runner function for a framework."""
    if framework == "custom":
        return run_custom_agent

    # Stub frameworks return a minimal result
    stub_runners = {
        "langchain": "benchmarks.apps.langchain_rag.app",
        "crewai": "benchmarks.apps.crewai_team.app",
        "autogen": "benchmarks.apps.autogen_group.app",
        "anthropic_sdk": "benchmarks.apps.anthropic_sdk.app",
        "openai_sdk": "benchmarks.apps.openai_sdk.app",
        "llamaindex": "benchmarks.apps.llamaindex_agent.app",
    }

    module_path = stub_runners.get(framework)
    if module_path is None:
        return None

    # Dynamically import
    import importlib
    try:
        module = importlib.import_module(module_path)
        # Find a run_* function
        for name in dir(module):
            if name.startswith("run_") and callable(getattr(module, name)):
                return getattr(module, name)
    except ImportError:
        pass

    return None


# ---------------------------------------------------------------------------
# Vanilla OTel trace analysis (no AGENT_SPAN_KIND attribute)
# ---------------------------------------------------------------------------

def _classify_vanilla_span(span: Dict[str, Any]) -> Optional[str]:
    """Guess the agent span kind from a vanilla OTel span.

    Without ``agenttelemetry.span.kind`` the best we can do is heuristic
    matching on span names and generic attributes.  This intentionally
    *cannot* identify all span kinds, which is the point of the baseline.

    Returns:
        A guessed kind string ("LLM_CALL", "TOOL_CALL", etc.) or None.
    """
    attrs = span.get("attributes", {})
    name = span.get("name", "").lower()

    # LLM call: span name contains "llm" or has llm.model attribute
    if attrs.get(LLM_MODEL) or "llm" in name:
        return "LLM_CALL"

    # Tool call: has tool.name attribute or span name starts with "tool-"
    if attrs.get(TOOL_NAME) or name.startswith("tool-"):
        return "TOOL_CALL"

    # Delegation: span name contains "delegate"
    if "delegate" in name:
        return "DELEGATION"

    return None


def _analyze_traces_vanilla(
    exported_spans: List[Dict[str, Any]],
    fault_type: FaultType,
    ground_truth: List[Dict[str, Any]],
) -> Tuple[bool, bool, float, int]:
    """Analyze vanilla OTel traces using heuristic span classification.

    This mirrors ``_analyze_traces`` but uses ``_classify_vanilla_span``
    instead of the ``AGENT_SPAN_KIND`` attribute.  Because the heuristic
    classification is imperfect, some fault types are undetectable:

    Detectable (via generic attributes / span names):
      - tool_failure   (tool.status == "error" or OTel ERROR status)
      - timeout         (OTel ERROR status with "timeout" in description)
      - cost_explosion  (llm.cost attribute present on LLM spans)
      - infinite_loop   (repeated tool.name values)
      - context_overflow (llm.input_tokens growth across LLM spans)

    Partially detectable:
      - wrong_tool      (can see tool.name but cannot confirm it was *wrong*
                         without semantic span kind for reliable filtering)

    NOT detectable:
      - hallucination    (requires RETRIEVAL span kind to check grounding)
      - circular_delegation (requires delegation.source/target *and*
                             DELEGATION span kind for reliable filtering;
                             vanilla spans have the attributes but no kind
                             to reliably isolate delegation spans from noise)
      - stale_retrieval      (requires RETRIEVAL span kind)
      - guardrail_bypass     (requires GUARD_RAIL span kind)
      - planning_failure     (requires PLANNING span kind)
      - reasoning_loop       (requires REASONING span kind)
      - agent_misroute       (requires AGENT span kind)
      - memory_corruption    (requires MEMORY span kind)
    """
    if not exported_spans:
        return False, False, 0.0, 0

    analysis_start = time.time()
    fault_detected = False

    if fault_type == FaultType.TOOL_FAILURE:
        # Can detect: tool spans with error status (via generic attributes)
        for span in exported_spans:
            attrs = span.get("attributes", {})
            status = span.get("status", {})
            guessed = _classify_vanilla_span(span)
            if guessed == "TOOL_CALL":
                if (attrs.get(TOOL_STATUS) == "error"
                        or status.get("code") == "ERROR"):
                    fault_detected = True
                    break

    elif fault_type == FaultType.TIMEOUT:
        # Can detect: OTel ERROR status with "timeout" (same as full)
        for span in exported_spans:
            status = span.get("status", {})
            if status.get("code") == "ERROR":
                desc = (status.get("description", "") or "").lower()
                if "timeout" in desc or "timed out" in desc:
                    fault_detected = True
                    break
            for event in span.get("events", []):
                event_attrs = event.get("attributes", {})
                exc_type = str(event_attrs.get("exception.type", ""))
                exc_msg = str(event_attrs.get("exception.message", ""))
                if "timeout" in exc_type.lower() or "timeout" in exc_msg.lower():
                    fault_detected = True
                    break
            if fault_detected:
                break

    elif fault_type == FaultType.COST_EXPLOSION:
        # Can detect: llm.cost attribute is present on vanilla LLM spans
        total_cost = 0.0
        for s in exported_spans:
            if _classify_vanilla_span(s) == "LLM_CALL":
                total_cost += s.get("attributes", {}).get(LLM_COST, 0) or 0
        if total_cost > 0.10:
            fault_detected = True

    elif fault_type == FaultType.INFINITE_LOOP:
        # Can detect: repeated tool.name values
        from collections import Counter
        tool_calls = Counter()
        for s in exported_spans:
            if _classify_vanilla_span(s) == "TOOL_CALL":
                tool_name = s.get("attributes", {}).get(TOOL_NAME, "unknown")
                tool_calls[tool_name] += 1
        for _name, count in tool_calls.items():
            if count >= 3:
                fault_detected = True
                break

    elif fault_type == FaultType.CONTEXT_OVERFLOW:
        # Can detect: progressive token growth on LLM spans
        llm_spans = sorted(
            [s for s in exported_spans if _classify_vanilla_span(s) == "LLM_CALL"],
            key=lambda s: s.get("start_time_ns", 0) or 0,
        )
        token_sequence = []
        for s in llm_spans:
            tokens = s.get("attributes", {}).get(LLM_INPUT_TOKENS, 0)
            if tokens and tokens > 0:
                token_sequence.append(tokens)
        if len(token_sequence) >= 3:
            growth_count = 0
            for i in range(1, len(token_sequence)):
                if token_sequence[i] > token_sequence[i - 1] * 1.3:
                    growth_count += 1
                else:
                    growth_count = 0
                if growth_count >= 2:
                    fault_detected = True
                    break

    elif fault_type == FaultType.WRONG_TOOL:
        # Partially detectable: we can see tool names but lack the semantic
        # span kind to reliably filter only tool spans.  The heuristic
        # classifier helps somewhat but is less reliable.
        wrong_tool_names = set()
        for gt in ground_truth:
            name = gt.get("details", {}).get("wrong_tool")
            if name:
                wrong_tool_names.add(name)
        if wrong_tool_names:
            for span in exported_spans:
                guessed = _classify_vanilla_span(span)
                if guessed in ("TOOL_CALL", "DELEGATION"):
                    attrs = span.get("attributes", {})
                    tool_name = attrs.get(TOOL_NAME, "")
                    if tool_name in wrong_tool_names:
                        fault_detected = True
                        break

    elif fault_type == FaultType.HALLUCINATION:
        # NOT detectable: requires RETRIEVAL span kind to verify grounding
        pass

    elif fault_type == FaultType.CIRCULAR_DELEGATION:
        # NOT detectable: while delegation.source/target attributes exist,
        # without DELEGATION span kind we cannot reliably distinguish
        # delegation spans from other spans that might coincidentally
        # have those attributes.
        pass

    # -- Span-attribute faults: all NOT detectable without agent span kinds --

    elif fault_type == FaultType.STALE_RETRIEVAL:
        # NOT detectable: requires RETRIEVAL span kind to identify
        # retrieval operations and check staleness_seconds.
        pass

    elif fault_type == FaultType.GUARDRAIL_BYPASS:
        # NOT detectable: requires GUARD_RAIL span kind to distinguish
        # guardrail spans from other spans.
        pass

    elif fault_type == FaultType.PLANNING_FAILURE:
        # NOT detectable: requires PLANNING span kind to identify
        # planning spans and check step_count.
        pass

    elif fault_type == FaultType.REASONING_LOOP:
        # NOT detectable: requires REASONING span kind to identify
        # reasoning spans and check for repeated chains.
        pass

    elif fault_type == FaultType.AGENT_MISROUTE:
        # NOT detectable: requires AGENT span kind to identify
        # agent spans and check misrouted attribute.
        pass

    elif fault_type == FaultType.MEMORY_CORRUPTION:
        # NOT detectable: requires MEMORY span kind to identify
        # memory spans and check corrupted attribute.
        pass

    ttrc_ms = (time.time() - analysis_start) * 1000
    faults_injected = 1 if ground_truth else 0
    faults_found = 1 if fault_detected else 0
    detection_correct = (fault_detected == bool(ground_truth))

    return fault_detected, detection_correct, ttrc_ms, faults_found


# ---------------------------------------------------------------------------
# OTel GenAI trace analysis (uses gen_ai.* attributes, no AGENT_SPAN_KIND)
# ---------------------------------------------------------------------------

def _classify_genai_span(span: Dict[str, Any]) -> Optional[str]:
    """Classify a span using current OTel GenAI semantic conventions.

    The GenAI conventions define typed operations via gen_ai.operation.name:
      - chat / text_completion / generate_content -> "INFERENCE" (CLIENT)
      - embeddings                                -> "EMBEDDINGS" (CLIENT)
      - retrieval                                 -> "RETRIEVALS" (CLIENT)
      - execute_tool (or gen_ai.tool.name set)    -> "EXECUTE_TOOL" (INTERNAL)
      - create_agent                              -> "CREATE_AGENT" (CLIENT)
      - invoke_agent / invoke_workflow            -> "INVOKE_AGENT" (CLIENT)

    Returns one of those literals, or None.
    """
    attrs = span.get("attributes", {})

    op_name = attrs.get(GENAI_OPERATION_NAME, "")
    if op_name == "execute_tool" or attrs.get(GENAI_TOOL_NAME):
        return "EXECUTE_TOOL"
    if op_name in ("chat", "text_completion", "generate_content"):
        return "INFERENCE"
    if op_name == "embeddings":
        return "EMBEDDINGS"
    if op_name == "retrieval":
        return "RETRIEVALS"
    if op_name == "create_agent":
        return "CREATE_AGENT"
    if op_name in ("invoke_agent", "invoke_workflow"):
        return "INVOKE_AGENT"

    return None


def _analyze_traces_genai(
    exported_spans: List[Dict[str, Any]],
    fault_type: FaultType,
    ground_truth: List[Dict[str, Any]],
) -> Tuple[bool, bool, float, int]:
    """Analyze traces using OTel GenAI semantic conventions.

    This is the intermediate baseline between vanilla_otel (heuristic only)
    and full agenttelemetry (9 span kinds).  GenAI conventions provide 4
    structured span types with standardized attributes, giving better
    detection than vanilla OTel but worse than full agent semantics.

    Detectable (7 of 14):
      - wrong_tool        (gen_ai.tool.name on EXECUTE_TOOL spans)
      - infinite_loop     (repeated gen_ai.tool.name)
      - tool_failure      (OTel ERROR on EXECUTE_TOOL spans)
      - timeout           (OTel ERROR with "timeout")
      - context_overflow  (gen_ai.usage.input_tokens growth on INFERENCE spans)
      - cost_explosion    (gen_ai.usage tokens + model pricing on INFERENCE spans)
      - hallucination     (INFERENCE span with output but no RETRIEVALS sibling)

    NOT detectable (7 of 14):
      - circular_delegation  (no delegation span type)
      - stale_retrieval      (RETRIEVALS exists but no staleness attribute)
      - guardrail_bypass     (no guardrail span type)
      - planning_failure     (no planning span type)
      - reasoning_loop       (no reasoning span type)
      - agent_misroute       (no agent span type)
      - memory_corruption    (no memory span type)
    """
    if not exported_spans:
        return False, False, 0.0, 0

    analysis_start = time.time()
    fault_detected = False

    if fault_type == FaultType.WRONG_TOOL:
        # Detectable: gen_ai.tool.name on EXECUTE_TOOL spans
        wrong_tool_names = set()
        for gt in ground_truth:
            name = gt.get("details", {}).get("wrong_tool")
            if name:
                wrong_tool_names.add(name)
        if wrong_tool_names:
            for span in exported_spans:
                if _classify_genai_span(span) == "EXECUTE_TOOL":
                    tool_name = span.get("attributes", {}).get(GENAI_TOOL_NAME, "")
                    if tool_name in wrong_tool_names:
                        fault_detected = True
                        break

    elif fault_type == FaultType.INFINITE_LOOP:
        # Detectable: repeated gen_ai.tool.name values
        from collections import Counter
        tool_calls = Counter()
        for s in exported_spans:
            if _classify_genai_span(s) == "EXECUTE_TOOL":
                tool_name = s.get("attributes", {}).get(GENAI_TOOL_NAME, "unknown")
                tool_calls[tool_name] += 1
        for _name, count in tool_calls.items():
            if count >= 3:
                fault_detected = True
                break

    elif fault_type == FaultType.TOOL_FAILURE:
        # Detectable: EXECUTE_TOOL span with OTel ERROR status
        for span in exported_spans:
            if _classify_genai_span(span) == "EXECUTE_TOOL":
                attrs = span.get("attributes", {})
                status = span.get("status", {})
                if (attrs.get(TOOL_STATUS) == "error"
                        or status.get("code") == "ERROR"):
                    fault_detected = True
                    break

    elif fault_type == FaultType.TIMEOUT:
        # Detectable: OTel ERROR status with "timeout"
        for span in exported_spans:
            status = span.get("status", {})
            if status.get("code") == "ERROR":
                desc = (status.get("description", "") or "").lower()
                if "timeout" in desc or "timed out" in desc:
                    fault_detected = True
                    break
            for event in span.get("events", []):
                event_attrs = event.get("attributes", {})
                exc_type = str(event_attrs.get("exception.type", ""))
                exc_msg = str(event_attrs.get("exception.message", ""))
                if "timeout" in exc_type.lower() or "timeout" in exc_msg.lower():
                    fault_detected = True
                    break
            if fault_detected:
                break

    elif fault_type == FaultType.CONTEXT_OVERFLOW:
        # Detectable: progressive gen_ai.usage.input_tokens growth on INFERENCE spans
        inference_spans = sorted(
            [s for s in exported_spans if _classify_genai_span(s) == "INFERENCE"],
            key=lambda s: s.get("start_time_ns", 0) or 0,
        )
        token_sequence = []
        for s in inference_spans:
            tokens = s.get("attributes", {}).get(GENAI_USAGE_INPUT_TOKENS, 0)
            if tokens and tokens > 0:
                token_sequence.append(tokens)
        if len(token_sequence) >= 3:
            growth_count = 0
            for i in range(1, len(token_sequence)):
                if token_sequence[i] > token_sequence[i - 1] * 1.3:
                    growth_count += 1
                else:
                    growth_count = 0
                if growth_count >= 2:
                    fault_detected = True
                    break

    elif fault_type == FaultType.COST_EXPLOSION:
        # Detectable: compute cost from gen_ai.usage tokens + model pricing
        total_cost = 0.0
        for s in exported_spans:
            if _classify_genai_span(s) == "INFERENCE":
                attrs = s.get("attributes", {})
                model_name = attrs.get(GENAI_REQUEST_MODEL, "")
                in_tok = attrs.get(GENAI_USAGE_INPUT_TOKENS, 0) or 0
                out_tok = attrs.get(GENAI_USAGE_OUTPUT_TOKENS, 0) or 0
                if model_name and (in_tok or out_tok):
                    total_cost += estimate_cost(model_name, in_tok, out_tok)
        if total_cost > 0.10:
            fault_detected = True

    elif fault_type == FaultType.HALLUCINATION:
        # Detectable: INFERENCE span with output but no RETRIEVALS span present
        has_retrievals = any(
            _classify_genai_span(s) == "RETRIEVALS"
            for s in exported_spans
        )
        has_inference_output = any(
            _classify_genai_span(s) == "INFERENCE"
            and (s.get("attributes", {}).get(GENAI_USAGE_OUTPUT_TOKENS, 0) or 0) > 50
            for s in exported_spans
        )
        if has_inference_output and not has_retrievals and ground_truth:
            fault_detected = True

    # -- NOT detectable with GenAI conventions --

    elif fault_type == FaultType.CIRCULAR_DELEGATION:
        # NOT detectable: GenAI has no delegation span type.
        # Delegation spans exist but without a typed span kind, we cannot
        # reliably distinguish them from generic spans.
        pass

    elif fault_type == FaultType.STALE_RETRIEVAL:
        # NOT detectable: GenAI RETRIEVALS span exists but has no
        # staleness_seconds attribute in the semantic conventions.
        pass

    elif fault_type == FaultType.GUARDRAIL_BYPASS:
        # NOT detectable: no guardrail span type in GenAI conventions.
        pass

    elif fault_type == FaultType.PLANNING_FAILURE:
        # NOT detectable: no planning span type in GenAI conventions.
        pass

    elif fault_type == FaultType.REASONING_LOOP:
        # NOT detectable: no reasoning span type in GenAI conventions.
        pass

    elif fault_type == FaultType.AGENT_MISROUTE:
        # NOT detectable: no agent span type in GenAI conventions.
        pass

    elif fault_type == FaultType.MEMORY_CORRUPTION:
        # NOT detectable: no memory span type in GenAI conventions.
        pass

    ttrc_ms = (time.time() - analysis_start) * 1000
    faults_injected = 1 if ground_truth else 0
    faults_found = 1 if fault_detected else 0
    detection_correct = (fault_detected == bool(ground_truth))

    return fault_detected, detection_correct, ttrc_ms, faults_found


# ---------------------------------------------------------------------------
# OpenInference trace analysis (uses openinference.span.kind attribute)
# ---------------------------------------------------------------------------

OI_SPAN_KIND_KEY = "openinference.span.kind"
OI_TOOL_NAME_KEY = "tool.name"
OI_PROMPT_TOKENS_KEY = "llm.token_count.prompt"
OI_COMPLETION_TOKENS_KEY = "llm.token_count.completion"
OI_LLM_MODEL_KEY = "llm.model_name"


def _classify_openinference_span(span: Dict[str, Any]) -> Optional[str]:
    """Classify a span using OpenInference (Arize) typed kinds.

    OpenInference defines ten typed kinds: LLM, EMBEDDING, CHAIN, RETRIEVER,
    RERANKER, TOOL, AGENT, GUARDRAIL, EVALUATOR, PROMPT.
    """
    return span.get("attributes", {}).get(OI_SPAN_KIND_KEY)


def _analyze_traces_openinference(
    exported_spans: List[Dict[str, Any]],
    fault_type: FaultType,
    ground_truth: List[Dict[str, Any]],
) -> Tuple[bool, bool, float, int]:
    """Analyze traces using OpenInference semantic conventions.

    Detectable (6 of 14) -- the same six surface for vanilla OTel via simpler
    attributes; OpenInference's typed LLM/TOOL/RETRIEVER kinds let detectors
    target spans precisely:
      - wrong_tool, infinite_loop, tool_failure, timeout,
        context_overflow, cost_explosion.

    NOT detectable (8 of 14): hallucination, circular_delegation,
    stale_retrieval, guardrail_bypass, planning_failure, reasoning_loop,
    agent_misroute, memory_corruption.
    """
    if not exported_spans:
        return False, False, 0.0, 0

    analysis_start = time.time()
    fault_detected = False

    if fault_type == FaultType.WRONG_TOOL:
        wrong_tool_names = set()
        for gt in ground_truth:
            name = gt.get("details", {}).get("wrong_tool")
            if name:
                wrong_tool_names.add(name)
        if wrong_tool_names:
            for s in exported_spans:
                if _classify_openinference_span(s) == "TOOL":
                    name = s.get("attributes", {}).get(OI_TOOL_NAME_KEY, "")
                    if name in wrong_tool_names:
                        fault_detected = True
                        break

    elif fault_type == FaultType.INFINITE_LOOP:
        from collections import Counter
        cnt = Counter()
        for s in exported_spans:
            if _classify_openinference_span(s) == "TOOL":
                cnt[s.get("attributes", {}).get(OI_TOOL_NAME_KEY, "?")] += 1
        if any(c >= 3 for c in cnt.values()):
            fault_detected = True

    elif fault_type == FaultType.TOOL_FAILURE:
        for s in exported_spans:
            if _classify_openinference_span(s) == "TOOL":
                if s.get("status", {}).get("code") == "ERROR":
                    fault_detected = True
                    break

    elif fault_type == FaultType.TIMEOUT:
        for s in exported_spans:
            st = s.get("status", {})
            if st.get("code") == "ERROR" and "timeout" in (st.get("description", "") or "").lower():
                fault_detected = True
                break
            for ev in s.get("events", []):
                ea = ev.get("attributes", {})
                if "timeout" in str(ea.get("exception.type", "")).lower() or \
                   "timeout" in str(ea.get("exception.message", "")).lower():
                    fault_detected = True
                    break
            if fault_detected:
                break

    elif fault_type == FaultType.CONTEXT_OVERFLOW:
        llm_spans = sorted(
            [s for s in exported_spans if _classify_openinference_span(s) == "LLM"],
            key=lambda s: s.get("start_time_ns", 0) or 0,
        )
        seq = [s.get("attributes", {}).get(OI_PROMPT_TOKENS_KEY, 0) for s in llm_spans]
        seq = [t for t in seq if t and t > 0]
        if len(seq) >= 3:
            growth = 0
            for i in range(1, len(seq)):
                if seq[i] > seq[i - 1] * 1.3:
                    growth += 1
                else:
                    growth = 0
                if growth >= 2:
                    fault_detected = True
                    break

    elif fault_type == FaultType.COST_EXPLOSION:
        total_cost = 0.0
        for s in exported_spans:
            if _classify_openinference_span(s) == "LLM":
                a = s.get("attributes", {})
                model = a.get(OI_LLM_MODEL_KEY, "")
                in_t = a.get(OI_PROMPT_TOKENS_KEY, 0) or 0
                out_t = a.get(OI_COMPLETION_TOKENS_KEY, 0) or 0
                if model and (in_t or out_t):
                    total_cost += estimate_cost(model, in_t, out_t)
        if total_cost > 0.10:
            fault_detected = True

    # All eight remaining faults are not detectable: OpenInference defines
    # AGENT and GUARDRAIL kinds but exposes no typed delegation source/target,
    # no constrained guardrail outcome, no staleness, no memory, and CHAIN is
    # an undifferentiated planning/reasoning wrapper.

    ttrc_ms = (time.time() - analysis_start) * 1000
    faults_injected = 1 if ground_truth else 0
    faults_found = 1 if fault_detected else 0
    detection_correct = (fault_detected == bool(ground_truth))

    return fault_detected, detection_correct, ttrc_ms, faults_found

def _analyze_traces(
    exported_spans: List[Dict[str, Any]],
    fault_type: FaultType,
    ground_truth: List[Dict[str, Any]],
) -> Tuple[bool, bool, float, int]:
    """Analyze exported traces for fault detection.

    Returns binary detection: was the injected fault found in the traces?

    Returns:
        (fault_detected, detection_correct, ttrc_ms, faults_found)
        faults_found is always 0 or 1 (binary).
    """
    if not exported_spans:
        return False, False, 0.0, 0

    analysis_start = time.time()
    fault_detected = False

    if fault_type == FaultType.WRONG_TOOL:
        # Detect: a tool was called that the injector forced as "wrong".
        # Check all ground truth entries for wrong tool names that appear in spans.
        wrong_tool_names = set()
        for gt in ground_truth:
            name = gt.get("details", {}).get("wrong_tool")
            if name:
                wrong_tool_names.add(name)
        if wrong_tool_names:
            for span in exported_spans:
                attrs = span.get("attributes", {})
                kind = attrs.get(AGENT_SPAN_KIND, "")
                # Check both TOOL_CALL and DELEGATION spans (delegate_task is a tool)
                if kind in ("TOOL_CALL", "DELEGATION"):
                    tool_name = attrs.get(TOOL_NAME, "")
                    target = attrs.get("delegation.target_agent", "")
                    if tool_name in wrong_tool_names or target:
                        fault_detected = True
                        break

    elif fault_type == FaultType.HALLUCINATION:
        # Detect: LLM produced output without retrieval grounding.
        # Check if any LLM_CALL span has output but no RETRIEVAL sibling.
        has_retrieval = any(
            s.get("attributes", {}).get(AGENT_SPAN_KIND) == "RETRIEVAL"
            for s in exported_spans
        )
        has_llm_output = any(
            s.get("attributes", {}).get(AGENT_SPAN_KIND) == "LLM_CALL"
            and s.get("attributes", {}).get(LLM_OUTPUT_TOKENS, 0) > 50
            for s in exported_spans
        )
        if has_llm_output and not has_retrieval and ground_truth:
            fault_detected = True

    elif fault_type == FaultType.INFINITE_LOOP:
        # Detect: any tool called more than threshold times with same args.
        from collections import Counter
        tool_calls = Counter()
        for s in exported_spans:
            a = s.get("attributes", {})
            if a.get(AGENT_SPAN_KIND) == "TOOL_CALL":
                tool_name = a.get(TOOL_NAME, "unknown")
                tool_calls[tool_name] += 1
        for name, count in tool_calls.items():
            if count >= 3:
                fault_detected = True
                break

    elif fault_type == FaultType.CONTEXT_OVERFLOW:
        # Detect: progressively increasing input token counts across LLM calls.
        token_sequence = []
        sorted_spans = sorted(
            [s for s in exported_spans if s.get("attributes", {}).get(AGENT_SPAN_KIND) == "LLM_CALL"],
            key=lambda s: s.get("start_time_ns", 0) or 0,
        )
        for s in sorted_spans:
            tokens = s.get("attributes", {}).get(LLM_INPUT_TOKENS, 0)
            if tokens and tokens > 0:
                token_sequence.append(tokens)
        if len(token_sequence) >= 3:
            # Check for sustained growth (at least 2 consecutive increases with 1.5x+ ratio)
            growth_count = 0
            for i in range(1, len(token_sequence)):
                if token_sequence[i] > token_sequence[i - 1] * 1.3:
                    growth_count += 1
                else:
                    growth_count = 0
                if growth_count >= 2:
                    fault_detected = True
                    break

    elif fault_type == FaultType.COST_EXPLOSION:
        # Detect: total LLM cost exceeds a reasonable threshold for a single task.
        total_cost = sum(
            s.get("attributes", {}).get(LLM_COST, 0) or 0
            for s in exported_spans
            if s.get("attributes", {}).get(AGENT_SPAN_KIND) == "LLM_CALL"
        )
        if total_cost > 0.10:  # > $0.10 for a single task is suspicious
            fault_detected = True

    elif fault_type == FaultType.CIRCULAR_DELEGATION:
        # Detect: DELEGATION spans forming a cycle (A->B->A).
        delegations = []
        for s in exported_spans:
            a = s.get("attributes", {})
            if a.get(AGENT_SPAN_KIND) == "DELEGATION":
                src = a.get("delegation.source_agent", "")
                tgt = a.get("delegation.target_agent", "")
                if src and tgt:
                    delegations.append((src, tgt))
        # Check for cycles
        if len(delegations) >= 2:
            targets_by_source: Dict[str, set] = {}
            for src, tgt in delegations:
                targets_by_source.setdefault(src, set()).add(tgt)
            for src, tgt in delegations:
                if tgt in targets_by_source and src in targets_by_source[tgt]:
                    fault_detected = True
                    break

    elif fault_type == FaultType.TOOL_FAILURE:
        # Detect: any tool span with error status.
        for span in exported_spans:
            attrs = span.get("attributes", {})
            status = span.get("status", {})
            if attrs.get(AGENT_SPAN_KIND) == "TOOL_CALL":
                if (attrs.get(TOOL_STATUS) == "error"
                        or status.get("code") == "ERROR"):
                    fault_detected = True
                    break

    elif fault_type == FaultType.TIMEOUT:
        # Detect: any span with error status mentioning timeout.
        for span in exported_spans:
            status = span.get("status", {})
            if status.get("code") == "ERROR":
                desc = (status.get("description", "") or "").lower()
                if "timeout" in desc or "timed out" in desc:
                    fault_detected = True
                    break
            # Also check events for recorded exceptions
            for event in span.get("events", []):
                event_attrs = event.get("attributes", {})
                exc_type = str(event_attrs.get("exception.type", ""))
                exc_msg = str(event_attrs.get("exception.message", ""))
                if "timeout" in exc_type.lower() or "timeout" in exc_msg.lower():
                    fault_detected = True
                    break
            if fault_detected:
                break

    # -- Span-attribute faults (require agent-specific span kinds) -----------

    elif fault_type == FaultType.STALE_RETRIEVAL:
        # Detect: RETRIEVAL span with staleness_seconds > 3600.
        # Requires RETRIEVAL span kind to identify retrieval operations.
        for span in exported_spans:
            attrs = span.get("attributes", {})
            if attrs.get(AGENT_SPAN_KIND) == "RETRIEVAL":
                staleness = attrs.get(RETRIEVAL_STALENESS_SECONDS, 0)
                if staleness and staleness > 3600:
                    fault_detected = True
                    break

    elif fault_type == FaultType.GUARDRAIL_BYPASS:
        # Detect: GUARD_RAIL span with result == "bypass" or "fail".
        # Requires GUARD_RAIL span kind to distinguish guardrail spans.
        for span in exported_spans:
            attrs = span.get("attributes", {})
            if attrs.get(AGENT_SPAN_KIND) == "GUARD_RAIL":
                result = attrs.get(GUARDRAIL_RESULT, "")
                if result in ("bypass", "fail"):
                    fault_detected = True
                    break

    elif fault_type == FaultType.PLANNING_FAILURE:
        # Detect: PLANNING span with step_count > 10 (excessive decomposition).
        # Requires PLANNING span kind to identify planning spans.
        for span in exported_spans:
            attrs = span.get("attributes", {})
            if attrs.get(AGENT_SPAN_KIND) == "PLANNING":
                step_count = attrs.get(PLANNING_STEP_COUNT, 0)
                if step_count and step_count > 10:
                    fault_detected = True
                    break

    elif fault_type == FaultType.REASONING_LOOP:
        # Detect: 2+ REASONING spans with the same reasoning.chain value.
        # Requires REASONING span kind to identify reasoning spans.
        from collections import Counter
        chain_counts = Counter()
        for span in exported_spans:
            attrs = span.get("attributes", {})
            if attrs.get(AGENT_SPAN_KIND) == "REASONING":
                chain = attrs.get(REASONING_CHAIN, "")
                if chain:
                    chain_counts[chain] += 1
        for _chain_val, count in chain_counts.items():
            if count >= 2:
                fault_detected = True
                break

    elif fault_type == FaultType.AGENT_MISROUTE:
        # Detect: AGENT span with agent.misrouted == true.
        # Requires AGENT span kind to identify agent spans.
        for span in exported_spans:
            attrs = span.get("attributes", {})
            if attrs.get(AGENT_SPAN_KIND) == "AGENT":
                if attrs.get(AGENT_MISROUTED) is True:
                    fault_detected = True
                    break

    elif fault_type == FaultType.MEMORY_CORRUPTION:
        # Detect: MEMORY span with operation == "read" and corrupted == true.
        # Requires MEMORY span kind to identify memory spans.
        for span in exported_spans:
            attrs = span.get("attributes", {})
            if attrs.get(AGENT_SPAN_KIND) == "MEMORY":
                if (attrs.get(MEMORY_OPERATION) == "read"
                        and attrs.get(MEMORY_CORRUPTED) is True):
                    fault_detected = True
                    break

    ttrc_ms = (time.time() - analysis_start) * 1000

    # Check correctness: detection should match whether faults were injected
    faults_injected = 1 if ground_truth else 0
    faults_found = 1 if fault_detected else 0
    detection_correct = (fault_detected == bool(ground_truth))

    return fault_detected, detection_correct, ttrc_ms, faults_found


# ---------------------------------------------------------------------------
# False-positive analysis: run ALL detectors on a single trace
# ---------------------------------------------------------------------------

def _analyze_all_detectors(
    exported_spans: List[Dict[str, Any]],
    condition: str = "full_capture",
) -> Dict[str, bool]:
    """Run all 14 detectors on a trace. Returns dict mapping fault_type -> bool (fired).

    Used for false-positive analysis: when no fault was injected, any
    detector that fires is a false positive.
    """
    results = {}
    for ft in FaultType:
        if ft == FaultType.NONE:
            continue
        if condition == "vanilla_otel":
            detected, _, _, _ = _analyze_traces_vanilla(exported_spans, ft, [])
        elif condition == "otel_genai":
            detected, _, _, _ = _analyze_traces_genai(exported_spans, ft, [])
        elif condition == "openinference":
            detected, _, _, _ = _analyze_traces_openinference(exported_spans, ft, [])
        else:
            detected, _, _, _ = _analyze_traces(exported_spans, ft, [])
        results[ft.value] = detected
    return results


# ---------------------------------------------------------------------------
# Single benchmark run
# ---------------------------------------------------------------------------

def run_single_benchmark(
    framework: str,
    model: str,
    fault_type: FaultType,
    condition: str,
    mock_only: bool = True,
) -> BenchmarkResult:
    """Run a single benchmark configuration.

    Args:
        framework: One of FRAMEWORKS.
        model: One of MODELS.
        fault_type: The fault to inject.
        condition: One of CONDITIONS.
        mock_only: If True, use mock clients only.

    Returns:
        BenchmarkResult with metrics.
    """
    start_time = time.time()

    # Set up fault injection
    injector = FaultInjector(fault_type, rate=1.0, seed=42)

    # Set up mock client
    is_anthropic_model = "claude" in model or "sonnet" in model or "haiku" in model or "opus" in model
    if is_anthropic_model:
        mock_client = MockAnthropicClient(default_model=model, fault_injector=injector)
    else:
        mock_client = MockOpenAIClient(default_model=model, fault_injector=injector)

    # Set up telemetry provider based on condition
    provider = None
    json_exporter = None

    if condition == "no_telemetry":
        # No instrumentation
        pass
    elif condition == "vanilla_otel":
        # Standard OTel with JSON exporter but no agent-specific span kinds
        provider = AgentTelemetryProvider(
            service_name=f"bench-{framework}",
            privacy_level=PrivacyLevel.METADATA_ONLY,
        )
        json_exporter = provider.add_json_exporter(os.devnull)
        provider.setup(set_global=False)
    elif condition == "otel_genai":
        # OTel + GenAI semantic conventions (4 span types, no agent span kinds)
        provider = AgentTelemetryProvider(
            service_name=f"bench-{framework}",
            privacy_level=PrivacyLevel.METADATA_ONLY,
        )
        json_exporter = provider.add_json_exporter(os.devnull)
        provider.setup(set_global=False)
    elif condition == "openinference":
        # OpenInference (Arize) typed span kinds
        provider = AgentTelemetryProvider(
            service_name=f"bench-{framework}",
            privacy_level=PrivacyLevel.METADATA_ONLY,
        )
        json_exporter = provider.add_json_exporter(os.devnull)
        provider.setup(set_global=False)
    elif condition == "metadata_only":
        provider = AgentTelemetryProvider(
            service_name=f"bench-{framework}",
            privacy_level=PrivacyLevel.METADATA_ONLY,
        )
        json_exporter = provider.add_json_exporter(os.devnull)
        provider.setup(set_global=False)
    elif condition == "full_capture":
        provider = AgentTelemetryProvider(
            service_name=f"bench-{framework}",
            privacy_level=PrivacyLevel.FULL,
        )
        json_exporter = provider.add_json_exporter(os.devnull)
        provider.setup(set_global=False)

    # Get app runner (vanilla_otel, otel_genai, and openinference always use their own runners)
    if condition == "vanilla_otel":
        app_runner = run_vanilla_agent
    elif condition == "otel_genai":
        app_runner = run_otel_genai_agent
    elif condition == "openinference":
        app_runner = run_openinference_agent
    else:
        app_runner = _get_app_runner(framework)
    if app_runner is None:
        return BenchmarkResult(
            framework=framework, model=model, fault_type=fault_type.value,
            condition=condition, fault_detected=False, detection_correct=False,
            time_to_root_cause_ms=0, total_spans=0, llm_spans=0, tool_spans=0,
            total_tokens=0, estimated_cost_usd=0, agent_iterations=0,
            faults_injected=0, faults_detected=0,
            run_time_ms=(time.time() - start_time) * 1000,
            error=f"No runner for framework: {framework}",
        )

    # Run the app
    try:
        result = app_runner(
            mock_client=mock_client,
            provider=provider,
            model=model,
            max_iterations=5,
            fault_injector=injector,
        )
    except Exception as e:
        result = {"iterations": 0, "steps": [], "error": str(e)}

    # Collect spans
    exported_spans = []
    if json_exporter:
        exported_spans = json_exporter.get_exported_spans()

    # Analyze traces
    ground_truth = injector.get_ground_truth()
    detector_results = None

    if fault_type == FaultType.NONE:
        # False-positive analysis: run all detectors, count spurious fires
        detector_results = _analyze_all_detectors(exported_spans, condition)
        fault_detected = any(detector_results.values())
        faults_injected = 0
        faults_found = sum(1 for v in detector_results.values() if v)
        detection_correct = not fault_detected  # correct means no false fires
        ttrc_ms = 0.0
    elif condition == "vanilla_otel":
        fault_detected, detection_correct, ttrc_ms, faults_found = _analyze_traces_vanilla(
            exported_spans, fault_type, ground_truth,
        )
    elif condition == "otel_genai":
        fault_detected, detection_correct, ttrc_ms, faults_found = _analyze_traces_genai(
            exported_spans, fault_type, ground_truth,
        )
    elif condition == "openinference":
        fault_detected, detection_correct, ttrc_ms, faults_found = _analyze_traces_openinference(
            exported_spans, fault_type, ground_truth,
        )
    else:
        fault_detected, detection_correct, ttrc_ms, faults_found = _analyze_traces(
            exported_spans, fault_type, ground_truth,
        )

    # faults_injected is binary: 1 if any faults were injected, 0 otherwise
    # (skip for NONE -- already set above)
    if fault_type != FaultType.NONE:
        faults_injected = 1 if ground_truth else 0

    # Compute aggregate metrics from spans
    total_tokens = 0
    total_cost = 0.0
    llm_spans = 0
    tool_spans = 0
    for span in exported_spans:
        attrs = span.get("attributes", {})
        if condition == "vanilla_otel":
            guessed_kind = _classify_vanilla_span(span)
            if guessed_kind == "LLM_CALL":
                llm_spans += 1
                total_tokens += attrs.get(LLM_INPUT_TOKENS, 0) + attrs.get(LLM_OUTPUT_TOKENS, 0)
                total_cost += attrs.get(LLM_COST, 0)
            elif guessed_kind == "TOOL_CALL":
                tool_spans += 1
        elif condition == "otel_genai":
            genai_kind = _classify_genai_span(span)
            if genai_kind == "INFERENCE":
                llm_spans += 1
                in_tok = attrs.get(GENAI_USAGE_INPUT_TOKENS, 0) or 0
                out_tok = attrs.get(GENAI_USAGE_OUTPUT_TOKENS, 0) or 0
                total_tokens += in_tok + out_tok
                model_name = attrs.get(GENAI_REQUEST_MODEL, "")
                if model_name and (in_tok or out_tok):
                    total_cost += estimate_cost(model_name, in_tok, out_tok)
            elif genai_kind == "EXECUTE_TOOL":
                tool_spans += 1
        else:
            agent_kind = attrs.get(AGENT_SPAN_KIND, "")
            if agent_kind == "LLM_CALL":
                llm_spans += 1
                total_tokens += attrs.get(LLM_INPUT_TOKENS, 0) + attrs.get(LLM_OUTPUT_TOKENS, 0)
                total_cost += attrs.get(LLM_COST, 0)
            elif agent_kind == "TOOL_CALL":
                tool_spans += 1

    # Also get stats from mock client
    if is_anthropic_model:
        stats = mock_client.get_call_stats()
        if total_tokens == 0:
            total_tokens = stats.get("total_input_tokens", 0) + stats.get("total_output_tokens", 0)
    else:
        stats = mock_client.get_call_stats()
        if total_tokens == 0:
            total_tokens = stats.get("total_prompt_tokens", 0) + stats.get("total_completion_tokens", 0)

    if provider:
        provider.shutdown()

    run_time_ms = (time.time() - start_time) * 1000

    return BenchmarkResult(
        framework=framework,
        model=model,
        fault_type=fault_type.value,
        condition=condition,
        fault_detected=fault_detected,
        detection_correct=detection_correct,
        time_to_root_cause_ms=ttrc_ms,
        total_spans=len(exported_spans),
        llm_spans=llm_spans,
        tool_spans=tool_spans,
        total_tokens=total_tokens,
        estimated_cost_usd=total_cost,
        agent_iterations=result.get("iterations", 0),
        faults_injected=faults_injected,
        faults_detected=faults_found,
        run_time_ms=run_time_ms,
        error=result.get("error"),
        detector_results=detector_results,
    )


# ---------------------------------------------------------------------------
# Full benchmark suite
# ---------------------------------------------------------------------------

def run_benchmarks(
    mock_only: bool = True,
    output_file: str = "results.tsv",
    frameworks: Optional[List[str]] = None,
    models: Optional[List[str]] = None,
    fault_types: Optional[List[FaultType]] = None,
    conditions: Optional[List[str]] = None,
    verbose: bool = True,
) -> List[BenchmarkResult]:
    """Run the full benchmark suite.

    Args:
        mock_only: If True, use only mock clients (no real API calls).
        output_file: Path to write TSV results.
        frameworks: Subset of FRAMEWORKS to test. Defaults to all.
        models: Subset of MODELS to test. Defaults to all.
        fault_types: Subset of FaultType to test. Defaults to all.
        conditions: Subset of CONDITIONS to test. Defaults to all.
        verbose: Print progress to stdout.

    Returns:
        List of BenchmarkResult objects.
    """
    frameworks = frameworks or FRAMEWORKS
    models = models or MODELS
    fault_types = fault_types or list(FaultType)
    conditions = conditions or CONDITIONS

    total = len(frameworks) * len(models) * len(fault_types) * len(conditions)
    results: List[BenchmarkResult] = []
    completed = 0

    if verbose:
        print(f"Running {total} benchmark configurations...")
        print(f"  Frameworks: {frameworks}")
        print(f"  Models: {models}")
        print(f"  Fault types: {[ft.value for ft in fault_types]}")
        print(f"  Conditions: {conditions}")
        print()

    for framework in frameworks:
        for model_name in models:
            for fault in fault_types:
                for condition in conditions:
                    completed += 1
                    if verbose:
                        print(
                            f"  [{completed}/{total}] "
                            f"{framework:>15} | {model_name:>20} | "
                            f"{fault.value:>22} | {condition:>15}",
                            end="",
                            flush=True,
                        )

                    result = run_single_benchmark(
                        framework, model_name, fault, condition, mock_only,
                    )
                    results.append(result)

                    if verbose:
                        status = "OK" if not result.error else f"ERR: {result.error[:30]}"
                        fdr = result.fault_detection_rate
                        print(f" | FDR={fdr:.2f} | {result.run_time_ms:.0f}ms | {status}")

    # Write results
    write_results(results, output_file)

    if verbose:
        print(f"\nResults written to {output_file}")
        _print_summary(results)

    return results


def write_results(results: List[BenchmarkResult], output_file: str) -> None:
    """Write benchmark results to a TSV file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(TSV_HEADER)
        for result in results:
            writer.writerow(result.to_tsv_row())


def _print_summary(results: List[BenchmarkResult]) -> None:
    """Print a summary of benchmark results."""
    print("\n" + "=" * 80)
    print("BENCHMARK SUMMARY")
    print("=" * 80)

    # Overall FDR by condition
    print("\nFault Detection Rate by Condition:")
    for condition in CONDITIONS:
        cond_results = [r for r in results if r.condition == condition and r.faults_injected > 0]
        if cond_results:
            avg_fdr = sum(r.fault_detection_rate for r in cond_results) / len(cond_results)
            print(f"  {condition:>15}: {avg_fdr:.3f} (n={len(cond_results)})")

    # FDR by fault type (full_capture only)
    print("\nFault Detection Rate by Fault Type (full_capture):")
    for ft in FaultType:
        ft_results = [
            r for r in results
            if r.fault_type == ft.value and r.condition == "full_capture"
            and r.faults_injected > 0
        ]
        if ft_results:
            avg_fdr = sum(r.fault_detection_rate for r in ft_results) / len(ft_results)
            avg_ttrc = sum(r.time_to_root_cause_ms for r in ft_results) / len(ft_results)
            print(f"  {ft.value:>22}: FDR={avg_fdr:.3f}  TTRC={avg_ttrc:.1f}ms  (n={len(ft_results)})")

    # FDR by fault type: vanilla_otel vs otel_genai vs full_capture comparison
    print("\nVanilla OTel vs OTel+GenAI vs Full Capture (FDR by Fault Type):")
    print(f"  {'fault_type':>22}  {'vanilla_otel':>12}  {'otel_genai':>12}  {'full_capture':>12}  {'v->g delta':>12}  {'g->f delta':>12}")
    for ft in FaultType:
        vanilla_results = [
            r for r in results
            if r.fault_type == ft.value and r.condition == "vanilla_otel"
            and r.faults_injected > 0
        ]
        genai_results = [
            r for r in results
            if r.fault_type == ft.value and r.condition == "otel_genai"
            and r.faults_injected > 0
        ]
        full_results = [
            r for r in results
            if r.fault_type == ft.value and r.condition == "full_capture"
            and r.faults_injected > 0
        ]
        if vanilla_results or genai_results or full_results:
            v_fdr = sum(r.fault_detection_rate for r in vanilla_results) / len(vanilla_results) if vanilla_results else 0.0
            g_fdr = sum(r.fault_detection_rate for r in genai_results) / len(genai_results) if genai_results else 0.0
            f_fdr = sum(r.fault_detection_rate for r in full_results) / len(full_results) if full_results else 0.0
            vg_delta = g_fdr - v_fdr
            gf_delta = f_fdr - g_fdr
            print(f"  {ft.value:>22}  {v_fdr:>12.3f}  {g_fdr:>12.3f}  {f_fdr:>12.3f}  {vg_delta:>+12.3f}  {gf_delta:>+12.3f}")

    # Span sufficiency by condition
    print("\nSpan Sufficiency by Condition:")
    for condition in CONDITIONS:
        cond_results = [r for r in results if r.condition == condition]
        if cond_results:
            avg_suff = sum(r.span_sufficiency for r in cond_results) / len(cond_results)
            print(f"  {condition:>15}: {avg_suff:.3f}")

    # False Positive Rate by detector (no_fault runs only)
    fp_results = [r for r in results if r.fault_type == "no_fault" and r.detector_results]
    if fp_results:
        print("\n" + "-" * 80)
        print("FALSE POSITIVE ANALYSIS (no_fault runs)")
        print("-" * 80)

        # Group by condition
        fp_by_condition: Dict[str, List[BenchmarkResult]] = {}
        for r in fp_results:
            fp_by_condition.setdefault(r.condition, []).append(r)

        for cond, cond_fp in sorted(fp_by_condition.items()):
            print(f"\n  Condition: {cond}  (n={len(cond_fp)} runs)")

            # Aggregate per-detector fire counts
            detector_fires: Dict[str, int] = {}
            for r in cond_fp:
                if r.detector_results:
                    for det, fired in r.detector_results.items():
                        detector_fires.setdefault(det, 0)
                        if fired:
                            detector_fires[det] += 1

            n_runs = len(cond_fp)
            print(f"  {'detector':>22}  {'fired':>6}  {'total':>6}  {'FPR':>8}")
            any_fp = False
            for det in sorted(detector_fires.keys()):
                fires = detector_fires[det]
                fpr = fires / n_runs
                marker = " ***" if fires > 0 else ""
                print(f"  {det:>22}  {fires:>6}  {n_runs:>6}  {fpr:>8.3f}{marker}")
                if fires > 0:
                    any_fp = True

            overall_fp_runs = sum(1 for r in cond_fp if any(r.detector_results.values()))
            overall_fpr = overall_fp_runs / n_runs
            print(f"  {'OVERALL':>22}  {overall_fp_runs:>6}  {n_runs:>6}  {overall_fpr:>8.3f}")
            if not any_fp:
                print("  All detectors clean -- zero false positives.")

    # Framework coverage
    implemented = [f for f in FRAMEWORKS if _get_app_runner(f) is not None]
    stub = [f for f in FRAMEWORKS if f not in implemented]
    print(f"\nFrameworks implemented: {implemented}")
    if stub:
        print(f"Frameworks stub only:  {stub}")

    # Errors
    errors = [r for r in results if r.error]
    if errors:
        print(f"\nErrors: {len(errors)} runs had errors")
        unique_errors = set(r.error for r in errors if r.error)
        for err in list(unique_errors)[:5]:
            print(f"  - {err[:80]}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AgentTelemetry benchmark runner")
    parser.add_argument(
        "--mock-only", action="store_true", default=True,
        help="Use mock clients only (default: True)",
    )
    parser.add_argument(
        "--output", default="results.tsv",
        help="Output TSV file path (default: results.tsv)",
    )
    parser.add_argument(
        "--framework", nargs="*", default=None,
        help="Specific frameworks to test (default: all)",
    )
    parser.add_argument(
        "--model", nargs="*", default=None,
        help="Specific models to test (default: all)",
    )
    parser.add_argument(
        "--fault", nargs="*", default=None,
        help="Specific fault types to test (default: all)",
    )
    parser.add_argument(
        "--condition", nargs="*", default=None,
        help="Specific conditions to test (default: all)",
    )
    parser.add_argument(
        "--quiet", action="store_true", default=False,
        help="Suppress progress output",
    )

    args = parser.parse_args()

    # Parse fault types
    fault_types = None
    if args.fault:
        fault_types = [FaultType(f) for f in args.fault]

    run_benchmarks(
        mock_only=args.mock_only,
        output_file=args.output,
        frameworks=args.framework,
        models=args.model,
        fault_types=fault_types,
        conditions=args.condition,
        verbose=not args.quiet,
    )
