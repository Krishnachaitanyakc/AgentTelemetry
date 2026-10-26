"""Run E1 tickets in one condition.

Record (live API, reference instrumentation only):
    python -m e1.run --mode record --condition ref --framework custom --scenarios S01,S02
Replay (recorded responses, one library condition):
    python -m e1.run --mode replay --condition oi --framework custom --scenarios all
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import json
import sys
import traceback
from pathlib import Path

import anthropic
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from e1 import custom_agent, graph_agent
from e1.domain import SCENARIOS
from e1.harness import JsonlSpanExporter, RecordReplayTransport, RefusalStop, RunContext

DATA = Path(__file__).resolve().parent.parent / "data"
LEDGER = DATA / "recordings" / "cost_ledger.json"
BUDGET_USD = 100.0
AGENTS = {"custom": custom_agent, "langgraph": graph_agent}
PACKAGES = {
    "oi": ["openinference-instrumentation-langchain", "openinference-instrumentation-anthropic"],
    "ollm": ["opentelemetry-instrumentation-langchain", "opentelemetry-instrumentation-anthropic"],
    "otel": ["opentelemetry-instrumentation-genai-langchain",
             "opentelemetry-instrumentation-genai-anthropic"],
    "ref": ["agenttelemetry"],
    "sdk": [],
}
BASE_PACKAGES = ["anthropic", "langgraph", "langchain-core", "opentelemetry-sdk"]


def instrument(condition: str, provider: TracerProvider) -> None:
    if condition == "oi":
        from openinference.instrumentation.anthropic import AnthropicInstrumentor
        from openinference.instrumentation.langchain import LangChainInstrumentor
    elif condition == "ollm":
        from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
        from opentelemetry.instrumentation.langchain import \
            LangchainInstrumentor as LangChainInstrumentor
    elif condition == "otel":
        from opentelemetry.instrumentation.genai.anthropic import AnthropicInstrumentor
        from opentelemetry.instrumentation.genai.langchain import LangChainInstrumentor
    else:
        return
    LangChainInstrumentor().instrument(tracer_provider=provider)
    AnthropicInstrumentor().instrument(tracer_provider=provider)


def load_ledger() -> dict:
    """spent_usd counts every live attempt, including re-recordings and failures."""
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"spent_usd": 0.0, "runs": {}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["record", "replay"], required=True)
    ap.add_argument("--condition", choices=["oi", "ollm", "otel", "ref", "sdk"], required=True)
    ap.add_argument("--framework", choices=list(AGENTS), required=True)
    ap.add_argument("--scenarios", default="all")
    ap.add_argument("--force", action="store_true", help="re-record existing recordings")
    args = ap.parse_args()
    if args.mode == "record" and args.condition != "ref":
        ap.error("recording runs only under the reference condition")

    wanted = [s for s in SCENARIOS
              if args.scenarios == "all" or s.id in args.scenarios.split(",")]
    rec_dir = DATA / "recordings" / args.framework
    out_dir = DATA / "runs" / args.framework / args.condition
    rec_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    exporter = JsonlSpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "e1-support-agent"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    instrument(args.condition, provider)
    ref_tracer = provider.get_tracer("agenttelemetry", "0.2.0") if args.condition == "ref" else None

    transport = RecordReplayTransport(args.mode)
    # Replay never reaches the network, so it needs no real key.
    client = anthropic.Anthropic(http_client=anthropic.DefaultHttpxClient(transport=transport),
                                 max_retries=4 if args.mode == "record" else 0,
                                 **({"api_key": "replay-only"} if args.mode == "replay" else {}))
    versions = {p: md.version(p) for p in BASE_PACKAGES + PACKAGES[args.condition]}
    ledger = load_ledger()
    failures = 0

    for scenario in wanted:
        rec_path = rec_dir / f"{scenario.id}.jsonl"
        if args.mode == "record":
            if rec_path.exists() and not args.force:
                print(f"{scenario.id}: already recorded, skipping")
                continue
            if ledger["spent_usd"] >= BUDGET_USD:
                print(f"budget of {BUDGET_USD} USD reached; stopping")
                return 2
            transport.reset()
        else:
            if not rec_path.exists():
                print(f"{scenario.id}: no recording, skipping")
                continue
            transport.load(rec_path)

        exporter.set_output(out_dir / f"{scenario.id}.spans.jsonl")
        ctx = RunContext(client, ref_tracer=ref_tracer)
        status, error, final = "ok", None, ""
        try:
            final = AGENTS[args.framework].run(ctx, scenario)
        except RefusalStop as exc:
            status, error = "refusal", str(exc)
        except Exception as exc:  # recorded and reported, never hidden
            status, error = "error", f"{type(exc).__name__}: {exc}"
            traceback.print_exc()
        provider.force_flush()
        exporter.set_output(None)

        if args.mode == "replay" and status == "ok" and transport.cursor != len(transport.entries):
            status, error = "error", (f"replay consumed {transport.cursor} of "
                                      f"{len(transport.entries)} recorded exchanges")
        if args.mode == "record":
            ledger["spent_usd"] = round(ledger["spent_usd"] + ctx.cost_usd(), 4)
            if status == "ok":
                with rec_path.open("w") as fh:
                    for entry in transport.entries:
                        fh.write(json.dumps(entry) + "\n")
                ledger["runs"][f"{args.framework}/{scenario.id}"] = {
                    "usd": round(ctx.cost_usd(), 4), "usage": ctx.usage}
            LEDGER.write_text(json.dumps(ledger, indent=2, sort_keys=True))

        (out_dir / f"{scenario.id}.gt.jsonl").write_text(
            "".join(json.dumps(ev, default=str) + "\n" for ev in ctx.ground_truth()))
        (out_dir / f"{scenario.id}.meta.json").write_text(json.dumps({
            "scenario": scenario.id, "framework": args.framework, "condition": args.condition,
            "mode": args.mode, "status": status, "error": error, "final": final,
            "usage": ctx.usage, "cost_usd": round(ctx.cost_usd(), 4),
            "stop_reasons": ctx.stop_reasons, "versions": versions,
        }, indent=2, sort_keys=True))
        failures += status != "ok"
        print(f"{scenario.id}: {status} calls={ctx.usage['calls']} "
              f"cost=${ctx.cost_usd():.3f} spent=${ledger['spent_usd']:.2f}"
              + (f" ({error})" if error else ""))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
