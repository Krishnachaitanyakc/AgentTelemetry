# Revision Log — Middleware 2026 Submission
> Tracks per-round changes to the paper across the cold-review iteration cycle.

## Round 1 → Round 2
Round-1 reviewer (WEAK_REJECT) demanded: expansion from 8 → 11-12 pages, explicit middleware-research kernel, comparative-overhead baseline, scalability scoping, adversarial multi-agent test, lazy-import measurement, deeper related work. Round-2 revision added the three explicit middleware contracts, the W3C-baggage carrier format, comparative-overhead row vs. vanilla OTel / OTel GenAI / OpenInference in Table 4, mock-LLM defence, scalability scoping paragraph, and explicit limitations on adversarial multi-agent coverage. Result: WEAK_ACCEPT.

## Round 2 → Round 3
Round-2 reviewer (WEAK_ACCEPT) listed 11 minor items. Addressed:

- **MN1 (placeholder package name)**: confirmed Listing 1 already uses neutral `<SDK>` placeholder; preserved through revision.
- **MN2 (Table 4 mean-row arithmetic)**: added explicit footnote distinguishing the `Mean` row (all 6 adapters, $+$1.07~ms) from the $\Delta$ row (5 non-CrewAI adapters, $+$0.92~ms).
- **MN3 (Conclusion repeats abstract)**: rewrote Conclusion as a forward-looking synthesis with two implications for middleware research, removing the per-RQ recap.
- **MN4 (Middleware 2025 venue awareness)**: added `unifyfl` and `argus` citations in a new related-work subsection on AI/ML middleware in the Middleware venue.
- **MN5 (variance reporting on $+$0.92~ms vs $+$1.95~ms headline)**: added Table 5 (paired per-adapter overhead with 95\% CIs, $n=90$ paired runs per cell). Added sample-standard-deviation discussion across non-CrewAI adapters.
- **MN6 (throughput repetition)**: kept the three appearances (abstract, contributions, summary) but tightened the summary phrasing.
- **MN7 (`agentrx` arXiv ID)**: verified 2602.02475 exists, exists as cited; corrected the author names (Arnav not Anirudh; Alind not Aniket; Avaljot not Aman) in `refs.bib`.
- **MN8 (API surface consistency)**: confirmed `configure(...)` + `<Adapter>Instrumentor().instrument(tracer_provider=...)` is consistent between body text and Listing 1.
- **MN9 (CCS concepts)**: noted Middleware does not require CCS; kept `printccs=false`.
- **MN10 (`JSONFileSpanExporter` naming)**: confirmed naming is consistent.
- **MN11 (overhead-figure framing)**: standardised on three numbers ($+$0.41~ms low, $+$1.07~ms aggregate mean, $+$0.92~ms 5-adapter $\Delta$ vs. baselines) and footnoted the distinction.

Major new piece of evidence introduced: **paired per-adapter delta CIs** (Table 5) showing the half-overhead claim holds with non-overlapping 95\% CIs on 4 of 5 non-CrewAI adapters.

Also added: "What is new in two sentences" intro paragraph for novelty-crisp framing; abstract update mentioning paired CIs explicitly; intro contributions bullet 3 mentioning paired CIs.

Result: ACCEPT (round-3 reviewer wanted championing-bar items before STRONG_ACCEPT).

## Round 3 → Round 4
Round-3 reviewer (ACCEPT) named 10 specific gaps preventing STRONG_ACCEPT. Addressed:

- **G1 (paired-cell matching methodological callout)**: added explicit text in the per-adapter paired-delta paragraph: "the unpaired per-cell sample standard deviation is $\sim$26~ms but the paired-delta sample standard deviation is $\sim$0.8--2.2~ms across adapters — two orders of magnitude smaller". Removed the now-redundant separate sample-sd sentence.
- **G2 (DELEGATION p99 explanation)**: strengthened from "we attribute" to an arithmetic-and-reference-backed argument citing OpenTelemetry's documented baggage-write cost $O(|\text{baggage entries}|)$ and 36-byte UUID entries; the observed 15~\textmu s gap is within OTel's own benchmarked range.
- **G3 (adversarial multi-agent case)**: acknowledged as a known gap, deferred to camera-ready (no data available; the existing 45/45 result is the best the current harness provides).
- **G4 ("what is hard")**: added "Why this is harder than it looks" paragraph in the intro, naming the three strategy-specific failure modes (handler ordering, hook demux, idempotent patching) and the four iterations the architecture went through.
- **G5 (OpenTelemetry Python Contrib citation)**: added `otel_contrib_python` bib entry; cited in the cross-framework-instrumentation related-work subsection with a one-sentence delta (hook-only, standard OTel vocabulary, does not address strategy heterogeneity or agent-semantic vocabulary).
- **G6 (figure dense and small)**: switched architecture figure from `figure` to `figure*` (2-column-wide); enlarged TikZ font from `\scriptsize` to `\small`; resized to 92\% of `\textwidth`.
- **G7 ("Why three strategies, not one?")**: re-cast from rhetorical question to declarative paragraph "Strategy heterogeneity is structural."
- **G8 (privacy filter property)**: replaced informal description with explicit safety-invariant statement (for all (level, key) pairs, if level $<$ FULL and key is content, then key is not emitted).
- **G9 (OTLP collector scope)**: strengthened from "existing literature documents OTLP collector throughput separately" to a citation-backed argument referencing the OpenTelemetry Collector's own published benchmark page; added `otel_collector_perf` bib entry; framed the scope as "within the published collector-throughput envelope (hundreds of thousands of spans/s per instance), the SDK at 78k spans/s in-memory is not the bottleneck."
- **G10 (Tier-3 analysis-tap cost)**: added "Analysis-tap cost" paragraph quantifying the in-process tap ceiling at 1.4--1.8~\textmu s p99 across the nine span kinds.

Line-by-line nits also addressed: defined `full` column in Table 5; split the §2.2 long sentence about Java APM into two; removed the conflicting `aegis` cite from §5.1 (the methodological defence) and replaced with `aegis,mast` as behavioural-axis pointers; consolidated the DELEGATION p99 acknowledgement into Limitations.

Result: **STRONG_ACCEPT** (championing-bar review; would defend in PC discussion).

## Cumulative state at submission
- 11 pages of body content (limit: 12).
- 36 references; all verified against ground truth.
- Anonymization clean: no author names, no GitHub URL, no PyPI link, no `AgentTelemetry` mention, no `OTEP` de-anonymizing phrasing. Listing 1 uses `<SDK>` placeholder.
- Reproduction commands and wall-time documented.
- 3,780-cell controlled benchmark matrix referenced by exact file path.
- Two cited Middleware-2025 papers for venue awareness.
- Per-adapter paired 95\% CIs as headline statistical evidence.
- Three named middleware contracts (attribute-overlay encoding, lazy-import discipline, analysis-downstream-of-exporter decoupling) tested against empirical evidence.
