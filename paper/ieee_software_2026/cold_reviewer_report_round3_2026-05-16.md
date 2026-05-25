# Cold Reviewer — Round 3 (Final) — 2026-05-16

**Paper:** `ieee_software_paper.tex` (7 pages, 204 KB PDF, compiles cleanly per log).

**Scope of this round:** Verify the Round-2 outstanding items (M1, M2, M3) are now full Threats-to-Validity paragraphs; check that nothing regressed in abstract/intro/claims and that no new issues were introduced.

---

## Per-item verification

### M1 — Single-author replication: **PASS**

Present at line 211 as a full Threats paragraph headed **"Single-author replication."** It does the methodological-limitation framing that Round 2 said was missing from the prior author-footnote placement:

- Names the replication as same-author and acknowledges independent-lab replication as the gold standard.
- Names the specific failure modes this design cannot detect ("a shared misunderstanding of the original harness's trigger semantics, or a shared bug in how the trigger condition is operationalized").
- Documents a concrete mitigation (synthetic-input unit test that fires the trigger by construction, demonstrating the 0.0 trigger rate across 960 runs is model behavior, not a harness defect).
- Names third-party replication as future work.

This goes beyond the disclosure framing — it is a substantive methodological caveat. Addresses Round-2 ask.

### M2 — No external instrumentation comparison: **PASS**

Present at line 213 as a full Threats paragraph headed **"No external instrumentation comparison."** It directly addresses the Round-2 ask:

- Names three concrete comparator stacks (LangChain+LangSmith, OTel GenAI on raw vendor APIs, vendor-provided structured-logging endpoints).
- Concedes the absorption claim is "consistent with what we measured but does not foreclose the possibility that some alternative instrumentation could surface portions of the internal loop via stdout/stderr capture, structured trace export, or vendor-side telemetry."
- Names the side-by-side CLI-wrapped vs. raw-API instrumentation experiment as future work.

This is the comparison-honest framing Round 2 asked for. Addresses Round-2 ask.

### M3 — Baseline-dependent power: **PASS**

The prior "Sample size" Threats item at line 209 has been rewritten as **"Sample size and baseline-dependent power"** and now explicitly handles the ceiling effect:

- Enumerates the five high-baseline cells (Opus v1 85.0 percent, GPT-5.5 v1 95.0 percent, Haiku v1 91.7 percent, Opus v2 88.3 percent, GPT-5.5 v2 83.3 percent).
- States the obvious arithmetic: a +25pp effect at 95 percent baseline would require exceeding 100 percent (impossible), and even +12.5pp would push GPT-5.5 v1 past 100 percent.
- Separately notes which cells (Sonnet v1 60 percent, Sonnet v2 3.3 percent, Haiku v2 13.3 percent) do have headroom and observes that they too showed near-identical patch rates across conditions.
- Reframes the claim conservatively: "Our claim is that the intervention's trigger condition does not fire — not that we have refuted the original effect's existence at any sample size."

This is the careful framing Round 2 asked for. Addresses Round-2 ask.

---

## Internal consistency / regression checks

- **Compile status:** `Output written on ieee_software_paper.pdf (7 pages, 204576 bytes).` Clean compile.
- **Abstract (line 33):** Unchanged headline numbers — 960 instance-runs, 2,991 iterations, $n=60$ per arm, eight cells, trigger never fires, $+12.5$pp prior effect, $0$ max-repeat under v1 and $1$ under v2. Consistent with Table 1.
- **Introduction (lines 41–63):** Unchanged thesis and contributions; the four contribution bullets still match the body.
- **Table 1 (lines 120–143):** Unchanged numbers. The new sample-size paragraph correctly cites the same baseline-rate values that appear in Table 1.
- **Findings 1–4 (Section IV):** Unchanged. Finding 4's "lowest observed $p$-value is $0.17$" claim is consistent with Table 1.
- **Threats section ordering:** Logical flow — benchmark scope, metric, CLI version, Sonnet/Haiku artifact, sample-size/power, single-author, no-external-instrumentation, edge-scope, Gemini/grok. No internal contradictions among the items.
- **Limitations section after Conclusion:** L1–L4 retained. L2 (raw-API behavior) is now distinct from new Threats M2 (external instrumentation observability) — these address different concerns and do not redundantly cover each other.
- **Conclusion (lines 231–233):** Unchanged. Still consistent with the now-tightened sample-size framing (does not overclaim refutation of the original effect).
- **No new issues introduced:** No broken `\ref{}`, no orphan citation, no stray figure float. Bibliography (lines 251–276) unchanged and complete.

---

## Final verdict

**PASS.**

All three Round-2 outstanding items (M1 single-author replication, M2 no external instrumentation comparison, M3 baseline-dependent power) are present as full, substantive Threats-to-Validity paragraphs — not stubs, not footnote-only mentions. The paper compiles to 7 pages, internal consistency is preserved across abstract / intro / results / threats / conclusion, and no regressions or new issues were introduced. The author has substantively addressed every concern raised across the three review rounds.

Ready for submission.
