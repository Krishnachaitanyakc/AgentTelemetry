"""CLI subprocess wrappers for Meta's claude and codex CLIs.

Standalone module — NO litellm dependency. Use this when you only need
the raw subprocess wrappers (e.g., for AgentTelemetry experiments that
manage their own response handling).

If you need litellm CustomLLM provider integration (e.g., for tau-bench),
use cli_litellm_provider.py instead.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any, Dict

CWD_FOR_CLI = "/tmp"  # bypass project-dir security gate


def _call_claude_cli(prompt: str, model: str, timeout: int = 600) -> Dict[str, Any]:
    """Invoke Meta `claude` CLI with --print and return text/error/latency.

    Returns dict with keys: text, error, latency_s.
    """
    start = time.time()
    try:
        r = subprocess.run(
            ["claude", "--model", model, "--print"],
            input=prompt, capture_output=True, text=True, timeout=timeout,
            cwd=CWD_FOR_CLI,
        )
        if r.returncode != 0:
            return {"text": "", "error": f"claude exit {r.returncode}: {r.stderr[:300]}",
                    "latency_s": time.time() - start}
        return {"text": r.stdout.strip(), "error": None,
                "latency_s": time.time() - start}
    except subprocess.TimeoutExpired:
        return {"text": "", "error": f"timeout after {timeout}s",
                "latency_s": time.time() - start}
    except Exception as e:
        return {"text": "", "error": f"{type(e).__name__}: {e}",
                "latency_s": time.time() - start}


def _parse_codex_output(stdout: str) -> str:
    """Extract the model response from `codex exec` output.

    codex exec wraps output as:
       OpenAI Codex v...
       ...
       user
       <prompt>
       hook: SessionStart
       ...
       codex
       <RESPONSE>
       2026-... ERROR codex_core::session: ...
       tokens used
       1234
    """
    text = stdout
    # Find the line that's exactly "codex" (the response marker)
    if "\ncodex\n" in text:
        text = text.split("\ncodex\n", 1)[1]
    elif text.startswith("codex\n"):
        text = text[len("codex\n"):]
    # Cut off trailing telemetry/tokens
    if "\ntokens used" in text:
        text = text.split("\ntokens used", 1)[0]
    # Strip lines starting with hook:, ERROR codex_core, or known telemetry
    keep = []
    for line in text.splitlines():
        if line.startswith(("hook:", "ERROR codex_core", "2026-", "2027-",
                            "thread ", "shutdown ")):
            continue
        keep.append(line)
    return "\n".join(keep).strip()


def _call_codex_cli(prompt: str, model: str, timeout: int = 600) -> Dict[str, Any]:
    """Invoke Meta `codex exec` CLI and return text/error/latency."""
    start = time.time()
    try:
        r = subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--model", model, prompt],
            capture_output=True, text=True, timeout=timeout, cwd=CWD_FOR_CLI,
        )
        if r.returncode != 0:
            return {"text": "", "error": f"codex exit {r.returncode}: {r.stderr[:300]}",
                    "latency_s": time.time() - start}
        return {"text": _parse_codex_output(r.stdout), "error": None,
                "latency_s": time.time() - start}
    except subprocess.TimeoutExpired:
        return {"text": "", "error": f"timeout after {timeout}s",
                "latency_s": time.time() - start}
    except Exception as e:
        return {"text": "", "error": f"{type(e).__name__}: {e}",
                "latency_s": time.time() - start}
