# Cold Review — Round 1

**Reviewer persona:** ISSRE 2026 Industry Track PC member; 15+ years senior reliability engineer at a major cloud provider; serves on IEEE Computer Society Reliability Society; reviewed 50+ ISSRE submissions; explicit history of rejecting benchmark-reframing papers.

**Bar:**
1. Industry contribution with real deployment evidence (not academic reframing)
2. Reliability metrics (MTTR/MTBF/availability/SLO) discussed
3. Distinct from prior AIware 2026 paper using same data
4. Credible operational deployment story
5. Page/format compliance

**Verdict: WEAK_REJECT.**

---

## Line-by-line criticism

### Critical issues

**[CR1 — AIware overlap defense is asserted but not built into the technical content.]**
The paper claims the contribution is distinct from AIware in §2 ("Boundary with prior work") and the reader is told the rubric is new — but Tables 1 and 2 (conformance, blast-radius) are derived analyses of the same TSV that backs AIware. AIware reports the per-condition FDR aggregate (0.612 at metadata) and the per-fault FDR matrix; this paper reports per-framework FDR. The per-framework breakdown is the *only* fundamentally new quantitative artifact in this paper. That is thin. AIware *could* have reported per-framework FDR with one extra table; the venue must believe that the deployment rubric framing requires a full paper, not just an "implications" subsection bolted onto the AIware revision. I find the defense plausible but not airtight — a hostile reviewer can argue this is "AIware extended abstract for SREs." **The paper needs a stronger, more visible declaration of what is empirically novel** — specifically, the per-framework conformance gap (Table 1) and the alert-fatigue budget calculation (Table 3) need to be explicitly badged as "new analysis not present in AIware 2026."

**[CR2 — Reliability metrics (MTTR/MTBF/SLO) are name-dropped, not quantified.]**
§2 lists MTTR, MTBF, SLO, error budget as the vocabulary the paper uses, and §7 lesson 5 admits the benchmark did not measure TTR. But the paper does not actually compute *any* operational reliability metric end-to-end. The alert-fatigue budget (Table 3) is the closest, and it is a fine calculation. But there is no MTBF analysis, no error-budget burn estimation, no SLO-translation worked example. Industry reviewers will read the section headers, scan for numbers, and find one number (7.1% FPR) doing all the operational work. **At minimum, the paper needs one worked example: "given a 99.5% availability SLO on agent workloads, here is how the per-framework conformance gap translates into expected error-budget burn over a 30-day window."** A short calculation would close this gap without expanding scope.

**[CR3 — "Real deployment evidence" is absent and acknowledged but not compensated for.]**
The paper openly admits in §8 that "No live production deployment is included in this paper" and the integration pattern is "designed, not measured." Industry Track reviewers will read this and immediately ask: "Why is this an Industry Track paper then?" The CFP literally says "work grounded in real-world systems, operational experience, or industrial practice." A pure rubric paper grounded in benchmark data is closer to Research Track territory. **The paper needs to either (a) cite *somebody's* production deployment of AgentTelemetry, even a public blog post or GitHub issue thread; or (b) reframe more aggressively as "designed-from-evidence" with explicit citation of SRE practice books, AIOps deployment retrospectives, and the OpenTelemetry production-adopter community.** Right now the operational story floats unanchored.

**[CR4 — Conformance grades are unfair to the third-party SDKs.]**
The custom adapter (Grade A, 9/9 span kinds) is the AgentTelemetry-author-written reference implementation. Every other framework was instrumented by adapting the AgentTelemetry author's adapter code, *which uses the existing framework hooks*. So the comparison isn't "vendor X ships at Grade C" — it's "the AgentTelemetry-author-written adapter for vendor X reaches Grade C using the framework's exposed hooks." If LangChain wanted to ship a Grade A adapter, they could; if I'm a LangChain maintainer reading this paper, I'm going to push back that the grade reflects *the AgentTelemetry adapter coverage*, not the *framework's intrinsic instrumentation deficit*. **The paper should distinguish (a) the adapter's coverage as shipped by AgentTelemetry, from (b) the framework's intrinsic ability to expose span kinds through its public APIs.** Otherwise the "vendor conformance gap" framing is misleading.

### Significant issues

**[CR5 — Lesson 4 "span-kind coverage is the right unit of reliability investment" is asserted without comparison to alternatives.]**
The paper says span-kind coverage has direct payoff; that's true. But the lesson would only be defensible if the paper had compared span-kind investment against, say, prompt-engineering investment, model upgrade investment, or human review investment. As written it's a tautology: "instrumenting for fault X enables detecting fault X." Either soften to "for the detection coverage axis specifically..." or drop the lesson.

**[CR6 — Alert-fatigue budget extrapolation has a load-bearing assumption.]**
Table 3 scales the 7.1% FPR from 42 controlled runs to 1,000–50,000 daily runs. This linear extrapolation assumes (a) production traffic has the same fault-class distribution as the benchmark (it doesn't — Lesson 3 explicitly notes organic fault rates differ), and (b) detector firings are independent across runs (they aren't — a misconfigured agent will fire detectors on every run until fixed). **Either add a sensitivity analysis showing the budget under, say, 0.5×, 1×, and 2× the benchmark FPR, or explicitly call out the linear extrapolation as a planning-grade estimate.**

**[CR7 — Runbook templates are sparse.]**
Two runbooks (reasoning_loop, cost_explosion) at ~5 bullet points each is not really a "playbook." For an Industry Track paper claiming runbook contribution, two examples in the paper plus "the rest are in the open-source release" risks reading as a tease. **Either expand to four worked runbooks (the four XL-blast classes) or honestly downscope the claim to "we sketch the runbook pattern; the full set is in the artifact."**

**[CR8 — Reference to Aegis and AgentDebug uses placeholder/anonymous BibTeX entries.]**
refs.bib has `Anonymous` and `Yu, Xinyi and Anonymous` for AgentDebug and Aegis. Submission is non-anonymous and references must be real. Either find the real citations or drop them.

**[CR9 — §6 four-week rollout sequence isn't grounded.]**
"Week 0 inventory, Week 1 bridge, Week 2-4 detectors, Week 4+ runbooks" — why those durations? Why not 2 weeks per phase or 1 day per phase? This needs either (a) citation to an SRE rollout pattern, or (b) explicit framing as "indicative cadence; teams should adapt to their change-management velocity."

**[CR10 — The mocked vs real-LLM distinction is muddled.]**
Lesson 3 says controlled benchmarks over-count organic faults. But Tables 1, 2, 3 all use the controlled-benchmark FDR/FPR numbers as the operational baselines for grading vendors and setting alert thresholds. There's a tension: if the benchmark over-counts, then conformance grades and alert thresholds derived from it also do. **The paper needs a clearer statement of how the controlled-benchmark numbers translate to operational expectations — even just a sentence: "We use controlled-benchmark FDR as a structural ceiling: the grade card reports what each adapter can detect when faults are present, not how often faults will be present in your traffic."**

### Minor issues

**[CR11]** §1 hook ("burns several hundred dollars") is generic. Either anchor to a real, citable incident or soften to "burns a meaningful share of the per-task budget."

**[CR12]** Table 4 (postmortem rubric) is good but should explicitly cite an existing postmortem template format (Google's, Etsy's, or PagerDuty's) so it reads as an *addition* to known practice, not a from-scratch invention.

**[CR13]** "Adopting LLM agents in production requires a reliability-engineering rubric, not just a benchmark" — the framing "not just a benchmark" subtly hits the AIware paper. Soften: "Adopting LLM agents in production requires reliability-engineering artifacts beyond benchmark evidence alone."

**[CR14]** No mention of OpenInference's recent agent-orchestration extensions. If they exist by submission time, the conformance comparison is incomplete.

### What works

- The deployment rubric framing IS legitimately distinct from AIware — the per-framework conformance card, the blast-radius taxonomy with triage policy, and the alert-fatigue budget are new artifacts derived from the same data.
- Honest negative findings throughout (Lesson 1–5) are well-aligned with the CFP's explicit invitation.
- 6 pages on the dot; IEEE format; references look properly structured (modulo CR8).
- Lesson 5 (no TTR measurement) is the kind of disarming admission that earns Industry Track trust.

---

## Verdict and required changes for round 2

**WEAK_REJECT.** The framing is right and the contribution is real, but the paper needs three substantive fixes before it crosses the WEAK_ACCEPT threshold:

1. **Strengthen the AIware-overlap defense in-line** (CR1). Add a sidebar table or callout list in §2: "What this paper analyzes that AIware did not." This must be impossible to miss.

2. **Add a worked SLO/error-budget translation** (CR2). One paragraph + one mini-calculation tying the conformance gap to error-budget burn on a worked agent SLO. This is the single biggest gap for the Industry Track bar.

3. **Reframe the conformance grades to be fair to vendors** (CR4). Distinguish "AgentTelemetry adapter coverage" from "framework's intrinsic instrumentation surface." Add a column or footnote.

Secondary: fix CR3 (anchor the operational story to public adoption signals, even minimal); CR6 (sensitivity caveat on budget); CR8 (replace Anonymous refs); CR10 (controlled-vs-organic clarifier).
