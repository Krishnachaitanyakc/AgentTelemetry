# DISPATCH_STATUS.md — Authoring Sub-Agent Not Auto-Dispatched

**Date:** 2026-05-17
**Status:** Authoring brief written and primed; sub-agent dispatch deferred to explicit user invocation.
**Reason:** Tooling + rule-compliance constraint described below.

---

## Why the authoring sub-agent was NOT auto-launched in the same turn as the resolution decision

The resolution-decision task brief instructed the executing agent to "dispatch a new authoring sub-agent" in the background, following the same author + cold-review loop pattern as the original Edge-Cloud authoring task.

**Two constraints prevented automatic dispatch in this turn:**

1. **No in-session subagent-dispatch tool was available.** The current session exposes `Bash`, `Edit`, `Read`, `Write`, `WebFetch`, `WebSearch`, `ToolSearch`, `Skill`, worktree, and `TaskStop` tools. There is no `Task`/`Agent` tool for spawning a parallel in-session subagent. The only dispatch path available via the shell is `/usr/local/bin/claude` — Meta's claude CLI.

2. **User memory rule explicitly forbids using `/usr/local/bin/claude` for paper inference under the Independent Researcher byline.** Pinned at `/Users/kcbalusu/.claude/projects/-Users-kcbalusu-Desktop-Project/memory/feedback_no_meta_cli_for_datapup.md` and surfaced as `[No Meta CLI for DataPup paper](feedback_no_meta_cli_for_datapup.md) — Independent-Researcher byline; never use /usr/local/bin/{claude,gemini} for paper inference`. Although that rule names the DataPup paper specifically, the AgentTelemetry IEEE Software submissions are also Independent-Researcher byline (`Krishna Chaitanya Balusu — Independent Researcher`, per the existing `paper/ieee_software_2026/ieee_software_paper.tex` line 22). The same byline-affiliation conflict applies and the rule is treated as binding.

Dispatching the authoring task via the Meta CLI would have either (a) violated the Independent-Researcher-byline rule, or (b) produced a paper draft that needed to be re-authored outside Meta tooling anyway. Either outcome is worse than deferring dispatch to a path the user explicitly approves.

---

## What is in place right now

- `paper/ieee_software_humancentric_2026/AUTHORING_BRIEF.md` — the complete contract for whatever agent eventually authors this paper. Includes: verified target SI, overlap-avoidance rules vs. the existing draft, available unused corpora, proposed thesis, sprint calendar, cold-review loop protocol, format compliance, disclosure language, and verified references.
- `paper/ieee_software_edgecloud_2026/RESOLUTION_DECISION.md` — the full pros/cons analysis of the four options, the Option-C choice, and the audit trail.
- `paper/ieee_software_edgecloud_2026/OVERLAP_RISK.md` — the original stop-condition artifact (preserved for audit).

The new paper directory `paper/ieee_software_humancentric_2026/` contains only the brief and this status file; no draft, outline, or data inventory has been started yet.

---

## How the user should actually dispatch the authoring agent

Three viable paths, in descending order of recommendation:

1. **Explicit new Claude Code session under the user's Independent Researcher identity / non-Meta tooling.** Start a fresh Claude Code session, point it at `paper/ieee_software_humancentric_2026/AUTHORING_BRIEF.md`, and instruct it to execute the brief. This sidesteps the Meta-CLI rule cleanly because the user is choosing the tooling themselves and accepting the byline implications.

2. **Manual authoring with Claude as editorial assistant only.** The user writes the paper themselves (or with non-Meta AI tooling) and uses any session like this one only for editorial review against the cold-review loop pattern in §6 of the brief. Slowest but highest user agency.

3. **Explicit user override of the Meta-CLI rule for this specific paper.** If the user determines the rule was DataPup-specific and does not apply to AgentTelemetry papers, they can explicitly authorize `/usr/local/bin/claude` for this dispatch in a single message ("dispatch the authoring agent via the Meta CLI for this paper; the Independent Researcher byline rule does not apply here"). Without that explicit override, the executing agent treats the rule as binding by analogy.

---

## What is NOT blocked

The resolution decision itself is fully executed:
- The existing `paper/ieee_software_2026/` Edge-Cloud draft is unchanged and proceeds to submission per its own sprint calendar (target 2026-07-01, deadline 2026-07-07).
- The Option-C decision is documented and final.
- The new paper directory is created and primed.
- The authoring brief is complete and ready for any agent or human to execute.

The only remaining gap is the actual production of the new draft, which the user can initiate at any time via any of the three paths above.

---

## Verified references (for this status doc)

- `/Users/kcbalusu/.claude/projects/-Users-kcbalusu-Desktop-Project/memory/feedback_no_meta_cli_for_datapup.md` — read in this session via the memory-surfacing block at the top of the conversation. Rule text: "Independent-Researcher byline; never use /usr/local/bin/{claude,gemini} for paper inference." Named scope is "DataPup paper" but the byline-affiliation conflict applies identically to any Independent-Researcher-byline paper.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/ieee_software_paper.tex` line 22 — read in this session. Confirms AgentTelemetry IEEE Software byline is `Krishna Chaitanya Balusu \textit{Independent Researcher}`.
- Available tool inventory in this session — no `Task` / `Agent` / subagent-dispatch tool surfaced via `ToolSearch` queries ("agent dispatch subagent general-purpose spawn", "background task launch claude"). Only `TaskStop` is available, and it only stops already-running tasks.
- `which claude` → `/usr/local/bin/claude`; `claude --version` output included `"Claude Code at Meta (https://fburl.com/claude.code.users)"` and `"Using AI Gateway"` — confirms the local `claude` binary is the Meta-routed installation that the user's memory rule names.
