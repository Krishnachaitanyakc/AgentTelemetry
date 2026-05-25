# ISSRE 2026 Industry Track — Venue Research Report

**Compiled:** 2026-05-17
**Sources:** https://cyprusconferences.org/issre2026/industry-track/ ; https://easychair.org/cfp/ISSRE2026 ; https://cyprusconferences.org/issre2026/ ; https://issre.github.io/2024/program_industry.html ; https://issre.github.io/2025/calls_cfp-industry.html

---

## 1. Conference & Track Logistics

| Item | Value | Source |
|------|-------|--------|
| Conference | 37th IEEE International Symposium on Software Reliability Engineering (ISSRE) | cyprusconferences.org/issre2026 |
| Location | St. Raphael Resort, Limassol, Cyprus | cyprusconferences.org/issre2026 |
| Dates | October 20–23, 2026 | cyprusconferences.org/issre2026 |
| Track | Industry Track | cyprusconferences.org/issre2026/industry-track |
| Industry Chairs | Jinyang Liu (ByteDance, USA); Sigrid Eldh (Ericsson AB, Sweden) | easychair.org/cfp/ISSRE2026 |
| Submission Portal | EasyChair: https://easychair.org/conferences/?conf=issre2026 | CFP page |

## 2. Deadlines (verbatim, AoE)

- **Abstracts:** "June 28, 2026 & July 3, 2026" (two cycles)
- **Full/Short Papers:** "July 5, 2026 & July 12, 2026"
- **Enlightening Talks / Tool Demos:** "15 August, 2026"
- **Author Notification:** August 12, 2026
- **Camera Ready:** August 19, 2026

We target the **July 5, 2026 AoE** full-paper deadline (first cycle).

## 3. !! CRITICAL FORMAT CORRECTION !!

**The user's prompt stated "10-page paper for ISSRE 2026 Industry Track" — this is INCORRECT per the official CFP.**

Verified page-limit reality (quoted from the official Industry Track CFP):

- "Enlightening talk or Tool demo: 1-2 page abstract"
- "Short paper: 4-pages (including references)"
- "Full paper: 6-pages (including references)"

There is no 10-page option. We will produce a **6-page Full Paper** (IEEE Computer Society format, including references). This is the longest format the venue accepts; producing 10 pages would result in desk rejection.

## 4. Template & Format

- **IEEE Computer Society Format Guidelines** (LaTeX or Word templates provided on CFP page)
- PDF with embedded fonts
- **Non-anonymous** — "submissions are not anonymous"; author identities visible to reviewers
- Single-blind / open review (typical for ISSRE Industry Track)

## 5. Topics of Interest (verbatim themes)

- Use cases and lessons learned in reliability/dependability
- Design for reliability; failure case studies
- **"Reliability in AI-driven and autonomic systems or AI techniques used for Reliability Engineering"** ← directly applicable
- Software reliability across domains
- Trustworthiness and security
- Human-centric reliability
- Standards adoption experiences

## 6. What the Industry Track Demands (vs Research Track)

Direct quote from CFP:
> "work grounded in real-world systems, operational experience, or industrial practice, and does it address reliability or dependability concerns?"

Direct quote:
> "papers with good evaluation, honest data, new insights and practical experiences"

> "submissions reporting negative results, unexpected outcomes, and lessons learned from real-world practice."

**Best Paper eligibility:** "at least one author whose primary affiliation is in Industry." (We are submitting as "Independent Researcher" — eligible for the track but technically not eligible for Industry Best Paper. Acceptable.)

**Implication for the paper:**
- Must read as practitioner experience, NOT academic re-framing
- Must lean into reliability-engineering vocabulary: MTTR, MTBF, SLO, error budget, blast radius, runbook
- Honest gaps and negative findings are explicitly welcomed (advantage — our mock-vs-real FDR gap and field-rate caveats become assets, not liabilities)
- Lessons learned > novel algorithm
- The reviewer is a senior practitioner, not an academic — they reward concrete, deployable artifacts and skewer hand-waving

## 7. ISSRE 2024 Industry Track Comparables (closest analogues)

From the published 2024 program (issre.github.io/2024/program_industry.html):

1. **"Early Bird: Ensuring Reliability of Cloud Systems Through Early Failure Prediction"** — Liu, Ma, Zhao et al. — operational AIOps deployment at scale
2. **"A Global Operational Readiness Review Process: Improving Cloud Availability"** — Cusick, Basil — process-driven reliability paper, no novel algorithm
3. **"Multivariate Time Series Anomaly Detection based on Pre-trained Models"** — Sun et al. — ML-for-reliability, framed as deployed AIOps
4. **"NICSDG: A Non-Intrusive Approach to Constructing Concise Service Dependency Graphs for Microservice Systems"** — Hong et al. — observability-tooling-as-reliability paper
5. **"A Systematic Methodology for Specifying the Operational Design Domain of Automated Vehicles"** — Eichenseer et al. — autonomous-systems reliability

**Pattern:** Industry Track favors (a) AIOps & cloud-reliability tooling, (b) process papers grounded in deployment realities, (c) autonomous-system reliability frameworks.

**Whitespace:** No prior ISSRE Industry Track paper has tackled **LLM-agent system reliability** as a discipline. Our paper is the first.

## 8. Reviewer Persona (synthesized from chair profiles + topic guidance)

The likely reviewer is a senior reliability engineer or AIOps researcher who:

1. Has built or operated large-scale cloud or telecom systems (ByteDance, Ericsson — both chairs are deeply industrial)
2. Is skeptical of academic re-framings — Industry Track has historically rejected papers that look like benchmark-toolkit reskins
3. Expects reliability vocabulary (MTTR, MTBF, SLO, error budget, oncall workflow, blast radius)
4. Will be hostile to a paper that does not explain how the benchmark integrates into a real reliability program
5. Will demand "what would I do Monday morning with this paper" — actionable deployment guidance, runbooks, alert thresholds, postmortem templates
6. Will check whether the contribution duplicates a recently accepted paper at an adjacent venue (AIware) — and will reject for self-plagiarism if the distinction is not airtight

## 9. Implications for Paper Design

The paper MUST:

- Frame the contribution as **a reliability-engineering process built on top of the benchmark**, not as the benchmark itself
- Provide explicit **reliability metrics**: detection latency translated to MTTR impact, FDR translated to incident-coverage SLO, false-positive rate translated to alert-fatigue impact
- Articulate the **deployment integration story**: how a team adopts this in their existing OTel + Grafana/Datadog stack, what alerts they wire, what runbooks they update, what error budgets they revise
- Include **operational lessons** absent from AIware: what we learned about agent-system reliability that surprised us; what is the right alert threshold; what is the cost of false negatives
- Cite the AIware paper explicitly and explain **what is new here**: AIware presented the benchmark and toolkit as research artifacts; this paper presents an integration pattern, reliability rubric, and field-engineering experience for production agent systems
- Stay within **6 pages including references** (IEEE Computer Society format)
