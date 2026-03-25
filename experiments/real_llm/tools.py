"""Tool definitions for real LLM experiment.

5 tools that produce different AgentTelemetry span kinds:
- search_kb -> RETRIEVAL
- calculator -> TOOL_CALL
- date_math -> TOOL_CALL
- unit_converter -> TOOL_CALL
- verify_answer -> GUARD_RAIL
"""

from __future__ import annotations

import ast
import json
import math
import operator
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND,
    GUARDRAIL_NAME,
    GUARDRAIL_RESULT,
    RETRIEVAL_DOC_COUNT,
    RETRIEVAL_QUERY,
    RETRIEVAL_SOURCE,
    TOOL_INPUT,
    TOOL_NAME,
    TOOL_OUTPUT,
    TOOL_STATUS,
    AgentSpanKind,
    start_agent_span,
)

from experiments.real_llm.knowledge_base import KB


def search_kb(query: str, tracer=None) -> str:
    """Fuzzy keyword search against the embedded knowledge base.

    Produces a RETRIEVAL span.
    """
    query_lower = query.lower()
    results = []

    for key, entry in KB.items():
        score = 0
        for field_name, field_value in entry.items():
            if query_lower in field_value.lower():
                score += 2
            for word in query_lower.split():
                if word in field_value.lower() or word in key.lower():
                    score += 1
        if score > 0:
            results.append((score, key, entry))

    results.sort(reverse=True, key=lambda x: x[0])
    top_results = results[:3]

    if not top_results:
        output = json.dumps({"results": [], "message": "No matching entries found"})
    else:
        formatted = []
        for _, key, entry in top_results:
            formatted.append({"id": key, **entry})
        output = json.dumps({"results": formatted})

    with start_agent_span(
        name=f"search_kb({query[:50]})",
        kind=AgentSpanKind.RETRIEVAL,
        tracer=tracer,
        attributes={
            RETRIEVAL_QUERY: query,
            RETRIEVAL_SOURCE: "embedded_kb",
            RETRIEVAL_DOC_COUNT: len(top_results),
            TOOL_OUTPUT: output,
        },
    ):
        pass

    return output


# Safe operators for calculator
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "int": int,
    "float": float,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node):
    """Safely evaluate an AST math expression."""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant: {node.value}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type.__name__}")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        return _SAFE_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _SAFE_OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
        return _SAFE_OPERATORS[op_type](_safe_eval(node.operand))
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _SAFE_FUNCTIONS:
            args = [_safe_eval(arg) for arg in node.args]
            return _SAFE_FUNCTIONS[node.func.id](*args)
        raise ValueError(f"Unsupported function call")
    elif isinstance(node, ast.Name):
        if node.id in _SAFE_FUNCTIONS:
            return _SAFE_FUNCTIONS[node.id]
        raise ValueError(f"Unknown name: {node.id}")
    else:
        raise ValueError(f"Unsupported expression type: {type(node).__name__}")


def calculator(expression: str, tracer=None) -> str:
    """Safe AST-based math evaluation.

    Produces a TOOL_CALL span.
    """
    status = "OK"
    try:
        tree = ast.parse(expression, mode="eval")
        result = _safe_eval(tree)
        output = json.dumps({"result": result, "expression": expression})
    except Exception as e:
        status = "ERROR"
        output = json.dumps({"error": str(e), "expression": expression})

    with start_agent_span(
        name=f"calculator({expression[:50]})",
        kind=AgentSpanKind.TOOL_CALL,
        tracer=tracer,
        attributes={
            TOOL_NAME: "calculator",
            TOOL_INPUT: expression,
            TOOL_OUTPUT: output,
            TOOL_STATUS: status,
        },
    ):
        pass

    return output


def date_math(
    operation: str,
    date1: Optional[str] = None,
    date2: Optional[str] = None,
    days: Optional[int] = None,
    tracer=None,
) -> str:
    """Date/time operations.

    Operations: 'diff' (days between two dates), 'add' (add days to date),
    'subtract' (subtract days from date), 'day_of_week' (get day name).

    Produces a TOOL_CALL span.
    """
    status = "OK"
    input_str = json.dumps({"operation": operation, "date1": date1, "date2": date2, "days": days})

    try:
        if operation == "diff":
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            d2 = datetime.strptime(date2, "%Y-%m-%d")
            delta = (d2 - d1).days
            output = json.dumps({"result": delta, "unit": "days"})
        elif operation == "add":
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            result = d1 + timedelta(days=days)
            output = json.dumps({"result": result.strftime("%Y-%m-%d")})
        elif operation == "subtract":
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            result = d1 - timedelta(days=days)
            output = json.dumps({"result": result.strftime("%Y-%m-%d")})
        elif operation == "day_of_week":
            d1 = datetime.strptime(date1, "%Y-%m-%d")
            output = json.dumps({"result": d1.strftime("%A")})
        else:
            output = json.dumps({"error": f"Unknown operation: {operation}"})
            status = "ERROR"
    except Exception as e:
        status = "ERROR"
        output = json.dumps({"error": str(e)})

    with start_agent_span(
        name=f"date_math({operation})",
        kind=AgentSpanKind.TOOL_CALL,
        tracer=tracer,
        attributes={
            TOOL_NAME: "date_math",
            TOOL_INPUT: input_str,
            TOOL_OUTPUT: output,
            TOOL_STATUS: status,
        },
    ):
        pass

    return output


# Unit conversion tables
_CONVERSIONS = {
    ("meters", "feet"): 3.28084,
    ("feet", "meters"): 0.3048,
    ("km", "miles"): 0.621371,
    ("miles", "km"): 1.60934,
    ("kg", "pounds"): 2.20462,
    ("pounds", "kg"): 0.453592,
    ("celsius", "fahrenheit"): None,  # special
    ("fahrenheit", "celsius"): None,  # special
    ("liters", "gallons"): 0.264172,
    ("gallons", "liters"): 3.78541,
    ("m/s", "km/h"): 3.6,
    ("km/h", "m/s"): 1 / 3.6,
    ("m/s", "mph"): 2.23694,
    ("mph", "m/s"): 0.44704,
    ("meters", "km"): 0.001,
    ("km", "meters"): 1000,
    ("nm", "meters"): 1e-9,
    ("meters", "nm"): 1e9,
}


def unit_converter(value: float, from_unit: str, to_unit: str, tracer=None) -> str:
    """Unit conversion using a lookup table.

    Produces a TOOL_CALL span.
    """
    status = "OK"
    input_str = json.dumps({"value": value, "from": from_unit, "to": to_unit})

    try:
        key = (from_unit.lower(), to_unit.lower())
        if key == ("celsius", "fahrenheit"):
            result = value * 9 / 5 + 32
        elif key == ("fahrenheit", "celsius"):
            result = (value - 32) * 5 / 9
        elif key in _CONVERSIONS:
            factor = _CONVERSIONS[key]
            result = value * factor
        else:
            status = "ERROR"
            result = None
            output = json.dumps({"error": f"Unsupported conversion: {from_unit} -> {to_unit}"})
    except Exception as e:
        status = "ERROR"
        output = json.dumps({"error": str(e)})
        result = None

    if result is not None:
        output = json.dumps({"result": result, "from": from_unit, "to": to_unit})

    with start_agent_span(
        name=f"unit_converter({from_unit}->{to_unit})",
        kind=AgentSpanKind.TOOL_CALL,
        tracer=tracer,
        attributes={
            TOOL_NAME: "unit_converter",
            TOOL_INPUT: input_str,
            TOOL_OUTPUT: output,
            TOOL_STATUS: status,
        },
    ):
        pass

    return output


def verify_answer(
    computed: float,
    expected: float,
    tolerance: float = 0.01,
    tracer=None,
) -> str:
    """Verify a computed answer against expected value.

    Produces a GUARD_RAIL span.
    """
    if expected == 0:
        passed = abs(computed) <= tolerance
    else:
        relative_error = abs(computed - expected) / abs(expected)
        passed = relative_error <= tolerance

    result = "PASS" if passed else "FAIL"
    output = json.dumps({
        "result": result,
        "computed": computed,
        "expected": expected,
        "tolerance": tolerance,
        "relative_error": abs(computed - expected) / max(abs(expected), 1e-10),
    })

    with start_agent_span(
        name="verify_answer",
        kind=AgentSpanKind.GUARD_RAIL,
        tracer=tracer,
        attributes={
            GUARDRAIL_NAME: "answer_verification",
            GUARDRAIL_RESULT: result,
            TOOL_OUTPUT: output,
        },
    ):
        pass

    return output


# ---------------------------------------------------------------------------
# Tool definitions for LLM function calling
# ---------------------------------------------------------------------------

_TOOL_SPECS = [
    {
        "name": "search_kb",
        "description": "Search the knowledge base for factual information. Returns matching entries with their properties.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant knowledge base entries",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Evaluate a mathematical expression. Supports +, -, *, /, **, sqrt(), log(), round(), abs(), and constants pi, e.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate, e.g. '330 * 3.28084' or 'sqrt(144)'",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "date_math",
        "description": "Perform date arithmetic. Operations: 'diff' (days between dates), 'add' (add days), 'subtract' (subtract days), 'day_of_week'.",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["diff", "add", "subtract", "day_of_week"],
                    "description": "The date operation to perform",
                },
                "date1": {
                    "type": "string",
                    "description": "First date in YYYY-MM-DD format",
                },
                "date2": {
                    "type": "string",
                    "description": "Second date in YYYY-MM-DD format (for 'diff' operation)",
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to add/subtract",
                },
            },
            "required": ["operation", "date1"],
        },
    },
    {
        "name": "unit_converter",
        "description": "Convert between units. Supports: meters/feet, km/miles, kg/pounds, celsius/fahrenheit, liters/gallons, m/s/km/h/mph, nm/meters.",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "number",
                    "description": "The numeric value to convert",
                },
                "from_unit": {
                    "type": "string",
                    "description": "Source unit (e.g. 'meters', 'celsius', 'km/h')",
                },
                "to_unit": {
                    "type": "string",
                    "description": "Target unit (e.g. 'feet', 'fahrenheit', 'mph')",
                },
            },
            "required": ["value", "from_unit", "to_unit"],
        },
    },
    {
        "name": "verify_answer",
        "description": "Verify a computed numerical answer against an expected value within a tolerance.",
        "parameters": {
            "type": "object",
            "properties": {
                "computed": {
                    "type": "number",
                    "description": "The computed answer to verify",
                },
                "expected": {
                    "type": "number",
                    "description": "The expected correct answer",
                },
                "tolerance": {
                    "type": "number",
                    "description": "Acceptable relative error (default 0.01 = 1%)",
                },
            },
            "required": ["computed", "expected"],
        },
    },
]


def get_tool_definitions(provider: str, exclude_tools: Optional[List[str]] = None) -> list:
    """Return tool definitions formatted for the given provider.

    Args:
        provider: "openai" or "anthropic"
        exclude_tools: Optional list of tool names to exclude
    """
    specs = _TOOL_SPECS
    if exclude_tools:
        specs = [s for s in specs if s["name"] not in exclude_tools]

    if provider == "openai":
        return [
            {
                "type": "function",
                "function": {
                    "name": spec["name"],
                    "description": spec["description"],
                    "parameters": spec["parameters"],
                },
            }
            for spec in specs
        ]
    elif provider == "anthropic":
        return [
            {
                "name": spec["name"],
                "description": spec["description"],
                "input_schema": spec["parameters"],
            }
            for spec in specs
        ]
    else:
        raise ValueError(f"Unknown provider: {provider}")


def execute_tool(tool_name: str, arguments: Dict[str, Any], tracer=None) -> str:
    """Execute a tool by name with given arguments."""
    if tool_name == "search_kb":
        return search_kb(arguments.get("query", ""), tracer=tracer)
    elif tool_name == "calculator":
        return calculator(arguments.get("expression", ""), tracer=tracer)
    elif tool_name == "date_math":
        return date_math(
            operation=arguments.get("operation", ""),
            date1=arguments.get("date1"),
            date2=arguments.get("date2"),
            days=arguments.get("days"),
            tracer=tracer,
        )
    elif tool_name == "unit_converter":
        return unit_converter(
            value=float(arguments.get("value", 0)),
            from_unit=arguments.get("from_unit", ""),
            to_unit=arguments.get("to_unit", ""),
            tracer=tracer,
        )
    elif tool_name == "verify_answer":
        return verify_answer(
            computed=float(arguments.get("computed", 0)),
            expected=float(arguments.get("expected", 0)),
            tolerance=float(arguments.get("tolerance", 0.01)),
            tracer=tracer,
        )
    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
