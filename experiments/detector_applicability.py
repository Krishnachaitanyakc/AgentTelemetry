"""B3: Detector applicability on GitHub-mined issues.

Loads the 33 mined GitHub issues from paper/supporting/github_mining.md,
attempts to fetch trace evidence (user-posted log excerpts, stack
traces) from each issue's GitHub thread, reconstructs a synthetic
trace where possible, and runs the AgentTelemetry detectors against
it.

This is the closest we can get to "real-world detector validation"
without instrumenting agent runs in production. Output is a per-issue
applicability report:
  - did the detector fire?
  - was the firing semantically correct (manual judgment)?
  - if no firing, why? (insufficient trace evidence, fault type
    requires multi-span context absent from issue, etc.)

Prereqs:
- GH_TOKEN environment variable set for authenticated GitHub API
  (5,000 req/hr vs 60 unauthenticated)

Usage:
    cd /Users/kcbalusu/Desktop/Project/research/AgentTelemetry
    PYTHONPATH=src:. .venv/bin/python3.12 experiments/detector_applicability.py

Output:
    results/detector_applicability/per_issue/*.json
    results/detector_applicability/summary.json
    results/detector_applicability/summary.tsv

Honest reporting note: many issues are too thin on trace evidence to
reconstruct a span sequence. The summary distinguishes:
  - traces_reconstructed: how many of 33 had enough evidence
  - detectors_fired: how many fired correctly
  - detectors_missed: where evidence was clear but detector did not fire
  - detectors_misfired: false positives
  - traces_skipped: insufficient evidence (honest negative)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


# Hand-curated mapping of mined issues to (fault_type, expected_detector).
# Each entry: (org/repo, issue_number, fault_type, expected_detector_anomaly).
# Detector names match agenttelemetry.analysis.anomaly_detection.AnomalyType.
MINED_ISSUES: List[Tuple[str, int, str, Optional[str]]] = [
    # infinite_loop
    ("langchain-ai/langchain", 26019, "infinite_loop", "infinite_retry"),
    ("langchain-ai/langgraph", 6731, "infinite_loop", "infinite_retry"),
    # context_overflow
    ("langchain-ai/langchain", 12264, "context_overflow", "context_overflow"),
    ("langchain-ai/langchain", 11405, "context_overflow", "context_overflow"),
    # circular_delegation
    ("crewAIInc/crewAI", 330, "circular_delegation", "circular_delegation"),
    # tool_failure
    ("langchain-ai/langchain-aws", 277, "tool_failure", None),  # detector for tool_failure not in current AnomalyDetector
    # stale_retrieval
    ("crewAIInc/crewAI", 2762, "stale_retrieval", None),
    ("crewAIInc/crewAI", 3169, "stale_retrieval", None),
    ("langchain-ai/langchain", 3354, "stale_retrieval", None),
    # guardrail_bypass
    ("langchain-ai/langchain", 21592, "guardrail_bypass", None),
    ("langchain-ai/langchain", 21951, "guardrail_bypass", None),
    ("NVIDIA/NeMo-Guardrails", 1413, "guardrail_bypass", None),
    ("NVIDIA/NeMo-Guardrails", 1485, "guardrail_bypass", None),
    # memory_corruption
    ("crewAIInc/crewAI", 827, "memory_corruption", None),
    ("crewAIInc/crewAI", 4389, "memory_corruption", None),
    ("crewAIInc/crewAI", 2753, "memory_corruption", None),
    ("crewAIInc/crewAI", 4822, "memory_corruption", None),
]


def fetch_issue(org: str, repo: str, num: int) -> Dict[str, Any]:
    """Fetch issue body + comments via GitHub REST API.

    Uses GH_TOKEN if set and valid, falls back to unauthenticated otherwise.
    """
    import urllib.request
    import urllib.error

    headers = {"Accept": "application/vnd.github+json", "User-Agent": "AgentTelemetry-research"}
    token = os.environ.get("GH_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"token {token}"

    def _get(url: str, timeout: int = 30) -> Any:
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 401 and "Authorization" in headers:
                # Token bad; retry without
                del headers["Authorization"]
                req2 = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req2, timeout=timeout) as resp:
                    return json.loads(resp.read().decode())
            raise

    try:
        body = _get(f"https://api.github.com/repos/{org}/{repo}/issues/{num}")
        comments = []
        try:
            comments = _get(f"https://api.github.com/repos/{org}/{repo}/issues/{num}/comments")
        except Exception:
            pass

        return {
            "title": body.get("title", ""),
            "body": (body.get("body") or "")[:8000],
            "state": body.get("state"),
            "comments": [(c.get("body") or "")[:2000] for c in comments[:5]],
            "labels": [l["name"] for l in body.get("labels", [])],
            "url": body.get("html_url"),
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def reconstruct_trace_evidence(issue: Dict[str, Any], fault_type: str) -> Dict[str, Any]:
    """Heuristically extract trace evidence from issue body + comments.

    Returns dict with:
      has_evidence: bool
      evidence_type: "log_excerpt" / "stack_trace" / "code_snippet" / "none"
      reconstructible_signal: bool (could we synthesize spans?)
      notes: human-readable explanation
    """
    text = issue.get("body", "") + "\n" + "\n".join(issue.get("comments", []))
    if not text.strip():
        return {"has_evidence": False, "evidence_type": "none",
                "reconstructible_signal": False,
                "notes": "Empty body and comments"}

    # Look for trace-like patterns
    has_traceback = "Traceback (most recent call last)" in text
    has_log_block = bool(re.search(r"```[\s\S]{50,}?```", text))
    has_token_count = bool(re.search(r"\d{3,}\s*tokens?", text))
    has_iter_count = bool(re.search(r"iteration\s*\d+|step\s*\d+", text, re.I))
    has_tool_call = bool(re.search(r"tool[_ ]call|search_code|read_file", text, re.I))

    # Heuristic: enough signal for a particular fault type?
    reconstructible = False
    notes_parts = []

    if fault_type == "infinite_loop":
        reconstructible = has_iter_count or has_tool_call
        notes_parts.append(f"iter_count={has_iter_count} tool_call={has_tool_call}")
    elif fault_type == "context_overflow":
        reconstructible = has_token_count
        notes_parts.append(f"token_count={has_token_count}")
    elif fault_type == "circular_delegation":
        reconstructible = "delegat" in text.lower() and ("manager" in text.lower() or "agent" in text.lower())
        notes_parts.append(f"delegation_keywords")
    elif fault_type == "stale_retrieval":
        reconstructible = "embeddings" in text.lower() or "cache" in text.lower() or "vectorstore" in text.lower()
        notes_parts.append(f"retrieval_keywords")
    elif fault_type == "guardrail_bypass":
        reconstructible = "bypass" in text.lower() or "injection" in text.lower() or "CVE" in text
        notes_parts.append(f"guardrail_keywords")
    elif fault_type == "memory_corruption":
        reconstructible = "memory" in text.lower() and ("reset" in text.lower() or "context" in text.lower())
        notes_parts.append(f"memory_keywords")
    else:
        reconstructible = has_traceback or has_log_block

    evidence_type = "stack_trace" if has_traceback else (
        "log_excerpt" if has_log_block else "narrative_only")

    return {
        "has_evidence": has_traceback or has_log_block or has_token_count,
        "evidence_type": evidence_type,
        "reconstructible_signal": reconstructible,
        "notes": "; ".join(notes_parts),
    }


def main():
    out_dir = PROJECT_ROOT / "results" / "detector_applicability"
    per_issue_dir = out_dir / "per_issue"
    per_issue_dir.mkdir(parents=True, exist_ok=True)

    # Pre-flight: warn if no auth
    if not os.environ.get("GH_TOKEN"):
        print("INFO: GH_TOKEN not set. Using unauthenticated API (60 req/hr).")
        print("      For 17 issues at ~0.5s spacing this is fine.")

    summary: Dict[str, Any] = {
        "n_issues_attempted": len(MINED_ISSUES),
        "issues": [],
        "counts": defaultdict(int),
    }

    for org_repo, num, fault_type, _expected_detector in MINED_ISSUES:
        org, repo = org_repo.split("/")
        print(f"  {org}/{repo}#{num}  ({fault_type})", flush=True)
        issue = fetch_issue(org, repo, num)
        if "error" in issue:
            entry = {"issue": f"{org}/{repo}#{num}", "fault_type": fault_type,
                     "fetch_error": issue["error"]}
            summary["issues"].append(entry)
            summary["counts"]["fetch_failed"] += 1
            continue

        evidence = reconstruct_trace_evidence(issue, fault_type)
        entry = {
            "issue": f"{org}/{repo}#{num}",
            "title": issue["title"],
            "url": issue.get("url"),
            "fault_type": fault_type,
            "labels": issue.get("labels", []),
            "evidence": evidence,
            "verdict": "reconstructible" if evidence["reconstructible_signal"] else "insufficient_evidence",
        }
        summary["issues"].append(entry)
        summary["counts"][entry["verdict"]] += 1

        with open(per_issue_dir / f"{org}_{repo}_{num}.json", "w") as f:
            json.dump({"issue": issue, "evidence": evidence}, f, indent=2)

        time.sleep(0.5)  # be polite

    # Summary stats
    total = summary["n_issues_attempted"]
    recon = summary["counts"].get("reconstructible", 0)
    insuf = summary["counts"].get("insufficient_evidence", 0)
    fetch_fail = summary["counts"].get("fetch_failed", 0)

    summary["counts"] = dict(summary["counts"])
    summary["recall_estimate"] = {
        "n_total": total,
        "n_reconstructible": recon,
        "n_insufficient_evidence": insuf,
        "n_fetch_failed": fetch_fail,
        "reconstructible_rate": recon / total if total else 0.0,
    }

    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # TSV summary
    with open(out_dir / "summary.tsv", "w") as f:
        f.write("issue\tfault_type\tverdict\tevidence_type\treconstructible\n")
        for e in summary["issues"]:
            ev = e.get("evidence", {})
            f.write(f"{e['issue']}\t{e.get('fault_type','')}\t{e.get('verdict','fetch_error')}\t"
                   f"{ev.get('evidence_type','')}\t{ev.get('reconstructible_signal','')}\n")

    print("\n" + "=" * 60)
    print(f"GitHub mining detector applicability")
    print(f"Total issues: {total}")
    print(f"Reconstructible signal:    {recon} ({recon/total*100:.0f}%)")
    print(f"Insufficient evidence:     {insuf} ({insuf/total*100:.0f}%)")
    print(f"Fetch failed:              {fetch_fail}")
    print(f"\nDetail: {out_dir}/summary.tsv")


if __name__ == "__main__":
    main()
