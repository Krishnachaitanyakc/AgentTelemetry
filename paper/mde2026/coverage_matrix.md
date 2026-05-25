# DSM Span-Kind Coverage Matrix per Benchmark App

Source: `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/benchmarks/apps/<app>/app.py`
Generated: 2026-05-05

Each cell indicates whether the benchmark app for the named framework emits a
typed DSM `SpanKind` for the workload. ✓ = emitted; ✗ = not emitted. Coverage
combines what the framework adapter produces and what the benchmark app
explicitly emits on top of it (some apps emit `DELEGATION`, `GUARD_RAIL`, or
`MEMORY` directly when the underlying framework lacks first-class events).

| Framework app   | AGENT | LLM_CALL | TOOL_CALL | PLANNING | REASONING | DELEGATION | GUARD_RAIL | RETRIEVAL | MEMORY | Cov. |
|-----------------|:-----:|:--------:|:---------:|:--------:|:---------:|:----------:|:----------:|:---------:|:------:|:----:|
| custom_agent    |  ✓    |    ✓     |    ✓      |    ✓     |    ✓      |     ✓      |     ✓      |    ✓      |   ✓    | 9/9  |
| langchain_rag   |  ✓    |    ✓     |    ✓      |    ✓     |    ✗      |     ✓      |     ✗      |    ✓      |   ✗    | 6/9  |
| llamaindex_agent|  ✓    |    ✓     |    ✓      |    ✓     |    ✓      |     ✓      |     ✗      |    ✓      |   ✗    | 7/9  |
| autogen_group   |  ✓    |    ✓     |    ✓      |    ✗     |    ✓      |     ✓      |     ✗      |    ✗      |   ✗    | 5/9  |
| crewai_team     |  ✓    |    ✓     |    ✓      |    ✗     |    ✗      |     ✓      |     ✗      |    ✗      |   ✗    | 4/9  |
| anthropic_sdk   |  ✗    |    ✓     |    ✓      |    ✗     |    ✗      |     ✓      |     ✗      |    ✗      |   ✗    | 3/9  |
| openai_sdk      |  ✗    |    ✓     |    ✓      |    ✗     |    ✗      |     ✓      |     ✗      |    ✗      |   ✗    | 3/9  |

## Conformance gap

Only the `custom_agent` reference app emits all 9 kinds. The third-party
adapter+app pairs span 3/9 (anthropic_sdk, openai_sdk) to 7/9
(llamaindex_agent). Notably, `GUARD_RAIL` and `MEMORY` are emitted by no
third-party app; `STALE_RETRIEVAL` (a `RETRIEVAL` attribute) is emitted only by
the four apps that emit `RETRIEVAL`. This explains the per-fault FDR pattern in
the paper: `circular_delegation` reaches FDR = 1.000 across all 7 apps because
all 7 emit typed `DELEGATION` spans, while `guardrail_bypass`,
`memory_corruption`, `planning_failure`, `reasoning_loop`, `agent_misroute`,
and `stale_retrieval` collapse to 0.143 (1/7) because only the conformant
`custom_agent` app emits the required typed kinds with the required
attributes.

## Derivation rule for the nine kinds

A DSM span kind is included if it is emitted by the conforming reference app
(`custom_agent`) AND named (under any synonym: e.g., `RetrievalQAChain` →
`RETRIEVAL`, `chain-of-thought` → `REASONING`) by at least two third-party
agent frameworks. All nine kinds satisfy this.
