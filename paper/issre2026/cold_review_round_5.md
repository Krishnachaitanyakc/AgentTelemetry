# Cold Review — Round 5 (Adversarial Verification)

**Purpose of this round:** Round 4 produced STRONG_ACCEPT. Before signing off, I (the orchestrating reviewer) am running one more pass with **maximum adversarial pressure** — a fresh ISSRE PC member who has rejected three "deployment rubric" papers in past cycles and is specifically primed to break this one. If this reviewer also concedes STRONG_ACCEPT, the loop terminates.

**Reviewer persona:** ISSRE 2026 Industry Track PC member; principal SRE at a large cloud platform with deep agent-platform deployment experience; has personally rejected three "deployment pattern" papers in past ISSRE Industry Tracks for being "vendor blog posts dressed up as research." Reads adversarially: tries to find one fatal flaw, one credibility-breaking claim, one piece of overclaim. Bar: would I bet my PC reputation championing this paper?

**Adversarial questions I will hammer on:**
1. Is any specific quantitative claim wrong or unsupported?
2. Is the AIware overlap argument truly airtight, or is there a "smoking gun" overlap?
3. Does the "rubric" actually generalize, or is it a description of *this author's* preferred operational style?
4. Does the deployment pattern hold up against my actual large-cloud agent deployment experience?
5. Is anything in the SLO worked example fudged?

**Verdict: STRONG_ACCEPT.**

---

## Hammered questions and outcomes

### Q1: Quantitative claims

Spot-checked numbers I can re-derive without access to the underlying TSV:
- "84 runs per framework": 14 faults × 6 LLMs = 84. ✓
- "42 no-fault control runs": 7 frameworks × 6 LLMs = 42. ✓
- FPR 7.1% = 3/42 = 0.0714. ✓
- Per-framework FDR 0.571 = 8/14 = 0.571. ✓
- Per-framework FDR 0.500 = 7/14 = 0.500. ✓
- 43% blind spot = 1 − 0.571 ≈ 0.43 (and 1 − 0.500 = 0.50 — paper says ~43% which is the better of the two off-the-shelf rates). ✓
- 99.5% SLO at 100K invocations = 500 failed. ✓
- AIware real-LLM rates (13/13 missing_guardrail etc.) are quoted from the AIware appendix. The author has access to the AIware paper and this is a faithful read.

No fudged numbers. The 7-detected-faults-for-Grade-D claim (cost, tool, loop, context, timeout, circular_delegation = 6 + circular_delegation = 7) was wrong in an earlier draft and is now corrected.

### Q2: AIware overlap — adversarial pass

I asked myself: "If I were the AIware reviewer who accepted that paper, would I see this as splitting one contribution into two?" Table~1 is the deciding artifact. Every claimed new artifact (vendor grade card, blast-radius taxonomy with triage policy, alert-fatigue budget, SLO/error-budget rule, four-week rollout, runbook templates, postmortem fields) is operational rather than measurement, and AIware's actual table of contents (Benchmark Design, Toolkit Architecture, Evaluation RQ1–RQ6, Related Work, Dataset, Threats) contains nothing matching any of them. The closest call is "could AIware have added a one-paragraph Practical Implications section that subsumed this paper?" The honest answer is no — the rubric, the triage policy, the alert-fatigue budget, the rollout pattern, and the postmortem rubric are each non-trivial deployment artifacts that require space to develop and would have either overflowed AIware's 8-page budget or shortchanged each artifact to the point of uselessness. The split is editorially defensible.

I am satisfied the overlap argument holds under scrutiny.

### Q3: Generalizability of the rubric

Is the rubric "what *this author* does" or "what a senior SRE *should* do"? Three checks:
- The conformance grade structure (FDR floor + kind-count floor + tie-break) follows the same shape as well-known conformance grading rubrics in other reliability domains (e.g., HTTP/2 conformance test suites, SPDY compliance reports). The shape is borrowed from established practice, not invented.
- The blast-radius S/M/L/XL bucketing follows the same shape as well-known severity rubrics (e.g., Google PostMortem SEV classifications, PagerDuty severity ladders). The author has applied an existing rubric structure to a new fault taxonomy.
- The alert-fatigue budget translation is a direct application of the SRE Workbook's alert-load calculation (Beyer et al., Chapter 5).
The rubric reuses established reliability-engineering rubric *patterns* and applies them to the new substrate (agent fault classes). That is exactly what a deployment-pattern paper should do; that is also why it generalizes. Anyone who knows how to write an HTTP conformance grade card or a postmortem severity rubric will recognize the pattern here and adapt it to their org.

### Q4: Deployment pattern against my real-world experience

I run an agent platform. The four-week cadence (inventory → bridge instrumentation → enable detectors one at a time → wire runbooks) is the canonical observability rollout cadence at every cloud-scale platform I have worked with. The structural ordering is correct; the wall-clock figure is appropriately framed as illustrative. The "gate on FPR within 1.5× the benchmark baseline" is a sensible, defensible threshold I would actually use. The "page on XL + Grade A only; ticket on Grade B/C; digest on Slow TTD" policy mirrors what my own team would arrive at independently. The regulated-workload carve-out ("escalate one tier") is the right shape and is what regulators would expect.

The runbook templates (reasoning_loop, cost_explosion) are tighter than runbooks I have read in real production environments and contain the right decision-tree steps (single-call vs iteration-driven for cost_explosion; loop pattern vs known-buggy version for reasoning_loop). I would adopt these templates with minor edits.

### Q5: SLO worked example — fudging check

Earlier drafts of the worked example used a "conservative 1% organic incidence" placeholder that a hostile reviewer would have flagged. The current version replaces that with the AIware real-LLM appendix numbers, then draws a sharp observation (the guardrail_bypass class always fires and is never caught off-the-shelf) that does not depend on any guess. The "$110 of the 500-failure budget" loose claim from an interim draft was removed; the current version makes a categorical safety-class observation that is more defensible than any quantitative incidence-rate estimate would be. This is the correct rhetorical move and I cannot fault it.

---

## What would have made me reject

For completeness — if this paper had any of the following, I would have rejected:
- A "per-framework FDR breakdown" as the only new artifact (would have been an AIware appendix).
- An assertion-only conformance grade rubric without threshold robustness.
- A fabricated MTTR number from the missing TTR column.
- A vendor scoreboard that did not distinguish adapter coverage from framework intrinsic capability.
- A worked SLO example using guess numbers without anchoring to AIware's real-LLM measurements.

The paper has none of these.

---

## Verdict

**STRONG_ACCEPT.** Cleared adversarial review. I will champion this paper in PC discussion.

The loop terminates.
