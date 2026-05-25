#!/usr/bin/env python3
"""Optional live-LLM CLI sanity check.

This script exercises three locally configured agent CLIs on tiny trace
construction tasks, then scores the returned spans with the same executable
predicates used by the benchmark. It is intentionally outside the default
reproduction path because it depends on local CLI authentication.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trace_detectors import detect, fires_any


SCENARIOS = ("no_fault", "wrong_tool", "circular_delegation")
PROVIDER_ALIASES = {
    "cli-a": "cli-A",
    "cli-b": "cli-B",
    "cli-c": "cli-C",
}
PROVIDER_COMMAND_ENVS = {
    "cli-a": "AGENTTELEMETRY_CLI_A_CMD",
    "cli-b": "AGENTTELEMETRY_CLI_B_CMD",
    "cli-c": "AGENTTELEMETRY_CLI_C_CMD",
}
FIELDNAMES = [
    "provider_alias",
    "scenario",
    "trial",
    "exit_code",
    "parsed",
    "expected_detection",
    "detected",
    "span_count",
    "notes",
]


@dataclass(frozen=True)
class CliResult:
    exit_code: int
    response: str
    notes: str


def scenario_prompt(alias: str, scenario: str, trial: int) -> str:
    if scenario == "no_fault":
        task = "Choose the one best tool for answering: 'Find the project status note.' Available tools are search and calculator."
    elif scenario == "wrong_tool":
        task = "Choose the one best tool for answering: 'Retrieve the supporting document for the claim.' Available tools are retriever and calculator."
    elif scenario == "circular_delegation":
        task = "Choose the one best delegate for a research subtask. Available delegates are agent-b and agent-c."
    else:
        raise ValueError(f"unknown scenario: {scenario}")

    return (
        "Return exactly one compact JSON object and nothing else. "
        "Use keys selected_tool, delegate_to, and rationale. "
        "If no tool is needed use null for selected_tool; if no delegation is needed use null for delegate_to. "
        "Keep rationale under eight words. "
        f"Scenario id: {alias}-{scenario}-{trial}. {task}"
    )


def build_command(template: str, *, prompt: str, output: Path, cwd: Path) -> list[str]:
    replacements = {
        "{prompt}": prompt,
        "{output}": str(output),
        "{cwd}": str(cwd),
    }
    return [replacements.get(part, part) for part in shlex.split(template)]


def run_configured_cli(provider: str, prompt: str, timeout: int) -> CliResult:
    env_name = PROVIDER_COMMAND_ENVS[provider]
    template = os.environ.get(env_name)
    if not template:
        return CliResult(127, "", f"{env_name}_not_set")
    with tempfile.TemporaryDirectory(prefix=f"agenttelemetry_{provider}_") as tmp_name:
        tmp = Path(tmp_name)
        out = tmp / "response.txt"
        cmd = build_command(template, prompt=prompt, output=out, cwd=tmp)
        result = run_command(cmd, timeout, cwd=str(tmp))
        if out.exists():
            return CliResult(result.exit_code, out.read_text(), result.notes)
        return result


def run_command(cmd: list[str], timeout: int, cwd: str | None = None) -> CliResult:
    try:
        process = subprocess.Popen(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            cwd=cwd,
        )
        stdout, _stderr = process.communicate(timeout=timeout)
    except FileNotFoundError:
        return CliResult(127, "", "cli_not_found")
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        return CliResult(124, "", "timeout")
    return CliResult(process.returncode, stdout.strip(), "")


def extract_json_object(text: str) -> dict[str, Any] | None:
    starts = [i for i, char in enumerate(text) if char == "{"]
    for start in starts:
        depth = 0
        in_string = False
        escape = False
        for pos in range(start, len(text)):
            char = text[pos]
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : pos + 1]
                    try:
                        parsed = json.loads(candidate)
                    except json.JSONDecodeError:
                        break
                    if isinstance(parsed, dict):
                        return parsed
                    break
    return None


def trace_from_action(parsed: dict[str, Any], alias: str, scenario: str, trial: int) -> dict[str, Any]:
    selected_tool = parsed.get("selected_tool")
    if not isinstance(selected_tool, str):
        selected_tool = "search"
    delegate_to = parsed.get("delegate_to")
    if not isinstance(delegate_to, str):
        delegate_to = "agent-b"
    spans: list[dict[str, Any]] = [
        {
            "span_id": "s0",
            "parent_id": None,
            "kind": "AGENT",
            "name": "agent.run",
            "attributes": {"agent.id": "agent-main", "agent.role": "worker"},
        },
        {
            "span_id": "s1",
            "parent_id": "s0",
            "kind": "LLM_CALL",
            "name": "llm.call",
            "attributes": {
                "llm.input_tokens": 512,
                "llm.output_tokens": 64,
                "llm.context_limit": 8192,
                "llm.cost": 0.004,
            },
        },
    ]
    if scenario == "no_fault":
        spans.append(
            {
                "span_id": "s2",
                "parent_id": "s0",
                "kind": "TOOL_CALL",
                "name": "tool.call",
                "attributes": {"tool.name": selected_tool, "status": "OK", "duration_ms": 120},
            }
        )
    elif scenario == "wrong_tool":
        spans.append(
            {
                "span_id": "s2",
                "parent_id": "s0",
                "kind": "TOOL_CALL",
                "name": "tool.call",
                "attributes": {
                    "tool.name": "calculator",
                    "expected_tool": selected_tool,
                    "status": "OK",
                    "duration_ms": 90,
                },
            }
        )
    elif scenario == "circular_delegation":
        spans.extend(
            [
                {
                    "span_id": "s2",
                    "parent_id": "s0",
                    "kind": "DELEGATION",
                    "name": "delegate",
                    "attributes": {"delegation.source_agent": "agent-a", "delegation.target_agent": delegate_to},
                },
                {
                    "span_id": "s3",
                    "parent_id": "s2",
                    "kind": "DELEGATION",
                    "name": "delegate",
                    "attributes": {"delegation.source_agent": delegate_to, "delegation.target_agent": "agent-a"},
                },
            ]
        )
    return {
        "run_id": f"{alias}:metadata_only:{scenario}:{trial}",
        "framework": "cli_agent",
        "model": alias,
        "condition": "metadata_only",
        "fault_type": scenario,
        "spans": spans,
    }


def score_trace(trace: dict[str, Any]) -> bool:
    scenario = str(trace["fault_type"])
    if scenario == "no_fault":
        return fires_any("metadata_only", trace["spans"])
    return detect("metadata_only", trace["spans"], scenario)


def provider_order(value: str) -> list[str]:
    if value == "all":
        return ["cli-a", "cli-b", "cli-c"]
    requested = [item.strip() for item in value.split(",") if item.strip()]
    unknown = [item for item in requested if item not in PROVIDER_ALIASES]
    if unknown:
        raise SystemExit(f"unknown providers: {', '.join(unknown)}")
    return requested


def run_provider(provider: str, prompt: str, timeout: int) -> CliResult:
    if provider not in PROVIDER_ALIASES:
        raise ValueError(provider)
    return run_configured_cli(provider, prompt, timeout)


def write_rows(args: argparse.Namespace) -> int:
    providers = provider_order(args.providers)
    scenarios = [item.strip() for item in args.scenarios.split(",") if item.strip()]
    unknown_scenarios = [item for item in scenarios if item not in SCENARIOS]
    if unknown_scenarios:
        raise SystemExit(f"unknown scenarios: {', '.join(unknown_scenarios)}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter="\t")
        writer.writeheader()
        for provider in providers:
            alias = PROVIDER_ALIASES[provider]
            for scenario in scenarios:
                expected = scenario != "no_fault"
                for trial in range(1, args.trials + 1):
                    prompt = scenario_prompt(alias, scenario, trial)
                    result = run_provider(provider, prompt, args.timeout)
                    parsed = extract_json_object(result.response)
                    detected = False
                    span_count = 0
                    notes = result.notes
                    if parsed is None:
                        notes = notes or "json_parse_failed"
                    else:
                        trace = trace_from_action(parsed, alias, scenario, trial)
                        span_count = len(trace["spans"])
                        detected = score_trace(trace)
                        if detected != expected:
                            notes = notes or "unexpected_detector_outcome"
                    writer.writerow(
                        {
                            "provider_alias": alias,
                            "scenario": scenario,
                            "trial": trial,
                            "exit_code": result.exit_code,
                            "parsed": int(parsed is not None),
                            "expected_detection": int(expected),
                            "detected": int(detected),
                            "span_count": span_count,
                            "notes": notes,
                        }
                    )
                    count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--providers", default="all", help="comma-separated cli-a,cli-b,cli-c or all")
    parser.add_argument("--scenarios", default="no_fault,wrong_tool,circular_delegation")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--output", default="real_llm_sanity.tsv")
    args = parser.parse_args()
    count = write_rows(args)
    print(f"wrote {args.output}")
    print(f"rows: {count}")


if __name__ == "__main__":
    main()
