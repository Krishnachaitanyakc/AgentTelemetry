# REQUEST_FOR_SCREENCAST.md

ICSE 2027 Tool Demonstrations **require** a 3–5 minute YouTube video at submission time. The video does not yet exist and **must be recorded before 2026-10-23 AoE**.

## Logistics

- **Length**: 3:00–5:00 (hard cap 5:00).
- **Resolution**: 1080p, screen recording (OBS, ScreenFlow, QuickTime).
- **Audio**: clear voiceover, no background music required (PC has noted that background music distracts).
- **Captions**: auto-generated YouTube captions are sufficient.
- **Upload**: YouTube, set to "Unlisted" (not Private). Title: "AgentTelemetry: OpenTelemetry-Native Observability for AI Agent Systems (ICSE 2027 Demo)."
- **URL to paste back**: replace the placeholder `https://youtu.be/AGENTTELEMETRY-ICSE27-DEMO` in `icse_tool_demo_paper.tex` (search for `AGENTTELEMETRY-ICSE27-DEMO`).

## Shot-by-shot script

**[0:00 – 0:20] Visual failure hook (no voiceover for the first 3 seconds)**
Open with a 3-second silent shot of a real Jaeger trace from a broken multi-agent run: dozens of identical-looking `gen_ai.completion` spans nested deep, no structural signal. Then cut to a slide overlay: "AI agents fail in ways your traces don't show." Voiceover starts:
> "This is what a circular delegation looks like in vanilla OpenTelemetry — twenty-eight indistinguishable LLM spans, no signal that two agents are stuck routing to each other. AgentTelemetry is a pip-installable Python SDK that adds nine agent-specific span kinds to OpenTelemetry so failures like this finally show up in your traces."

**[0:20 – 0:50] Installation in one command (pinned)**
Terminal recording:
```
$ time pip install agenttelemetry==0.1.0
... installed agenttelemetry-0.1.0 in 18.4s
$ python -c "from agenttelemetry import configure, AgentSpanKind; print(len(AgentSpanKind))"
9
```
Voiceover: "One pip install — pinned to version 0.1.0 so this video reproduces forever. Eighteen seconds, no backend setup. AgentTelemetry uses OpenTelemetry's standard SDK, so it exports to any OTLP backend — Jaeger, Tempo, Datadog, you pick."

**[0:50 – 1:40] Manual instrumentation in <10 lines**
Open the file `examples/basic_usage.py` in an editor, highlight lines. Show this minimal code on screen:
```python
from agenttelemetry import configure, start_agent_span, AgentSpanKind

provider = configure(service_name="my-agent", console=True)
tracer = provider.get_tracer()

with start_agent_span("research-task", AgentSpanKind.AGENT, tracer=tracer):
    with start_agent_span("call-gpt4", AgentSpanKind.LLM_CALL, tracer=tracer) as llm:
        llm.set_attribute("llm.model", "gpt-4o")
        llm.set_attribute("llm.input_tokens", 500)
    with start_agent_span("web-search", AgentSpanKind.TOOL_CALL, tracer=tracer) as tool:
        tool.set_attribute("tool.name", "search")
```
Run it, show console output: nested spans labelled `AGENT`, `LLM_CALL`, `TOOL_CALL`. Voiceover walks through.

**[1:40 – 2:30] Auto-instrumentation with LangChain**
Show `examples/langchain_example.py`. Highlight that the only AgentTelemetry-specific code is:
```python
from agenttelemetry.adapters import LangChainInstrumentor
LangChainInstrumentor().instrument(tracer_provider=provider.tracer_provider)
```
Run a small LangChain ReAct agent answering a question that needs a tool call. Switch to Jaeger UI showing the trace: AGENT → PLANNING → LLM_CALL → TOOL_CALL → REASONING → LLM_CALL. Voiceover: "Two lines turn on auto-instrumentation. The trace shows the actual agent cognition phases, not just `chat.completions.create`."

**[2:30 – 3:30] Analysis module: anomaly detection catches a circular delegation**
Run `examples/multi_agent.py` configured to circularly delegate. In a notebook/REPL, run:
```python
from agenttelemetry.analysis import AnomalyDetector
anomalies = AnomalyDetector().detect(trace)
for a in anomalies:
    print(a.type, a.evidence_span_ids)
```
Output shows `CIRCULAR_DELEGATION`. Voiceover: "AgentTelemetry ships four analysis modules. Anomaly detection looks at the structural span graph, not the LLM output, and catches coordination failures before they cost you money."

**[3:30 – 4:20] Comparison + benchmark**
Slide: "Why not LangSmith / Langfuse / AgentOps / Phoenix / OpenLIT?" Show the comparison table from the paper. Voiceover: "AgentTelemetry is the only Apache-licensed, OpenTelemetry-native SDK with first-class span kinds for the agent orchestration phases — planning, reasoning, delegation, memory, guardrails — that other tools either don't model or fold into generic LLM spans."
Then: "We ship a 3,780-row fault detection benchmark on Zenodo. Vanilla OpenTelemetry detects 6 of 14 fault classes; AgentTelemetry's full span vocabulary detects all 14."

**[4:20 – 4:45] Where to get it**
Slide: links + DOIs.
- `pip install agenttelemetry`
- github.com/Krishnachaitanyakc/AgentTelemetry
- doi.org/10.5281/zenodo.20129005
- ICSE 2027 paper (this submission)

**[4:45 – 5:00] Concrete next-60-seconds call to action**
Slide: "Next 60 seconds:" with three lines:
```
pip install agenttelemetry==0.1.0
python -m agenttelemetry.examples.basic_usage
# typed agent spans in your terminal in 30 seconds
```
Voiceover: "Run these three lines and you have typed agent spans in your terminal in thirty seconds. Then swap one import for `LangChainInstrumentor` and you have them for your real agent. Source, benchmark, and OTEP draft are all linked below." Fade.

## Required environment for filming

- Python 3.11, `pip install agenttelemetry[all] langchain-openai`.
- `OPENAI_API_KEY` set (or a mock — see `examples/debugging_case_study.py` for an offline-friendly variant).
- Local Jaeger instance: `docker run -d --name jaeger -p 16686:16686 -p 4317:4317 jaegertracing/all-in-one:latest`.
- Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317` before running the LangChain demo.

## Rehearsal checklist

- [ ] All terminal commands work cleanly (no pip warnings on screen).
- [ ] Jaeger trace shows all nine span kinds correctly labelled.
- [ ] Anomaly detector example produces `CIRCULAR_DELEGATION` deterministically (use seeded mock LLM if needed).
- [ ] Comparison slide matches the paper's Table 1 exactly.
- [ ] Total runtime under 5:00.
- [ ] Voiceover has no AI / Claude / assistant references.
