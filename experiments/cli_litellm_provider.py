"""Custom litellm provider that wraps Meta `claude` and `codex` CLIs.

Lets tau-bench (which uses litellm.completion) drive Anthropic+OpenAI models
via the Meta CLI subprocesses for $0 marginal cost.

Tool-calling adapter: tau-bench passes OpenAI-format `tools=[...]` and
expects `response.choices[0].message.tool_calls`. The CLIs return free text,
so we (a) inject tool-calling instructions into the prompt, (b) parse
`<tool_call>{"name": "X", "arguments": {...}}</tool_call>` blocks back from
the response, (c) construct a litellm ModelResponse mimicking OpenAI's
tool-calling response shape.

Registration:
    import litellm
    from cli_litellm_provider import register_cli_providers
    register_cli_providers()
    # then in tau-bench:
    completion(model="claude_cli/claude-opus-4-7", ...)
    completion(model="codex_cli/gpt-5.5", ...)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import litellm
from litellm import CustomLLM
from litellm.types.utils import (
    Choices, Message, ModelResponse, Usage, ChatCompletionMessageToolCall,
    Function as LLMFunction,
)

# ============================================================
# Subprocess wrappers
# ============================================================

CWD_FOR_CLI = "/tmp"  # bypass project-dir security gate


def _call_claude_cli(prompt: str, model: str, timeout: int = 600) -> Dict[str, Any]:
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
    """Extract the model response from codex exec output.

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


# ============================================================
# Tool-call protocol over text
# ============================================================

TOOL_INSTRUCTIONS_TEMPLATE = """

You have access to the following tools. To call a tool, emit a single
JSON object inside <tool_call>...</tool_call> tags, exactly:

<tool_call>{{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}</tool_call>

Available tools:
{tool_descriptions}

If you do NOT need to call a tool, just respond with plain text. Do not
emit <tool_call> tags around plain prose. Only call ONE tool per turn.
"""


def _format_tools_for_prompt(tools: List[Dict[str, Any]]) -> str:
    lines = []
    for t in tools:
        if t.get("type") != "function":
            continue
        f = t.get("function", {})
        name = f.get("name", "")
        desc = f.get("description", "")
        params = f.get("parameters", {})
        param_str = json.dumps(params.get("properties", {}), indent=2) if params else "{}"
        lines.append(f"- {name}: {desc}\n  parameters: {param_str}")
    return "\n".join(lines)


def _messages_to_text(messages: List[Dict[str, Any]],
                       tools: Optional[List[Dict[str, Any]]] = None) -> str:
    """Flatten OpenAI-style messages into a plain text prompt for CLI input."""
    parts = []
    if tools:
        parts.append(TOOL_INSTRUCTIONS_TEMPLATE.format(
            tool_descriptions=_format_tools_for_prompt(tools)
        ))
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "") or ""
        # Handle assistant messages with tool_calls
        if role == "assistant" and m.get("tool_calls"):
            tc_lines = []
            for tc in m["tool_calls"]:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", "{}")
                tc_lines.append(f'<tool_call>{{"name": "{name}", "arguments": {args}}}</tool_call>')
            content = (content or "") + "\n" + "\n".join(tc_lines)
        if role == "tool":
            tname = m.get("name", "")
            parts.append(f"<tool_response name=\"{tname}\">\n{content}\n</tool_response>")
        elif role == "system":
            parts.append(f"[SYSTEM]\n{content}")
        elif role == "user":
            parts.append(f"[USER]\n{content}")
        elif role == "assistant":
            parts.append(f"[ASSISTANT]\n{content}")
        else:
            parts.append(f"[{role.upper()}]\n{content}")
    return "\n\n".join(parts) + "\n\n[ASSISTANT]"


_TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)


def _parse_tool_calls(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract <tool_call>...</tool_call> JSON blocks from text.

    Returns (cleaned_content, list_of_tool_calls).
    """
    calls = []
    for m in _TOOL_CALL_RE.finditer(text):
        raw = m.group(1).strip()
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict) and "name" in obj:
                args = obj.get("arguments", {})
                if not isinstance(args, str):
                    args = json.dumps(args)
                calls.append({"name": obj["name"], "arguments": args})
        except json.JSONDecodeError:
            # Try to be lenient: fix common issues like single quotes
            try:
                fixed = raw.replace("'", '"')
                obj = json.loads(fixed)
                if isinstance(obj, dict) and "name" in obj:
                    args = obj.get("arguments", {})
                    if not isinstance(args, str):
                        args = json.dumps(args)
                    calls.append({"name": obj["name"], "arguments": args})
            except Exception:
                continue
    cleaned = _TOOL_CALL_RE.sub("", text).strip()
    return cleaned, calls


# ============================================================
# CustomLLM implementations
# ============================================================

def _build_response(model: str, content: str, tool_calls: List[Dict[str, Any]],
                    latency_ms: int) -> ModelResponse:
    """Build a litellm ModelResponse mimicking OpenAI's chat completion shape."""
    msg_kwargs: Dict[str, Any] = {
        "role": "assistant",
        "content": content if content else None,
    }
    if tool_calls:
        formatted_tcs = []
        for tc in tool_calls:
            formatted_tcs.append(ChatCompletionMessageToolCall(
                id=f"call_{uuid.uuid4().hex[:12]}",
                type="function",
                function=LLMFunction(name=tc["name"], arguments=tc["arguments"]),
            ))
        msg_kwargs["tool_calls"] = formatted_tcs
    message = Message(**msg_kwargs)

    # Approximate token count (we don't have exact)
    ptokens = max(1, len(str(content)) // 4)
    ctokens = max(1, len(str(content)) // 4)

    resp = ModelResponse(
        id=f"chatcmpl-cli-{uuid.uuid4().hex[:12]}",
        object="chat.completion",
        created=int(time.time()),
        model=model,
        choices=[Choices(index=0, message=message, finish_reason="stop" if not tool_calls else "tool_calls")],
        usage=Usage(prompt_tokens=ptokens, completion_tokens=ctokens,
                    total_tokens=ptokens + ctokens),
    )
    # Cost is unknown when going through CLI — set to 0 to keep tau-bench happy
    resp._hidden_params = {"response_cost": 0.0, "cli_latency_s": latency_ms / 1000.0}
    return resp


class ClaudeCLIProvider(CustomLLM):
    def completion(self, *args, **kwargs) -> ModelResponse:
        messages = kwargs.get("messages", [])
        tools = kwargs.get("tools") or kwargs.get("optional_params", {}).get("tools")
        model = kwargs.get("model", "claude-opus-4-7")
        # Strip "claude_cli/" prefix if present
        if "/" in model:
            model = model.split("/", 1)[1]

        prompt = _messages_to_text(messages, tools=tools)
        out = _call_claude_cli(prompt, model=model)
        if out["error"]:
            raise RuntimeError(f"claude CLI failed: {out['error']}")
        cleaned, tcs = _parse_tool_calls(out["text"])
        return _build_response(model, cleaned, tcs, int(out["latency_s"] * 1000))

    async def acompletion(self, *args, **kwargs) -> ModelResponse:
        # tau-bench uses sync; just delegate
        return self.completion(*args, **kwargs)


class CodexCLIProvider(CustomLLM):
    def completion(self, *args, **kwargs) -> ModelResponse:
        messages = kwargs.get("messages", [])
        tools = kwargs.get("tools") or kwargs.get("optional_params", {}).get("tools")
        model = kwargs.get("model", "gpt-5.5")
        if "/" in model:
            model = model.split("/", 1)[1]

        prompt = _messages_to_text(messages, tools=tools)
        out = _call_codex_cli(prompt, model=model)
        if out["error"]:
            raise RuntimeError(f"codex CLI failed: {out['error']}")
        cleaned, tcs = _parse_tool_calls(out["text"])
        return _build_response(model, cleaned, tcs, int(out["latency_s"] * 1000))

    async def acompletion(self, *args, **kwargs) -> ModelResponse:
        return self.completion(*args, **kwargs)


_REGISTERED = False


def register_cli_providers() -> None:
    """Idempotently register claude_cli and codex_cli with litellm."""
    global _REGISTERED
    if _REGISTERED:
        return
    claude = ClaudeCLIProvider()
    codex = CodexCLIProvider()
    existing = getattr(litellm, "custom_provider_map", None) or []
    # Filter out any prior entries for our providers
    existing = [e for e in existing if e.get("provider") not in ("claude_cli", "codex_cli")]
    existing.extend([
        {"provider": "claude_cli", "custom_handler": claude},
        {"provider": "codex_cli", "custom_handler": codex},
    ])
    litellm.custom_provider_map = existing
    _REGISTERED = True


# ============================================================
# Standalone test
# ============================================================

if __name__ == "__main__":
    import sys
    register_cli_providers()
    print("=== test 1: claude_cli no-tools ===")
    try:
        r = litellm.completion(
            model="claude_cli/claude-opus-4-7",
            messages=[{"role": "user", "content": "Reply with only the word: pong"}],
        )
        print(f"  content: {r.choices[0].message.content!r}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")

    print("\n=== test 2: codex_cli no-tools ===")
    try:
        r = litellm.completion(
            model="codex_cli/gpt-5.5",
            messages=[{"role": "user", "content": "Reply with only the word: pong"}],
        )
        print(f"  content: {r.choices[0].message.content!r}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")

    print("\n=== test 3: claude_cli WITH tools ===")
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }]
    try:
        r = litellm.completion(
            model="claude_cli/claude-opus-4-7",
            messages=[{"role": "user", "content": "What's the weather in Paris? Use the get_weather tool."}],
            tools=tools,
        )
        msg = r.choices[0].message
        print(f"  content: {msg.content!r}")
        print(f"  tool_calls: {msg.tool_calls}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")

    print("\n=== test 4: codex_cli WITH tools ===")
    try:
        r = litellm.completion(
            model="codex_cli/gpt-5.5",
            messages=[{"role": "user", "content": "What's the weather in Tokyo? Use the get_weather tool."}],
            tools=tools,
        )
        msg = r.choices[0].message
        print(f"  content: {msg.content!r}")
        print(f"  tool_calls: {msg.tool_calls}")
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
