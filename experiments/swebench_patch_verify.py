"""SWE-bench Patch Verification: Lightweight correctness check.

Compares agent-proposed patches (from swebench case study) against
SWE-bench ground-truth patches using heuristic similarity metrics.

Checks:
1. File match: Does the agent mention the same files as the ground truth?
2. Code similarity: Does the agent's answer reference similar code constructs?
3. Approach match: Does the agent's described fix align with the ground truth change?

This is NOT a substitute for the full Docker-based SWE-bench evaluation,
but provides a plausibility estimate for how many patches are on the right track.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results" / "swebench_verification"
CASE_STUDY_RESULTS = PROJECT_ROOT.parent / "results" / "swebench_case_study" / "agent_results.json"
SWEBENCH_100_RESULTS = PROJECT_ROOT.parent / "AgentTelemetry" / "results" / "swebench_100" / "agent_results.json"


@dataclass
class PatchVerification:
    """Result of verifying one agent patch against ground truth."""
    instance_id: str
    repo: str
    source_file: str  # which results file it came from

    # Ground truth info
    gt_files: List[str]
    gt_changes_summary: str
    gt_lines_added: int
    gt_lines_removed: int

    # Agent info
    agent_answer_length: int
    agent_mentioned_files: List[str]
    agent_code_snippets: List[str]

    # Match scores (0.0 - 1.0)
    file_match_score: float  # fraction of GT files mentioned by agent
    code_similarity_score: float  # textual similarity of code snippets
    approach_match_score: float  # keyword/concept overlap

    # Verdict
    plausible: bool
    verdict: str  # "correct_approach", "partial_match", "wrong_approach", "no_content"
    notes: str = ""


def extract_gt_info(patch: str) -> Dict[str, Any]:
    """Extract structured info from a ground-truth unified diff patch."""
    files = re.findall(r'^diff --git a/(.+?) b/', patch, re.MULTILINE)

    lines_added = len(re.findall(r'^\+[^+]', patch, re.MULTILINE))
    lines_removed = len(re.findall(r'^-[^-]', patch, re.MULTILINE))

    # Extract the actual changed lines (added)
    added_lines = re.findall(r'^\+(.+)$', patch, re.MULTILINE)
    added_lines = [l for l in added_lines if not l.startswith('++')]

    # Extract removed lines
    removed_lines = re.findall(r'^-(.+)$', patch, re.MULTILINE)
    removed_lines = [l for l in removed_lines if not l.startswith('--')]

    # Extract key identifiers from changes
    all_change_text = "\n".join(added_lines + removed_lines)
    identifiers = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', all_change_text))

    # Extract function/class names from context
    context_funcs = re.findall(r'@@.*@@\s*(?:def|class)\s+(\w+)', patch)

    return {
        "files": files,
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "identifiers": identifiers,
        "context_functions": context_funcs,
        "changes_summary": _summarize_changes(files, added_lines, removed_lines),
    }


def _summarize_changes(files: List[str], added: List[str], removed: List[str]) -> str:
    """Create a brief summary of what the ground truth patch does."""
    parts = []
    if files:
        parts.append(f"Files: {', '.join(files[:3])}")
    if added:
        parts.append(f"Added {len(added)} lines")
    if removed:
        parts.append(f"Removed {len(removed)} lines")
    key_added = [l.strip() for l in added[:3] if l.strip()]
    if key_added:
        parts.append(f"Key additions: {'; '.join(key_added[:2])}")
    return " | ".join(parts)


def extract_agent_info(answer: str) -> Dict[str, Any]:
    """Extract structured info from agent's answer text."""
    if not answer or not answer.strip():
        return {
            "mentioned_files": [],
            "code_snippets": [],
            "key_identifiers": set(),
            "mentioned_functions": [],
        }

    # Extract file paths mentioned
    file_patterns = re.findall(
        r'(?:[\w/]+\.(?:py|js|ts|java|rb|go|rs|c|cpp|h|hpp|txt|cfg|ini|toml|yml|yaml))',
        answer
    )
    # Also look for paths like django/db/models/fields/__init__.py
    path_patterns = re.findall(r'(?:[\w]+(?:/[\w]+){2,}\.py)', answer)
    mentioned_files = list(set(file_patterns + path_patterns))

    # Extract code snippets (inside ``` blocks)
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', answer, re.DOTALL)
    # Also look for inline code changes
    inline_code = re.findall(r'`([^`]{10,})`', answer)
    code_snippets = code_blocks + inline_code

    # Extract identifiers from code and text
    all_text = answer + "\n".join(code_snippets)
    identifiers = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\b', all_text))

    # Extract function/class names mentioned
    func_mentions = re.findall(r'(?:def|class|function|method)\s+[`]?(\w+)', answer)
    func_mentions += re.findall(r'`(\w+)\(\)`', answer)
    func_mentions += re.findall(r'`(\w+)`\s+(?:method|function|class)', answer)

    return {
        "mentioned_files": mentioned_files,
        "code_snippets": code_snippets,
        "key_identifiers": identifiers,
        "mentioned_functions": func_mentions,
    }


def compute_file_match(gt_files: List[str], agent_files: List[str], agent_answer: str) -> float:
    """Compute how well the agent identified the correct files."""
    if not gt_files:
        return 0.0

    matched = 0
    for gt_file in gt_files:
        gt_basename = os.path.basename(gt_file)
        gt_parts = gt_file.split("/")

        # Check exact match
        if gt_file in agent_files:
            matched += 1
            continue

        # Check basename match
        if any(gt_basename in af for af in agent_files):
            matched += 1
            continue

        # Check if file path appears in answer text at all
        if gt_file in agent_answer:
            matched += 1
            continue

        # Check partial path match (last 2+ components)
        if len(gt_parts) >= 2:
            partial = "/".join(gt_parts[-2:])
            if partial in agent_answer:
                matched += 1
                continue

        # Check if basename appears in answer
        if gt_basename in agent_answer:
            matched += 0.5
            continue

    return min(matched / len(gt_files), 1.0)


def compute_code_similarity(gt_info: Dict, agent_info: Dict) -> float:
    """Compute similarity between ground truth code changes and agent's code."""
    if not agent_info["code_snippets"]:
        # Fall back to identifier overlap
        return compute_identifier_overlap(gt_info, agent_info) * 0.5

    # Compare agent code snippets against GT added lines
    gt_code = "\n".join(gt_info.get("added_lines", []))
    agent_code = "\n".join(agent_info["code_snippets"])

    if not gt_code or not agent_code:
        return compute_identifier_overlap(gt_info, agent_info) * 0.5

    # SequenceMatcher on normalized code
    gt_norm = _normalize_code(gt_code)
    agent_norm = _normalize_code(agent_code)

    ratio = SequenceMatcher(None, gt_norm, agent_norm).ratio()

    # Also check identifier overlap as a supplementary signal
    id_overlap = compute_identifier_overlap(gt_info, agent_info)

    return 0.6 * ratio + 0.4 * id_overlap


def compute_identifier_overlap(gt_info: Dict, agent_info: Dict) -> float:
    """Compute Jaccard similarity of identifiers."""
    gt_ids = gt_info.get("identifiers", set())
    agent_ids = agent_info.get("key_identifiers", set())

    # Filter out very common Python keywords
    common_words = {
        "self", "return", "import", "from", "class", "def", "None", "True",
        "False", "not", "and", "for", "while", "with", "pass", "raise",
        "try", "except", "finally", "else", "elif", "the", "this", "that",
        "will", "should", "would", "could", "have", "been", "has", "was",
        "are", "were", "being", "The", "print", "str", "int", "float",
        "list", "dict", "set", "tuple", "args", "kwargs", "isinstance",
    }

    gt_ids = gt_ids - common_words
    agent_ids = agent_ids - common_words

    if not gt_ids or not agent_ids:
        return 0.0

    intersection = gt_ids & agent_ids
    union = gt_ids | agent_ids

    return len(intersection) / len(union) if union else 0.0


def _normalize_code(code: str) -> str:
    """Normalize code for comparison."""
    # Remove comments
    code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    # Normalize whitespace
    code = re.sub(r'\s+', ' ', code)
    # Remove leading +/- from diff lines
    code = re.sub(r'^[+-]\s*', '', code, flags=re.MULTILINE)
    return code.strip().lower()


def compute_approach_match(
    gt_info: Dict,
    agent_info: Dict,
    agent_answer: str,
) -> float:
    """Compute whether the agent's described approach matches the GT fix."""
    score = 0.0
    signals = 0

    # Check if agent mentions the right functions/classes
    gt_funcs = set(gt_info.get("context_functions", []))
    agent_funcs = set(agent_info.get("mentioned_functions", []))
    if gt_funcs:
        func_overlap = len(gt_funcs & agent_funcs) / len(gt_funcs)
        score += func_overlap
        signals += 1

    # Check if key GT identifiers appear in agent answer
    gt_key_ids = gt_info.get("identifiers", set())
    # Focus on the most distinctive identifiers (not too short, not too common)
    distinctive = {
        i for i in gt_key_ids
        if len(i) > 4 and i.lower() not in {
            "self", "return", "import", "class", "super", "value",
            "values", "items", "string", "false", "other", "error",
        }
    }
    if distinctive:
        mentioned = sum(1 for i in distinctive if i in agent_answer or i.lower() in agent_answer.lower())
        score += mentioned / len(distinctive)
        signals += 1

    # Check structural similarity: does the agent propose similar types of changes?
    gt_added = "\n".join(gt_info.get("added_lines", []))
    change_patterns = {
        "add_check": (r'if\s+', "conditional check"),
        "add_import": (r'import\s+', "import"),
        "modify_return": (r'return\s+', "return value"),
        "exception": (r'raise\s+|except\s+', "exception handling"),
        "regex": (r're\.\w+|IGNORECASE|compile', "regex modification"),
        "string_method": (r'\.lower\(\)|\.upper\(\)|\.strip\(\)', "string method"),
    }

    for pattern_name, (regex, desc) in change_patterns.items():
        gt_has = bool(re.search(regex, gt_added))
        agent_has = bool(re.search(regex, agent_answer))
        if gt_has and agent_has:
            score += 0.5
            signals += 0.5
        elif gt_has and not agent_has:
            signals += 0.5

    return score / signals if signals > 0 else 0.0


def classify_verdict(
    file_score: float,
    code_score: float,
    approach_score: float,
    agent_answer: str,
) -> Tuple[bool, str]:
    """Classify the verification verdict."""
    if not agent_answer or len(agent_answer.strip()) < 20:
        return False, "no_content"

    # Weighted composite score
    composite = 0.35 * file_score + 0.30 * code_score + 0.35 * approach_score

    if composite >= 0.45:
        return True, "correct_approach"
    elif composite >= 0.25:
        return True, "partial_match"
    elif composite >= 0.15:
        return False, "weak_match"
    else:
        return False, "wrong_approach"


def verify_one(
    agent_result: Dict,
    gt_instance: Dict,
    source_file: str,
) -> PatchVerification:
    """Verify one agent result against the ground truth."""
    instance_id = agent_result["instance_id"]
    repo = agent_result.get("repo", gt_instance.get("repo", ""))
    answer = agent_result.get("answer", "")
    gt_patch = gt_instance.get("patch", "")

    gt_info = extract_gt_info(gt_patch)
    agent_info = extract_agent_info(answer)

    file_score = compute_file_match(gt_info["files"], agent_info["mentioned_files"], answer)
    code_score = compute_code_similarity(gt_info, agent_info)
    approach_score = compute_approach_match(gt_info, agent_info, answer)

    plausible, verdict = classify_verdict(file_score, code_score, approach_score, answer)

    notes_parts = []
    if file_score >= 0.5:
        notes_parts.append(f"files: {agent_info['mentioned_files'][:3]}")
    if gt_info["context_functions"]:
        notes_parts.append(f"gt_funcs: {gt_info['context_functions'][:3]}")

    return PatchVerification(
        instance_id=instance_id,
        repo=repo,
        source_file=source_file,
        gt_files=gt_info["files"],
        gt_changes_summary=gt_info["changes_summary"],
        gt_lines_added=gt_info["lines_added"],
        gt_lines_removed=gt_info["lines_removed"],
        agent_answer_length=len(answer),
        agent_mentioned_files=agent_info["mentioned_files"],
        agent_code_snippets=[s[:200] for s in agent_info["code_snippets"][:5]],
        file_match_score=round(file_score, 3),
        code_similarity_score=round(code_score, 3),
        approach_match_score=round(approach_score, 3),
        plausible=plausible,
        verdict=verdict,
        notes=" | ".join(notes_parts),
    )


def load_results() -> List[Dict]:
    """Load agent results from both result files, deduplicating by instance_id."""
    all_results = {}

    # Load case study results (primary)
    if CASE_STUDY_RESULTS.exists():
        data = json.loads(CASE_STUDY_RESULTS.read_text())
        for r in data:
            if r.get("proposed_patch") and r.get("answer", "").strip():
                r["_source"] = "swebench_case_study"
                all_results[r["instance_id"]] = r
        print(f"  Loaded {len(data)} instances from case_study ({sum(1 for r in data if r.get('proposed_patch'))} patches)")

    # Load swebench_100 results (supplementary)
    if SWEBENCH_100_RESULTS.exists():
        data = json.loads(SWEBENCH_100_RESULTS.read_text())
        for r in data:
            if r.get("proposed_patch") and r.get("answer", "").strip():
                if r["instance_id"] not in all_results:
                    r["_source"] = "swebench_100"
                    all_results[r["instance_id"]] = r
        print(f"  Loaded {len(data)} instances from swebench_100 ({sum(1 for r in data if r.get('proposed_patch'))} patches)")

    print(f"  Total unique patches to verify: {len(all_results)}")
    return list(all_results.values())


def main():
    """Run patch verification."""
    print("=" * 70)
    print("SWE-bench Patch Verification (Lightweight)")
    print("=" * 70)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load agent results
    print("\nLoading agent results...")
    agent_results = load_results()

    if not agent_results:
        print("ERROR: No agent results with proposed patches found.")
        sys.exit(1)

    # Load SWE-bench Lite dataset
    print("\nLoading SWE-bench Lite dataset...")
    from datasets import load_dataset
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    gt_lookup = {inst["instance_id"]: inst for inst in ds}
    print(f"  {len(ds)} ground-truth instances loaded")

    # Verify each patch
    print(f"\nVerifying {len(agent_results)} proposed patches...")
    print("-" * 70)

    verifications = []
    for r in sorted(agent_results, key=lambda x: x["instance_id"]):
        instance_id = r["instance_id"]
        source = r.get("_source", "unknown")

        if instance_id not in gt_lookup:
            print(f"  SKIP {instance_id}: not in SWE-bench Lite")
            continue

        gt = gt_lookup[instance_id]
        v = verify_one(r, gt, source)
        verifications.append(v)

        status = "PLAUSIBLE" if v.plausible else "UNLIKELY "
        print(
            f"  [{status}] {instance_id:<45} "
            f"file={v.file_match_score:.2f} code={v.code_similarity_score:.2f} "
            f"approach={v.approach_match_score:.2f} -> {v.verdict}"
        )

    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    total = len(verifications)
    plausible = sum(1 for v in verifications if v.plausible)
    by_verdict = defaultdict(int)
    for v in verifications:
        by_verdict[v.verdict] += 1

    print(f"\n  Total patches verified: {total}")
    print(f"  Plausibly correct:      {plausible} ({plausible/total*100:.1f}%)")
    print(f"  Likely incorrect:       {total - plausible} ({(total-plausible)/total*100:.1f}%)")

    print(f"\n  Verdict breakdown:")
    for verdict in ["correct_approach", "partial_match", "weak_match", "wrong_approach", "no_content"]:
        count = by_verdict.get(verdict, 0)
        if count > 0:
            print(f"    {verdict:<20} {count:>3} ({count/total*100:.1f}%)")

    # Score distributions
    file_scores = [v.file_match_score for v in verifications]
    code_scores = [v.code_similarity_score for v in verifications]
    approach_scores = [v.approach_match_score for v in verifications]

    print(f"\n  Score distributions (mean / median):")
    for name, scores in [("File match", file_scores), ("Code similarity", code_scores), ("Approach match", approach_scores)]:
        mean = sum(scores) / len(scores) if scores else 0
        sorted_s = sorted(scores)
        median = sorted_s[len(sorted_s)//2] if sorted_s else 0
        print(f"    {name:<20} {mean:.3f} / {median:.3f}")

    # By repo
    print(f"\n  By repository:")
    repo_results = defaultdict(lambda: {"total": 0, "plausible": 0})
    for v in verifications:
        repo_results[v.repo]["total"] += 1
        if v.plausible:
            repo_results[v.repo]["plausible"] += 1

    for repo in sorted(repo_results.keys()):
        r = repo_results[repo]
        rate = r["plausible"] / r["total"] * 100
        print(f"    {repo:<40} {r['plausible']}/{r['total']} ({rate:.0f}%)")

    # Detailed results for plausible patches
    print(f"\n  Plausibly correct patches:")
    for v in verifications:
        if v.plausible:
            composite = 0.35 * v.file_match_score + 0.30 * v.code_similarity_score + 0.35 * v.approach_match_score
            print(f"    {v.instance_id:<45} composite={composite:.3f} [{v.verdict}]")
            if v.gt_files:
                print(f"      GT files: {', '.join(v.gt_files[:3])}")
            if v.agent_mentioned_files:
                print(f"      Agent files: {', '.join(v.agent_mentioned_files[:3])}")

    # Save results
    results_data = {
        "summary": {
            "total_verified": total,
            "plausibly_correct": plausible,
            "plausible_rate": round(plausible / total * 100, 1) if total else 0,
            "by_verdict": dict(by_verdict),
            "mean_file_match": round(sum(file_scores) / len(file_scores), 3) if file_scores else 0,
            "mean_code_similarity": round(sum(code_scores) / len(code_scores), 3) if code_scores else 0,
            "mean_approach_match": round(sum(approach_scores) / len(approach_scores), 3) if approach_scores else 0,
        },
        "verifications": [asdict(v) for v in verifications],
    }

    output_path = RESULTS_DIR / "verification_results.json"
    with open(output_path, "w") as f:
        json.dump(results_data, f, indent=2, default=str)
    print(f"\n  Results saved to: {output_path}")

    # Also save a compact CSV-like summary
    summary_path = RESULTS_DIR / "verification_summary.txt"
    with open(summary_path, "w") as f:
        f.write(f"SWE-bench Patch Verification Summary\n")
        f.write(f"{'='*70}\n")
        f.write(f"Total verified: {total}\n")
        f.write(f"Plausibly correct: {plausible} ({plausible/total*100:.1f}%)\n")
        f.write(f"Likely incorrect: {total-plausible} ({(total-plausible)/total*100:.1f}%)\n\n")
        f.write(f"{'Instance ID':<45} {'File':>5} {'Code':>5} {'Appr':>5} {'Verdict':<20}\n")
        f.write(f"{'-'*85}\n")
        for v in verifications:
            f.write(
                f"{v.instance_id:<45} {v.file_match_score:>5.2f} "
                f"{v.code_similarity_score:>5.2f} {v.approach_match_score:>5.2f} "
                f"{v.verdict:<20}\n"
            )
    print(f"  Summary saved to: {summary_path}")

    print(f"\n{'='*70}")
    print("VERIFICATION COMPLETE")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
