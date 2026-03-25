"""OpenAI SDK end-to-end integration test with AgentTelemetry.

Validates that the OpenAI SDK adapter (monkey-patching) works with
real API calls and produces correct span kinds.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from openai import OpenAI

from agenttelemetry.core.tracer import AgentTelemetryProvider
from agenttelemetry.core.privacy import PrivacyLevel
from agenttelemetry.core.spans import (
    AgentSpanKind, start_agent_span,
    AGENT_NAME, AGENT_FRAMEWORK, AGENT_TASK,
    PLANNING_STRATEGY, REASONING_CHAIN,
    MEMORY_OPERATION, MEMORY_KEY,
)
from agenttelemetry.adapters.openai_sdk import OpenAIInstrumentor
from agenttelemetry.analysis import AnomalyDetector, CostAggregator, DecisionAttributor

RESULTS_DIR = PROJECT_ROOT / "results" / "openai_sdk_e2e"


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("OpenAI SDK End-to-End Integration Test")
    print("=" * 60)

    provider = AgentTelemetryProvider(
        service_name="openai_sdk_e2e",
        privacy_level=PrivacyLevel.FULL,
    )
    json_exporter = provider.add_json_exporter(str(RESULTS_DIR / "traces.jsonl"))
    provider.setup(set_global=True)

    instrumentor = OpenAIInstrumentor()
    instrumentor.instrument(
        tracer_provider=provider.tracer_provider,
        privacy_level=PrivacyLevel.FULL,
    )

    client = OpenAI()
    tracer = provider.get_tracer("openai_e2e")

    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Evaluate a math expression",
                "parameters": {
                    "type": "object",
                    "properties": {"expression": {"type": "string"}},
                    "required": ["expression"],
                },
            },
        }
    ]

    questions = [
        "What is 42 * 17? Use the calculate tool.",
        "What is the square root of 144? Use the calculate tool.",
        "What is 2^10? Use the calculate tool.",
    ]

    print(f"\n[1/3] Running {len(questions)} questions with tool use...")

    for i, q in enumerate(questions):
        with start_agent_span(
            name=f"openai_agent_q{i+1}",
            kind=AgentSpanKind.AGENT,
            tracer=tracer,
            attributes={AGENT_NAME: "openai_calc_agent", AGENT_FRAMEWORK: "openai_sdk"},
        ):
            with start_agent_span(name="plan", kind=AgentSpanKind.PLANNING, tracer=tracer,
                                  attributes={PLANNING_STRATEGY: "direct_tool_use"}):
                pass

            # This call will be intercepted by the instrumentor
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": q}],
                tools=tools,
                max_tokens=200,
            )

            with start_agent_span(name="reason", kind=AgentSpanKind.REASONING, tracer=tracer,
                                  attributes={REASONING_CHAIN: f"Processing response for: {q[:30]}"}):
                pass

        print(f"  Q{i+1}: OK")

    provider.shutdown()

    # Analyze
    spans = json_exporter.get_exported_spans()
    print(f"\n[2/3] {len(spans)} spans exported")

    kind_counts = {}
    for s in spans:
        kind = s.get("agent_span_kind", "UNKNOWN") or "UNKNOWN"
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    for k, v in sorted(kind_counts.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    cost_report = CostAggregator().analyze(spans)

    print(f"\n[3/3] Validation:")
    checks = {
        "AGENT spans": kind_counts.get("AGENT", 0) >= 3,
        "LLM_CALL spans": kind_counts.get("LLM_CALL", 0) >= 3,
        "PLANNING spans": kind_counts.get("PLANNING", 0) >= 3,
        "REASONING spans": kind_counts.get("REASONING", 0) >= 3,
        "Cost tracked": cost_report.total_cost > 0,
        "Tokens tracked": cost_report.total_input_tokens > 0,
    }

    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {check}")

    summary = {
        "spans": len(spans),
        "kinds": kind_counts,
        "cost": cost_report.total_cost,
        "tokens_in": cost_report.total_input_tokens,
        "tokens_out": cost_report.total_output_tokens,
        "all_pass": all_pass,
    }

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'=' * 60}")
    print("ALL CHECKS PASSED" if all_pass else "SOME CHECKS FAILED")
    print(f"{'=' * 60}")
    return all_pass


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
