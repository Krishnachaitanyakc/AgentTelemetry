# Venue Research Report — ACM/IFIP Middleware 2026 (Cycle 2)

Compiled: 2026-05-17. Sources fetched and verified in-session.

## Verified References

- https://middleware-conf.github.io/2026/ — Main conference page; confirms dates (14-18 Dec 2026, Tarragona), General Chair Pedro García López (URV), PC Co-Chairs Sara Bouchenak (INSA Lyon) & Abhishek Chandra (UMN), three topic clusters (Applications / Systems / Design Principles).
- https://middleware-conf.github.io/2026/calls/call-for-research-papers/ — Official Call for Research Papers; confirms Cycle 2 abstract registration May 29 2026, full paper June 5 2026, 12-page technical content limit, ACM SIGCONF 9pt style, doubly anonymous, four-decision outcome model.
- https://middleware26c2.hotcrp.com/ — HotCRP submission portal for Cycle 2; confirms registration deadline "Friday May 29, 2026, 11:59:59 PM AoE". (Original `middleware2026c2.hotcrp.com` 302-redirects to this canonical host.)
- https://middleware-conf.github.io/2025/program/accepted-paper-list/ — Middleware 2025 accepted papers list (36 papers); used for venue calibration. No papers explicitly on distributed tracing or observability infrastructure. AI/ML middleware well represented (UnifyFL, MVTEE, Argus, FedRec, RAG caching, MoE federated). Anomaly/monitoring papers present (WasmEye, XChainWatcher, PAMO).
- https://ece.engin.umich.edu/stories/manos-kapritsos-and-collaborators-win-best-paper-award-at-middleware-2025 — Confirms Best Paper Award at Middleware 2025 went to a Kapritsos-group paper (university press release; full title not accessible due to 403, but the existence of the award is confirmed by URL/title metadata).

## 1. Deadlines (verbatim from CFP)

**Cycle 2 (the target):**
- Abstract registration: **May 29, 2026**
- Full paper: **June 5, 2026, 11:59:59 PM AoE** (firm)
- Early rejection notification: July 10, 2026
- Rebuttal: August 12-14, 2026
- Notification: August 28, 2026
- Camera-ready: October 16, 2026

Today is 2026-05-17. **T-12 days to abstract registration; T-19 days to full paper.**

## 2. Page Limit

> "Research papers and Experimentation and Deployment papers must have at most 12 pages of technical content, including text, figures, and appendices, but excluding any number of additional pages for bibliographic references."

12 pages of body + unlimited references. Appendices count against the 12.

## 3. Template

ACM SIGCONF style, font size **9pt**. The `acmart.cls` we already have for AIware 2026 works (`\documentclass[sigconf,screen]{acmart}` — must add `anonymous,review` for double-blind).

## 4. Double-Blind Requirements

> "Submissions must be doubly anonymous - authors' names must not appear on the manuscript, and authors must make a good-faith attempt to anonymize their submissions."

Specific rules:
- No author names or affiliations anywhere
- No funding-source acknowledgements
- No de-anonymizing links to authors' online content (so: cite our own GitHub repo as "anonymous"-style placeholder or refer to it indirectly during review)
- No acknowledgement of research-group members or collaborators

For AgentTelemetry-specific consequence: the PyPI link, GitHub repo, prior accepted-papers list, and Krishna's name must be stripped. Use phrases like "an open-source SDK whose anonymized repository is available to reviewers."

## 5. Topics of Interest (relevant matches)

The CFP lists topics under three umbrellas. AgentTelemetry maps directly onto:

**Middleware Applications** (strongest fit):
- "Middleware for AI and machine learning systems" ← primary topic match
- "Middleware for data science pipelines" ← secondary (analysis modules)

**Middleware Systems** (secondary fit):
- "Distributed and parallel systems" ← multi-agent topologies
- "Cloud, fog, edge computing, and data centers" ← deployment story

**Middleware Design Principles** (architectural fit):
- "Programming abstractions and paradigms for middleware" ← span kinds as an abstraction
- "Reconfigurable, adaptable, and reflective middleware" ← lazy-import, hot-swap adapters
- "Monitoring, resource management, and analysis" ← analysis modules (anomaly, cost, attribution, hallucination)
- "Methodologies and tools for middleware systems design, implementation, verification, and evaluation"

The single most legitimate framing is **"Middleware for AI and machine learning systems"** with strong design-principles support.

## 6. Acceptance Criteria

Papers receive Accept / Minor Revision / Major Revision / Reject. Reject means cannot resubmit for one full year.

The CFP emphasises (paraphrased from the surrounding CFP text):
- Novelty relative to prior middleware work
- Soundness and rigour of evaluation
- Reproducibility (artifact track is voluntary but encouraged)

## 7. Artifact Evaluation

> "The authors of accepted papers will be invited to submit supporting materials made publicly available as 'source materials' in the ACM Digital Library. This submission is voluntary but encouraged and will not influence the final decision regarding the papers. Papers that go through the Artifact Availability Evaluation process successfully and are made available in the ACM Digital Library will receive a badge printed on the papers themselves."

Artifact availability is voluntary. We should design the submission so the artifact is trivially available (AgentTelemetry is already on PyPI / GitHub), but submit anonymously and offer the de-anonymized link post-acceptance.

## 8. Organisation

- General Chair: **Pedro García López** (Universitat Rovira i Virgili, Tarragona, Spain) — serverless / edge / FaaS background
- PC Co-Chairs: **Sara Bouchenak** (INSA Lyon, France) — dependability, fault tolerance, distributed systems — and **Abhishek Chandra** (University of Minnesota, USA) — distributed systems, edge computing, resource management

The PC chairs' research orientations suggest the venue will value:
- Dependability / fault tolerance angles (Bouchenak)
- Distributed-systems rigour and resource accounting (Chandra)
- Edge/cloud/FaaS architectural framing (García López)

## 9. Reviewer-Persona Calibration (from Middleware 2025 accepted-paper survey)

Of 36 Middleware 2025 main-conference accepted papers:
- ~7 are AI/ML middleware (federated learning, model serving, RAG, MoE adaptation)
- 0 are distributed-tracing / observability infrastructure
- ~4 are anomaly / monitoring / forensic systems (WasmEye, XChainWatcher, PAMO, Tiaccoon)
- ~10 are blockchain / consensus / BFT
- ~7 are serverless / FaaS / WASM

Implication: a paper framed as **"middleware for AI/ML systems"** (with an observability lens) hits an active topic with no recent direct competition. A paper framed as "yet another distributed tracing tool" would face an uphill battle because the topic list doesn't index it directly.

Middleware-flavoured evaluation expectations distilled from the accepted list:
- Concrete throughput/latency numbers across multiple system configurations
- A scalability story (multi-process, multi-node, or stress-test driven)
- Honest comparison against named alternatives, not just an internal ablation
- A reproducibility statement, even if the artifact is not formally evaluated

## 10. Best-Paper Calibration

University of Michigan press release confirms a Manos Kapritsos co-authored paper won Best Paper at Middleware 2025. Kapritsos's research is consensus protocols / Byzantine fault tolerance / verified systems — extremely systems-deep work. The bar for the venue is "deep systems contribution with rigorous evaluation," not "tool paper." Our Middleware submission must be framed as a **middleware-architecture contribution** with rigorous evaluation, not as a benchmark or toolkit paper (those go to AIware/ASE).

## 11. Implications for the AgentTelemetry Middleware Submission

The Middleware-distinct framing must be:
1. **A middleware architecture for cross-framework AI-agent observability**, not a benchmark and not a toolkit (those papers exist).
2. The contribution is **the design and evaluation of a heterogeneous-adapter middleware layer** that reconciles three structurally different instrumentation strategies (callback-based, hook-based, monkey-patch) under a single semantic-convention overlay on top of OpenTelemetry.
3. The systems-research bar is met by: (a) per-adapter overhead measurements, (b) stress-test scalability (concurrent threads, long traces, export backpressure), (c) span correlation across async/multi-process agent topologies, (d) honest comparison against named alternatives (vanilla OTel, OTel GenAI, OpenInference).
4. The empirical evaluation uses a **subset** of the existing 3,780-row benchmark — specifically the architectural / overhead / correlation results — and explicitly **defers the fault-detection completeness story to a companion paper** so reviewers see clear scope discipline rather than a recycled benchmark.
