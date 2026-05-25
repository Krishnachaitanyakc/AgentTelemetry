# Cold Reviewer Report — Round 2

**Reviewer persona:** ATC 2026 PC member, 6+ years ATC reviewing, senior systems
researcher. Fresh read — no anchoring to Round 1.

**Paper version reviewed:** `atc_paper.pdf` (10 pages: 9 text + conclusion +
references split across page 9--10)

**Overall verdict:** **WEAK_ACCEPT** — the systems contribution is now well-
defended with rigorous measurement. Remaining concerns are mostly minor.

---

## What Got Better Since Round 1

- M1 (page count): paper grew from 7 to ~9 text pages with substantive content
  (per-fault matrix, per-framework breakdown, threats, reproducibility, code
  listing, span correlation subsection, real circuit-breaker overhead
  measurement). The added pages earn their space.
- M2 (statistical rigor): Wilson 95% CIs and two-proportion z-test
  ($p<0.001$) now appear in §7. The CI overlap argument is the right
  defense.
- M3 (per-fault matrix): Table 6 is the load-bearing structural result —
  "bottom-up faults" vs "orchestration faults" framing is exactly what an
  ATC reviewer wants.
- M4 (systems trade-offs): activation overhead now has a real number
  (+1.75µs p50, +17.6%); adapter fragility column has a methodology footnote.
- M5 (span correlation): §3.4 added with three boundary classes named (asyncio,
  process pool, inter-agent RPC) and a fidelity result (zero orphan spans
  across the 45-run real-LLM study).
- M6 (code listing): Figure 2 added.
- M7 (related work): each adjacent tool now gets a concrete sentence.
- M8 (threats to validity): new §10 added, four threats articulated.
- M9 (reproducibility): new §11 with per-table commands.
- M10 (SWE-bench citation): "[redacted for double-blind review]" marker added.
- m1 (SDK version): now stated as "opentelemetry-api/sdk 1.27.x" in §11.

## Remaining Issues

### R1. Per-fault matrix shows METADATA_ONLY = FULL exactly for all 14
classes. Confirm this is real (it is, from the data) and add one sentence
explaining why: the matcher predicates key off attribute *names* and *kinds*,
not message bodies, so dropping payload (METADATA_ONLY vs FULL) preserves
detection coverage exactly. The paper says this in passing in §3.2 but the
inference for the per-fault table should be cross-referenced.
**Severity: cosmetic.**

### R2. The four ``bottom-up faults caught by GenAI baselines'' include
\texttt{infinite\_loop} and \texttt{context\_overflow}. These are
orchestration-flavored faults that a reviewer might expect to require
agent-specific vocabulary. Add a clarifying sentence: vanilla OTel catches
them because the GenAI semconv (\texttt{gen\_ai.usage.input\_tokens}) and the
adapter's run-time wall clock are sufficient signals; this is exactly why
the GenAI baselines reach 0.429 instead of a lower number.
**Severity: minor — could mislead a reviewer.**

### R3. The conformance-complete-adapter CI is reported as [0.957, 1.000]
in Table 5. With $n=84$ and $p=1.000$, the Wilson upper bound is 1.000 and
the lower bound is 0.957. Verify: yes, this is correct for the Wilson
interval. Optionally report the rule-of-three lower bound (1 - 3/n = 0.964)
as an alternative.
**Severity: cosmetic.**

### R4. The DELEGATION p99 outlier (42.6µs vs 27µs for other kinds, std 87.8µs)
still has no GC measurement to back the "GC interaction" speculation.
Either drop the speculation or add a sentence noting that the outlier was
verified by running with PYTHONDEVMODE=1 and observing GC pauses
(if true). Currently the assertion is the only one in the paper without
evidence.
**Severity: minor — but ATC reviewers notice claims-without-evidence.**

### R5. The architecture figure is still ASCII-in-a-box. A TikZ rendering
would be more professional, but functional ASCII is acceptable for review.
**Severity: cosmetic.**

### R6. The acknowledgments are absent (correctly suppressed for double-
blind). Note for camera-ready.
**Severity: none — correct for review.**

### R7. The conclusion is two sentences too long; could lose the
"The systems trade-offs (...) are reported in full rather than hidden"
qualifier without losing meaning.
**Severity: stylistic.**

### R8. §3.4 says "no orphan spans were observed" across 570 spans. Add
the binomial 95% upper bound on the true orphan rate: with 0/570, the
exact upper bound is $\sim$0.52%. This is the kind of statistical
fastidiousness ATC reviewers reward.
**Severity: minor — would strengthen the claim.**

### R9. The policy DSL listing uses \texttt{breaker.set\_cost\_threshold}
which is not in the public API per circuit\_breaker.py. Either rename to
match the real API or note that the listing is illustrative.
**Severity: minor — reproducibility concern.**

### R10. The repro section claims one-shot scripts at
\texttt{benchmarks/scalability.py}; verify this file exists.
**Severity: minor — broken claim is worse than no claim.**

---

## Systems-paper check (final)
- Adapter taxonomy: yes ✓
- Circuit breaker mechanism: yes ✓ (with measured overhead)
- Overhead/scalability with percentiles: yes ✓
- Per-fault and per-framework breakdown: yes ✓ (NEW)
- Statistical rigor: yes ✓ (Wilson CIs, z-test)
- Span correlation as a first-class problem: yes ✓ (NEW)
- Threats to validity: yes ✓ (NEW)
- Reproducibility commands: yes ✓ (NEW)
- Real workload end-to-end: yes ✓

## Page-count check
- ~9 pages text + 1 page references (split last page) = 10 total
- Long-paper limit is 12 pages text excluding references
- 3 pages under budget — could expand with TikZ figure, more topology-study
  detail, or a discussion paragraph on collector deployment patterns. Not
  required.

## Double-blind check
- Author block anonymous ✓
- [redacted for double-blind review] marker present in §1 ✓
- \sysname pseudonym used throughout ✓
- No author URLs ✓

## Verdict
**WEAK_ACCEPT.** The R-series issues are all minor; fixing R1, R2, R4, R8,
R9, R10 takes a few hours and pushes to **ACCEPT**. The systems story is
defensible, the measurements are real, and the related-work positioning is
honest.
