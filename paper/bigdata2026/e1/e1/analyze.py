"""Score E1 runs against ground truth, following PROTOCOL.md.

    python -m e1.analyze            # writes data/results.json and data/tables/*.tex
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
FRAMEWORKS = ["custom", "langgraph"]
CONDITIONS = ["sdk", "oi", "ollm", "otel", "ref"]
FAMILIES = ["Loops", "Plan", "Guard", "Memory", "Deleg.", "Tool prov.", "Tokens", "Retr."]
SDK_SCOPE = "com.anthropic.sdk.python"

# Standard span-kind attributes, in priority order, mapped to canonical kinds.
KIND_KEYS = [
    ("agenttelemetry.span.kind", {
        "LLM_CALL": "llm", "TOOL_CALL": "tool", "RETRIEVAL": "retrieval", "AGENT": "agent",
        "PLANNING": "planning", "MEMORY": "memory", "GUARD_RAIL": "guardrail",
        "DELEGATION": "delegation", "REASONING": "reasoning"}),
    ("openinference.span.kind", {
        "LLM": "llm", "TOOL": "tool", "RETRIEVER": "retrieval", "AGENT": "agent",
        "CHAIN": "chain", "GUARDRAIL": "guardrail", "EMBEDDING": "embedding",
        "RERANKER": "reranker", "EVALUATOR": "evaluator", "PROMPT": "prompt"}),
    ("gen_ai.operation.name", {
        "chat": "llm", "generate_content": "llm", "text_completion": "llm",
        "execute_tool": "tool", "retrieval": "retrieval", "invoke_agent": "agent",
        "create_agent": "agent", "invoke_workflow": "workflow", "embeddings": "embedding"}),
    ("traceloop.span.kind", {
        "workflow": "workflow", "task": "chain", "agent": "agent", "tool": "tool"}),
]
TOOL_NAME_KEYS = ["tool.name", "gen_ai.tool.name"]
AGENT_NAME_KEYS = ["gen_ai.agent.name", "agent.name", "delegation.target_agent"]
INPUT_TOKEN_KEYS = ["gen_ai.usage.input_tokens", "llm.token_count.prompt", "llm.input_tokens",
                    "gen_ai.usage.prompt_tokens", "llm.usage.prompt_tokens"]
OUTPUT_TOKEN_KEYS = ["gen_ai.usage.output_tokens", "llm.token_count.completion",
                     "llm.output_tokens", "gen_ai.usage.completion_tokens",
                     "llm.usage.completion_tokens"]
TOOL_CALL_ID_KEYS = ["gen_ai.tool.call.id", "tool_call.id", "tool.call_id", "tool.id"]
NAME_PREFIXES = ("execute_task ", "execute_tool ", "invoke_agent ", "invoke_workflow ",
                 "vector_db_retrieve ", "chat ", "retrieval ")
NAME_SUFFIXES = (".workflow", ".task", ".tool", ".agent")

# The application's own names, which an analyst would have to map by hand.
APP_PLAN = {"planner"}
APP_GUARD = {"refund_guardrail"}
APP_RETRIEVAL = {"retrieve_policies", "PolicyRetriever", "search_policies"}
REAL_AGENTS = {"support_agent", "billing_specialist"}


# --------------------------------------------------------------------------- loading
def load(framework: str, condition: str):
    runs = {}
    d = DATA / "runs" / framework / condition
    for meta_path in sorted(d.glob("*.meta.json")):
        sid = meta_path.name.split(".")[0]
        meta = json.loads(meta_path.read_text())
        if meta["status"] != "ok":
            continue
        spans = [json.loads(l) for l in (d / f"{sid}.spans.jsonl").read_text().splitlines() if l]
        gt = [json.loads(l) for l in (d / f"{sid}.gt.jsonl").read_text().splitlines() if l]
        runs[sid] = {"spans": [enrich(s) for s in spans], "gt": gt, "meta": meta}
    return runs


def first(attrs: dict, keys: list[str]):
    for k in keys:
        if attrs.get(k) not in (None, ""):
            return attrs[k]
    return None


def enrich(span: dict) -> dict:
    a = span["attributes"]
    kind = None
    for key, mapping in KIND_KEYS:
        if key in a:
            kind = mapping.get(str(a[key]), "other")
            break
    tool_name = first(a, TOOL_NAME_KEYS)
    if tool_name is None and a.get("traceloop.span.kind") == "tool":
        tool_name = a.get("traceloop.entity.name")
    agent_name = first(a, AGENT_NAME_KEYS)
    if agent_name is None and a.get("openinference.span.kind") == "AGENT":
        agent_name = a.get("graph.node.id") or a.get("agent.name")
    names = {span["name"]}
    for p in NAME_PREFIXES:
        if span["name"].startswith(p):
            names.add(span["name"][len(p):])
    for sfx in NAME_SUFFIXES:
        if span["name"].endswith(sfx):
            names.add(span["name"][: -len(sfx)])
    for key in ("traceloop.entity.name", "gen_ai.agent.name", "gen_ai.tool.name",
                "gen_ai.workflow.name", "tool.name", "graph.node.id", "langgraph.node"):
        if a.get(key):
            names.add(str(a[key]))
    meta = a.get("metadata")
    if isinstance(meta, str) and "langgraph_node" in meta:
        try:
            node = json.loads(meta).get("langgraph_node")
            if node:
                names.add(node)
        except json.JSONDecodeError:
            pass
    span["_kind"] = kind
    span["_tool"] = tool_name
    span["_agent"] = agent_name
    span["_names"] = names
    span["_error"] = span["status"] == "ERROR" or "error.type" in a or a.get("tool.status") == "error"
    span["_sdk"] = span["scope"] == SDK_SCOPE
    span["_blob"] = json.dumps(a, default=str)
    return span


def overlapping(spans, ev):
    return [s for s in spans if s["start_ns"] <= ev["end_ns"] and s["end_ns"] >= ev["start_ns"]]


def ancestors(span, by_id):
    seen, cur = [], span
    while cur and cur.get("parent_span_id") and cur["parent_span_id"] in by_id:
        cur = by_id[cur["parent_span_id"]]
        seen.append(cur["span_id"])
    return seen


# --------------------------------------------------------------------------- instances
def loop_instances(gt):
    """Runs of >=3 consecutive same-tool executions where all but the last errored."""
    out = []
    by_agent = defaultdict(list)
    for ev in gt:
        if ev["kind"] == "TOOL_CALL":
            by_agent[ev["agent"]].append(ev)
    for evs in by_agent.values():
        i = 0
        while i < len(evs):
            j = i
            while (j + 1 < len(evs) and evs[j + 1]["attrs"]["tool_name"] == evs[i]["attrs"]["tool_name"]
                   and evs[j]["attrs"].get("error")):
                j += 1
            if j - i + 1 >= 3:
                out.append(evs[i:j + 1])
                i = j + 1
            else:
                i += 1
    return out


def level(std: bool, app: bool) -> str:
    return "standard" if std else ("app" if app else "none")


def tool_span(spans, ev, require_standard=False):
    name = ev["attrs"]["tool_name"]
    cands = overlapping(spans, ev)
    std = [s for s in cands if s["_kind"] == "tool" and s["_tool"] == name]
    if std:
        return std[0], True
    if require_standard:
        return None, False
    app = [s for s in cands if name in s["_names"] and s["_kind"] not in ("llm",)]
    return (app[0], False) if app else (None, False)


def score_run(run, use_sdk: bool):
    spans = [s for s in run["spans"] if use_sdk or not s["_sdk"]]
    by_id = {s["span_id"]: s for s in spans}
    gt = run["gt"]
    gt_by_seq = {ev["seq"]: ev for ev in gt}
    res = defaultdict(list)
    details = defaultdict(list)

    for ev in gt:
        k = ev["kind"]
        cands = overlapping(spans, ev)
        if k == "PLANNING":
            std = any(s["_kind"] == "planning" for s in cands)
            app = any(s["_names"] & APP_PLAN for s in cands)
            res["Plan"].append(level(std, app))
        elif k == "MEMORY":
            std = any(s["_kind"] == "memory" and s["attributes"].get("memory.operation")
                      for s in cands)
            app = any(ev["name"] in s["_names"] for s in cands)
            res["Memory"].append(level(std, app))
        elif k == "GUARD_RAIL":
            hits = [s for s in cands if s["_kind"] == "guardrail"]
            app_hits = [s for s in cands if s["_names"] & APP_GUARD]
            res["Guard"].append(level(bool(hits), bool(app_hits)))
            decision = "absent"
            if any(s["attributes"].get("guardrail.result") for s in hits):
                decision = "standard"
            elif any(("within policy" in s["_blob"] or "exceeds" in s["_blob"]
                      or "outside the 30-day" in s["_blob"]) for s in hits + app_hits):
                decision = "content"
            details["guard_decision"].append(decision)
        elif k == "RETRIEVAL":
            std = any(s["_kind"] == "retrieval" for s in cands)
            app = any(s["_names"] & APP_RETRIEVAL for s in cands)
            res["Retr."].append(level(std, app))
        elif k == "DELEGATION":
            traces_support = {s["trace_id"] for s in spans if s["_agent"] == "support_agent"}
            traces_support_app = {s["trace_id"] for s in spans
                                  if s["_names"] & {"support_agent", "escalate_to_billing"}}
            std = any(s["_kind"] in ("agent", "delegation")
                      and (s["_agent"] == "billing_specialist"
                           or s["attributes"].get("delegation.target_agent") == "billing_specialist")
                      and s["trace_id"] in traces_support for s in cands)
            app = any("billing_specialist" in s["_names"]
                      and s["trace_id"] in (traces_support | traces_support_app) for s in cands)
            res["Deleg."].append(level(std, app))
        elif k == "LLM_CALL":
            llm = [s for s in cands if s["_kind"] == "llm"]
            std = any(first(s["attributes"], INPUT_TOKEN_KEYS) is not None
                      and first(s["attributes"], OUTPUT_TOKEN_KEYS) is not None for s in llm)
            res["Tokens"].append(level(std, False))
        elif k == "TOOL_CALL":
            t, t_std = tool_span(spans, ev)
            if ev["attrs"].get("error"):
                # Descriptive, not a protocol family: is each failure visible as an error?
                details["failed_tool"].append(
                    "no tool span" if t is None else ("error visible" if t["_error"] else "no error status"))
            if t is None:
                res["Tool prov."].append("none")
                details["prov_link"].append("no tool span")
                continue
            llm_ev = gt_by_seq[ev["attrs"]["requested_by"]]
            llms = [s for s in overlapping(spans, llm_ev) if s["_kind"] == "llm"]
            tool_id = ev["attrs"]["tool_call_id"]
            link = None
            anc = set(ancestors(t, by_id))
            if any(L["span_id"] in anc for L in llms):
                link = "parent"
            elif (first(t["attributes"], TOOL_CALL_ID_KEYS) == tool_id
                  and any(tool_id in L["_blob"] for L in llms)):
                link = "call id"
            else:
                for L in llms:
                    same_trace = [s for s in spans if s["trace_id"] == t["trace_id"] and s["_kind"] == "llm"]
                    before = [s for s in same_trace if s["end_ns"] <= t["start_ns"]]
                    if L["trace_id"] == t["trace_id"] and before and max(
                            before, key=lambda s: s["end_ns"])["end_ns"] == L["end_ns"]:
                        link = "order"
                        break
            details["prov_link"].append(link or "unlinked")
            if link in ("parent", "call id"):
                res["Tool prov."].append("standard" if t_std else "app")
            elif link == "order":
                res["Tool prov."].append("app")
            else:
                res["Tool prov."].append("none")

    for loop in loop_instances(gt):
        lv = "standard"
        for ev in loop:
            t, t_std = tool_span(spans, ev)
            errored = ev["attrs"].get("error")
            if t is None or (errored and not t["_error"]):
                lv = "none"
                break
            if not t_std:
                lv = "app"
        res["Loops"].append(lv)
    return res, details


def structure_stats(run, use_sdk: bool):
    spans = [s for s in run["spans"] if use_sdk or not s["_sdk"]]
    traces = {s["trace_id"] for s in spans}
    roots = [s for s in spans if not s["parent_span_id"]]
    agent_spans = [s for s in spans if s["_kind"] == "agent"]
    spurious = [s for s in agent_spans if (s["_agent"] or next(iter(s["_names"]))) not in REAL_AGENTS]
    ticket = run["meta"].get("final", "")
    return {
        "spans": len(spans),
        "traces": len(traces),
        "roots": len(roots),
        "agent_spans": len(agent_spans),
        "spurious_agent_spans": len(spurious),
        "attributes": sum(len(s["attributes"]) for s in spans),
        "final_text_captured": bool(ticket) and any(ticket[:40] in s["_blob"] for s in spans),
    }


def content_captured(run, use_sdk, ticket_text):
    spans = [s for s in run["spans"] if use_sdk or not s["_sdk"]]
    return any(ticket_text[:40] in s["_blob"] for s in spans)


def materialize_sqlite(all_runs, path: Path):
    if path.exists():
        path.unlink()
    db = sqlite3.connect(path)
    db.execute("create table spans (id integer primary key, framework text, condition text, "
               "scenario text, trace_id text, span_id text, parent_span_id text, name text, "
               "kind text, start_ns integer, end_ns integer, status text, scope text)")
    db.execute("create table attributes (span_row integer, key text, value text)")
    for (fw, cond), runs in all_runs.items():
        for sid, run in runs.items():
            for s in run["spans"]:
                cur = db.execute("insert into spans (framework, condition, scenario, trace_id, "
                                 "span_id, parent_span_id, name, kind, start_ns, end_ns, status, "
                                 "scope) values (?,?,?,?,?,?,?,?,?,?,?,?)",
                                 (fw, cond, sid, s["trace_id"], s["span_id"], s["parent_span_id"],
                                  s["name"], s["kind"], s["start_ns"], s["end_ns"], s["status"],
                                  s["scope"]))
                db.executemany("insert into attributes values (?,?,?)",
                               [(cur.lastrowid, k, json.dumps(v, default=str))
                                for k, v in s["attributes"].items()])
    db.commit()
    db.close()


def main() -> None:
    from e1.domain import SCENARIOS
    tickets = {s.id: s.ticket for s in SCENARIOS}
    all_runs = {(fw, c): load(fw, c) for fw in FRAMEWORKS for c in CONDITIONS}
    results = {"recall": {}, "levels": {}, "details": {}, "structure": {}, "n_runs": {},
               "instances": {}, "content_capture": {}}
    for (fw, cond), runs in all_runs.items():
        for use_sdk in (True, False):
            tag = f"{fw}/{cond}/{'with_sdk' if use_sdk else 'library_only'}"
            agg = defaultdict(Counter)
            det = defaultdict(Counter)
            stats = Counter()
            captured = 0
            for sid, run in runs.items():
                res, details = score_run(run, use_sdk)
                for fam, levels in res.items():
                    agg[fam].update(levels)
                for key, vals in details.items():
                    det[key].update(vals)
                st = structure_stats(run, use_sdk)
                stats.update({k: v for k, v in st.items() if isinstance(v, (int, bool))})
                captured += content_captured(run, use_sdk, tickets[sid])
            results["n_runs"][tag] = len(runs)
            results["levels"][tag] = {f: dict(agg[f]) for f in FAMILIES}
            results["recall"][tag] = {
                f: {"standard": agg[f]["standard"] / max(1, sum(agg[f].values())),
                    "any": (agg[f]["standard"] + agg[f]["app"]) / max(1, sum(agg[f].values())),
                    "n": sum(agg[f].values())}
                for f in FAMILIES}
            results["details"][tag] = {k: dict(v) for k, v in det.items()}
            results["structure"][tag] = dict(stats)
            results["content_capture"][tag] = captured / max(1, len(runs))
    out = DATA / "results.json"
    out.write_text(json.dumps(results, indent=2, sort_keys=True))
    materialize_sqlite(all_runs, DATA / "e1_backend.sqlite")
    print(f"wrote {out}")
    for fw in FRAMEWORKS:
        print(f"\n== {fw} (library + SDK spans): standard / any")
        print(f"{'cond':6s} " + " ".join(f"{f:>11s}" for f in FAMILIES))
        for cond in CONDITIONS:
            r = results["recall"][f"{fw}/{cond}/with_sdk"]
            print(f"{cond:6s} " + " ".join(
                f"{100 * r[f]['standard']:4.0f}/{100 * r[f]['any']:3.0f}%" if r[f]["n"] else f"{'n/a':>11s}"
                for f in FAMILIES))
        print("instances:", {f: results["recall"][f"{fw}/ref/with_sdk"][f]["n"] for f in FAMILIES})


if __name__ == "__main__":
    main()
