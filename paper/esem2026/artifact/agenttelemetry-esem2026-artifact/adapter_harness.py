"""Executable adapter/fault-injection harness for the trace corpus.

The benchmark intentionally uses mocked model clients so every adapter sees
the same workload and fault schedule. This module is the trace-producing
layer: adapter profiles emit condition-specific spans, and fault injectors
mutate the adapter run before detector scoring.
"""

from __future__ import annotations

from dataclasses import dataclass


ADAPTERS = [
    "langchain",
    "crewai",
    "autogen",
    "llamaindex",
    "anthropic_sdk",
    "openai_sdk",
    "custom_agent",
]
MODELS = ["model-A1", "model-A2", "model-A3", "model-B1", "model-B2", "model-B3"]
CONDITIONS = [
    "no_telemetry",
    "vanilla_otel",
    "otel_genai",
    "openinference",
    "metadata_only",
    "full_capture",
]
NO_FAULT_SCENARIOS = [
    "simple_success",
    "writer_repeat",
    "planning_review",
    "guardrail_pass",
    "retrieval_refresh",
    "memory_lookup",
]
FAULTS = [
    "wrong_tool",
    "tool_failure",
    "timeout",
    "infinite_loop",
    "context_overflow",
    "cost_explosion",
    "circular_delegation",
    "agent_misroute",
    "planning_failure",
    "reasoning_loop",
    "guardrail_bypass",
    "hallucination",
    "memory_corruption",
    "stale_retrieval",
]

EASY_FAULTS = {
    "wrong_tool",
    "tool_failure",
    "timeout",
    "infinite_loop",
    "context_overflow",
    "cost_explosion",
}
CREWAI_FP_REPETITIONS = {
    "model-A1": 4,
    "model-A2": 3,
    "model-A3": 2,
}
PERMISSIVE_CONTROL_NOISE = {
    "openinference": {
        "openai_sdk": {"model-A1", "model-A2"},
    },
}
PERMISSIVE_EXTRA = {
    "otel_genai": {"planning_failure"},
    "openinference": {"guardrail_bypass"},
}
EXTENDED_EXTRA = {
    "otel_genai": {"reasoning_loop"},
    "openinference": {"reasoning_loop"},
}


@dataclass(frozen=True)
class AdapterProfile:
    name: str
    supports_full_dsm: bool = False
    easy_faults: frozenset[str] = frozenset(EASY_FAULTS)
    emits_delegation: bool = False
    emits_guardrail: bool = False
    emits_agent_role_verifier: bool = False


PROFILES = {
    "langchain": AdapterProfile("langchain"),
    "crewai": AdapterProfile("crewai"),
    "autogen": AdapterProfile("autogen", emits_delegation=True),
    "llamaindex": AdapterProfile("llamaindex"),
    "anthropic_sdk": AdapterProfile(
        "anthropic_sdk",
        easy_faults=frozenset({"context_overflow", "cost_explosion"}),
    ),
    "openai_sdk": AdapterProfile(
        "openai_sdk",
        emits_delegation=True,
        emits_guardrail=True,
        emits_agent_role_verifier=True,
    ),
    "custom_agent": AdapterProfile(
        "custom_agent",
        supports_full_dsm=True,
        emits_delegation=True,
        emits_guardrail=True,
        emits_agent_role_verifier=True,
    ),
}


def span(
    span_id: str,
    kind: str,
    name: str,
    attributes: dict[str, object],
    parent_id: str | None = None,
) -> dict[str, object]:
    return {
        "span_id": span_id,
        "parent_id": parent_id,
        "kind": kind,
        "name": name,
        "attributes": attributes,
    }


class AdapterRun:
    """One deterministic mocked adapter execution."""

    def __init__(self, adapter: str, model: str, condition: str, control_scenario: str = "default") -> None:
        self.profile = PROFILES[adapter]
        self.adapter = adapter
        self.model = model
        self.condition = condition
        self.control_scenario = control_scenario
        self.spans: list[dict[str, object]] = []

    def emit_base_run(self, fault: str) -> None:
        if self.condition == "no_telemetry":
            return

        kind_agent = "AGENT" if self.condition in {"metadata_only", "full_capture", "openinference"} else "INTERNAL"
        kind_llm = "LLM_CALL" if self.condition in {"metadata_only", "full_capture"} else "CLIENT"
        kind_tool = "TOOL_CALL" if self.condition in {"metadata_only", "full_capture"} else "CLIENT"
        self.spans.extend(
            [
                span("s0", kind_agent, "agent.run", {"agent.id": "agent-main", "agent.role": "worker"}),
                span(
                    "s1",
                    kind_llm,
                    "llm.call",
                    {
                        "llm.input_tokens": 512,
                        "llm.output_tokens": 64,
                        "llm.context_limit": 8192,
                        "llm.cost": 0.004,
                    },
                    "s0",
                ),
                span("s2", kind_tool, "tool.call", {"tool.name": "search", "status": "OK", "duration_ms": 120}, "s0"),
            ]
        )
        self.emit_known_no_fault_noise(fault)

    def emit_known_no_fault_noise(self, fault: str) -> None:
        """Emit pre-registered no-fault control workflows."""
        if fault != "no_fault":
            return
        if self.control_scenario == "default":
            self.emit_default_no_fault_noise()
            return
        if self.control_scenario == "simple_success":
            return
        if self.control_scenario == "writer_repeat":
            self.emit_crewai_writer_repeat_noise()
        elif self.control_scenario == "planning_review":
            self.spans.append(
                span(
                    "nf_plan_review",
                    "PLANNING",
                    "planning.review",
                    {"plan.status": "ok", "plan.executable_steps": 2},
                    "s0",
                )
            )
        elif self.control_scenario == "guardrail_pass":
            self.spans.append(
                span(
                    "nf_guardrail_pass",
                    "GUARD_RAIL",
                    "guardrail.check",
                    {"guardrail.result": "pass"},
                    "s0",
                )
            )
        elif self.control_scenario == "retrieval_refresh":
            self.spans.append(
                span(
                    "nf_retrieval_refresh",
                    "RETRIEVAL",
                    "retrieval.fetch",
                    {"retrieval.staleness_seconds": 0, "retrieval.doc_count": 4},
                    "s0",
                )
            )
        elif self.control_scenario == "memory_lookup":
            self.spans.append(
                span(
                    "nf_memory_lookup",
                    "MEMORY",
                    "memory.read",
                    {"memory.owner_agent": "agent-main", "agent.id": "agent-main", "memory.key": "task_state"},
                    "s0",
                )
            )
        else:
            raise ValueError(f"unknown no-fault scenario: {self.control_scenario}")

    def emit_default_no_fault_noise(self) -> None:
        """Reproduce the original one-workflow controls exactly."""
        self.emit_crewai_writer_repeat_noise()
        if self.condition in PERMISSIVE_CONTROL_NOISE:
            noisy_models = PERMISSIVE_CONTROL_NOISE[self.condition].get(self.adapter, set())
            if self.model in noisy_models:
                noise_name = {
                    "vanilla_otel": "reasoning-guardrail-review",
                    "otel_genai": "planning-review",
                    "openinference": "guardrail-review",
                }[self.condition]
                self.spans.append(
                    span(
                        "fp_permissive_name",
                        "INTERNAL",
                        noise_name,
                        {"status": "OK"},
                        "s0",
                    )
                )

    def emit_crewai_writer_repeat_noise(self) -> None:
        if (
            self.adapter == "crewai"
            and self.condition in {"metadata_only", "full_capture"}
            and self.model in CREWAI_FP_REPETITIONS
        ):
            for i in range(CREWAI_FP_REPETITIONS[self.model]):
                self.spans.append(
                    span(
                        f"fp{i}",
                        "TOOL_CALL",
                        "writer.tool.repeat",
                        {"tool.name": "writer_lookup", "status": "OK", "duration_ms": 80},
                        "s0",
                    )
                )

    def inject_fault(self, fault: str) -> None:
        if fault == "no_fault" or self.condition == "no_telemetry":
            return
        if self.condition in {"vanilla_otel", "otel_genai", "openinference"}:
            BaselineFaultInjector(self).inject(fault)
        elif self.condition in {"metadata_only", "full_capture"}:
            DSMFaultInjector(self).inject(fault)
        else:
            raise ValueError(f"unknown condition: {self.condition}")


class BaselineFaultInjector:
    """Faults visible through standardized LLM/tool attributes."""

    def __init__(self, run: AdapterRun) -> None:
        self.run = run

    def inject(self, fault: str) -> None:
        if fault not in EASY_FAULTS:
            inject_secondary_evidence(self.run, fault)
            return
        if fault in self.run.profile.easy_faults:
            inject_easy_fault(self.run.spans, fault)


class DSMFaultInjector(BaselineFaultInjector):
    """Faults visible when adapter profiles emit the relevant DSM span kind."""

    def inject(self, fault: str) -> None:
        if fault == "infinite_loop" and fault in self.run.profile.easy_faults:
            inject_dsm_infinite_loop(self.run)
        elif fault in EASY_FAULTS and fault in self.run.profile.easy_faults:
            inject_easy_fault(self.run.spans, fault)
        elif fault in EASY_FAULTS:
            return
        elif fault == "circular_delegation" and self.run.profile.emits_delegation:
            self.run.spans.append(span("f_del_a", "DELEGATION", "delegate", {"delegation.source_agent": "agent-a", "delegation.target_agent": "agent-b"}, "s0"))
            self.run.spans.append(span("f_del_b", "DELEGATION", "delegate", {"delegation.source_agent": "agent-b", "delegation.target_agent": "agent-a"}, "s0"))
        elif fault == "guardrail_bypass" and self.run.profile.emits_guardrail:
            self.run.spans.append(span("f_guard", "GUARD_RAIL", "guardrail.check", {"guardrail.result": "bypass"}, "s0"))
        elif fault == "hallucination" and self.run.profile.emits_agent_role_verifier:
            self.run.spans.append(span("f_agent_role", "AGENT", "verifier.agent", {"agent.id": "agent-verifier", "agent.role": "verifier", "verification.result": "false_positive"}, "s0"))
        elif not self.run.profile.supports_full_dsm:
            return
        elif fault == "agent_misroute":
            self.run.spans.append(span("f_memory_owner", "MEMORY", "memory.read", {"memory.owner_agent": "agent-a", "agent.id": "agent-b", "memory.key": "task_owner"}, "s0"))
        elif fault == "planning_failure":
            self.run.spans.append(span("f_plan", "PLANNING", "plan.step", {"plan.status": "failed", "plan.executable_steps": 0}, "s0"))
        elif fault == "reasoning_loop":
            for i in range(4):
                self.run.spans.append(span(f"f_reason_{i}", "REASONING", "reasoning.step", {"reasoning.step_hash": "same-state"}, "s0"))
        elif fault == "guardrail_bypass":
            self.run.spans.append(span("f_guard", "GUARD_RAIL", "guardrail.check", {"guardrail.result": "bypass"}, "s0"))
        elif fault == "memory_corruption":
            self.run.spans.append(span("f_memory", "MEMORY", "memory.write", {"memory.key": "customer_state", "memory.corrupt": True}, "s0"))
        elif fault == "stale_retrieval":
            self.run.spans.append(span("f_retrieval", "RETRIEVAL", "retrieval.fetch", {"retrieval.staleness_seconds": 172800}, "s0"))


def inject_easy_fault(spans: list[dict[str, object]], fault: str) -> None:
    if fault == "wrong_tool":
        spans.append(span("f_wrong_tool", "TOOL_CALL", "tool.call", {"tool.name": "calculator", "expected_tool": "retriever", "status": "OK"}, "s0"))
    elif fault == "tool_failure":
        spans.append(span("f_tool_failure", "TOOL_CALL", "tool.call", {"tool.name": "search", "status": "ERROR", "error.type": "ToolExecutionError"}, "s0"))
    elif fault == "timeout":
        spans.append(span("f_timeout", "TOOL_CALL", "tool.call", {"tool.name": "browser", "status": "TIMEOUT", "duration_ms": 120000, "timeout_ms": 30000}, "s0"))
    elif fault == "infinite_loop":
        for i in range(4):
            spans.append(span(f"f_loop_{i}", "TOOL_CALL", "tool.call", {"tool.name": "search", "status": "OK", "duration_ms": 90}, "s0"))
    elif fault == "context_overflow":
        spans.append(span("f_context", "LLM_CALL", "llm.call", {"llm.input_tokens": 9000, "llm.output_tokens": 32, "llm.context_limit": 8192, "llm.cost": 0.015}, "s0"))
    elif fault == "cost_explosion":
        spans.append(span("f_cost", "LLM_CALL", "llm.call", {"llm.input_tokens": 30000, "llm.output_tokens": 5000, "llm.context_limit": 131072, "llm.cost": 2.50, "llm.cost_budget": 0.25}, "s0"))


def dsm_loop_repetitions(adapter: str, model: str) -> int:
    high = {
        ("langchain", "model-A1"), ("langchain", "model-A2"), ("langchain", "model-A3"),
        ("langchain", "model-B1"), ("langchain", "model-B2"), ("langchain", "model-B3"),
        ("crewai", "model-A1"), ("crewai", "model-A2"), ("crewai", "model-A3"),
        ("crewai", "model-B1"), ("crewai", "model-B2"), ("crewai", "model-B3"),
        ("autogen", "model-A1"), ("autogen", "model-A2"), ("autogen", "model-A3"),
        ("autogen", "model-B1"), ("autogen", "model-B2"), ("autogen", "model-B3"),
        ("openai_sdk", "model-A1"), ("openai_sdk", "model-A2"),
    }
    medium = {
        ("openai_sdk", "model-A3"), ("openai_sdk", "model-B1"),
        ("openai_sdk", "model-B2"), ("openai_sdk", "model-B3"),
        ("llamaindex", "model-A1"),
    }
    if (adapter, model) in high:
        return 6
    if (adapter, model) in medium:
        return 5
    return 4


def inject_dsm_infinite_loop(run: AdapterRun) -> None:
    for i in range(dsm_loop_repetitions(run.adapter, run.model)):
        run.spans.append(span(f"f_loop_{i}", "TOOL_CALL", "tool.call", {"tool.name": "search", "status": "OK", "duration_ms": 90}, "s0"))


def inject_secondary_evidence(run: AdapterRun, fault: str) -> None:
    spans = run.spans
    condition = run.condition
    adapter = run.adapter
    if fault in PERMISSIVE_EXTRA.get(condition, set()):
        if condition == "openinference" and adapter not in {"autogen", "openai_sdk"}:
            return
        name = {
            "reasoning_loop": "reasoning-repeat",
            "guardrail_bypass": "guardrail-review",
            "planning_failure": "planning-failed",
            "memory_corruption": "memory-write",
        }[fault]
        spans.append(span(f"sec_perm_{fault}", "INTERNAL", name, {"status": "OK"}, "s0"))

    if fault in EXTENDED_EXTRA.get(condition, set()):
        if condition == "otel_genai" and fault == "reasoning_loop":
            spans.append(
                span(
                    "sec_ext_reason",
                    "CLIENT",
                    "genai.invoke",
                    {"gen_ai.operation.name": "invoke_agent", "gen_ai.usage.reasoning.output_tokens": 1024},
                    "s0",
                )
            )
        elif condition == "openinference" and fault == "reasoning_loop":
            if adapter not in {"autogen", "openai_sdk"}:
                return
            spans.append(
                span(
                    "sec_ext_reason",
                    "CHAIN",
                    "chain.step",
                    {
                        "openinference.span.kind": "CHAIN",
                        "llm.output_messages.0.message.content": "same-state",
                        "llm.output_messages.1.message.content": "same-state",
                    },
                    "s0",
                )
            )


def run_adapter_case(
    adapter: str,
    model: str,
    condition: str,
    fault: str,
    control_scenario: str = "default",
) -> dict[str, object]:
    run = AdapterRun(adapter, model, condition, control_scenario)
    run.emit_base_run(fault)
    run.inject_fault(fault)
    run_id = f"{adapter}:{model}:{condition}:{fault}"
    if fault == "no_fault" and control_scenario != "default":
        run_id = f"{run_id}:{control_scenario}"
    return {
        "run_id": run_id,
        "framework": adapter,
        "model": model,
        "condition": condition,
        "fault_type": fault,
        "control_scenario": control_scenario if fault == "no_fault" else "",
        "adapter_profile": run.profile.name,
        "spans": run.spans,
    }
