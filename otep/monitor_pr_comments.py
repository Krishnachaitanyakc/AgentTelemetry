#!/usr/bin/env python3
"""Poll a GitHub PR for new comments/reviews and log newly observed items.

Usage:
  python3 monitor_pr_comments.py --repo open-telemetry/semantic-conventions --pr 3594
  python3 monitor_pr_comments.py --repo open-telemetry/semantic-conventions --pr 3594 --watch 60
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def gh_api(path: str) -> list[dict[str, Any]]:
    proc = subprocess.run(
        ["gh", "api", path],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout)
    if not isinstance(data, list):
        raise TypeError(f"Expected list from gh api {path}, got {type(data).__name__}")
    return data


def normalize_issue_comment(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "issue_comment",
        "id": item["id"],
        "created_at": item.get("created_at"),
        "author": item.get("user", {}).get("login"),
        "url": item.get("html_url"),
        "body": item.get("body", "").strip(),
    }


def normalize_review(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "review",
        "id": item["id"],
        "created_at": item.get("submitted_at") or item.get("submittedAt") or item.get("created_at"),
        "author": item.get("user", {}).get("login"),
        "url": item.get("html_url"),
        "state": item.get("state"),
        "body": (item.get("body") or "").strip(),
    }


def normalize_review_comment(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "review_comment",
        "id": item["id"],
        "created_at": item.get("created_at"),
        "author": item.get("user", {}).get("login"),
        "url": item.get("html_url"),
        "path": item.get("path"),
        "line": item.get("line") or item.get("original_line"),
        "body": item.get("body", "").strip(),
    }


def fetch_snapshot(repo: str, pr: int) -> list[dict[str, Any]]:
    issue_comments = [
        normalize_issue_comment(x)
        for x in gh_api(f"repos/{repo}/issues/{pr}/comments")
    ]
    reviews = [
        normalize_review(x)
        for x in gh_api(f"repos/{repo}/pulls/{pr}/reviews")
    ]
    review_comments = [
        normalize_review_comment(x)
        for x in gh_api(f"repos/{repo}/pulls/{pr}/comments")
    ]
    items = issue_comments + reviews + review_comments
    items.sort(key=lambda x: (x.get("created_at") or "", x["kind"], x["id"]))
    return items


def format_item(item: dict[str, Any]) -> str:
    header = f"[{item['kind']}] {item.get('author') or 'unknown'}"
    if item["kind"] == "review" and item.get("state"):
        header += f" ({item['state']})"
    if item["kind"] == "review_comment" and item.get("path"):
        suffix = item["path"]
        if item.get("line"):
            suffix += f":{item['line']}"
        header += f" on {suffix}"
    parts = [header]
    if item.get("url"):
        parts.append(item["url"])
    body = item.get("body") or ""
    if body:
        parts.append(body)
    return "\n".join(parts)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def shell_quote(value: str) -> str:
    return shlex.quote(value)


def send_desktop_notification(title: str, message: str) -> None:
    script = (
        f'display notification {shell_quote(message)} '
        f'with title {shell_quote(title)}'
    )
    subprocess.run(
        ["osascript", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )


def write_log(log_path: Path, new_items: list[dict[str, Any]]) -> None:
    if not new_items:
        return
    with log_path.open("a", encoding="utf-8") as f:
        for item in new_items:
            f.write(f"\n=== {now_iso()} ===\n")
            f.write(format_item(item))
            f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--watch", type=int, default=0, help="poll interval in seconds")
    parser.add_argument(
        "--notify",
        action="store_true",
        help="send macOS desktop notifications for newly observed PR activity",
    )
    parser.add_argument(
        "--state-dir",
        default=str(Path.home() / ".codex-pr-monitor"),
        help="directory to store monitor state",
    )
    args = parser.parse_args()

    state_dir = Path(args.state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    key = f"{args.repo.replace('/', '__')}__pr_{args.pr}"
    state_path = state_dir / f"{key}.json"
    log_path = state_dir / f"{key}.log"

    def run_once() -> int:
        items = fetch_snapshot(args.repo, args.pr)
        previous: list[dict[str, Any]] = []
        if state_path.exists():
            previous = json.loads(state_path.read_text(encoding="utf-8"))
        prev_ids = {(x["kind"], x["id"]) for x in previous}
        new_items = [x for x in items if (x["kind"], x["id"]) not in prev_ids]
        if new_items:
            write_log(log_path, new_items)
            for item in new_items:
                print(format_item(item))
                print()
            if args.notify:
                latest = new_items[-1]
                author = latest.get("author") or "unknown"
                if latest["kind"] == "review":
                    summary = f"New review from {author}"
                elif latest["kind"] == "review_comment":
                    path = latest.get("path") or "file"
                    summary = f"New review comment from {author} on {path}"
                else:
                    summary = f"New PR comment from {author}"
                send_desktop_notification(
                    f"PR #{args.pr} activity",
                    summary,
                )
        else:
            print("No new PR comments or reviews.")
        state_path.write_text(json.dumps(items, indent=2), encoding="utf-8")
        print(f"State: {state_path}")
        print(f"Log:   {log_path}")
        return 0

    if args.watch <= 0:
        return run_once()

    while True:
        try:
            run_once()
        except subprocess.CalledProcessError as exc:
            print(exc.stderr or str(exc), file=sys.stderr)
        time.sleep(args.watch)


if __name__ == "__main__":
    raise SystemExit(main())
