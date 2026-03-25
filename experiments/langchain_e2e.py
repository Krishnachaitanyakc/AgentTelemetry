"""End-to-end LangChain integration test with real OpenAI API calls.

Runs a REAL LangChain ReAct agent with the AgentTelemetry callback handler
against real OpenAI APIs. Validates that:
1. The LangChainInstrumentor callback handler works with real LangChain code
2. All expected span kinds are produced (AGENT, LLM_CALL, TOOL_CALL, PLANNING)
3. Span attributes are correctly populated (model, tokens, cost, tool names)
4. The AnomalyDetector, CostAggregator, and DecisionAttributor run on real traces
5. Fault detection works on real LangChain agent traces
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")


def run_langchain_e2e():
    """Run end-to-end LangChain agent with AgentTelemetry instrumentation."""
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool
    from langchain_classic.agents import AgentExecutor, create_react_agent
    from langchain_core.prompts import PromptTemplate

    from agenttelemetry.core.tracer import AgentTelemetryProvider
    from agenttelemetry.core.privacy import PrivacyLevel
    from agenttelemetry.adapters.langchain import LangChainInstrumentor
    from agenttelemetry.analysis import (
        AnomalyDetector,
        CostAggregator,
        DecisionAttributor,
    )

    RESULTS_DIR = PROJECT_ROOT / "results" / "langchain_e2e"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Set up AgentTelemetry ---
    print("=" * 60)
    print("LangChain End-to-End Integration Test")
    print("=" * 60)

    provider = AgentTelemetryProvider(
        service_name="langchain_e2e_test",
        privacy_level=PrivacyLevel.FULL,
    )
    json_exporter = provider.add_json_exporter(
        str(RESULTS_DIR / "langchain_traces.jsonl")
    )
    provider.setup(set_global=True)

    # --- Step 2: Instrument LangChain ---
    instrumentor = LangChainInstrumentor()
    instrumentor.instrument(
        tracer_provider=provider.tracer_provider,
        privacy_level=PrivacyLevel.FULL,
    )
    handler = instrumentor.get_callback_handler()

    print("\n[1/5] AgentTelemetry + LangChain instrumentation configured")

    # --- Step 3: Define real tools ---
    @tool
    def calculator(expression: str) -> str:
        """Evaluate a math expression. Use Python syntax like '2 + 3' or '100 / 7'."""
        import ast
        import operator

        ops = {
            ast.Add: operator.add, ast.Sub: operator.sub,
            ast.Mult: operator.mul, ast.Div: operator.truediv,
            ast.Pow: operator.pow, ast.USub: operator.neg,
        }

        def _eval(node):
            if isinstance(node, ast.Expression):
                return _eval(node.body)
            elif isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.BinOp):
                return ops[type(node.op)](_eval(node.left), _eval(node.right))
            elif isinstance(node, ast.UnaryOp):
                return ops[type(node.op)](_eval(node.operand))
            raise ValueError(f"Unsupported: {type(node)}")

        try:
            tree = ast.parse(expression, mode="eval")
            result = _eval(tree)
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {e}"

    @tool
    def lookup_fact(query: str) -> str:
        """Look up a factual answer from a knowledge base."""
        facts = {
            "eiffel tower height": "The Eiffel Tower is 330 meters tall.",
            "speed of light": "The speed of light is 299,792,458 meters per second.",
            "earth diameter": "Earth's diameter is 12,742 km.",
            "moon distance": "The Moon is 384,400 km from Earth.",
            "mars orbital period": "Mars has an orbital period of 687 days.",
            "mount everest height": "Mount Everest is 8,849 meters tall.",
        }
        query_lower = query.lower()
        for key, value in facts.items():
            if any(word in query_lower for word in key.split()):
                return value
        return f"No fact found for: {query}"

    tools = [calculator, lookup_fact]

    # --- Step 4: Create a real LangChain ReAct agent ---
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # ReAct prompt template
    react_prompt = PromptTemplate.from_template(
        """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
    )

    agent = create_react_agent(llm, tools, react_prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        max_iterations=6,
        handle_parsing_errors=True,
    )

    print("[2/5] LangChain ReAct agent created with 2 tools (calculator, lookup_fact)")

    # --- Step 5: Run questions through the real agent ---
    questions = [
        "What is the height of the Eiffel Tower in feet? Look it up and convert using the calculator.",
        "How many Mount Everests stacked would reach the Moon? Look up both values and calculate.",
        "What is the speed of light in km/h? Look it up and convert from m/s.",
    ]

    results = []
    for i, question in enumerate(questions, 1):
        print(f"\n  Q{i}: {question[:60]}...", end=" ", flush=True)
        try:
            result = agent_executor.invoke(
                {"input": question},
                config={"callbacks": [handler]},
            )
            answer = result.get("output", "")
            print(f"OK — {answer[:50]}...")
            results.append({"question": question, "answer": answer, "error": None})
        except Exception as e:
            print(f"ERROR — {e}")
            results.append({"question": question, "answer": "", "error": str(e)})

    print(f"\n[3/5] {len(results)} questions answered")

    # --- Step 6: Flush traces and analyze ---
    provider.shutdown()

    # Read exported spans
    spans = json_exporter.get_exported_spans()
    print(f"[4/5] {len(spans)} spans exported")

    # Analyze span kinds
    kind_counts = {}
    for s in spans:
        kind = s.get("agent_span_kind", "UNKNOWN") or "UNKNOWN"
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    print(f"\n  Span Kind Distribution:")
    for kind, count in sorted(kind_counts.items(), key=lambda x: -x[1]):
        print(f"    {kind:<15} {count}")

    # Run analysis modules
    detector = AnomalyDetector(max_retries=3, cost_threshold=0.10, token_growth_factor=1.5)
    aggregator = CostAggregator()
    attributor = DecisionAttributor()

    anomalies = detector.detect(spans)
    cost_report = aggregator.analyze(spans)
    decisions = attributor.analyze(spans)

    print(f"\n  Analysis Results:")
    print(f"    Anomalies detected: {len(anomalies)}")
    for a in anomalies:
        print(f"      [{a.severity}] {a.anomaly_type.value}: {a.description[:70]}")
    print(f"    Total cost: ${cost_report.total_cost:.6f}")
    print(f"    Total tokens: {cost_report.total_input_tokens} in / {cost_report.total_output_tokens} out")
    print(f"    Tool decisions traced: {len(decisions)}")
    for d in decisions[:5]:
        print(f"      {d.tool_name} → decided by {d.llm_model}")

    # --- Step 7: Validate expected spans ---
    print(f"\n[5/5] Validation:")
    checks = {
        "AGENT spans present": kind_counts.get("AGENT", 0) > 0,
        "LLM_CALL spans present": kind_counts.get("LLM_CALL", 0) > 0,
        "TOOL_CALL spans present": kind_counts.get("TOOL_CALL", 0) > 0,
        "PLANNING spans present": kind_counts.get("PLANNING", 0) > 0,
        "REASONING spans present": kind_counts.get("REASONING", 0) > 0,
        "Cost > $0": cost_report.total_cost > 0,
        "Token counts > 0": cost_report.total_input_tokens > 0,
        "Tool decisions traced": len(decisions) > 0,
        "All questions answered": all(r["error"] is None for r in results),
    }

    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"    [{status}] {check}")

    # Save results
    summary = {
        "questions": len(questions),
        "answers": len([r for r in results if r["error"] is None]),
        "total_spans": len(spans),
        "span_kinds": kind_counts,
        "anomalies": len(anomalies),
        "total_cost": cost_report.total_cost,
        "total_input_tokens": cost_report.total_input_tokens,
        "total_output_tokens": cost_report.total_output_tokens,
        "tool_decisions": len(decisions),
        "checks": {k: v for k, v in checks.items()},
        "all_pass": all_pass,
    }

    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    with open(RESULTS_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    if all_pass:
        print("ALL CHECKS PASSED — LangChain E2E integration validated")
    else:
        print("SOME CHECKS FAILED — see details above")
    print(f"Results saved to: {RESULTS_DIR}")
    print(f"{'=' * 60}")

    return all_pass


if __name__ == "__main__":
    success = run_langchain_e2e()
    sys.exit(0 if success else 1)
