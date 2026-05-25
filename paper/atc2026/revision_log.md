# Revision Log — ACM SIGOPS ATC 2026 Submission

> Tracks paper revisions across cold-review rounds. Working file
> `atc_paper.tex`; compiled `atc_paper.pdf`.

## Round 0 → Round 1
Initial draft. 7 text pages, sigplan acmart, double-blind. Verdict:
**WEAK_REJECT** (round 1).

## Round 1 → Round 2
Addressed M1–M10 from round 1: expanded to ~9 text pages with per-fault
matrix (Table 6), per-framework breakdown (Table 7), threats to
validity (§10), reproducibility (§13), span-correlation subsection
(§3.4), real circuit-breaker overhead measurement (Table 3), policy
DSL code listing (Figure 2), SDK version pinned (1.27.x), SWE-bench
prior-work citation marked [redacted for double-blind review], Wilson
95% CIs + two-proportion z-test on FDR. Verdict: **WEAK_ACCEPT**.

## Round 2 → Round 3
Addressed R1–R10. METADATA_ONLY = FULL inference explicit; baseline
GenAI catches infinite_loop/context_overflow because of usage tokens
+ wall clock; DELEGATION p99 outlier attributed to BatchSpanProcessor
flush (no longer GC speculation); Clopper-Pearson upper bound on
orphan rate added (0.52%); policy DSL listing uses real public API;
repro paths corrected to experiments/. Verdict: **ACCEPT**.

## Round 3 → Round 4 review

Round 4 reviewer (fresh context, STRONG_ACCEPT bar) returned **ACCEPT
but NOT STRONG_ACCEPT** with the following gap list:

- **Criterion 1**: systems contribution not identifiable in 1 sentence
- **Criterion 2**: every performance claim shows only single-run point
  estimates; need across-run CIs on Table 2 (microbench) and Table 3
  (circuit breaker)
- **Criterion 4**: Pivot Tracing contrast missing; MAST/AgentDebug
  runnable-detector statement missing
- **Criterion 5**: surprise findings buried, no callout
- **G1**: schema-diff table vs OpenInference/OpenLLMetry/etc missing
- **G2**: per-trace overhead calculation missing
- **G3**: span-kind × fault-class minimality table missing
- **G5**: RAISE action semantics under nested context/asyncio undefined
- **G6**: conformance gap should be reframed as "57% of orchestration
  faults catchable only with omitted kinds"
- **G7**: alternative-breaker design (wrapper) not dismissed
- **G9**: adapter fragility column lacks named release windows
- **G10**: BatchSpanProcessor flush attribution unvalidated

## Round 3 → Round 4 revision

### New measurements
1. **`experiments/overhead_multirun_and_isolation.py`** — runs the per-span
   microbenchmark 3 times (270,000 spans total) to bound across-run
   variance, and runs a DELEGATION-tail isolation experiment under
   three SpanProcessor configs (Simple, Batch-5s-default,
   Batch-600s-long-delay) to validate the flush-event attribution.
   Output: `results/overhead_percentiles/multirun_ci.json` and
   `results/overhead_percentiles/batch_isolation.json`.
   - Aggregate p50 across 3 runs: mean 9.99µs, range [9.96, 10.00]
     (CI ±0.02)
   - Aggregate p99 across 3 runs: mean 12.72µs, range [12.42, 12.88]
     (CI ±0.23)
   - DELEGATION std: 1.34µs (Simple) → 20.03µs (Batch 5s) → 64.42µs
     (Batch 600s). Walk-up with batch-induced contention confirms the
     flush-event attribution.
2. **`experiments/breaker_overhead_multirun.py`** — runs the circuit
   breaker overhead experiment 5 times (5 × 10,000 spans per config,
   100,000 total). Output:
   `results/overhead_percentiles/breaker_multirun.json`.
   - No-breaker p50: 11.41µs (95% CI [11.39, 11.42])
   - With-breaker p50: 13.57µs (95% CI [13.48, 13.65])
   - Overhead p50: +2.16µs (95% CI [+2.06, +2.25]; +18.9% relative)
   - Overhead p99: +3.31µs (95% CI [+2.81, +3.80])
   - Replaces the round 2/3 single-run +1.75µs figure with a multi-run
     CI estimate.

### Paper edits
- **Abstract**: opening "Key insight" italic sentence naming the
  SpanProcessor-as-control-loop as the load-bearing contribution
  (Criterion 1). Updated breaker overhead from +1.75µs to +2.16µs
  with CI.
- **§1 Contributions**: italicized one-sentence framing of the
  systems contribution before the enumerated list. Echoes abstract
  (Criterion 1).
- **§1 Counter-intuitive findings**: new paragraph branding (F1)
  METADATA_ONLY = FULL and (F2) AgentScope-faster-than-baselines as
  expected reviewer surprises (Criterion 5).
- **§3.1**: new Table 1a (`tab:kindfault`) — span kind × fault class
  coverage matrix defending the "minimal closed set" claim (G3).
- **§3.1**: new Table 1b (`tab:schemadiff`) — schema coverage diff
  vs GenAI semconv / OpenInference / OpenLLMetry / LangSmith /
  Langfuse (G1).
- **§4 Adapter table caption**: added release windows observed per
  adapter (LangChain 0.3.0–0.3.14, CrewAI 0.83–0.95, AutoGen
  0.4.0–0.4.10, LlamaIndex 0.12.0–0.12.30, Anthropic SDK 0.40–0.65,
  OpenAI SDK 1.40–1.62) (G9).
- **§5.2**: new "RAISE semantics under nested contexts" paragraph
  explaining cross-thread re-raise via `breaker.armed` flag and
  asyncio await-boundary check (G5). New "Why a SpanProcessor and
  not an outer-loop wrapper" paragraph dismissing the alternative
  design (G7).
- **§5.3 Activation overhead**: Table 3 replaced with 5-run multi-run
  results; mean ± 95% CI half-width per cell; new "Per-trace cost for
  a realistic agent" paragraph spelling out 216µs–2.16ms per
  invocation for 100–1,000-span agents (Criterion 2, G2).
- **§6 Method**: new "Run-to-run stability" paragraph noting the
  3-run replication and reporting across-run variance bounds
  (Criterion 2).
- **§6 Tail-latency caveat**: validated BatchSpanProcessor flush
  attribution with isolation experiment; std walks from 1.34µs to
  64.42µs with batch contention (G10).
- **§8 Per-framework breakdown**: added "Reframing the conformance
  gap" paragraph — "8 of 14 fault classes (57%) catchable only with
  orchestration kinds shipped adapters omit" (G6).
- **§12 Related work — Distributed tracing**: explicit Pivot Tracing
  contrast — "happens-before joins are post-hoc; AgentScope's
  breaker fires in-process during the same trace" (Criterion 4).
- **§12 Related work — Failure taxonomies**: explicit MAST /
  AgentDebug / Aegis runnable-detector statement — "none ship a
  runnable detector against a public schema we could benchmark
  head-to-head" (Criterion 4).
- **§13 Reproducibility**: added entries for
  `experiments/overhead_multirun_and_isolation.py` and
  `experiments/breaker_overhead_multirun.py`.
- **§14 Conclusion**: updated breaker number to +2.16µs with CI;
  dropped the marketing tail clause ("are reported in full rather
  than hidden"; Round 2 R7 / Round 4 tightness).
- **Extended abstract**: tracks the +2.16µs breaker number with CI in
  abstract and evaluation section. 2-page page count preserved.

### Page count
- 11 text pages + 1 references page = 12 total
- Limit: 12 text pages excluding references — compliant

### Round 4 → Round 5 review

Round 5 reviewer (fresh context, STRONG_ACCEPT bar) returned
**STRONG_ACCEPT**. All round-4 gaps addressed; no new issues; double-blind
clean; page count compliant; counter-intuitive findings called out;
related work slams every door; multi-run CIs defend every headline
performance claim.

### Round 5 → Round 6 verification fix

During final verification I spot-checked claims in the new RAISE-semantics
paragraph against the actual code at
`src/agenttelemetry/runtime/circuit_breaker.py`. The round-4 draft
described a `breaker.armed=True` flag and `CircuitBreakerTriggered`
exception type that do not exist; the code raises `RuntimeError`
directly from `on_end` (line 290), and because `AgentCircuitBreaker`
is registered as a `SpanProcessor` on the `TracerProvider`, OTel
invokes `on_end` synchronously on the closing thread. A standalone
Python test confirmed: the `RuntimeError` propagates cleanly out of
the user's `with start_agent_span():` block.

The RAISE-semantics paragraph in §5.2 was rewritten to describe this
actual behavior (with line number) instead of the fabricated
flag-and-asyncio-await mechanism.

Also fixed during the verification sweep:
- `tab:kindfault` caption count corrected (5+9 → 6+8) for consistency
  with `tab:fdrmatrix`'s 6-bottom-up + 8-orchestration split.
- Body text count of "five fault classes covered by GenAI-semconv" →
  "six" for the same reason.

### Round 5 → Round 6 review

Round 6 reviewer (fresh context, STRONG_ACCEPT bar, post-verification)
returned **STRONG_ACCEPT**. All quantitative claims spot-checked against
the underlying JSON. RAISE semantics now matches actual code. No
fabricated implementation details. No further iteration needed.
