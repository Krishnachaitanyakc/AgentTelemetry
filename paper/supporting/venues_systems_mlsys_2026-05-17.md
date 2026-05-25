# AgentTelemetry — Systems & MLSys Venue Search (deadline > 2026-05-17)

**Compiled:** 2026-05-17
**Search scope:** Peer-reviewed Systems, ML Systems, Distributed Systems, Cloud, Dependability, and adjacent venues with submission deadlines AFTER 2026-05-17 (today). Excludes venues already in flight or accepted (AIware 2026, ASE 2026, ESEM 2026, MDE Intelligence 2026, NeurIPS 2026, IEEE Software, ICSE 2027).
**Verification posture:** Every deadline below was read directly off the venue's own CFP page (sigops.org, usenix.org, eurosys.org, acmsocc.org, mlsys.org, srds-conference.org, middleware-conf.github.io, cidrdb.org, conf.researchr.org, ornl.github.io, dimes.ws, hotstorage.org). Aggregator-only entries are explicitly tagged ESTIMATED.

AgentTelemetry positioning recap for fit-scoring:
- OpenTelemetry-based observability SDK for AI agent systems
- 9 agent-specific span kinds, 7 framework adapters, 4 analysis modules
- 3,780-row fault-injection benchmark (14 fault classes × 6 telemetry conditions × 7 frameworks × 6 LLMs)
- Real-LLM validation corpus on 13 models + multi-agent topology study
- Sits at the intersection of distributed systems observability, ML systems, and agentic AI infrastructure

---

## Verified Venues (deadline AFTER 2026-05-17)

### Tier 1 — Full conference papers, strong fit

| Venue | Verified Deadline (TZ) | Page Limit | Format / Blind | Location & Dates | Fit | One-sentence fit | Source URL |
|---|---|---|---|---|---|---|---|
| **SoCC 2026 (Round 2)** | Abstract Tue 2026-07-07; Paper **Tue 2026-07-14, 03:59:59 PDT** (HotCRP) | Full 12 pp + unlimited refs; Short/Vision 6 pp + refs; Industry 12 pp | ACM Proceedings (acmart), 9pt; dual-anonymous (Industry: company transparent, authors anonymous) | Singapore, 18–20 Nov 2026 | **VERY STRONG** | Premier ACM cloud venue with explicit Industry and Vision tracks — AgentTelemetry's framework adapters + fault benchmark fit the "operational systems for cloud-scale workloads" thesis directly. | https://acmsocc.org/2026/papers.html and https://socc26.hotcrp.com/deadlines |
| **Middleware 2026 (Cycle 2)** | Paper **2026-06-05** (firm) | Research/Experimentation 12 pp tech + unlimited refs; Big Ideas 6 pp | ACM SIGCONF 9pt; doubly anonymous | Tarragona, Spain, 14–18 Dec 2026 | **VERY STRONG** | ACM/IFIP Middleware is the canonical venue for observability/middleware infra; AgentTelemetry's 7 framework adapters are textbook middleware contributions and the Big Ideas track suits position framing. | https://middleware-conf.github.io/2026/calls/call-for-research-papers/ |
| **SRDS 2026** | Full paper **2026-05-08 → extended; check** (CFP page lists "May 1 May 8" — borderline; treat as **CLOSED**, see Rejected) | n/a | n/a | Rome, 21–25 Sep 2026 | n/a | See Rejected — deadline is on/before 2026-05-17. | https://srds-conference.org/index.php/call-for-papers/ |
| **EuroSys 2027 (Fall Round)** | Abstract Thu **2026-09-17 AoE**; Full Thu **2026-09-24 AoE** | 12 pp tech + unlimited refs | SIGPLAN LaTeX two-column, 10pt+; double-blind | Rabat, Morocco, 19–23 Apr 2027 | **VERY STRONG** | Top-tier European systems venue, accepts ML-systems and observability work in scope; Fall round gives a full summer to revise the AgentTelemetry paper. | https://2027.eurosys.org/cfp.html |
| **CIDR 2027** | All contributions **2026-08-04, 23:59 Pacific** | 6 pp incl. refs & appendix | ACM sigconf double-column; single-blind | Amsterdam, 24–27 Jan 2027 | **STRONG (vision angle)** | Biennial vision venue explicitly values "innovation, experience-based insight, and vision" — AgentTelemetry's position as "OpenTelemetry for agents" is exactly a CIDR-style vision/architecture paper. | https://www.cidrdb.org/cidr2027/cfp.html |
| **ATC 2026 (ACM SIGOPS Annual Technical Conference)** | Paper + 2-page extended abstract **2026-06-10** (no extensions) | Long 12 pp / Short 6 pp (excl. refs & appendices) | PDF A4/US-letter, 178×229mm, 10pt; double-blind | Hyatt Hotel, Shatin, Hong Kong, 16–18 Nov 2026 | **VERY STRONG** | Premier general-systems venue with both long and short paper formats; AgentTelemetry's experimental benchmark and SDK fit ATC's applied-systems profile and the short paper option de-risks the submission. | https://sigops.org/s/conferences/atc/2026/cfp.html |

### Tier 2 — Workshops at top systems venues (excellent EB-1A acceleration)

| Venue | Verified Deadline (TZ) | Page Limit | Format / Blind | Location & Dates | Fit | One-sentence fit | Source URL |
|---|---|---|---|---|---|---|---|
| **HotStorage 2026** (18th ACM Workshop on Hot Topics in Storage) | **Fri 2026-06-05 AoE** | not specified on landing page | colocated with SOSP'26, ACM in-coop USENIX | Prague, Czechia, 28–29 Sep 2026 | **MODERATE** | AgentTelemetry's trace-storage / span-volume scaling argument fits HotStorage's "hot topics" remit; tangential if the paper foregrounds agents over storage. | https://www.hotstorage.org/2026 |
| **DIMES 2026** (4th Workshop on Disruptive Memory Systems @ SOSP) | **2026-05-29** | 6 pp + refs (demos 2 pp + refs) | acmart sigplan,anonymous,10pt two-col; **double-blind** | Prague, Czechia, 29 Sep 2026 | **WEAK** | Memory-systems focus — only relevant if you reframe AgentTelemetry's memory/state-tracking spans as a memory-systems contribution; otherwise a stretch. | https://dimes.ws/cfp/ |
| **AgenticOS 2026 @ SOSP** (2nd Workshop on OS Design for AI Agents) | **TBA** (deadline not yet announced as of 2026-05-17) — ESTIMATED late-June to early-July 2026 based on Sep-29 workshop date | Vision 1–2 pp / Research up to 6 pp (excl. refs) | ACM double-column; single-blind, ≥2 reviews | Prague, Czechia, 29 Sep 2026 | **VERY STRONG** | This is the single best workshop fit in the entire workspace: a SOSP-colocated workshop explicitly chartered for "OS-level mechanisms for AI-agent workloads" including observability — submit a 6-page version of the AgentTelemetry SDK + fault benchmark. | https://os-for-agent.github.io/ |
| **PACMI 2026 @ SOSP** (5th Workshop on Practical Adoption Challenges of ML for Systems) | **TBA** (Google Sites page requires login; deadline not retrievable as of 2026-05-17) — ESTIMATED June–July 2026 | not specified | ML-for-systems workshop tradition | Prague, Czechia, 29 Sep 2026 | **STRONG** | Practical-adoption framing fits AgentTelemetry's "what works in production" benchmark perfectly; verify deadline by emailing organizers or checking the SOSP workshops page in mid-June. | https://sigops.org/s/conferences/sosp/2026/workshops.html |
| **AgenticAI4HPC 2026 @ SC26** | **2026-08-01 AoE** | Up to 10 pp incl. refs | IEEE conference format; single-blind; AD/AE artifact required | Chicago, 15–20 Nov 2026 | **STRONG** | First international workshop on agentic AI for HPC explicitly covers "Evaluation, Benchmarking & Reliability" — AgentTelemetry's 3,780-row benchmark is squarely in scope. Caveat: HPC framing may require minor re-spin. | https://ornl.github.io/events/agenticai4hpc2026/ |

### Tier 3 — Other validated venues (deadline > 2026-05-17, weaker fit)

| Venue | Verified Deadline (TZ) | Page Limit | Format / Blind | Location & Dates | Fit | One-sentence fit | Source URL |
|---|---|---|---|---|---|---|---|
| **ACSOS 2026** (Posters & Demos) | **Thu 2026-06-25** | not specified on landing | not specified | Cesena, Italy, 7–11 Sep 2026 | **MODERATE** | Autonomic-computing community is a natural EB-1A reference network; poster/demo bar is lower and the SDK itself is demoable. Main track deadline already past. | https://2026.acsos.org/ |
| **ACSOS 2026** (Artifacts) | **Mon 2026-06-29** | n/a | n/a | Cesena, Italy, 7–11 Sep 2026 | **MODERATE** | Artifact track only valid for already-accepted papers; mark as future option if AgentTelemetry accepted elsewhere in time. | https://2026.acsos.org/ |
| **ACSOS 2026** (Doctoral Symposium / Tutorial extended abstract) | **Sun 2026-07-05** | not specified | not specified | Cesena, Italy, 7–11 Sep 2026 | **MODERATE** | Tutorial track is a credible "tools-for-the-community" venue — AgentTelemetry could be pitched as a tutorial on agent observability with OpenTelemetry. | https://2026.acsos.org/ |
| **HotOS XXI (2027)** | **TBA** as of 2026-05-17 — ESTIMATED Jan 2027 based on prior cycles | typically 5 pp | ACM SIGOPS; usually single-blind | Workshop 24–26 May 2027 | **MODERATE** | Vision/provocation paper venue; "OpenTelemetry for agentic systems" is a credible HotOS provocation but competitive. Track CFP from mid-Sep 2026. | https://sigops.org/s/conferences/hotos/2027/cfp.html |
| **NSDI 2027** | CFP PDF returned 403; based on prior cycles ESTIMATED Spring round Apr 2026 (passed) and **Fall round ~Sep 2026** | ESTIMATED 12 pp double-blind (USENIX norm) | not directly retrievable today | not retrievable today | **MODERATE** | If the fall round opens, AgentTelemetry's trace-overhead measurements are NSDI-shaped; verify via https://www.usenix.org/conference/nsdi27 when accessible. | https://www.usenix.org/conference/nsdi27/call-for-papers (returned 403 today — re-verify before submitting) |
| **IJCAI-ECAI 2026** (Workshop proposals) | Workshop proposals **2026-02-06** (PASSED — but individual workshops set their own paper deadlines after this) | varies by workshop | varies | Workshops mid-Aug 2026 | **MODERATE** | If an agent-systems workshop was accepted, its paper deadline likely falls mid-May to mid-June 2026; monitor https://chairingtool.com/conferences/IJCAIECAI2026/workshops for individual workshop CFPs. | https://2026.ijcai.org/ijcai-ecai-2026-call-for-workshop-proposals/ |
| **SC26 (Supercomputing)** Research Submissions (ACM SRC, Doctoral Showcase, Posters, e-Posters) | Opens 2026-01-01; **closes 2026-08-01 AoE** | varies | varies; "All Deadlines Are 11:59 PM Anywhere on Earth" | Chicago, 15–20 Nov 2026 | **MODERATE** | Poster/e-Poster path is a low-bar venue to plant a flag at SC; main paper deadline (2026-04-08) already passed. | https://sc26.supercomputing.org/all-dates-deadlines/ |

---

## Not Yet Released (ESTIMATED cycles — track and re-verify)

| Venue | Estimated Deadline | Estimation basis | Source / Tracker |
|---|---|---|---|
| **HotOS XXI (2027)** | ESTIMATED Jan–Feb 2027 (CFP currently "TBA") | Prior HotOS cycles open CFP ~6 mo before workshop (May 2027) | https://sigops.org/s/conferences/hotos/2027/cfp.html |
| **NSDI 2027 Fall** | ESTIMATED Sep 2026 (USENIX 403 today blocks direct verification) | NSDI runs spring + fall cycles historically | https://www.usenix.org/conference/nsdi27/call-for-papers |
| **OSDI 2027** | ESTIMATED late-2026 to early-2027 | OSDI is biennial in CFP form, alternating with EuroSys; OSDI'26 deadline (Dec-2025) is already closed | https://www.usenix.org/conferences |
| **AgenticOS 2026 (2nd) @ SOSP** | ESTIMATED late-June to mid-July 2026 | Sep-29 workshop, "TBA" today on website | https://os-for-agent.github.io/ |
| **PACMI 2026 @ SOSP** | ESTIMATED June–July 2026 | Sep-29 workshop, login-gated CFP today | https://sigops.org/s/conferences/sosp/2026/workshops.html |
| **HARNESS @ SOSP 2026** (Hardening Agent Runtimes) | ESTIMATED June–July 2026 | New SOSP workshop; landing page existed but only displayed header on fetch | https://harness.mpi-dsg.org |
| **VLDB 2027** Research Track | Rolling monthly deadlines under PVLDB Vol-20 model — ESTIMATED next eligible cycle is **1st of each month** through ~Mar 2027 (the 25th of prior month for abstract) | VLDB 2027 CFP confirms rolling model | https://www.vldb.org/2027/ |
| **AAAI 2027** Workshops | ESTIMATED workshop proposals due ~Aug 2026; individual workshop paper deadlines Oct–Nov 2026 | AAAI annual cycle | https://aaai.org/conference/aaai/ |
| **AAAI-26** (Jan 2026 workshops) | PASSED — workshops occurred 26–27 Jan 2026 (LaMAS, AIR-FM, FAST, Agentic AI Benchmarks for Enterprise Tasks all already held) | Confirmed | https://aaai.org/conference/aaai/aaai-26/workshops-program/ |
| **CoNEXT 2026** | Could not retrieve CFP today (empty response) — ESTIMATED full paper June–Jul 2026 based on prior cycle | Networking community standard cycle | https://conferences.sigcomm.org/co-next/2026/ |

---

## Rejected (deadline on/before 2026-05-17)

| Venue | Verified Deadline | Why rejected |
|---|---|---|
| **EuroSys 2027 Spring Round** | Full paper **Thu 2026-05-14 AoE** | 3 days before today |
| **SRDS 2026** | Full paper **2026-05-08** (extended to "May 8th") AoE | 9 days before today |
| **ACM/IEEE SEC 2026** (Symposium on Edge Computing) — main paper | **2026-05-08** (extended) | 9 days before today |
| **SOSP 2026** main track | Abstract **2026-03-26 AoE** / Paper **2026-04-01 AoE** | Over 6 weeks before today |
| **OSDI 2026** | Closed (HotCRP "deadline has passed"; 681 submissions → 136 accepted) | Closed |
| **MLSys 2026** | **2025-10-30 20:00 UTC** | Long past |
| **DSN 2026** | Paper **2025-12-04**, Final Notification 2026-03-19 | Long past |
| **ICDCS 2026** Research | **2026-01-21 AoE** | Long past |
| **DEBS 2026** (all tracks: research, industry, posters, doctoral, AI/Serverless workshop) | latest **2026-05-06** (AI & Serverless workshop) | Past |
| **IEEE CLOUD 2026** | Extended **2026-03-22** | Past |
| **AAAI-26 Workshops** | Workshops held 26–27 Jan 2026 | Past |
| **HotCloudPerf 2026** | **2026-01-30 AoE** | Past |
| **Cloud Intelligence / AIOps Workshop 2026** | **2026-02-08 AoE** | Past |
| **AgenticOS 2026 @ ASPLOS** (1st edition) | Workshop held 22–23 Mar 2026 | Past — but watch the 2nd edition at SOSP 2026 (Tier 2 above) |
| **AAAI 2026 (main)** | Past | Past |
| **KDD 2026 Cycle 2** | Paper **2026-02-08 AoE** | Past |
| **ECMLPKDD 2026 ADS** | Paper **2026-03-12 AoE** | Past |
| **SC26 main Papers** | Abstract **2026-04-01**, Paper **2026-04-08 AoE** (no extensions) | Past |
| **SC26 Workshop CFPs** | Submissions closed **2026-02-16** (notif 2026-03-18) | Past — but individual workshop paper CFPs (e.g., AgenticAI4HPC, FTXS) are open separately |
| **ICSE 2027 Research Track** | not rejected, but Abstract **2026-06-23 AoE** / Paper **2026-06-30 AoE** — user already has ICSE 2027 marked as placeholder, so flagged but not re-recommended | Already in user's portfolio |
| **ASE 2026 Industry Showcase** | Paper **2026-04-30 AoE** | Past |
| **PaPoC 2026 @ EuroSys** | held with EuroSys 2026 (Apr 27–30 2026); the 2027 edition's CFP not yet released | Past for 2026 |
| **HotInfra** | No 2026 edition found; series may be paused (last edition HotInfra 2024) | Inactive — do not pursue |
| **HotCloud** | No 2026 USENIX HotCloud edition found; series appears discontinued post-2020 | Inactive — do not pursue |

---

## Top 5 recommendations (ranked for AgentTelemetry + EB-1A)

1. **AgenticOS 2026 (2nd) @ SOSP 2026** — perfect topical fit (OS-level observability for AI agents), SOSP-colocated lends prestige; deadline TBA but ESTIMATED late-June to mid-July 2026. **ACTION:** poll https://os-for-agent.github.io/ weekly starting now; submit 6-page research paper.
2. **Middleware 2026 Cycle 2** — full ACM/IFIP conference paper, doubly anonymous, 12 pp; deadline **2026-06-05 firm**. Premier middleware/observability venue. **ACTION:** prioritise as the highest-prestige paper-track submission given the four-week runway.
3. **ATC 2026** — premier general-systems venue, both 12pp long and 6pp short options, double-blind, deadline **2026-06-10**. Strong applied-systems fit and short-paper option de-risks. **ACTION:** decide long vs. short by 2026-05-25.
4. **SoCC 2026 Round 2** — ACM SIGOPS+SIGMOD-sponsored cloud venue with explicit Industry and Vision tracks (6 or 12 pp). Deadline **2026-07-14 PDT** gives the longest runway among Tier 1. **ACTION:** earmark for the most polished version after Middleware and ATC submissions land.
5. **EuroSys 2027 Fall Round** — top-tier European systems conference; deadline **2026-09-24 AoE** allows a full summer of revisions and post-review-feedback iteration from the earlier submissions. **ACTION:** treat as the flagship Tier-1 target for the strongest version of the paper after iterating through Middleware/ATC/SoCC reviewer feedback.

Additional high-leverage shots: **CIDR 2027 (vision paper, 2026-08-04)** for a "Foundations of Agent Observability" 6-page vision piece; **AgenticAI4HPC 2026 @ SC26 (2026-08-01)** for an HPC-flavoured retelling of the fault benchmark; **HotStorage 2026 (2026-06-05)** if trace storage is reframed as the headline contribution.

---

## Verified references

- https://acmsocc.org/2026/papers.html — SoCC 2026 official CFP page: dual-anonymous reviewing, Singapore 18–20 Nov 2026; Round 1 abstract 6 Feb / paper 13 Feb (past); Round 2 abstract 7 Jul / paper 14 Jul 2026 AoE; page limits 12 pp full / 6 pp short / 6 pp vision / 12 pp industry, 9pt acmart.
- https://socc26.hotcrp.com/deadlines — SoCC 2026 HotCRP deadlines page: Round 2 Registration Tue Jul 7 2026 03:59:59 PDT; Round 2 Submission Tue Jul 14 2026 03:59:59 PDT.
- https://middleware-conf.github.io/2026/calls/call-for-research-papers/ — Middleware 2026 research papers CFP: two cycles, Cycle 1 12 Dec 2025 (past), Cycle 2 5 Jun 2026 (firm); 12pp tech + unlimited refs (Big Ideas 6pp); ACM SIGCONF 9pt; doubly anonymous.
- https://middleware-conf.github.io/2026/ — Middleware 2026 home: Tarragona 14–18 Dec 2026; single-track program plus industrial track, posters, demos, doctoral symposium, tutorials, workshops.
- https://sigops.org/s/conferences/atc/2026/cfp.html — ATC 2026 official CFP: paper + 2pp extended abstract due Jun 10 2026 (no extensions); Long ≤12pp / Short ≤6pp (excl. refs/appendices); A4 or US letter 178x229mm two-col 10pt; double-blind; Hong Kong 16–18 Nov 2026.
- https://2027.eurosys.org/cfp.html — EuroSys 2027 official CFP: double-blind, 12pp tech + unlimited refs; Spring abstract 7 May 2026 / paper 14 May 2026 (past); Fall abstract 17 Sep 2026 / paper 24 Sep 2026; SIGPLAN LaTeX 10pt+; Rabat 19–23 Apr 2027.
- https://www.cidrdb.org/cidr2027/cfp.html — CIDR 2027 official CFP: all contributions due 4 Aug 2026 23:59 Pacific; max 6 pp incl. refs/appendix; ACM sigconf double-column; single-blind; Amsterdam 24–27 Jan 2027.
- https://www.hotstorage.org/2026 — HotStorage 2026 landing: submission deadline Fri 5 Jun 2026 AoE; co-located with SOSP'26 in Prague 28–29 Sep 2026; sponsored by ACM in coop with USENIX.
- https://dimes.ws/cfp/ — DIMES 2026 CFP: deadline 29 May 2026; 6pp + refs (demos 2pp + refs); acmart sigplan,anonymous,10pt two-col; double-blind; Prague 29 Sep 2026.
- https://os-for-agent.github.io/ — AgenticOS 2026 (2nd edition @ SOSP) landing: scope includes observability and OS-level mechanisms for agent workloads; tracks 1–2 pp vision and ≤6 pp research (excl. refs); ACM double-column; single-blind ≥2 reviews; Prague 29 Sep 2026; submission deadline currently TBA.
- https://easychair.org/cfp/AgenticOS2026 — AgenticOS 2026 EasyChair CFP (1st edition): held 22–23 Mar 2026 co-located with ASPLOS — past; informs the format expected for the 2nd edition.
- https://ornl.github.io/events/agenticai4hpc2026/ — AgenticAI4HPC 2026 CFP: submission deadline 1 Aug 2026 AoE; up to 10pp incl. refs; IEEE conf format; single-blind; AD/AE artifact mandatory; co-located with SC26 in Chicago 15–20 Nov 2026.
- https://2026.acsos.org/ — ACSOS 2026 official page: main track deadline past; Posters & Demos 25 Jun 2026, Artifacts 29 Jun 2026, Doctoral Symposium 5 Jul 2026, Tutorials proposals 5 Jun 2026 / abstracts 5 Jul 2026; Cesena, Italy 7–11 Sep 2026.
- https://sigops.org/s/conferences/sosp/2026/cfp.html — SOSP 2026 official CFP: abstract 26 Mar 2026 AoE / paper 1 Apr 2026 AoE (past); 12pp + unlimited refs; double-blind; Prague conference 30 Sep 2026, workshops 29 Sep 2026.
- https://sigops.org/s/conferences/sosp/2026/workshops.html — SOSP 2026 workshops page: 13 colocated workshops on 29 Sep 2026 including AgenticOS, HARNESS, PACMI, HotStorage, DIMES, BigMem, eBPF, PLOS, qStack, SysteMPC, Sys4Health, DC²-FPGA, SysDW.
- https://srds-conference.org/index.php/call-for-papers/ — SRDS 2026 official CFP: deadline 8 May 2026 AoE (past); 10pp excl. refs IEEE two-col; double-blind; Tool Papers + Practical Experience Reports tracks; Rome 21–25 Sep 2026.
- https://dsn2026.github.io/cfpapers.html — DSN 2026 CFP: abstract 27 Nov 2025, paper 4 Dec 2025 (past); 11pp regular / 7pp PER / 7pp Tool Description; IEEE 2-col 10pt; double-blind.
- https://icdcs2026.icdcs.org/ — ICDCS 2026: research papers 21 Jan 2026 AoE (past); workshops 23 Apr 2026 (past); posters/demos 24 Apr 2026 (past); Seoul 22–25 Jun 2026.
- https://2026.debs.org/ — DEBS 2026: research papers 1 Mar 2026 AoE, industry 27 Mar 2026, posters/demos 24 Apr 2026, doctoral 22 Apr 2026, AI&Serverless workshop 6 May 2026 — all past.
- https://services.conferences.computer.org/2026/cloud/cloud-call-for-papers/ — IEEE CLOUD 2026: paper deadline extended firm 22 Mar 2026; Sydney 13–18 Jul 2026 — past.
- https://hotcloudperf.spec.org/ — HotCloudPerf 2026: paper deadline extended firm 30 Jan 2026 AoE; Florence colocated with ICPE 2026 5 May 2026 — past.
- https://cloudintelligenceworkshop.org/CFP.html — Cloud Intelligence/AIOps Workshop 2026: deadline 8 Feb 2026 AoE; held 22 Mar 2026 — past.
- https://kdd2026.kdd.org/research-track-call-for-papers/ — KDD 2026 Research Track Cycle 2: paper 8 Feb 2026 AoE (past); Jeju 9–13 Aug 2026.
- https://ecmlpkdd.org/2026/submissions-ads-track/ — ECMLPKDD 2026 ADS: paper 12 Mar 2026 23:59 AoE; Springer LNCS 16pp; double-blind — past.
- https://www.vldb.org/2027/ — VLDB 2027 home: Athens 23–27 Aug 2027; rolling Research Track abstracts due 25th of month prior to full paper deadline; exact monthly deadlines on the conference's Important Dates page (not retrieved today).
- https://icde2027.github.io/submission-guidelines.html — ICDE 2027 submission guidelines: Copenhagen 17–21 May 2027; 12pp excl. refs; single-blind; max 5 papers per author; specific round dates not posted on this page yet.
- https://conf.researchr.org/track/icse-2027/icse-2027-research-track — ICSE 2027 Research Track: Dublin 25 Apr – 1 May 2027; abstract 23 Jun 2026 / paper 30 Jun 2026 AoE; 10pp + 2pp refs; double-anonymous (already in user's portfolio).
- https://conf.researchr.org/track/ase-2026/ase-2026-industry-showcase — ASE 2026 Industry Showcase: abstract 23 Apr 2026 / paper 30 Apr 2026 AoE (past); 10pp+2pp long, 5pp+1pp short; not double-blind.
- https://sc26.supercomputing.org/all-dates-deadlines/ — SC26 dates page: Papers Abstract 1 Apr 2026 / Paper 8 Apr 2026 (past, no extensions); Workshops CFP submissions closed 16 Feb 2026; Research Submissions (ACM SRC, Doctoral Showcase, Posters, e-Posters) open 1 Jan 2026 / close 1 Aug 2026 AoE; SC26 program 15–20 Nov 2026 Chicago.
- https://sc26.supercomputing.org/2026/04/a-gold-standard-sc26-welcomes-50-workshops-to-chicago/ — SC26 50 accepted workshops including AgenticAI4HPC, FTXS (Faults, Trustworthiness, eXplainability for AI Systems at Scale), Trillion Parameter Workshop, ProTools, HPC-ODA, PMBS26, AI4S.
- https://sigops.org/s/conferences/hotos/2027/cfp.html — HotOS XXI 2027 CFP: paper/panel proposal deadline currently "TBA"; workshop dates 24–26 May 2027.
- https://www.usenix.org/conference/nsdi27/call-for-papers — NSDI 2027 CFP page: returned HTTP 403 today, cannot directly verify; re-attempt later or use USENIX RSS.
- https://www.usenix.org/conference/osdi26/call-for-papers — OSDI 2026 CFP: returned HTTP 403 today.
- https://osdi26.usenix.hotcrp.com/ — OSDI 2026 HotCRP: "The deadline for registering submissions has passed"; 681 submissions → 136 accepted.
- https://2026.ijcai.org/ijcai-ecai-2026-call-for-workshop-proposals/ — IJCAI-ECAI 2026 workshops: proposals due 6 Feb 2026 (past); individual workshop CFPs and deadlines published separately; agents-related workshops likely but not enumerable from this page.
- https://aaai.org/conference/aaai/aaai-26/workshops-program/ — AAAI-26 accepted workshops list with date/room (workshops held 26–27 Jan 2026 — past); includes W8 Agentic AI Benchmarks for Enterprise Tasks, W36 LaMAS, W45 FAST, W51 Trust/Control Agentic AI, W15 AIR-FM.
- https://conf.researchr.org/track/fse-2026/fse-2026-workshops — FSE 2026 workshops list (proposals submitted by Oct 16 2025, notif Nov 13 2025); accepted workshops include LLMSC, LLMTrust, SEE-AIT, HumanAISE, DevOpsSustain — paper submission deadlines on individual workshop sites (not retrieved today).
- https://acm-ieee-sec.org/2026/ — ACM/IEEE SEC 2026: abstract extended to 8 May 2026 / paper extended to 8 May 2026 (past); Oct 13–16 2026.
- https://mlsys.org/Conferences/2026/CallForPapers — MLSys 2026 CFP: deadline 30 Oct 2025 20:00 UTC (long past); confirms NEW industrial track at MLSys.

End of document.
