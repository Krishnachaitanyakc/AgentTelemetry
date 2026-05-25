# CLAUDE.md — AgentTelemetry Project

## Project Overview

AgentTelemetry is an OpenTelemetry-based observability SDK for AI agent systems. 9 agent-specific span kinds, 7 framework adapters, privacy controls, and analysis tools.

## GitHub Engagement Tone (comments, PRs, issues)

### Voice
- First person singular ("I"). Direct, declarative. No hedging.
- Evidence-first: concrete failure case or data point, then the claim, then a suggestion.
- Own the research openly — "in a study we conducted" not "I noticed."
- One unique contribution per comment. No mini-proposals or full spec dumps.

### What to avoid
- Never list all 6 framework adapters in a single sentence — reads as product pitch
- Never link AgentTelemetry more than once across a set of related comments
- Never cite the same study (e.g., SWE-bench) in multiple threads
- Never use the same closing pattern in consecutive comments
- Never open with "Interesting proposal" or "Nice proposal" — reference something specific from the thread
- Never use H3 headers (###) in GitHub comments — keep them conversational
- Never present research findings as casual implementation observations
- Never use "ablation" in GitHub comments — say "in testing"
- Never post two markdown tables in one comment
- Never end with "does this align with..." — ask a direct question about a specific aspect

### Structure
- Vary comment structure. Some should be 2-3 sentences. Others longer.
- Break perfect symmetry — real comments are uneven, not perfectly parallel bullet lists.
- Reference specific existing comments in the thread to show you read them.
- End with direct questions about specific aspects, not generic alignment checks.

### PR descriptions
- Lead with the problem, not the solution
- Include cross-provider evidence table (with honest gaps — use dashes where coverage is weak)
- Proactively address competing proposals (#3575 grouping primitives)
- Reference implementation link once, at the end
- Create follow-up issues for deferred scope to signal roadmap thinking

### Research citations
- When citing empirical findings, be transparent about the source: "Our study of 112 SWE-bench instances found..." not "I've seen in practice that..."
- Provide specific numbers with context: "75% of failures (95% CI [66%, 82%])" not "the majority"
- Performance data should include methodology context, not appear as casual observation

## Build & Test

```bash
pip install -e .
pytest tests/
python examples/basic_usage.py
```

## Key directories
- `agenttelemetry/` — core SDK
- `agenttelemetry/adapters/` — framework instrumentors (LangChain, CrewAI, AutoGen, etc.)
- `agenttelemetry/analysis/` — anomaly detection, cost aggregation, decision attribution
- `paper/` — research papers (position paper, AIware, ASE, NeurIPS)
- `otep/` — OTel semantic conventions proposal materials
- `blog/` — blog posts
