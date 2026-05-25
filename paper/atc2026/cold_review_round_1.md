# Cold Reviewer Report — Round 1

**Reviewer persona:** ATC 2026 PC member, 6+ years ATC reviewing, senior systems
researcher who has built/operated large distributed systems. Skeptical, demands
measurement quality, treats "systems vs. application paper" as a first-class gate.

**Paper version reviewed:** `atc_paper.pdf` (8 pages: 7 text + 1 references)

**Overall verdict:** **WEAK_REJECT** — the paper has the bones of a systems
contribution and the measurements are real, but several gaps will sink it on
the PC floor.

---

## Major Criticisms

### M1. Page count is far under budget — looks like a short paper masquerading as long.
Format choice said 12 pages text; the draft is 7 pages text. ATC PC members
read "long paper with 7 pages of text" as either (a) the authors couldn't fill
the space, or (b) the work isn't long-paper sized. Either reading hurts.
**Fix:** either resubmit as a short paper, or expand to use $\ge$10 pages of
text with content that earns the space (more rigorous statistics, threats to
validity, span-correlation figure, code listing for the policy DSL, ablations).

### M2. No statistical rigor on the headline FDR numbers.
Table~\ref{tab:fdr} reports point estimates (0.429, 0.612, 1.000) with no
confidence intervals, no per-fault-class breakdown, no per-framework
breakdown, and no significance test. An ATC reviewer will say: "0.429 vs 0.612
across 588 runs — is the difference significant? what's the variance across
seeds? what's the per-fault breakdown?" The repo has the raw data; the paper
must show it.

### M3. Missing per-fault-class breakdown.
The most important figure in a fault-injection paper is the matrix
"fault class $\times$ telemetry condition", showing which classes each
condition catches. The aggregate FDR hides the structural claim — that the
GenAI baselines catch the bottom-up classes (tool failure, hallucination
keyword) while \sysname catches the orchestration classes (circular
delegation, reasoning loop). Without that matrix, the reviewer cannot verify
the architectural argument.

### M4. The "systems trade-off" framing is asserted, not earned, in three places.
- §3.2 (privacy as a systems constraint): the claim "no observable loss of
  detection coverage" is supported by a single aggregate number; should be
  per-class.
- §4 (adapter table): the Fragility column (low/medium/high) is qualitative
  and unbacked. Either drop the column or back it with a metric (number of
  versions tested, breaking-change history from the vendor changelog).
- §5 (circuit breaker activation overhead): claim of "sub-microsecond,
  dominated by lock-acquire" is stated without a number. ATC reviewers
  will not accept "sub-microsecond" as a measurement.

### M5. No figure of span correlation across async/multi-process boundaries.
D2 is one of the three pillars in §1 and gets one paragraph in §3.3. There is
no figure showing the carrier injection and no measurement of correlation
fidelity (e.g., what % of cross-process spans get their parent ID right).
This is the second-most-important systems contribution after the circuit
breaker and is the weakest-defended in the current draft.

### M6. No code listing for the policy DSL.
§5.2 describes the policy API in prose. An ATC systems paper that introduces
an API contributes more when the API is shown. A 10-line Python listing
showing how a user composes a policy would earn its space.

### M7. Related-work section lumps OpenInference / OpenLLMetry / LangSmith /
Langfuse / AgentOps into one paragraph.
Each one deserves a sentence on what specifically it does and does not do
relative to the four-property list in §2. The current "none expose a
runtime-control surface" claim is true but underdeveloped. The PC member who
works at one of those companies will notice.

### M8. No threats-to-validity section.
ATC papers in the bug-finding/tracing axis are expected to call out: (a)
mock-LLM vs. real-LLM split (you have a real-LLM section but the threat goes
unstated), (b) single-machine measurement (Apple M4 Pro vs. a real production
box), (c) the conformance gap as a per-app issue and what it means for
generalizability, (d) the static rule-based detector vs. a learned one.

### M9. Reproducibility claim is asserted not demonstrated.
The contributions claim "open-source artifact with reproducibility commands";
the body does not list those commands. ATC reviewers who serve on the
artifact-evaluation committee look for "to reproduce Table 4, run X" lines.

### M10. The "84/112 SWE-bench Lite" anchor in §1 is unsourced.
The number is a citation hook ("from a prior controlled study") but the
prior study is not cited (the AIware paper is anonymized for double-blind,
which is correct, but the citation must still appear as
\cite{anon} or [redacted for double-blind review]). As written, the reviewer
sees an unverifiable number.

---

## Minor Criticisms

### m1. The OTel SDK version is not stated.
"OTel SDK pinned in requirements.lock" without naming the version is not
reproducible.

### m2. The standard deviation of 87.8\,\textmu{}s for DELEGATION p99 is
flagged as a GC interaction, but there is no measurement of GC
incidence — assert and show, or drop the speculation.

### m3. The "DSM" acronym in the abstract is used without expansion.
The abstract uses "\sysname{}'s DSM extends" without ever defining DSM. This
is a leftover from the prior outline. (Actually checking — the abstract
doesn't use DSM; the venue_research_report does. Confirm the abstract is
clean.)

### m4. Tables are not cross-referenced consistently.
§7 says "Table~\ref{tab:fdr}" — verify all label/ref pairs resolve.

### m5. The architecture figure is ASCII-art in a \fbox.
A real figure (TikZ or PDF) would be expected at ATC. The current rendering
is acceptable but spartan.

### m6. \balance is called from the second column — package warning fires.
Move to before \bibliographystyle, or accept unbalanced last page.

### m7. Anonymous authorship metadata is correct, but the
\acmConference still says "ATC '26" with proceedings boilerplate — fine for
review but verify.

### m8. The contribution list (§1, items 1--5) and the abstract should agree
on numbering and content. Currently the abstract enumerates 4 items and §1
enumerates 5; align them.

### m9. §7 says the matcher is "the same across all telemetry conditions" —
that's a critical methodological claim and should be defended with a
sentence on how the matcher's predicates handle missing attributes
gracefully (so absence of an attribute is NOT counted as detection).

### m10. The conclusion is short (1 paragraph). ATC conclusions usually
recap the contribution numerically; the current one does this but could be
sharper.

---

## Double-blind Check
- Author block: anonymous ✓
- No author URLs ✓
- Anonymized system name (\sysname{}/AgentScope) ✓
- "in a prior controlled study" in §1 is appropriately third-person ✓ but
  needs a `[redacted for double-blind]` marker per M10.
- No first-person self-cites detected ✓

## Page-count check
- 7 pages text + 1 page references = 8 total
- Long-paper limit is 12 pages text excluding references
- We are 5 pages UNDER budget — see M1.

## Systems-paper check
- Adapter taxonomy is a systems contribution ✓
- Circuit breaker as SpanProcessor is a novel mechanism ✓
- Overhead/scalability measurements are present ✓
- BUT the per-fault breakdown, the cross-process correlation figure, and
  the missing statistical rigor weaken the systems-evidence claim. See
  M2, M3, M5.

## What would flip this to ACCEPT
1. Expand to 10--11 pages text with per-fault matrix, statistical
   confidence intervals, span-correlation figure, code listing, threats
   section, reproducibility commands.
2. Fix M4 (back every "systems trade-off" claim with a number).
3. Fix M10 (cite the SWE-bench prior study with [redacted] marker).
4. Address m1--m10 in the next iteration.

**Verdict if all major points addressed:** WEAK_ACCEPT, possibly ACCEPT.
