"""The support agent as plain Python on the Anthropic SDK, with no agent framework."""

from __future__ import annotations

import json

from e1.domain import (BILLING_SYSTEM, BILLING_TOOLS, MAX_AGENT_ITERATIONS,
                       MAX_BILLING_ITERATIONS, PLANNER_SYSTEM, SUPPORT_SYSTEM, SUPPORT_TOOLS,
                       Scenario, SupportBackend, ToolError, planner_prompt, search_kb,
                       support_prompt)
from e1.harness import RunContext, count_plan_steps, text_of, tool_uses

SUPPORT = "support_agent"
BILLING = "billing_specialist"


def _result(tool_use_id: str, payload, is_error: bool = False) -> dict:
    content = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
    block = {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
    if is_error:
        block["is_error"] = True
    return block


def run_billing(ctx: RunContext, backend: SupportBackend, order_id: str, summary: str) -> str:
    with ctx.step("AGENT", BILLING, BILLING, role="billing"):
        messages = [{"role": "user", "content": f"Order {order_id}: {summary}"}]
        final = ""
        for _ in range(MAX_BILLING_ITERATIONS):
            with ctx.step("REASONING", "billing_iteration", BILLING):
                response = ctx.call_model(agent=BILLING, system=BILLING_SYSTEM,
                                          messages=messages, tools=BILLING_TOOLS)
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                final = text_of(response)
                break
            llm_seq = [e for e in ctx.events if e.kind == "LLM_CALL"][-1].seq
            results = []
            for tu in tool_uses(response):
                with ctx.step("TOOL_CALL", tu.name, BILLING, tool_name=tu.name,
                              tool_call_id=tu.id, requested_by=llm_seq) as ev:
                    try:
                        if tu.name == "lookup_invoice":
                            out = backend.lookup_invoice(tu.input["order_id"])
                        else:
                            out = backend.apply_credit(tu.input["order_id"],
                                                       float(tu.input["amount"]), tu.input["reason"])
                        ev.attrs["error"] = False
                        results.append(_result(tu.id, out))
                    except (ToolError, KeyError) as exc:
                        ev.attrs.update(error=True, error_message=str(exc))
                        results.append(_result(tu.id, f"Error: {exc}", True))
            messages.append({"role": "user", "content": results})
        return final or "Billing specialist could not resolve the dispute."


def _execute_support_tool(ctx: RunContext, backend: SupportBackend, tu, llm_seq: int,
                          decisions: dict) -> dict:
    name, args = tu.name, tu.input
    if name == "issue_refund":
        allowed, why = decisions[tu.id]
        if not allowed:
            return _result(tu.id, f"Blocked by refund guardrail: {why}", True)
    with ctx.step("TOOL_CALL", name, SUPPORT, tool_name=name, tool_call_id=tu.id,
                  requested_by=llm_seq) as ev:
        try:
            if name == "get_order":
                out = backend.get_order(args["order_id"])
            elif name == "get_customer":
                out = backend.get_customer(args["customer_id"])
            elif name == "check_return_eligibility":
                out = backend.check_return_eligibility(args["order_id"])
            elif name == "issue_refund":
                out = backend.issue_refund(args["order_id"], float(args["amount"]), args["reason"])
            elif name == "update_shipping_address":
                out = backend.update_shipping_address(args["order_id"], args["address"])
            elif name == "search_policies":
                with ctx.step("RETRIEVAL", "search_policies", SUPPORT, source="policy_kb") as r:
                    docs = search_kb(args["query"])
                    r.attrs["doc_count"] = len(docs)
                out = [{"id": d, "text": t} for d, t in docs]
            elif name == "escalate_to_billing":
                with ctx.step("DELEGATION", "delegate_to_billing", SUPPORT,
                              source_agent=SUPPORT, target_agent=BILLING):
                    out = run_billing(ctx, backend, args["order_id"], args["summary"])
            else:
                raise ToolError(f"unknown tool {name}")
            ev.attrs["error"] = False
            return _result(tu.id, out)
        except (ToolError, KeyError, ValueError) as exc:
            ev.attrs.update(error=True, error_message=str(exc))
            return _result(tu.id, f"Error: {exc}", True)


def run(ctx: RunContext, scenario: Scenario) -> str:
    backend = SupportBackend(scenario)
    cid = scenario.customer_id
    with ctx.step("AGENT", SUPPORT, SUPPORT, role="support"):
        with ctx.step("MEMORY", "load_memory", SUPPORT, operation="read", key=cid):
            memory = dict(backend.memory.get(cid, {}))
        with ctx.step("PLANNING", "plan", SUPPORT) as p:
            response = ctx.call_model(agent=SUPPORT, system=PLANNER_SYSTEM,
                                      messages=[{"role": "user",
                                                 "content": planner_prompt(scenario, memory)}])
            plan = text_of(response)
            p.attrs["step_count"] = count_plan_steps(plan)
        with ctx.step("RETRIEVAL", "retrieve_policies", SUPPORT, source="policy_kb") as r:
            docs = search_kb(scenario.ticket)
            r.attrs["doc_count"] = len(docs)
        messages = [{"role": "user", "content": support_prompt(scenario, memory, plan, docs)}]
        final = ""
        for _ in range(MAX_AGENT_ITERATIONS):
            with ctx.step("REASONING", "support_iteration", SUPPORT):
                response = ctx.call_model(agent=SUPPORT, system=SUPPORT_SYSTEM,
                                          messages=messages, tools=SUPPORT_TOOLS)
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                final = text_of(response)
                break
            llm_seq = [e for e in ctx.events if e.kind == "LLM_CALL"][-1].seq
            decisions = {}
            for tu in tool_uses(response):
                if tu.name == "issue_refund":
                    with ctx.step("GUARD_RAIL", "refund_guardrail", SUPPORT,
                                  guardrail_name="refund_policy") as g:
                        decisions[tu.id] = backend.refund_guardrail(
                            tu.input.get("order_id", ""), float(tu.input.get("amount", 0)))
                        g.attrs["result"] = "allow" if decisions[tu.id][0] else "block"
            results = [_execute_support_tool(ctx, backend, tu, llm_seq, decisions)
                       for tu in tool_uses(response)]
            messages.append({"role": "user", "content": results})
        with ctx.step("MEMORY", "save_memory", SUPPORT, operation="write", key=cid):
            backend.memory.setdefault(cid, {})["last_issue"] = scenario.ticket[:80]
    return final
