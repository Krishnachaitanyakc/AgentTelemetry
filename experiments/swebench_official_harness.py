"""B2: Run official SWE-bench evaluation harness on the 33 verified patches.

Replaces the current LLM-judged 87.9% plausibility number with the
ground-truth pass/fail rate from SWE-bench's own test runner.
This addresses reviewer WS9c #3b (most damaging concern: SWE-bench
patch rate is self-verified, not against ground-truth tests).

Prereqs:
- Docker installed and running (Docker Desktop for Mac)
- pip install swebench  (the official harness package)
- 10-20 GB free disk for SWE-bench eval Docker images
- 1-2 days of runtime depending on instance count

Usage:
    cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
    pip install swebench
    .venv/bin/python3.12 experiments/swebench_official_harness.py \\
        --predictions-file results/swebench_verification/predictions.jsonl \\
        --output-dir results/swebench_official_harness

Output:
    results/swebench_official_harness/results.json
    results/swebench_official_harness/per_instance/
    results/swebench_official_harness/summary.txt

Honest reporting: even if the official pass rate is much lower than
87.9%, that IS the contribution -- it shows the gap between guardrail
self-verification and ground-truth correctness. WS9c will accept an
honest "X% (much lower than self-judged 87.9%; we report this gap as
itself a useful finding for agent observability)" framing.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def check_prereqs() -> bool:
    """Verify Docker and swebench are available."""
    ok = True
    docker = shutil.which("docker")
    if not docker:
        print("ERROR: Docker not found. Install Docker Desktop for Mac.")
        ok = False
    else:
        print(f"Docker: {docker}")
        try:
            result = subprocess.run(["docker", "info"], capture_output=True,
                                   text=True, timeout=10)
            if result.returncode != 0:
                print("ERROR: Docker daemon not running. Start Docker Desktop.")
                ok = False
        except Exception as e:
            print(f"ERROR: Docker check failed: {e}")
            ok = False

    try:
        import swebench  # noqa: F401
        print(f"swebench: importable")
    except ImportError:
        print("ERROR: swebench not installed. Run: pip install swebench")
        ok = False

    return ok


def load_verified_patches() -> List[Dict[str, Any]]:
    """Load the 33 verified patches from prior LLM-judged verification."""
    summary_path = PROJECT_ROOT / "results" / "swebench_verification" / "verification_results.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing {summary_path}")
    with open(summary_path) as f:
        data = json.load(f)
    # data may be {"results": [...]} or [...]
    if isinstance(data, dict):
        return data.get("results", data.get("verified_patches", []))
    return data


def to_swebench_predictions_format(patches: List[Dict[str, Any]],
                                    model_name_or_path: str) -> List[Dict[str, str]]:
    """Convert internal patch records to SWE-bench predictions.jsonl format.

    SWE-bench expects each line to be a JSON object with:
      instance_id, model_name_or_path, model_patch
    """
    preds = []
    for p in patches:
        iid = p.get("instance_id")
        patch_text = p.get("patch") or p.get("model_patch") or p.get("answer", "")
        if not iid:
            continue
        preds.append({
            "instance_id": iid,
            "model_name_or_path": model_name_or_path,
            "model_patch": patch_text,
        })
    return preds


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--predictions-file", default=None,
                   help="If set, use this jsonl directly; else build from verification_results.json")
    p.add_argument("--output-dir", default="results/swebench_official_harness")
    p.add_argument("--model-name", default="agenttelemetry-coding-agent")
    p.add_argument("--max-workers", type=int, default=4,
                   help="Parallel test runners (mind your CPU/RAM)")
    p.add_argument("--run-id", default="agenttelemetry_b2",
                   help="SWE-bench run identifier")
    args = p.parse_args()

    if not check_prereqs():
        sys.exit(1)

    out_dir = PROJECT_ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build predictions file if not provided
    if args.predictions_file is None:
        patches = load_verified_patches()
        preds = to_swebench_predictions_format(patches, args.model_name)
        pred_path = out_dir / "predictions.jsonl"
        with open(pred_path, "w") as f:
            for pr in preds:
                f.write(json.dumps(pr) + "\n")
        print(f"Wrote {len(preds)} predictions to {pred_path}")
    else:
        pred_path = Path(args.predictions_file)
        if not pred_path.exists():
            print(f"ERROR: {pred_path} does not exist")
            sys.exit(1)

    # Run official harness
    cmd = [
        sys.executable, "-m", "swebench.harness.run_evaluation",
        "--dataset_name", "princeton-nlp/SWE-bench_Lite",
        "--predictions_path", str(pred_path),
        "--max_workers", str(args.max_workers),
        "--run_id", args.run_id,
        "--report_dir", str(out_dir),
        "--cache_level", "instance",
    ]
    print("\nRunning:", " ".join(cmd))
    print("(This pulls Docker images per instance and runs the test suite.)")
    print("(Expect 1-2 days for 33 instances depending on test runtime.)\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\nharness exit code {result.returncode}")
        sys.exit(result.returncode)

    # Parse and summarize
    report_files = list(out_dir.glob(f"{args.model_name}.{args.run_id}.json"))
    if not report_files:
        print("WARNING: no report file found; check out_dir")
        return

    report_path = report_files[0]
    with open(report_path) as f:
        report = json.load(f)

    n_resolved = len(report.get("resolved_ids", []))
    n_total = report.get("total_instances", 0)
    pass_rate = (n_resolved / n_total * 100) if n_total else 0.0

    summary = [
        "=" * 60,
        "B2: Official SWE-bench harness on AgentTelemetry patches",
        "=" * 60,
        f"Total instances:   {n_total}",
        f"Resolved (passed): {n_resolved}",
        f"Ground-truth pass rate: {pass_rate:.1f}%",
        f"(Compare to LLM-judged plausibility: 87.9% on 33 patches)",
        "",
        "Per-instance results: see report file at",
        f"  {report_path}",
    ]
    text = "\n".join(summary)
    with open(out_dir / "summary.txt", "w") as f:
        f.write(text + "\n")
    print("\n" + text)


if __name__ == "__main__":
    main()
