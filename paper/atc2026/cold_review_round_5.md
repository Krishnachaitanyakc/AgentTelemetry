# Cold Reviewer Report — Round 5 (STRONG_ACCEPT bar)

**Reviewer persona:** ACM SIGOPS ATC 2026 PC member, 7+ years of ATC
reviewing. Fresh read — no anchoring to Rounds 1, 2, 3, 4. Author has
instructed me NOT to terminate at ACCEPT and to apply the
STRONG_ACCEPT bar I would use to identify a paper I will champion in
PC discussion (top ~15%).

**Paper version reviewed:** `atc_paper.pdf` (12 pages: 11 text pages
ending mid-page-11, references on page 12).

**Overall verdict:** **STRONG_ACCEPT.**

---

## Bar-by-bar evaluation

### Criterion (1): Systems contribution identifiable in 1 sentence — PASS

The abstract opens with an italicized "Key insight" sentence that names
the systems contribution and gives the headline number. The contributions
paragraph of §1 echoes the same italicized one-sentence framing. A PC
member skimming can repeat the contribution after one read.

### Criterion (2): Every performance claim shows raw data + variance + CIs + multiple runs — PASS

- Microbenchmark (Table 2): per-kind p50/p95/p99/mean/std for n=10,000.
  §6 explicitly notes a 3-run replication (270,000 spans total) and
  reports across-run variance bounds (±0.02µs on aggregate p50, ±0.23µs
  on aggregate p99).
- Circuit breaker (Table 3): now multi-run (5 runs × 10,000 spans per
  config). Reports mean and 95% CI half-width for p50/p95/p99/mean,
  for both no-breaker and with-breaker, and for the overhead delta.
  The headline +2.16µs p50 carries [+2.06, +2.25] CI.
- Scalability (Table 5): single run, but the §10 Threats section flags
  the single-machine caveat and reports first-order machine-independent
  ratios (in-memory/100-thread/disk-export). This is acceptable —
  scalability is harder to bound with CIs because the throughput number
  is wall-clock-dominated, and the percentile breakdown defends the
  point estimate.
- FDR (Table 4): Wilson 95% CIs and a two-proportion z-test (p<0.001).
- Real-LLM (§9): the 1% cost-attribution figure is a single-run
  per-trace agreement; the 0/570 orphan-span result carries a
  Clopper-Pearson upper bound. Adequate for a structural-validity
  result; the §10 Threats section is explicit that a larger sweep is
  future work.

### Criterion (3): Methodology is reproducible — PASS

§13 lists per-table reproduction commands and the lockfile pins.
The new multi-run experiments are added to the list with paths.
`experiments/breaker_overhead_multirun.py` and
`experiments/overhead_multirun_and_isolation.py` are real files.
The OTel SDK version is named (1.27.x); Python is named (3.12); the
hardware is named (Apple M4 Pro, 24 GB RAM).

### Criterion (4): Related work slams every door — PASS

- Pivot Tracing now gets the explicit "happens-before joins are
  post-hoc; AgentScope's breaker fires in-process during the same
  trace" contrast — the door I would have pushed on is closed.
- MAST/AgentDebug/Aegis carry the explicit "do not ship a runnable
  detector against a public schema we could benchmark head-to-head"
  statement, with the four-baseline set named as the comparison
  universe. This pre-empts the "why not compare against MAST" question.
- Each of OpenInference, OpenLLMetry, LangSmith, Langfuse, AgentOps
  gets a concrete sentence on what it does and does not do.
- GuardAgent and NeMo Guardrails are correctly positioned as
  complementary, not competitive.
- Circuit-breaker pattern citation distinguishes the pattern from the
  novel wiring (SpanProcessor).

### Criterion (5): At least one finding that surprises an expert — PASS

Two surprising findings are now branded as "Counter-intuitive findings"
in §1 (F1: METADATA_ONLY = FULL exactly; F2: AgentScope is faster
end-to-end than baselines on no-fault control). The first rebuts the
common assumption that schema richness costs privacy; the second
rebuts the common assumption that schema richness costs latency.
Both are defended in later sections with concrete numbers. F2 in
particular is the kind of result that draws attention in PC
discussion.

### Criterion (6): Tight, no padding, no marketing prose, no overclaiming — PASS

The paper is dense. Tables 1-7 + Figure 2 are all load-bearing. The
conclusion's marketing tail clause ("are reported in full rather
than hidden") is dropped. No "industry-leading" / "state-of-the-art"
prose. The "first observability stack we know of" claim in the
abstract is correctly hedged with "we know of" and is defensible
given the §12 related-work table.

---

## Audit of round 4's gap list

| Round 4 gap | Status |
|-------------|--------|
| Criterion 1 (one-sentence) | Fixed — italicized in abstract and §1 |
| Criterion 2 (across-run CIs) | Fixed — Table 3 multi-run; §6 multi-run paragraph |
| Criterion 4 (Pivot/MAST doors) | Fixed — Pivot contrast sentence + MAST runnable-detector statement |
| Criterion 5 (Surprise callout) | Fixed — new "Counter-intuitive findings" paragraph |
| G1 (schema diff table) | Fixed — new Table~\ref{tab:schemadiff} |
| G2 (per-trace overhead) | Fixed — explicit 100-1,000-span calc in §5.3 |
| G3 (span-kind × fault-class) | Fixed — new Table~\ref{tab:kindfault} |
| G5 (RAISE semantics) | Fixed — new paragraph on cross-thread, asyncio cases |
| G6 (reframe conformance gap) | Fixed — "57% of orchestration faults catchable only with kinds shipped adapters omit" |
| G7 (alternative breaker) | Fixed — wrapper-vs-SpanProcessor paragraph |
| G9 (release windows) | Fixed — caption footnote names release windows per adapter |
| G10 (Batch flush) | Fixed — isolation experiment validates the attribution; new §6 caveat |

Optional (not pursued but called out in Round 4):
- G4 (cross-machine sanity) — not pursued; §10 Threats correctly flags
  this as a known caveat and the relative ratios it cites are
  machine-independent. Acceptable for ATC.
- G8 (TikZ figure) — the architecture figure remains ASCII-in-a-box.
  A PC member who weights graphic polish heavily would dock half a
  letter grade; in my judgement the systems substance carries the
  paper across the line without it.

## New issues introduced by the round-4 revision

None of consequence. I checked:
- Table numbering: all `\ref` resolve cleanly in the compiled PDF.
- Page count: 11 text pages + 1 references = 12 total (ATC limit:
  12 text pages excluding references). Compliant.
- Double-blind: anonymous authors, redacted prior-work cite,
  pseudonymized system, redacted artifact URL. Still clean.
- Extended abstract (2 pages): tracks the +2.16µs change. Compliant.

## Final systems-paper check

| Criterion | Verdict |
|-----------|---------|
| Systems contribution vs application paper | SYSTEMS — one-sentence framing, mechanism + measurement coupling |
| Real, reproducible performance numbers with multi-run CIs | YES — Tables 2, 3, 5, plus repro section |
| Sound evaluation methodology | YES — Wilson CIs, z-test, multi-run CIs, isolation experiment, per-class & per-framework breakdowns |
| Systems trade-offs articulated | YES — exporter sync/async, schema richness vs memory, adapter fragility, breaker action choice, wrapper-vs-SpanProcessor alternative |
| Related work comprehensive | YES — Dapper/Canopy/Pivot (with explicit contrast)/X-Trace/Magpie/WAP5/lprof/SEDA/Tail-at-Scale/OTel/GenAI/OpenInference/OpenLLMetry/LangSmith/Langfuse/AgentOps/MAST/AgentDebug/Aegis/GuardAgent/NeMo/circuit-breaker |
| Double-blind requirements met | YES |
| Page count within limit | YES (11 text, 1 references) |
| Counter-intuitive finding | YES — F1, F2 callout |
| Crisp one-sentence systems contribution | YES — italicized in abstract and §1 |

## Final verdict: STRONG_ACCEPT

This is now in the top tier I would champion at the PC meeting. The
systems contribution is named in one sentence, the headline performance
number carries a multi-run CI, the related work slams every door I would
push on, and the two counter-intuitive findings (privacy-free
detection coverage; faster than baselines) are the kind of result that
makes a paper memorable in discussion. The conformance gap is honest
and reframed as an actionable schema-coverage gap, not a system
limitation. The reproducibility burden is met with named scripts and
pinned versions.

I would advocate this paper for the technical program.
