"""The support agent as a LangGraph StateGraph.

Nodes call the Anthropic SDK directly. Tools are LangChain StructuredTools, the
policy knowledge base is a LangChain BaseRetriever, memory is a LangGraph store,
and billing disputes are delegated to a compiled billing subgraph.
"""

from __future__ import annotations

import json
from typing import Any, TypedDict

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from e1.domain import (BILLING_SYSTEM, BILLING_TOOLS, MAX_AGENT_ITERATIONS,
                       MAX_BILLING_ITERATIONS, PLANNER_SYSTEM, SUPPORT_SYSTEM, SUPPORT_TOOLS,
                       Scenario, SupportBackend, ToolError, planner_prompt, search_kb,
                       support_prompt)
from e1.harness import RunContext, count_plan_steps, text_of, tool_uses

SUPPORT = "support_agent"
BILLING = "billing_specialist"


class PolicyRetriever(BaseRetriever):
    k: int = 3

    def _get_relevant_documents(self, query: str, *,
                                run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        return [Document(page_content=text, metadata={"id": doc_id})
                for doc_id, text in search_kb(query, self.k)]


class SupportState(TypedDict, total=False):
    memory: dict
    plan: str
    docs: list
    messages: list
    last_response: Any
    last_llm_seq: int
    decisions: dict
    iterations: int
    final: str


class BillingState(TypedDict, total=False):
    messages: list
    last_response: Any
    last_llm_seq: int
    iterations: int
    final: str


def _json(payload) -> str:
    return json.dumps(payload, sort_keys=True)


def _result(tool_use_id: str, payload, is_error: bool = False) -> dict:
    content = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True)
    block = {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
    if is_error:
        block["is_error"] = True
    return block


def _invoke_tool(ctx: RunContext, agent: str, tool: StructuredTool, tu, llm_seq: int) -> dict:
    with ctx.step("TOOL_CALL", tu.name, agent, tool_name=tu.name, tool_call_id=tu.id,
                  requested_by=llm_seq) as ev:
        try:
            # Invoke with a ToolCall, as LangGraph's ToolNode does, so the call ID
            # is available to callbacks and instrumentation.
            message = tool.invoke({"name": tu.name, "args": dict(tu.input),
                                   "id": tu.id, "type": "tool_call"})
            ev.attrs["error"] = False
            return _result(tu.id, message.content)
        except (ToolError, KeyError, ValueError) as exc:
            ev.attrs.update(error=True, error_message=str(exc))
            return _result(tu.id, f"Error: {exc}", True)


def build_billing_graph(ctx: RunContext, backend: SupportBackend):
    tools = {
        "lookup_invoice": StructuredTool.from_function(
            func=lambda order_id: _json(backend.lookup_invoice(order_id)),
            name="lookup_invoice", description="Show the charges captured for an order."),
        "apply_credit": StructuredTool.from_function(
            func=lambda order_id, amount, reason: _json(backend.apply_credit(order_id, float(amount), reason)),
            name="apply_credit", description="Apply a billing credit to the customer's payment method."),
    }

    def billing_agent(state: BillingState) -> BillingState:
        with ctx.step("REASONING", "billing_iteration", BILLING):
            response = ctx.call_model(agent=BILLING, system=BILLING_SYSTEM,
                                      messages=state["messages"], tools=BILLING_TOOLS)
        update: BillingState = {
            "messages": state["messages"] + [{"role": "assistant", "content": response.content}],
            "last_response": response,
            "last_llm_seq": [e for e in ctx.events if e.kind == "LLM_CALL"][-1].seq,
            "iterations": state.get("iterations", 0) + 1,
        }
        if response.stop_reason != "tool_use":
            update["final"] = text_of(response)
        return update

    def billing_tools(state: BillingState) -> BillingState:
        results = [_invoke_tool(ctx, BILLING, tools[tu.name], tu, state["last_llm_seq"])
                   for tu in tool_uses(state["last_response"])]
        return {"messages": state["messages"] + [{"role": "user", "content": results}]}

    def route(state: BillingState) -> str:
        if "final" in state or state.get("iterations", 0) >= MAX_BILLING_ITERATIONS:
            return END
        return "billing_tools"

    g = StateGraph(BillingState)
    g.add_node("billing_agent", billing_agent)
    g.add_node("billing_tools", billing_tools)
    g.add_edge(START, "billing_agent")
    g.add_conditional_edges("billing_agent", route, ["billing_tools", END])
    g.add_edge("billing_tools", "billing_agent")
    return g.compile(name=BILLING)


def build_support_graph(ctx: RunContext, scenario: Scenario, backend: SupportBackend):
    retriever = PolicyRetriever()
    billing_graph = build_billing_graph(ctx, backend)
    cid = scenario.customer_id

    def search_policies(query: str) -> list:
        with ctx.step("RETRIEVAL", "search_policies", SUPPORT, source="policy_kb") as r:
            docs = retriever.invoke(query)
            r.attrs["doc_count"] = len(docs)
        return [{"id": d.metadata["id"], "text": d.page_content} for d in docs]

    def escalate_to_billing(order_id: str, summary: str) -> str:
        with ctx.step("DELEGATION", "delegate_to_billing", SUPPORT,
                      source_agent=SUPPORT, target_agent=BILLING):
            with ctx.step("AGENT", BILLING, BILLING, role="billing"):
                out = billing_graph.invoke(
                    {"messages": [{"role": "user", "content": f"Order {order_id}: {summary}"}]},
                    config={"recursion_limit": 40})
        return out.get("final") or "Billing specialist could not resolve the dispute."

    funcs = {
        "get_order": lambda order_id: _json(backend.get_order(order_id)),
        "get_customer": lambda customer_id: _json(backend.get_customer(customer_id)),
        "check_return_eligibility": lambda order_id: _json(backend.check_return_eligibility(order_id)),
        "issue_refund": lambda order_id, amount, reason: _json(
            backend.issue_refund(order_id, float(amount), reason)),
        "update_shipping_address": lambda order_id, address: _json(
            backend.update_shipping_address(order_id, address)),
        "search_policies": lambda query: _json(search_policies(query)),
        "escalate_to_billing": escalate_to_billing,
    }
    tools = {spec["name"]: StructuredTool.from_function(
        func=funcs[spec["name"]], name=spec["name"], description=spec["description"])
        for spec in SUPPORT_TOOLS}

    def load_memory(state: SupportState, *, store: BaseStore) -> SupportState:
        with ctx.step("MEMORY", "load_memory", SUPPORT, operation="read", key=cid):
            item = store.get(("memory",), cid)
        return {"memory": dict(item.value) if item else {}}

    def planner(state: SupportState) -> SupportState:
        with ctx.step("PLANNING", "plan", SUPPORT) as p:
            response = ctx.call_model(agent=SUPPORT, system=PLANNER_SYSTEM, messages=[
                {"role": "user", "content": planner_prompt(scenario, state["memory"])}])
            plan = text_of(response)
            p.attrs["step_count"] = count_plan_steps(plan)
        return {"plan": plan}

    def retrieve_policies(state: SupportState) -> SupportState:
        with ctx.step("RETRIEVAL", "retrieve_policies", SUPPORT, source="policy_kb") as r:
            docs = retriever.invoke(scenario.ticket)
            r.attrs["doc_count"] = len(docs)
        docs = [(d.metadata["id"], d.page_content) for d in docs]
        return {"docs": docs, "messages": [{"role": "user", "content": support_prompt(
            scenario, state["memory"], state["plan"], docs)}]}

    def agent(state: SupportState) -> SupportState:
        with ctx.step("REASONING", "support_iteration", SUPPORT):
            response = ctx.call_model(agent=SUPPORT, system=SUPPORT_SYSTEM,
                                      messages=state["messages"], tools=SUPPORT_TOOLS)
        update: SupportState = {
            "messages": state["messages"] + [{"role": "assistant", "content": response.content}],
            "last_response": response,
            "last_llm_seq": [e for e in ctx.events if e.kind == "LLM_CALL"][-1].seq,
            "iterations": state.get("iterations", 0) + 1,
            "decisions": {},
        }
        if response.stop_reason != "tool_use":
            update["final"] = text_of(response)
        return update

    def refund_guardrail(state: SupportState) -> SupportState:
        decisions = {}
        for tu in tool_uses(state["last_response"]):
            if tu.name == "issue_refund":
                with ctx.step("GUARD_RAIL", "refund_guardrail", SUPPORT,
                              guardrail_name="refund_policy") as g:
                    decisions[tu.id] = backend.refund_guardrail(
                        tu.input.get("order_id", ""), float(tu.input.get("amount", 0)))
                    g.attrs["result"] = "allow" if decisions[tu.id][0] else "block"
        return {"decisions": decisions}

    def run_tools(state: SupportState) -> SupportState:
        results = []
        for tu in tool_uses(state["last_response"]):
            if tu.name == "issue_refund" and not state["decisions"][tu.id][0]:
                results.append(_result(tu.id, f"Blocked by refund guardrail: "
                                              f"{state['decisions'][tu.id][1]}", True))
                continue
            if tu.name not in tools:
                results.append(_result(tu.id, f"Error: unknown tool {tu.name}", True))
                continue
            results.append(_invoke_tool(ctx, SUPPORT, tools[tu.name], tu, state["last_llm_seq"]))
        return {"messages": state["messages"] + [{"role": "user", "content": results}]}

    def save_memory(state: SupportState, *, store: BaseStore) -> SupportState:
        with ctx.step("MEMORY", "save_memory", SUPPORT, operation="write", key=cid):
            item = store.get(("memory",), cid)
            value = dict(item.value) if item else {}
            value["last_issue"] = scenario.ticket[:80]
            store.put(("memory",), cid, value)
        return {}

    def route_after_agent(state: SupportState) -> str:
        if "final" in state or state.get("iterations", 0) >= MAX_AGENT_ITERATIONS:
            return "save_memory"
        if any(tu.name == "issue_refund" for tu in tool_uses(state["last_response"])):
            return "refund_guardrail"
        return "tools"

    g = StateGraph(SupportState)
    g.add_node("load_memory", load_memory)
    g.add_node("planner", planner)
    g.add_node("retrieve_policies", retrieve_policies)
    g.add_node("agent", agent)
    g.add_node("refund_guardrail", refund_guardrail)
    g.add_node("tools", run_tools)
    g.add_node("save_memory", save_memory)
    g.add_edge(START, "load_memory")
    g.add_edge("load_memory", "planner")
    g.add_edge("planner", "retrieve_policies")
    g.add_edge("retrieve_policies", "agent")
    g.add_conditional_edges("agent", route_after_agent, ["refund_guardrail", "tools", "save_memory"])
    g.add_edge("refund_guardrail", "tools")
    g.add_edge("tools", "agent")
    g.add_edge("save_memory", END)
    store = InMemoryStore()
    for customer_id, value in backend.memory.items():
        store.put(("memory",), customer_id, dict(value))
    return g.compile(name=SUPPORT, store=store)


def run(ctx: RunContext, scenario: Scenario) -> str:
    backend = SupportBackend(scenario)
    graph = build_support_graph(ctx, scenario, backend)
    with ctx.step("AGENT", SUPPORT, SUPPORT, role="support"):
        out = graph.invoke({}, config={"recursion_limit": 80})
    return out.get("final", "")
