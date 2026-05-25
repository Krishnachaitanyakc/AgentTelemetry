# DSM Diagnostic Coverage Matrix

This file reports which DSM diagnostic kinds each adapter profile contributes
to the anonymized benchmark. The unit is not "every optional event a framework
can emit"; it is "source-grounded evidence that the exercised benchmark profile
exposes the detector-specific fields needed by the DSM predicates." Optional
events found in source but not credited are documented explicitly in
`source_survey_evidence.tsv`.

The survey was performed against public framework repositories at the pinned
HEAD revisions below (queried 2026-05-06). Public framework names and commits
are study-subject identifiers, not author identifiers.

| adapter | repository | pinned revision | source-query evidence |
|---|---|---:|---|
| langchain | `github.com/langchain-ai/langchain` | `1519ed5afbc3bfcc7170b12baa07f1ae7e98edd0` | file/line evidence for `on_llm_*`, `on_tool_*`, `on_retriever_*`, and `run_type` in `source_survey_evidence.tsv` |
| llamaindex | `github.com/run-llama/llama_index` | `d601b0f36af4f6362375eefeda509d1070340652` | file/line evidence for `CBEventType.AGENT_STEP`, `LLM`, `FUNCTION_CALL`, `TOOL`, and `RETRIEVE` in `source_survey_evidence.tsv` |
| autogen | `github.com/microsoft/autogen` | `027ecf0a379bcc1d09956d46d12d44a3ad9cee14` | file/line evidence for GenAI agent/tool spans, model-client calls, and handoff messages in `source_survey_evidence.tsv` |
| crewai | `github.com/crewAIInc/crewAI` | `d165bcb65f400d63c9ab431280f7633414e6f82c` | file/line evidence for credited LLM/tool events and excluded optional agent, guardrail, memory, reasoning, and A2A events in `source_survey_evidence.tsv` |
| anthropic_sdk | `github.com/anthropics/anthropic-sdk-python` | `04b468daf76e4b95a949cecb03e29f4a1374d3b5` | file/line evidence for beta managed-agent model-request span events plus negative OpenTelemetry grep in `source_survey_evidence.tsv` |
| openai_sdk | `github.com/openai/openai-agents-python` | `eed9100777d16b36e4a1ce764566bb652e43b26d` | file/line evidence for `AgentSpanData`, `GenerationSpanData`/`ResponseSpanData`, `FunctionSpanData`, `HandoffSpanData`, and `GuardrailSpanData` in `source_survey_evidence.tsv` |

Audit commands used for the source survey:

```sh
git clone <repository> repo && cd repo && git checkout <pinned revision>
git grep -n -E 'BaseTracer|run_type|on_tool|retriev' .
git grep -n -E 'CBEventType|AGENT_STEP|LLM|RETRIEVE|TOOL' .
git grep -n -E 'trace|span|handoff|message|tool' .
git grep -n -E 'Tool Usage|Task Execution|LLM|tracing|telemetry' .
git grep -n -E 'opentelemetry|tracer|telemetry|span' src/anthropic || true
git grep -n -E 'generation|response|function|handoff|guardrail|Span' src/agents
```

The positive rows below are included only when the file/line evidence exposed
a typed event/span or a stable callback field that the benchmark profile can
map to a DSM diagnostic predicate. Generic events are not credited when the
detector requires a more specific field such as `guardrail.result`,
`memory.owner_agent`, `reasoning.step_hash`, or
`retrieval.staleness_seconds`. The Anthropic row is intentionally sparse: the
negative OpenTelemetry grep is the basis for treating it as LLM-call-only
under external instrumentation.

| adapter | AGENT | LLM_CALL | TOOL_CALL | PLANNING | REASONING | DELEGATION | GUARD_RAIL | RETRIEVAL | MEMORY | total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| langchain | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 3/9 |
| llamaindex | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 | 4/9 |
| anthropic_sdk | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1/9 |
| autogen | 1 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 4/9 |
| crewai | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2/9 |
| openai_sdk | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 5/9 |
| custom_agent | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 9/9 |

Interpretation: the six third-party adapters differ sharply in source-grounded
diagnostic evidence under the exercised benchmark profile. Anthropic SDK
exposes only LLM-call evidence through external instrumentation in this
benchmark; LangChain, LlamaIndex, and CrewAI expose the easy LLM/tool evidence
but no credited typed delegation, guardrail, planning, reasoning, memory, or
staleness fields used by the DSM detectors; AutoGen adds delegation; OpenAI
Agents adds delegation, guardrail, and role-attributed verifier evidence. The
CrewAI source contains optional guardrail, memory, reasoning, and A2A events,
but these are documented as excluded optional events because the default
benchmark profile does not emit the required detector fields. Only the
reference adapter emits all nine DSM diagnostic kinds.
