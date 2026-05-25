# Cold Review — Round 2
**Reviewer persona:** Middleware 2026 PC member; fresh context, no anchoring to Round 1.
**Date:** 2026-05-17
**Paper:** *Heterogeneous Adapters for AI-Agent Observability* (revised after Round 1)
**Verdict:** **WEAK_ACCEPT — minor revisions**

---

## Summary
The revision substantially improves on the Round 1 version. The systems-research kernel is now visible (three explicit middleware contracts, carrier format spelled out, idempotency argued, comparative-overhead row added to Table 4, scoping decisions made explicit). The paper is now 9 pages on a 12-page budget, which is acceptable: it earns its length through content density rather than padding. Honest gaps (DELEGATION p99 decomposition, cross-process correlation under high concurrency, mixed-adapter delegation, formal verification) are now called out by name in the limitations rather than buried. The middleware framing is defensible.

I would accept this paper if the following minor concerns are addressed.

---

## Issues by category

### Acceptable (no action needed)
- The architecture diagram (Fig. 1) is dense but legible.
- The three-tier abstraction is now properly framed as a set of contracts, not just a layering convention.
- The lazy-import discipline has a stated test-suite verification.
- The privacy filter has a property-test argument.
- Comparative overhead row in Table 4 ($+$0.92~ms vs $+$1.95~ms for vanilla OTel) is a genuine win for the paper.
- Reproduction steps are listed by exact command and file path.
- Mock-LLM defence (Sec 5.1) is a strong methodological argument.
- The scoping of RQ2 (in-process only, OTLP collector out-of-scope) is explicit and defensible.

### Minor (please address before camera-ready)

#### MN1 — Listing 1 uses a placeholder package name `agentmw`
The listing's `from agentmw import ...` reveals the SDK's real name absence. For double-blind this is fine; for the camera-ready, this MUST be replaced with the actual package name. The current `agentmw` placeholder is too short — a casual search of PyPI for `agentmw` returns nothing, which inadvertently signals the real name is hidden. Consider using a fully neutral placeholder like `from <SDK> import ...` or `from sdkname import ...`.

#### MN2 — Table 4 mean row arithmetic
The `Mean` row reports 10.89 for `meta` and 9.82 for `none`, implying $+$1.07~ms aggregate overhead (also stated in the abstract). The `$\Delta$ (vs.\ none, mean of 5 non-CrewAI rows)` row separately reports $+$0.92~ms for `meta`. Both numbers are correct but a reader might confuse them. Add a one-sentence footnote distinguishing the two aggregations explicitly.

#### MN3 — The Conclusion repeats the abstract verbatim in places
The Conclusion's opening 2 sentences echo the abstract's framing closely. Tighten the Conclusion to be a forward-looking synthesis rather than a re-recap.

#### MN4 — Related Work could cite one of the recent Middleware 2025 AI/ML papers
Middleware 2025 had several AI/ML middleware papers (e.g., UnifyFL, Argus). Citing one would signal venue-awareness. This is a polish move, not a correctness issue.

#### MN5 — Honesty: the comparison `$+$0.92 ms vs $+$1.95 ms` (Table 4 $\Delta$ row) is the headline number but it lacks a confidence interval
Add a brief mention of variance (or "sample standard deviation across 5 adapter rows is X ms") to support the comparison.

#### MN6 — Throughput numbers in the abstract (78,087 vs 19,071) appear three times in the paper
The abstract, intro contributions list, and Sec 5 summary each cite the same numbers. This is fine but contributes to a slight "abstract-as-roadmap" repetition. Consider tightening either the intro or the summary.

#### MN7 — Reference `agentrx` arXiv ID 2602.02475 needs verification
arXiv IDs are date-encoded: 2602 would mean Feb 2026 (not June). At submission time (Jun 2026) this would be a past month. The Round-1 reviewer flagged this; verify the actual arXiv ID and year before camera-ready. If the paper does not yet exist on arXiv with that ID, remove the cite or replace with a verified alternative.

#### MN8 — Listing 1's `instrument(frameworks=...)` is presented as the user API, but the body text describes `Instrumentor.instrument()` (per the OTel `BaseInstrumentor` contract)
Decide on one user-facing surface and use it consistently. The current text mixes two APIs.

#### MN9 — `\settopmatter{printccs=false}` strips CCS concepts. Middleware does not require CCS but some submission portals do. Confirm the HotCRP submission requirements.

#### MN10 — Section 3.7 mentions a `JSONFileSpanExporter` (line ~ in Listing 1's setup options) but the SDK source lists only `agenttelemetry/core/exporters.py`. Confirm naming consistency in the final draft. (Minor cosmetic.)

#### MN11 — The Conclusion claims a $+$0.41~ms low-end overhead. Table 4 shows Anthropic at $+$0.41~ms. The "Mean" row at $+$1.07~ms is the SDK's aggregate. The framing "approximately half the per-run overhead of vanilla OTel" comes from the $\Delta$ row ($+$0.92~ms vs $+$1.95~ms). All three numbers are correct; just ensure consistent framing across abstract, summary, and conclusion. The current revision is close but not yet perfect.

---

## Anonymization audit
PASS. No author names, no funder acknowledgement, no GitHub URL, no PyPI link. The OTEP language is general ("an OpenTelemetry Enhancement Proposal describing the conventions is included with the source archive"). The Listing 1 placeholder `agentmw` is short and obscure enough that it does not de-anonymize.

## Page-limit audit
9 pages of body content. Limit is 12. Acceptable; slight room to expand if the authors want a stronger Related Work or a worked context-propagation example, but not required.

## Reproducibility audit
PASS. The implementation section now lists exact reproduction commands and total wall time. The source archive is referenced consistently. This is more than most Middleware submissions provide.

---

## Final verdict
**WEAK_ACCEPT — minor revisions.** Address the minor items above (especially MN1, MN7, MN8 which are correctness-adjacent) and the paper is ready for the committee. The systems-research bar is met; the empirical evaluation is rigorous; the middleware framing is venue-appropriate. With the noted polish I would defend this for acceptance.
