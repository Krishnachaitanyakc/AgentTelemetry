# AgentTelemetry — Additional Venue Targets (Synthesis)
> Generated: 2026-05-17
> Method: 5 parallel deep-research sub-agents, each verifying deadlines directly against the venue's official CFP page (no aggregators)
> Excluded from search: AIware 2026 (ACCEPTED), ASE 2026, ESEM 2026, MDE 2026, NeurIPS 2026 main, EMNLP 2026 Industry (deferred), IEEE Software (active draft), ICSE 2027 main (placeholder)

This is the **master index**. Each candidate links to its source report. The five source reports contain the full Verified References ritual (every URL fetched in-session, with one-sentence ground-truth summary per CLAUDE.md).

| Topic Bucket | Source Report |
|---|---|
| SE conferences / workshops / NIER / Tool Demos | [venues_se_workshops_2026-05-17.md](venues_se_workshops_2026-05-17.md) |
| Systems / MLSys / cloud / distributed | [venues_systems_mlsys_2026-05-17.md](venues_systems_mlsys_2026-05-17.md) |
| ML / AI conference workshops | [venues_ml_ai_workshops_2026-05-17.md](venues_ml_ai_workshops_2026-05-17.md) |
| Industry / practitioner CFPs | [venues_industry_2026-05-17.md](venues_industry_2026-05-17.md) |
| Journals + special issues | [venues_journals_2026-05-17.md](venues_journals_2026-05-17.md) |

---

## Filing-Window Strategy (today is 2026-05-17, EB-1A filing target: Jan 2027)

Three submission windows align with the Jan 2027 filing date:
- **Window A (now → end of June 2026)** — fast tier-1 hits and time-critical CFPs. First decisions likely Sep–Nov 2026 → cite as "Submitted" or "Accepted" in petition.
- **Window B (Jul → Oct 2026)** — main flagship cycle (ICSE 2027 satellites, FSE 2027, MSR 2027, NSDI '27, SoCC R2, USENIX Security '27, EuroSys 2027). Decisions Nov 2026 – Apr 2027.
- **Window C (Nov 2026 → Jan 2027)** — workshop CFPs from ICSE/FSE that release later, plus ICLR 2027 workshops, AAMAS 2027.

**Recommended portfolio cap:** 6–8 additional submissions on top of the 8 already in flight. More than that risks reviewer-pool collisions and dilutes per-paper quality.

---

## TIER 1 — Submit (Window A, deadline ≤ 2026-06-30)

These are the highest-EV, lowest-friction targets with verified deadlines in the next 6 weeks.

| Venue | Verified Deadline | Page Limit | Track Type | Fit | Source |
|---|---|---|---|---|---|
| **AIES 2026** | **2026-05-21 AoE** (4 days) | 10p, double-blind | AAAI/ACM full paper | Benchmark as agentic AI accountability instrument | ml_ai_workshops |
| **ICSME 2026 Tool Demo + Data Showcase** | **2026-05-24 abstract / 2026-05-28 paper** | 4p IEEE | Tool demo | Direct SDK + benchmark demo | se_workshops |
| **SREcon26 EMEA** | **2026-05-27 AoE** | Talk proposal | USENIX practitioner CFP | OTel-based agent observability talk | industry |
| **ESEM 2026 Emerging Results / Vision / Reflection** | **2026-05-29** | 4p IEEE | Short paper | Companion to your in-flight ESEM 2026 main | se_workshops |
| **KubeCon + CloudNativeCon NA 2026 (Atlanta, Nov)** | **2026-05-31** | Talk proposal | CNCF flagship CFP | OTel agent semantic-conventions story | industry |
| **AI Engineer World's Fair 2026 (SF, June)** | **2026-06-05** | Talk proposal | AI engineering CFP | Practitioner pitch on agent observability | industry |
| **Middleware 2026 Cycle 2 (Tarragona, Dec)** | **2026-06-05** | 12p ACM/IFIP, double-blind | Tier-1 systems paper | Premier middleware/observability venue | systems_mlsys |
| **HotStorage 2026** | **2026-06-05** | Workshop paper | Systems workshop | Telemetry storage angle (weak fit) | systems_mlsys |
| **NeurIPS 2026 Workshop Proposals** (you propose a workshop) | **2026-06-06** | Workshop proposal | NeurIPS organizing | Propose agent observability workshop | ml_ai_workshops |
| **ATC 2026 (Hong Kong, Nov)** | **2026-06-10 (no extensions)** | 12p Long / 6p Short, double-blind | USENIX flagship | General systems venue, short option de-risks | systems_mlsys |
| **APSEC 2026 Technical Track** | **2026-07-13** | 10p IEEE | Full paper | Asia-Pacific flagship SE | se_workshops |
| **SoCC 2026 Industry Papers Round 2** | **2026-07-14 03:59:59 PDT** | 12p Industry / 6p Vision | ACM SIGOPS+SIGMOD cloud | Longest runway among Tier 1 | systems_mlsys / industry |
| **ISSRE 2026 Industry Track (Cyprus, Oct)** | **2026-07-05 AoE** | 10p IEEE | Industry track | IEEE flagship software-reliability venue — DIRECT FIT for benchmark | ml_ai_workshops / industry |
| **IEEE Software "Edge–Cloud Continuum" SI** | **2026-07-07** | Magazine article | Special issue | CFP explicitly lists Observability and AIOps + MLOps continuum | journals |

**Allocation recommendation for Tier 1:** pick **3 of these** to submit by end-of-June 2026. My top 3 (verify with you before drafting any):
1. **Middleware 2026 Cycle 2** — Tier-1 paper credit, double-blind protects against in-flight overlap concerns
2. **ISSRE 2026 Industry Track** — IEEE flagship for reliability/fault detection; the 3,780-row benchmark is the perfect submission
3. **IEEE Software Edge-Cloud SI** — second SI alongside your existing IEEE Software draft, on a distinct topic axis

---

## TIER 2 — Submit (Window B, deadline 2026-07-01 → 2026-10-31)

These map onto the flagship Fall 2026 cycle. Decisions arrive in time for the Jan 2027 filing.

| Venue | Verified Deadline | Page Limit | Track Type | Fit | Source |
|---|---|---|---|---|---|
| **CIDR 2027 (vision)** | **2026-08-04** | 6p | Conference on Innovative Data Systems Research | Vision paper on tracing systems for agentic data | systems_mlsys |
| **AgenticAI4HPC 2026 @ SC26** | **2026-08-01** | 10p | SC-colocated workshop | OS/HPC observability for AI agents | systems_mlsys |
| **USENIX Security '27 Cycle 1** | **2026-08-25** | Full paper | USENIX flagship | Frame as agentic AI safety / threat detection | industry |
| **JSS "Software Quality Assurance for AI" SI** | **2026-08-31** | Journal article | Special issue | Best home for 3,780-row benchmark + 4 analysis modules | journals |
| **NeurIPS 2026 Workshops (multiple, non-archival)** | **est. 2026-08-29 AoE** (workshop list announced 2026-07-11) | Workshop paper | NeurIPS | Non-archival → safe parallel-submit | ml_ai_workshops |
| **EuroSys 2027 Fall (Rabat, Apr 2027)** | **2026-09-24 AoE** | Full paper | Tier-1 European systems | Flagship — iterate on Middleware/ATC reviews | systems_mlsys / industry |
| **SANER 2027** | **2026-09-25** (abstract 2026-09-21, Richmond VA Mar 2027) | Full paper | CORE A SE venue | Analysis modules + benchmark | se_workshops |
| **JSS "AI Techniques for Performance, Reliability, Sustainability" SI** | **2026-09-30** | Journal article | Special issue | Distinct framing from QA-for-AI SI | journals |
| **NSDI '27 Fall Operational Systems Track** | **2026-09-17** | Operational paper | USENIX networked systems | Strong fit if framed as production deployment study | industry |
| **FSE 2027 Research Papers (Shenzhen, Jul 2027)** | **2026-10-02 AoE** | 18p ACM acmsmall, double-blind | Flagship main track | Top SE venue | se_workshops |
| **ICSE 2027 NIER** | **2026-10-23 AoE** | 4p + 1 ref IEEE, double-anon | Flagship satellite track | Distinct from ICSE 2027 main placeholder | se_workshops |
| **ICSE 2027 SEIP** | **2026-10-23 AoE** | 10p + 2 ref IEEE, single-anon | Industrial track | Can name Meta/OpsMate; strongest fit for industrial narrative | se_workshops / industry |
| **ICSE 2027 Tool Demonstrations + Data Showcase** | **2026-10-23 AoE** | 4p IEEE single-anon | Demo/data | Purpose-built for the SDK + benchmark | se_workshops |

**Allocation recommendation for Tier 2:** pick **3–5 of these**. The ICSE 2027 satellite track triple (NIER + SEIP + Tool Demos, all same Oct 23 deadline) is a high-leverage cluster — each is a separate paper but they share materials. If you have bandwidth, do all three at ICSE plus Middleware/ATC for systems coverage.

---

## TIER 3 — Window C and Watchlist (deadlines past Oct 2026 or TBA)

| Venue | Expected Window | Track | Source |
|---|---|---|---|
| **AgenticOS 2026 (2nd) @ SOSP** | TBA, est. late-Jun / mid-Jul 2026 — POLL https://os-for-agent.github.io/ WEEKLY | SOSP workshop | systems_mlsys |
| **ICSE 2027 Workshops** | proposal **2026-06-12** / workshop papers **2026-11-27** | Two-stage | se_workshops |
| **ICSA 2027** | **2026-11-04** | SW Architecture | se_workshops |
| **AAAI 2027** | est. **2026-08** (TBD) | AAAI flagship | ml_ai_workshops |
| **AAMAS 2027** | est. **2026-10** (TBD) | Demo + workshops | ml_ai_workshops |
| **ICLR 2027 main + workshops** | main est. **2026-09–10**, workshops Feb 2027 | ICLR | ml_ai_workshops |
| **ICSE 2027 Artifact Evaluation** | **2027-01-29** | Mandatory follow-on if accepted at any ICSE 2027 track | se_workshops |
| **COLM 2026 AIA Workshop** | est. **2026-06-23** | Non-archival LLM workshop | ml_ai_workshops |
| **SREcon27 Americas** | CFP opens est. **2026-08** | USENIX practitioner | industry |
| **OSS Europe / Japan 2026** | 2026-06-24 / 2026-08-24 | Linux Foundation | industry |
| **TOSEM Agentic AI Special Collection** | UNCLEAR — contact tosem@acm.org to confirm status | Special collection | journals |

---

## Rolling Journals (no deadline pressure — submit anytime)

| Journal | Status | Fit |
|---|---|---|
| ACM TOSEM | Open | High — agentic AI SI if still open, else regular track |
| IEEE TSE | Open | High |
| Springer EMSE | Open | High — empirical SE, benchmarks fit well |
| Elsevier JSS | Open | High |
| Elsevier IST | Open | Medium |
| ACM TIST | Open | Medium |
| ACM TAAS | Open | High — autonomous & adaptive systems |
| IEEE TDSC | Open | Medium — security framing needed |
| TMLR | Open (rolling, resumed Jan 6 2026) | High — accepts experimental ML systems work |

---

## Rejected — Past Deadline (≤ 2026-05-17), preserved for transparency

| Venue | Deadline | Why considered |
|---|---|---|
| NeurIPS 2026 Main / Datasets / Position | 2026-05-06 | Already submitted main paper |
| SOSP 2026 main | 2026-04-01 | Tier-1 systems |
| OSDI 2026 | Closed | Tier-1 systems |
| MLSys 2026 main | Oct 2025 | ML systems flagship |
| SRDS 2026 | 2026-05-08 | Reliable distributed systems |
| EuroSys 2027 Spring | 2026-05-14 | Europe systems Tier-1 |
| DSN 2026 / ICDCS 2026 / DEBS 2026 | Various Q1 2026 | Distributed |
| AAAI-26 workshops | Closed | AAAI |
| KDD 2026 Cycle 2 | Closed | Applied data |
| SC26 main papers | Closed | HPC |
| ASE 2026 Industry Showcase | Closed | (Main track already in flight) |
| FSE 2026 / ICSME 2026 main | Closed | (Tool Demo still open) |
| ECSA 2026 / SSBSE 2026 / QUATIC 2026 main | Closed | SE conferences |
| ICML 2026 most workshops (FAGEN, AIWILD, AI4GOOD, SCALE, Mech Interp, CompLearn) | Apr 28 – May 11 | ICML workshops |
| ACL 2026 main + Industry | Apr 2026 | NLP |
| Onward! Essays SPLASH 2026 | 2026-05-15 (2 days before scan) | Essay venue |
| AIware 2026 ArXiv Round 2 | Closed | (Main paper already accepted) |
| Multiple IEEE Software SIs ("Engineering Agentic Systems" Jan 2026, "AIware in the FM Era" Apr 2025) | Closed | Topic-relevant; watch for follow-on calls |
| EMSE / IST AI-for-SE SIs | Nov–Dec 2025 / Jan 2026 | Watch for next-year cycles |

(Each source report contains the full rejected list with the URL that established the closed deadline.)

---

## Caveats & Open Verifications

These items require additional verification before acting on them:
- **AgenticOS 2026 @ SOSP** — CFP not yet released as of 2026-05-17; check weekly at https://os-for-agent.github.io/
- **NSDI '27 and OSDI '26 CFP pages** returned HTTP 403 during the systems_mlsys scan — re-verify before drafting
- **PACMI 2026 SOSP CFP** is login-gated on Google Sites — monitor the SOSP workshops page
- **HotInfra and HotCloud workshops** — no 2026 edition found; appear discontinued
- **Monitorama** — on hiatus; no 2026/2027 edition announced
- **TOSEM Agentic AI Special Collection** — prior `conference_targets.md` listed as "ROLLING" but se-deadlines shows a fixed Nov 1 2025 deadline (now missed). Primary CFP PDF returned 403 — email tosem@acm.org to confirm current status
- **CAIN 2027, ICPC 2027, MSR 2027, AST 2027, ESEM 2027, ECSA 2027, AIware 2027** — official CFPs not yet released as of 2026-05-17; check monthly
- **AAAI-27 and AAMAS-27 official sites** are placeholders; estimated deadlines are based on prior-year cadence
- **USENIX ;login: magazine** — writing guidelines gated behind free USENIX account
- **DL4C @ ICML 2026 (2026-05-19 AoE)** and **AIES 2026 (2026-05-21 AoE)** — extremely tight; only viable if a paper is already largely drafted

---

## How to use this index

1. Pick a Tier 1 candidate this week.
2. Read the corresponding source report (`venues_<bucket>_2026-05-17.md`) for full deadline, page-limit, blind-policy, format, and one-line fit notes.
3. Verify the CFP URL in the source report's "Verified references" block — every URL was fetched in-session, but conference pages change; spot-check the deadline against the live page before drafting.
4. Add a paper directory under `paper/<venue>YYYY/` mirroring the existing `paper/aiware2026/`, `paper/esem2026/`, etc. structure.
5. Update `paper/supporting/conference_targets.md` to reflect what was chosen.

---

## Verified-references provenance

Each of the 5 source reports ends with a "Verified references" block containing every URL fetched during that scan, with a one-sentence ground-truth summary of what the page actually says. Total URLs verified across all 5 reports:
- venues_se_workshops: 53 URLs
- venues_systems_mlsys: see file
- venues_ml_ai_workshops: see file
- venues_industry: 35+ URLs
- venues_journals: see file

No URL was cited in any report that was not actually fetched in this session.
