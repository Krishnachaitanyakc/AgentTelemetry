"""Recovery script: aggregate per-run JSONs from a completed
multi_agent_topology_cli run into summary.json and summary.txt
when the original run's post-completion step crashed.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

OUT_DIR = Path("/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/results/multi_agent_topology_cli")
PER_RUN = OUT_DIR / "per_run"
TRACES = OUT_DIR / "traces.jsonl"


def load_runs():
    runs = []
    for p in sorted(PER_RUN.glob("*.json")):
        try:
            with open(p) as f:
                runs.append(json.load(f))
        except Exception as e:
            print(f"WARN: could not load {p.name}: {e}", file=sys.stderr)
    return runs


def aggregate(runs):
    by_cell = defaultdict(list)
    for r in runs:
        by_cell[(r.get("topology", "?"), r.get("model", "?"))].append(r)

    per_cell = {}
    for (topology, model), cell_runs in by_cell.items():
        n = len(cell_runs)
        successes = sum(
            1 for r in cell_runs
            if not r.get("error")
            and any(t.get("output") for t in r.get("transcript", []))
        )
        avg_cost = sum(r.get("total_cost_usd", 0) for r in cell_runs) / n if n else 0
        avg_wall = sum(r.get("wall_clock_s", 0) for r in cell_runs) / n if n else 0
        avg_in = sum(r.get("total_input_tokens", 0) for r in cell_runs) / n if n else 0
        avg_out = sum(r.get("total_output_tokens", 0) for r in cell_runs) / n if n else 0
        per_cell[f"{topology}__{model}"] = {
            "topology": topology,
            "model": model,
            "n_runs": n,
            "n_completed": successes,
            "completion_rate": successes / n if n else 0.0,
            "avg_cost_usd": avg_cost,
            "avg_wall_clock_s": avg_wall,
            "avg_input_tokens": avg_in,
            "avg_output_tokens": avg_out,
        }
    return per_cell


def organic_faults_from_traces():
    """Try the AnomalyDetector if available; otherwise return raw span counts."""
    out = {}
    try:
        sys.path.insert(0, str(Path("/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/src")))
        from agenttelemetry.analysis.anomaly import AnomalyDetector
        spans = []
        with open(TRACES) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    spans.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        detector = AnomalyDetector()
        anomalies = detector.detect(spans)
        out = {
            "total_spans": len(spans),
            "total_anomalies": len(anomalies),
            "by_type": dict(Counter(a.get("type", "unknown") for a in anomalies)),
        }
    except Exception as e:
        # Fallback: just count spans by kind
        try:
            spans = []
            with open(TRACES) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        spans.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            kind_counts = Counter()
            for s in spans:
                attrs = s.get("attributes", {}) or {}
                k = attrs.get("agenttelemetry.span.kind") or attrs.get("span.kind") or "unknown"
                kind_counts[k] += 1
            out = {
                "anomaly_detector_error": f"{type(e).__name__}: {e}",
                "total_spans": len(spans),
                "spans_by_kind": dict(kind_counts),
            }
        except Exception as e2:
            out = {"error": f"trace load failed: {type(e2).__name__}: {e2}"}
    return out


def main():
    runs = load_runs()
    per_cell = aggregate(runs)
    organic = organic_faults_from_traces()

    summary = {
        "n_runs": len(runs),
        "n_topologies": len({r.get("topology") for r in runs}),
        "n_models": len({r.get("model") for r in runs}),
        "per_cell": per_cell,
        "organic_faults": organic,
    }

    with open(OUT_DIR / "summary.json", "w") as f:
        json.dump({"summary": summary, "runs": runs}, f, indent=2, default=str)

    # Human-readable
    lines = [
        "=" * 80,
        "B2: Multi-agent topology comparison (recovered from per_run/)",
        "=" * 80,
        f"Total runs: {summary['n_runs']}",
        f"Topologies: {summary['n_topologies']} | Models: {summary['n_models']}",
        "",
        "Per-cell results:",
        f"  {'topology':<13} {'model':<38} {'n':<3} {'done':<5} {'cost($)':<10} {'wall(s)':<10} {'in_tok':<8} {'out_tok':<8}",
        "  " + "-" * 96,
    ]
    for cell_key, st in sorted(per_cell.items()):
        lines.append(
            f"  {st['topology']:<13} {st['model']:<38} {st['n_runs']:<3} "
            f"{st['n_completed']:<5} {st['avg_cost_usd']:<10.4f} {st['avg_wall_clock_s']:<10.1f} "
            f"{int(st['avg_input_tokens']):<8} {int(st['avg_output_tokens']):<8}"
        )
    lines.append("")
    if "by_type" in organic:
        lines.append(f"Organic faults detected: {organic['total_anomalies']} across {organic['total_spans']} spans")
        for ftype, n in sorted(organic["by_type"].items()):
            lines.append(f"    {ftype}: {n}")
    elif "spans_by_kind" in organic:
        lines.append(f"Spans by kind ({organic['total_spans']} total):")
        for kind, n in sorted(organic["spans_by_kind"].items(), key=lambda x: -x[1]):
            lines.append(f"    {kind}: {n}")
        if "anomaly_detector_error" in organic:
            lines.append("")
            lines.append(f"(AnomalyDetector unavailable: {organic['anomaly_detector_error']})")
    text = "\n".join(lines)
    with open(OUT_DIR / "summary.txt", "w") as f:
        f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
