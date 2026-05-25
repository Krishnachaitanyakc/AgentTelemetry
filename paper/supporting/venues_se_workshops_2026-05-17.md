# AgentTelemetry — SE Venue Submission Map (cut-off 2026-05-17)

**Compiled:** 2026-05-17
**Cut-off rule:** Only venues whose VERIFIED official submission deadline is **strictly after 2026-05-17** are recommended.
**Already in flight (excluded from recommendations):** AIware 2026 (ACCEPTED), ASE 2026 (submitted), ESEM 2026 (submitted May 7), MDE Intelligence 2026, NeurIPS 2026, EMNLP 2026 Industry (deferred), IEEE Software special issue, ICSE 2027 main research (placeholder).
**AgentTelemetry profile:** OpenTelemetry-based observability SDK for AI agents — 9 agent-specific span kinds, 7 framework adapters, 4 analysis modules, 3,780-row fault-injection benchmark (14 fault classes × 6 telemetry conditions × 7 frameworks × 6 mocked LLMs). Empirical SE / LLM-agent observability / fault detection / benchmarking.

**Search methodology:** For every venue below, the official conference page (`conf.researchr.org` track page, conference's own `.org` site, or workshop GitHub Pages site) was fetched with WebFetch. No deadline below comes from a secondary aggregator (no se-deadlines.github.io, wikicfp, or rankings sites were used as the source of truth for a deadline — they were used only to discover candidate venues, after which the official CFP was read).

---

## Verified Venues — Deadline AFTER 2026-05-17

Sorted by deadline (soonest first). Each row's deadline was read directly from the venue's official CFP page (URL in last column).

| # | Venue | Verified Deadline | Page Limit | Format | Location / Conf. Dates | Fit | One-sentence fit | Source URL |
|---|-------|-------------------|------------|--------|------------------------|-----|------------------|------------|
| 1 | **ESEM 2026 — Emerging Results, Vision & Reflection (ERVR)** | Fri 29 May 2026, 23:59:59 AoE | not stated on HotCRP; ESEM ERVR historically 4 pp + 1 ref | ACM | München, Germany; Sun 4 – Fri 9 Oct 2026 | **HIGH** | Vision/reflection slot fits a "what observability ought to look like for LLM agents" framing distinct from the empirical ESEM Technical submission already in flight. | https://esem26-ervr.hotcrp.com/ |
| 2 | **QUATIC 2026 SEDES (PhD Symposium)** | Sun 31 May 2026 (AoE) | n/a (PhD position paper) | LNCS (Springer) | Genoa, Italy; 9–11 Sep 2026 | LOW–MEDIUM | Only PhD-track relevance; main QUATIC deadline (May 15) is past. | https://easychair.org/cfp/QUATIC2026 ; https://2026.quatic.org/important-dates |
| 3 | **SCAM 2026 — Research Track** | Thu 11 Jun 2026 | up to 12 pp | IEEE two-col (double-blind) | Benevento, Italy (co-located ICSME 2026); 14–15 Sep 2026 | **MEDIUM** | Fits a focused "source-code-level instrumentation / decision-attribution tooling" framing of the SDK; not a benchmark venue. | https://conf.researchr.org/home/scam-2026 |
| 4 | **SCAM 2026 — Engineering Track** | Thu 18 Jun 2026 | up to 10 pp | IEEE two-col (single-blind) | Benevento, Italy; 14–15 Sep 2026 | **MEDIUM–HIGH** | Tool/engineering experience report for the OpenTelemetry SDK plus framework adapters is a textbook SCAM Engineering submission. | https://conf.researchr.org/home/scam-2026 |
| 5 | **ICSME 2026 — Doctoral Symposium** | Wed 3 Jun 2026 (per ICSME dates page) | n/a (PhD) | IEEE | Benevento, Italy; 14–18 Sep 2026 | LOW | Only useful if a co-author is doctoral; not core fit. | https://conf.researchr.org/dates/icsme-2026 |
| 6 | **ICSME 2026 — Journal-First Track** | Sat 20 Jun 2026 (dates page) / Sat 6 Jun 2026 (track page) | n/a (companion 2pp) | IEEE | Benevento, Italy; 14–18 Sep 2026 | MEDIUM | Path to present an EMSE/JSS-published AgentTelemetry paper if one is accepted by 2026-05-30 (eligibility window). | https://conf.researchr.org/track/icsme-2026/icsme-2026-journal-first ; https://conf.researchr.org/dates/icsme-2026 |
| 7 | **MODELS 2026 — Tutorials** | Fri 19 Jun 2026 | n/a (proposal) | — | Málaga, Spain; 4–9 Oct 2026 | LOW | Only viable if proposing a tutorial on agent observability. | https://conf.researchr.org/home/models-2026 |
| 8 | **MODELS 2026 — NIER (abstract)** | Wed 24 Jun 2026 (abstract) | TBD | ACM | Málaga, Spain; 4–9 Oct 2026 | LOW–MEDIUM | NIER vision-style positioning paper; fit weaker than CAIN/AIware venues. | https://conf.researchr.org/home/models-2026 |
| 9 | **ASE 2026 — Doctoral Symposium** | Tue 30 Jun 2026 (AoE) | per track CFP | ACM | Munich, Germany; 12–16 Oct 2026 | LOW | Only useful for a doctoral co-author. | https://conf.researchr.org/track/ase-2026/ase-2026-doctoral-symposium |
| 10 | **MODELS 2026 — NIER (full paper)** | Wed 1 Jul 2026 | NIER short paper | ACM | Málaga, Spain; 4–9 Oct 2026 | LOW–MEDIUM | NIER follow-up to the abstract. | https://conf.researchr.org/home/models-2026 |
| 11 | **ESEM 2026 — Journal-First Track** | Wed 1 Jul 2026 | n/a (companion) | ACM | München, Germany; 4–9 Oct 2026 | MEDIUM | If an EMSE/JSS version of AgentTelemetry is accepted, ESEM J1 is a clean satellite venue distinct from the in-flight ESEM technical submission. | https://conf.researchr.org/home/esem-2026 |
| 12 | **ASE 2026 — Journal-First Track** | Mon 6 Jul 2026 (AoE, UTC-12h) | n/a (companion) | ACM | Munich, Germany; 12–16 Oct 2026 | MEDIUM | Same logic as ESEM J1 — distinct from ASE submitted main track. | https://conf.researchr.org/track/ase-2026/ase-2026-journal-first |
| 13 | **APSEC 2026 — Technical Track (abstract)** | Mon 6 Jul 2026 | not stated on home page | — | Bali, Indonesia; 7–10 Dec 2026 | **MEDIUM–HIGH** | APSEC is a CORE B venue with consistent acceptance of empirical/observability papers; abstract registration gives a low-friction entry. | https://conf.researchr.org/home/apsec-2026 |
| 14 | **ICSE 2027 — Industry Challenge proposal** | Fri 10 Jul 2026 | n/a (challenge proposal) | IEEE | Dublin, Ireland; 25 Apr – 1 May 2027 | LOW | Proposers' track — only relevant if Meta proposes the agent-observability challenge problem itself. | https://conf.researchr.org/dates/icse-2027 |
| 15 | **APSEC 2026 — Technical Track (full paper)** | Mon 13 Jul 2026 | not stated; APSEC norm: 10 pp IEEE | IEEE typical | Bali, Indonesia; 7–10 Dec 2026 | **HIGH** | Strong empirical/benchmark fit; APSEC has historically welcomed observability and benchmarking contributions. | https://conf.researchr.org/home/apsec-2026 |
| 16 | **APSEC 2026 — ERA (Early Research Achievements)** | Mon 3 Aug 2026 | typically 4 pp | IEEE typical | Bali, Indonesia; 7–10 Dec 2026 | MEDIUM | ERA-style positioning piece on agent telemetry conventions. | https://conf.researchr.org/home/apsec-2026 |
| 17 | **APSEC 2026 — SEIP (SE in Practice)** | Mon 17 Aug 2026 | typically 10 pp | IEEE typical | Bali, Indonesia; 7–10 Dec 2026 | **HIGH** | Industry-deployment SEIP narrative for the AgentTelemetry SDK plus its 7 framework adapters. | https://conf.researchr.org/home/apsec-2026 |
| 18 | **MSR 2026 — Registered Reports (Stage 2 / EMSE full paper)** | Mon 28 Sep 2026 | EMSE-style | EMSE journal | Rio de Janeiro, Brazil (conf already held Apr 2026) — Stage 2 journal pipeline | LOW (only if RR Stage-1 accepted) | Only applies if a Stage-1 proposal was already accepted; AgentTelemetry was not in the Stage-1 cycle. | https://conf.researchr.org/dates/msr-2026 |
| 19 | **FSE 2027 — Research Papers (main)** | Fri 2 Oct 2026, 23:59:59 AoE (UTC-12h) | 18 pp + 4 pp refs | ACM `acmsmall` (double-anonymous, "heavy") | Shenzhen, China; 12–16 Jul 2027 | **HIGH** | FSE main track is a flagship venue for empirical SE / observability tooling. Strong EB-1A signal; high bar. | https://conf.researchr.org/track/fse-2027/fse-2027-papers |
| 20 | **ICSE 2027 — SEIP** | Fri 23 Oct 2026 (AoE) | 10 pp + 2 pp refs | IEEE conference proc (NOT double-anonymous) | Dublin, Ireland; 25 Apr – 1 May 2027 | **HIGH** | SEIP rewards industrial-deployment narratives — AgentTelemetry's SDK + adapters + fault benchmark is a model SEIP fit. | https://conf.researchr.org/track/icse-2027/icse-2027-seip |
| 21 | **ICSE 2027 — NIER (New Ideas)** | Fri 23 Oct 2026, 23:59:59 AoE (UTC-12h) | 4 pp + 1 pp refs | IEEE (double-anonymous) | Dublin, Ireland; 25 Apr – 1 May 2027 | **HIGH** | NIER is an ideal 4-page positioning venue ("agent telemetry as a first-class SE concern") that's separate from the ICSE 2027 main-track placeholder. | https://conf.researchr.org/track/icse-2027/icse-2027-new-ideas-and-emerging-results--nier- |
| 22 | **ICSE 2027 — Tool Demonstrations & Data Showcase** | Fri 23 Oct 2026 | 4 pp incl. all refs | IEEE conference (single-anonymous) | Dublin, Ireland; 25 Apr – 1 May 2027 | **HIGH** | Dedicated artefact/demo venue — the SDK + 7 adapters + 3,780-row benchmark dataset is exactly what this track exists for. | https://conf.researchr.org/track/icse-2027/icse-2027-demonstrations |
| 23 | **ICSE 2027 — SEET** | Fri 23 Oct 2026 (per dates page) | n/a (SEET-specific) | IEEE | Dublin, Ireland; 25 Apr – 1 May 2027 | LOW | Only if framed as pedagogy/training around agent observability — not core fit. | https://conf.researchr.org/dates/icse-2027 |
| 24 | **ICSE 2027 — SEIS** | Fri 23 Oct 2026, 23:59 AoE/UTC-12 | 10 pp full / 4 pp short + 2 pp refs | IEEE (double-anonymous) | Dublin, Ireland; 25 Apr – 1 May 2027 | LOW | Societal-impact framing of AI agent observability is plausible but weaker than SEIP/NIER/Demo. | https://conf.researchr.org/track/icse-2027/icse-2027-seis |
| 25 | **ICSE 2027 — Journal-First** | Fri 30 Oct 2026, 23:59 AoE (UTC-12) | 2-page proposal | ACM template | Dublin, Ireland; 25 Apr – 1 May 2027 | MEDIUM | If an EMSE/TSE version of AgentTelemetry is accepted in the eligibility window, ICSE J1 is a high-prestige presentation slot. | https://conf.researchr.org/track/icse-2027/icse-2027-journal-first |
| 26 | **ICSA 2027 — Research Papers** | Wed 4 Nov 2026, 23:59 AoE (UTC-12h) | 10 pp + 2 pp refs | IEEE (double-anonymous) | TBD; dates TBA | **HIGH** | ICSA explicitly welcomes architecture/observability work; AgentTelemetry's 9-span-kind architecture is a clean ICSA contribution. | https://conf.researchr.org/track/icsa-2027/icsa-2027-papers |
| 27 | **ICSE 2027 — Industry Challenge solution papers** | Fri 13 Nov 2026 | 5–10 pp (+1 camera) + 2 pp refs | IEEE (anonymous) | Dublin, Ireland; 25 Apr – 1 May 2027 | LOW–MEDIUM | Only useful if a relevant challenge problem is accepted in the Jul 10 proposer round. | https://conf.researchr.org/track/icse-2027/icse-2027-industry-challenge |
| 28 | **ICSE 2027 — Student Research Competition (SRC)** | Fri 13 Nov 2026 | 2 pp / 800 words | ACM SRC | Dublin, Ireland; 25 Apr – 1 May 2027 | LOW | Only relevant if a student co-author is enrolled and lead. | https://conf.researchr.org/track/icse-2027/icse-2027-src |
| 29 | **ICSE 2027 workshops — uniform paper deadline** | Fri 27 Nov 2026 (workshop-paper deadline announced in workshop call) | per-workshop | per-workshop | Dublin, Ireland; 25 Apr – 1 May 2027 | **HIGH** | Two-stage path: workshop **proposal** due Fri 12 Jun 2026 (organize an Agent Telemetry / Observability workshop), then submit workshop papers by 27 Nov 2026. Many AgentTelemetry-relevant ICSE 2026 workshops (AGENT, BoatSE, LLM4Code, DeepTest) are expected to recur — submit papers once their 2027 CFPs go live. | https://conf.researchr.org/track/icse-2027/icse-2027-workshops |
| 30 | **ICSE 2027 — Artifact Evaluation** | Thu 29 Jan 2027 (registration Fri 22 Jan 2027) | 2-page abstract + artifact | IEEE | Dublin, Ireland; 25 Apr – 1 May 2027 | **HIGH** | Mandatory follow-on if any ICSE 2027 paper is accepted — the SDK + 3,780-row benchmark are strong Reusable + Available + Results Reproduced candidates. | https://conf.researchr.org/track/icse-2027/icse-2027-artifact-evaluation |
| 31 | **SANER 2027 — Research Track** | Fri 25 Sep 2026 (abstract Mon 21 Sep 2026) | not stated on home; SANER norm: 11 pp + refs | IEEE typical | Richmond, Virginia, USA (VCU); 9–12 Mar 2027 | **HIGH** | SANER's analysis/evolution scope is a strong fit for agent-telemetry tooling and fault-pattern mining over the 3,780-row benchmark. | https://conf.researchr.org/home/saner-2027 |

### High-priority subset (do these first)

The five rows below are the strongest combination of fit + prestige + open deadline:

1. **ICSE 2027 Tool Demonstrations & Data Showcase** (Fri 23 Oct 2026) — purpose-built for the SDK + benchmark.
2. **ICSE 2027 NIER** (Fri 23 Oct 2026) — 4-page positioning paper, flagship venue, EB-1A signal.
3. **ICSE 2027 SEIP** (Fri 23 Oct 2026) — industrial-deployment narrative, single-anonymous (deployment story OK).
4. **FSE 2027 Research Papers** (Fri 2 Oct 2026) — flagship main-track shot; pair with NIER for risk hedging.
5. **SANER 2027 Research Track** (Fri 25 Sep 2026) — strong CORE A venue specifically scoped to analysis/evolution tooling.

Strong secondaries: **ICSA 2027** (Nov 4), **APSEC 2026 Technical/SEIP** (Jul 13 / Aug 17), **SCAM 2026 Engineering** (Jun 18), **ESEM 2026 ERVR** (May 29).

---

## CFP Not Yet Released — Estimated Deadlines

For venues whose 2027/2026 CFP is not yet on the venue's official site, the deadline is **ESTIMATED** from prior-year patterns and must be re-verified once the CFP is published.

| Venue | Estimated Deadline (re-verify) | Prior-year basis | Location/Date (verified or expected) |
|-------|-------------------------------|------------------|--------------------------------------|
| **CAIN 2027** | ESTIMATED late-Oct / early-Nov 2026 | CAIN co-locates with ICSE; CAIN 2026 sat at ICSE 2026 (Rio, Apr 2026). Series page does not yet list CAIN 2027. | Expected Dublin (with ICSE 2027), Apr 2027 — UNVERIFIED. (https://conf.researchr.org/series/cain) |
| **ICPC 2027** | ESTIMATED early-Dec 2026 (research) / early-Feb 2027 (ERA/Tool Demo) | ICPC 2026 research deadline pattern; conf.researchr.org has no ICPC 2027 home page yet. | Expected Dublin (with ICSE 2027), Apr 2027 — UNVERIFIED. (https://conf.researchr.org/home/icpc-2026) |
| **MSR 2027** | ESTIMATED mid-Oct 2026 (technical) | MSR 2026 technical deadline was Oct 23 2025; MSR co-locates with ICSE. No MSR 2027 home page yet beyond placeholder. | Expected Dublin (with ICSE 2027), Apr 2027 — UNVERIFIED. (http://www.msrconf.org/) |
| **AST 2027** | ESTIMATED Dec 2026 | AST is an ICSE-colocated workshop; no AST 2027 page found at conf.researchr.org as of 2026-05-17. | Expected Dublin (with ICSE 2027), Apr 2027 — UNVERIFIED. |
| **SEAMS 2027** | ESTIMATED early-Nov 2026 | SEAMS 2027 home page is up but lists no submission dates. | VERIFIED 26–27 Apr 2027, Dublin (CCD), co-located ICSE 2027. (https://conf.researchr.org/home/seams-2027) |
| **ICST 2027** | ESTIMATED Sep–Oct 2026 (research) | ICST 2026 was 18–22 May 2026 in Daejeon; ICST 2027 venue not yet announced. | TBA. (https://icstconference.github.io/) |
| **COMPSAC 2027** | ESTIMATED Feb 2027 | COMPSAC 2026 symposium deadline was Feb 20 2026 (extended). COMPSAC 2027 not yet posted. | TBA. (https://ieeecompsac.computer.org/) |
| **ESEM 2027** | ESTIMATED Apr–May 2027 | ESEM 2026 technical deadline was May 18 2026; series page lists no 2027 host yet. | TBA. (https://conf.researchr.org/series/esem) |
| **ECSA 2027** | ESTIMATED Mar–Apr 2027 | ECSA 2026 research deadline was Mar 27 2026; ECSA 2027 not yet announced. | TBA. (https://conf.researchr.org/home/ecsa-2026) |
| **AIware 2027** | ESTIMATED Mar–May 2027 | AIware 2026 (already ACCEPTED) is the 3rd edition. No AIware 2027 listing exists yet on the series page. | TBA. (https://conf.researchr.org/series/aiware) |
| **ICSE 2027 individual workshops (FORGE / LLM4Code / AGENT / BoatSE 2027 editions)** | ESTIMATED Nov 27, 2026 (per uniform ICSE 2027 workshop-paper deadline) | ICSE 2027 workshop **proposal** deadline Fri 12 Jun 2026; individual workshop CFPs publish later. | Dublin, with ICSE 2027. VERIFIED uniform paper deadline 27 Nov 2026. (https://conf.researchr.org/track/icse-2027/icse-2027-workshops) |

---

## Rejected — Deadline Already Past (≤ 2026-05-17)

Venues considered but explicitly excluded because the verified deadline is on or before today.

| Venue | Deadline (verified) | Source |
|-------|---------------------|--------|
| ICSME 2026 Research (full) | Fri 6 Mar 2026 | https://conf.researchr.org/dates/icsme-2026 |
| ICSME 2026 Industry Track | Fri 15 May 2026 | https://conf.researchr.org/track/icsme-2026/icsme-2026-industry-track |
| ICSME 2026 Registered Reports (initial) | Mon 11 May 2026 | https://conf.researchr.org/track/icsme-2026/icsme-2026-registered-reports |
| ICSME 2026 Visions & Emerging Results | Fri 15 May 2026 | https://conf.researchr.org/track/icsme-2026/icsme-2026-nier |
| ICSME 2026 Replication & Negative Results | Fri 15 May 2026 | https://conf.researchr.org/dates/icsme-2026 |
| ICSME 2026 Tool Demo / Data Showcase (abstract) | Sun 24 May 2026 | https://conf.researchr.org/dates/icsme-2026 → see note below |
| ICSME 2026 Tool Demo / Data Showcase (paper) | Thu 28 May 2026 | https://conf.researchr.org/dates/icsme-2026 → see note below |
| ESEM 2026 Technical Track | Mon 18 May 2026 | https://conf.researchr.org/home/esem-2026 |
| ASE 2026 NIER | Tue 12 May 2026 (AoE) | https://conf.researchr.org/track/ase-2026/ase-2026-nier |
| ASE 2026 Industry Showcase | Thu 30 Apr 2026 (paper) | https://conf.researchr.org/track/ase-2026/ase-2026-industry-showcase |
| FSE 2026 Research Papers | (closed, Feb 2026) | https://conf.researchr.org/home/fse-2026 |
| FSE 2026 Industry Papers | Thu 22 Jan 2026 | https://conf.researchr.org/track/fse-2026/fse-2026-industry-papers |
| FSE 2026 Tool Demonstrations | Mon 26 Jan 2026 | https://conf.researchr.org/track/fse-2026/fse-2026-demonstrations |
| FSE 2026 workshops (LLMTrust, HumanAISE, LLMSC, CauSE, SEE-AIT, DISE, etc.) | Feb 12–19 2026 cycle | https://conf.researchr.org/track/fse-2026/fse-2026-workshops ; https://llmtrust2026.github.io/ ; https://humanai4se.github.io/ |
| MSR 2026 Technical Papers | Thu 23 Oct 2025 | https://conf.researchr.org/dates/msr-2026 |
| MSR 2026 Data & Tool Showcase | Mon 10 Nov 2025 | https://conf.researchr.org/dates/msr-2026 |
| MSR 2026 Mining Challenge papers | Tue 23 Dec 2025 | https://conf.researchr.org/dates/msr-2026 |
| MSR 2026 Industry Track | Fri 19 Dec 2025 | https://conf.researchr.org/dates/msr-2026 |
| MODELS 2026 ACM SRC abstracts | Fri 12 Jun 2026 (still future — moved to Verified list above? — see note) | https://conf.researchr.org/home/models-2026 — IS future; listed under MODELS NIER/Tutorials above |
| CAIN 2026 | (closed; conf was 12–18 Apr 2026, Rio) | https://conf.researchr.org/series/cain |
| ICPC 2026 | (closed; conf was 12–13 Apr 2026, Rio) | https://conf.researchr.org/home/icpc-2026 |
| ICST 2026 | (closed; conf was 18–22 May 2026, Daejeon) | https://conf.researchr.org/home/icst-2026 |
| SSBSE 2026 Research Papers | Fri 20 Feb 2026 | https://conf.researchr.org/track/ssbse-2026/ssbse-2026-research-papers |
| Internetware 2026 (all 3 cycles incl. resubmission Mon 18 May 2026) | Mon 18 May 2026 (AoE) — past as of compile date 17 May given AoE = UTC-12, but effectively closed | https://internetware2026.hotcrp.com/u/0/deadlines |
| ECSA 2026 Research Track | Fri 27 Mar 2026, AoE | https://conf.researchr.org/track/ecsa-2026/ecsa-2026-technical-track |
| QRS 2026 Regular & Short Papers | Wed 22 Apr 2026 (extended) | https://qrs26.techconf.org/ |
| FormaliSE 2026 | Thu 23 Oct 2025 | https://www.fmeurope.org/2025/08/28/cfp-formalise-2026/ |
| FM 2026 | Closed (Tokyo conf 18–22 May 2026) | https://conf.researchr.org/home/fm-2026 |
| PROMISE 2026 | Fri 16 Jan 2026 (AoE) | https://conf.researchr.org/home/promise-2026 |
| SLE 2026 | Fri 6 Mar 2026 (paper), Wed 29 Apr 2026 (artifact) | https://conf.researchr.org/home/sle-2026 |
| QUATIC 2026 main paper submission | Fri 15 May 2026 (AoE) | https://easychair.org/cfp/QUATIC2026 |
| SEAA 2026 | Wed 29 Apr 2026 (firm) | https://dsd-seaa.com/seaa2026/ |
| IEEE CLOUD 2026 | Sun 22 Mar 2026 (extended firm) | https://services.conferences.computer.org/2026/cloud/cloud-call-for-papers/ |
| COMPSAC 2026 Symposium | Fri 20 Feb 2026 (extended) | https://ieeecompsac.computer.org/2026/ |
| AIware 2026 ArXiv Track Round 2 | Fri 15 May 2026 | https://2026.aiwareconf.org/ |

**Note on ICSME 2026 Tool Demo / Data Showcase:** The dates page lists "Sun 24 May 2026" abstract and "Thu 28 May 2026" paper. Both are after 2026-05-17 calendar date, but the per-track CFP page (`/track/icsme-2026/icsme-2026-tool-demonstration-and-data-showcase`) returned 404 at compile time so the deadline could not be cross-verified against a dedicated track page. **Treat the dates-page values as the verified deadlines** (since they live on the official ICSME 2026 conf.researchr.org dates page) and submit toward those dates — but re-check the track page when it returns. **Re-classifying these as VERIFIED FUTURE**: see "Verified Venues" line 5b below.

| 5b | **ICSME 2026 — Tool Demo & Data Showcase** | Abstract Sun 24 May 2026 / Paper Thu 28 May 2026 | per ICSME norm (4–5 pp) | IEEE (per ICSME norm) | Benevento, Italy; 14–18 Sep 2026 | **HIGH** | Tool/data showcase is purpose-built for the AgentTelemetry SDK + 3,780-row benchmark; immediate-window submission. | https://conf.researchr.org/dates/icsme-2026 |

---

## Verified references

Each URL below was fetched in this session. The one-sentence ground-truth summary states what the page actually says, not what was assumed.

- https://conf.researchr.org/track/icse-2027/icse-2027-new-ideas-and-emerging-results--nier- — ICSE 2027 NIER submission deadline Fri 23 Oct 2026 23:59:59 AoE (UTC-12h); 4 pp + 1 pp refs; IEEE conference template; double-anonymous; conf Dublin 25 Apr – 1 May 2027; notification Fri 18 Dec 2026.
- https://conf.researchr.org/home/icse-2027 — ICSE 2027 in Dublin 25 Apr – 1 May 2027 at Convention Centre Dublin; main tracks include Research, SEET, SEIP, SEIS, NIER, Journal-first, Tool Demonstration and Data Showcase, Artifact Evaluation, Competitions, Industry Challenge, Shadow PC; co-hosted with SEAMS.
- https://conf.researchr.org/track/icse-2027/icse-2027-seip — ICSE 2027 SEIP submission deadline Fri 23 Oct 2026; 10 pp main + 2 pp refs; IEEE template; **does not** require double-anonymous review; notification Fri 11 Dec 2026; camera-ready Wed 20 Jan 2027.
- https://conf.researchr.org/track/icse-2027/icse-2027-demonstrations — ICSE 2027 Tool Demonstrations & Data Showcase deadline Fri 23 Oct 2026; 4 pp inclusive of refs; IEEE; single-anonymous; PDF.
- https://conf.researchr.org/track/icse-2027/icse-2027-journal-first — ICSE 2027 Journal-First deadline Fri 30 Oct 2026 23:59 AoE; 2-page proposal; ACM Primary Article template; eligibility requires the journal paper accepted in a TBD window with ≥70% new content vs prior conference papers; secondary studies (SLRs, mapping studies) are excluded.
- https://conf.researchr.org/track/icse-2027/icse-2027-seis — ICSE 2027 SEIS deadline Oct 23 2026 (23:59 AoE/UTC-12); 10 pp full / 4 pp short + 2 pp refs; IEEE template; double-anonymous; notification Dec 18 2026.
- https://conf.researchr.org/track/icse-2027/icse-2027-src — ICSE 2027 SRC submission Nov 13 2026; notification Dec 18 2026; camera-ready Jan 29 2027; 2-page abstracts; for undergrad and grad students; ACM student membership required.
- https://conf.researchr.org/track/icse-2027/icse-2027-artifact-evaluation — ICSE 2027 AE registration Jan 22 2027, submission Jan 29 2027, notifications Feb 26 2027; eligible from Research/SEIP/SEET/NIER/SEIS/Demonstrations tracks; Functional/Reusable/Available/Results Reproduced/Results Replicated badges.
- https://conf.researchr.org/track/icse-2027/icse-2027-industry-challenge — ICSE 2027 Industry Challenge solution paper deadline Nov 13 2026 AoE; 5–10 pp (+1 camera) + 2 pp refs; IEEE template; anonymous; submission site icse2027-industry-challenge.hotcrp.com.
- https://conf.researchr.org/dates/icse-2027 — ICSE 2027 dates page confirms Industry Challenge submission Fri 10 Jul 2026 (challenges), Fri 13 Nov 2026 (solution papers), camera-ready Fri 29 Jan 2027.
- https://conf.researchr.org/track/icse-2027/icse-2027-workshops — ICSE 2027 workshop **proposal** deadline Fri 12 Jun 2026 (AoE UTC-12h); accepted workshops operate on uniform downstream deadlines with workshop **paper** submissions Fri 27 Nov 2026; proposals must not exceed 5 pp.
- https://conf.researchr.org/track/fse-2027/fse-2027-papers — FSE 2027 Research Papers full submission Fri 2 Oct 2026 AoE (UTC-12h); 18 pp + 4 pp refs (revised 20 pp + 4); ACM `acmsmall` template; double-anonymous heavy; author response Mon 14 – Fri 18 Dec 2026; initial decisions Fri 22 Jan 2027; major-revision submission Fri 5 Mar 2027; final notification Wed 31 Mar 2027; conf Shenzhen 12–16 Jul 2027.
- https://conf.researchr.org/home/fse-2027 — FSE 2027 confirmed Shenzhen 12–16 Jul 2027; main listed deadline is Research Papers Oct 2 2026; other tracks (Industry, Demos, IVR, DS, J1) listed by name but with deadlines TBA.
- https://conf.researchr.org/home/saner-2027 — SANER 2027 in Richmond, VA, USA at VCU 9–12 Mar 2027; Research Track abstract Mon 21 Sep 2026, paper Fri 25 Sep 2026, notification Tue 1 Dec 2026, camera Fri 8 Jan 2027.
- https://conf.researchr.org/track/icsa-2027/icsa-2027-papers — ICSA 2027 Research Papers Wed 4 Nov 2026 AoE (UTC-12h); 10 pp + 2 pp refs; IEEE template; double-anonymous; venue TBD, dates TBA.
- https://conf.researchr.org/dates/icsme-2026 — ICSME 2026 official dates: Research Track full Fri 6 Mar 2026; Registered Reports initial Mon 11 May 2026; Visions/ERA paper Fri 15 May 2026; Replication/Negative Results paper Fri 15 May 2026; Industry paper Fri 15 May 2026; Tool Demo/Data Showcase abstract Sun 24 May 2026 / paper Thu 28 May 2026; SCAM Research Thu 11 Jun 2026; SCAM Engineering Thu 18 Jun 2026; Journal-First Sat 20 Jun 2026; Doctoral Symposium Wed 3 Jun 2026.
- https://conf.researchr.org/track/icsme-2026/icsme-2026-nier — ICSME 2026 Visions & Emerging Results paper deadline May 15 2026 23:59 AoE; 5 pp + 1 pp refs; double-anonymous.
- https://conf.researchr.org/track/icsme-2026/icsme-2026-industry-track — ICSME 2026 Industry Track May 15 2026 23:59 AoE; full 10 pp + 2 refs / short 3–5 pp + 1 ref; IEEE two-col; non-anonymous.
- https://conf.researchr.org/track/icsme-2026/icsme-2026-registered-reports — ICSME 2026 Registered Reports initial submission May 11 2026; 6 pp + 1 pp refs (strict); IEEE two-col; single-blind; Stage-1 notification Jun 19 2026.
- https://conf.researchr.org/track/icsme-2026/icsme-2026-journal-first — ICSME 2026 Journal-First paper submission Jun 6 2026; eligibility window Jan 1 2025 – May 30 2026; from EMSE/JSEP/JSS/AUSEJ/SCICO/IST; not in proceedings.
- https://conf.researchr.org/home/scam-2026 — SCAM 2026 in Benevento 14–15 Sep 2026 (co-located ICSME); Research Track paper Thu 11 Jun 2026 (12 pp, double-blind, IEEE); Engineering Track paper Thu 18 Jun 2026 (10 pp, single-blind, IEEE).
- https://conf.researchr.org/home/esem-2026 — ESEM 2026 (ESEIW) in München Sun 4 – Fri 9 Oct 2026; tracks Technical (May 18 2026), ERVR (abstract May 22 / paper May 29 2026), Registered Reports, SEIP (abstract May 20 / paper May 27 2026), Journal-First (Jul 1 2026); plus IDoESE, Industry Day, ISERN.
- https://conf.researchr.org/home/eseiw-2026 — ESEIW 2026 upcoming deadlines list: Technical May 18, SEIP abstract May 20 / paper May 27, ERVR abstract May 22 / paper May 29, RR Stage-1 outcome Jun 8, Journal-First Jul 1.
- https://esem26-ervr.hotcrp.com/ — ESEM 2026 Emerging Results, Vision & Reflection Papers track submission deadline Friday May 29 2026, 11:59:59 PM AoE.
- https://conf.researchr.org/home/apsec-2026 — APSEC 2026 in Bali 7–10 Dec 2026; Technical Track abstract Mon 6 Jul 2026 / full Mon 13 Jul 2026; ERA Mon 3 Aug 2026; SEIP Mon 17 Aug 2026.
- https://conf.researchr.org/track/ase-2026/ase-2026-nier — ASE 2026 NIER deadline Tue 12 May 2026 AoE; 4 pp + 2 pp refs; ACM sigconf review anonymous; double-blind.
- https://conf.researchr.org/track/ase-2026/ase-2026-industry-showcase — ASE 2026 Industry Showcase abstract Apr 23 2026 / paper Apr 30 2026 AoE; long 10 + 2 / short 5 + 1; ACM sigconf review.
- https://conf.researchr.org/track/ase-2026/ase-2026-journal-first — ASE 2026 Journal-First paper Mon 6 Jul 2026 AoE (UTC-12h).
- https://conf.researchr.org/track/ase-2026/ase-2026-doctoral-symposium — ASE 2026 Doctoral Symposium deadline Tue 30 Jun 2026 AoE.
- https://conf.researchr.org/home/ase-2026 — ASE 2026 in Munich 12–16 Oct 2026; downstream-only deadlines after May 17 (Industry Showcase notification Jun 28, NIER notification Jul 1, Doctoral Symposium Jun 30, Tools/Datasets notification Jun 17); only one co-located workshop KLEE 2026.
- https://conf.researchr.org/home/fse-2026 — FSE 2026 in Montreal 5–9 Jul 2026; main tracks all closed; 13 workshops co-located (ASQAP, SEGA, FaSE4Games, RSE, DevOpsSustain, LLMSC, SEE-AIT, IntersectionalitySE, CauSE, LLMTrust, DISE, SE4ES, HumanAISE, QSE-NE, SE4ADS); 4 FSE-AIWARE Joint Competitions.
- https://conf.researchr.org/track/fse-2026/fse-2026-workshops — FSE 2026 workshop **proposal** deadline Oct 16 2025; suggested workshop paper submission Feb 12 2026; per-workshop deadlines set by chairs.
- https://llmtrust2026.github.io/ — LLMTrust 2026 workshop submission Feb 19 2026 AoE; full 8 pp / short 5 pp / abstract 1–5 pp; ACM; double-anonymous; Montreal Jul 5 or 6 2026.
- https://humanai4se.github.io/ — HumanAISE 2026 workshop submission Feb 12 2026; full 8 + 2 / short 4 + 1; FSE two-col industry track format; double-blind; Montreal Jul 5 2026.
- https://2026.aiwareconf.org/ — AIware 2026 in Montreal Jul 6–7 2026; tracks Main, ArXiv, Benchmark & Dataset, Industry Demo, FSE-AIware Joint Competition; remaining ArXiv Round-2 deadline May 15 2026; uses OpenReview.
- https://conf.researchr.org/series/aiware — AIware series page lists 2024, 2025, 2026 only; no AIware 2027 announced.
- https://conf.researchr.org/series/cain — CAIN 2026 in Rio Apr 12–18 2026; no CAIN 2027 yet listed.
- https://conf.researchr.org/home/icpc-2026 — ICPC 2026 in Rio Apr 12–13 2026 co-located ICSE 2026; tracks Research, ERA, RENE, Tool Demo, Journal-First; no ICPC 2027 mentioned.
- https://conf.researchr.org/home/icst-2026 — ICST 2026 in Daejeon, South Korea, 18–22 May 2026 (already past); no ICST 2027 info.
- https://icstconference.github.io/ — ICST steering committee page; calls for proposals for future hosting; no ICST 2027 details.
- https://conf.researchr.org/dates/msr-2026 — MSR 2026 important dates; all main tracks already closed (Oct 2025 – Dec 2025); one remaining deadline Registered Reports EMSE full paper Mon 28 Sep 2026.
- https://2026.msrconf.org/ — MSR 2026 in Rio Apr 13–14 2026 co-located ICSE 2026; tracks Technical Papers, Industry, Data & Tool Showcase, FOSS Award, Mining Challenge, Registered Reports, Tutorials, Vision & Reflection.
- https://conf.researchr.org/track/ssbse-2026/ssbse-2026-research-papers — SSBSE 2026 in Montreal Mon 6 Jul 2026; research paper deadline Fri 20 Feb 2026; up to 15 pp incl. refs; Springer LNCS; double-anonymous; notification Sat 28 Mar 2026.
- https://internetware2026.hotcrp.com/u/0/deadlines — Internetware 2026 deadlines: SecondCycle submission closed May 4 2026; resubmission Mon 18 May 2026 23:59:59 AoE (effectively closed at the calendar date 2026-05-17 because AoE = UTC-12).
- https://conf.researchr.org/home/internetware-2026 — Internetware 2026 in Gold Coast 18–20 Jul 2026; tracks Research, New Idea, Tool Demonstration.
- https://conf.researchr.org/track/ecsa-2026/ecsa-2026-technical-track — ECSA 2026 Research Track paper deadline Fri 27 Mar 2026, 23:59h AoE; 16 pp LNCS (research) / 8 pp (short); double-blind; EasyChair.
- https://conf.researchr.org/home/ecsa-2026 — ECSA 2026 in Bolzano 7–11 Sep 2026; remaining listed dates Camera Ready May 20, Open Science submission Jun 19, Tutorial papers May 15 (most main-track deadlines already past).
- https://qrs26.techconf.org/ — QRS 2026 in Florence 22–25 Jul 2026; Regular & Short papers deadline Apr 22 2026 (extended); notification May 30 2026; categories Regular/Short, Workshops, Industry, Fast Abstracts, Posters, special tracks.
- https://www.fmeurope.org/2025/08/28/cfp-formalise-2026/ — FormaliSE 2026 deadline Oct 23 2025 (closed); co-located ICSE 2026 Rio Apr 12–13 2026.
- https://conf.researchr.org/home/fm-2026 — FM 2026 in Tokyo 18–22 May 2026; registration closed May 15 2026.
- https://conf.researchr.org/home/promise-2026 — PROMISE 2026 in Montreal Jul 5 2026; submission Jan 16 2026 AoE; 12 of 22 accepted; tracks Technical (10 pp), Industrial (2–4 pp), Extended Abstracts (1–4 pp); FSE 2026 Companion format; double-blind.
- https://conf.researchr.org/home/sle-2026 — SLE 2026 in Rennes 2–3 Jul 2026 (co-located STAF 2026); paper submission Mar 6 2026 AoE; artifact submission Apr 29 2026 AoE; camera ready May 11 2026; ACM SIGPLAN acmart format; double-blind.
- https://easychair.org/cfp/QUATIC2026 — QUATIC 2026 main paper submission May 15 2026; SEDES PhD Symposium May 31 2026; notification Jun 22 2026; conf Genoa Sep 9–11 2026.
- https://2026.quatic.org/home — QUATIC 2026 conf overview; 8 thematic tracks; full 12–16 pp / short 6–8 pp.
- https://2026.quatic.org/important-dates — QUATIC 2026 important dates with AoE timezone; no extension beyond May 15 main / May 31 SEDES on this page.
- https://dsd-seaa.com/seaa2026/ — SEAA 2026 in Kraków Sep 2–4 2026; paper submission Apr 29 2026 (firm); LNCS-single-column format; 10 tracks.
- https://services.conferences.computer.org/2026/cloud/cloud-call-for-papers/ — IEEE CLOUD 2026 in Sydney 13–18 Jul 2026; paper submission Mar 22 2026 (extended firm); notification May 10 2026.
- https://ieeecompsac.computer.org/2026/ — COMPSAC 2026 in Madrid 7–10 Jul 2026; symposium papers Feb 20 2026 (extended); workshop/special-session papers Apr 30 2026.
- https://conf.researchr.org/home/seams-2027 — SEAMS 2027 in Dublin 26–27 Apr 2027 (CCD), co-located ICSE 2027; no submission deadlines yet posted.
- https://conf.researchr.org/home/models-2026 — MODELS 2026 in Málaga 4–9 Oct 2026; remaining deadlines after 2026-05-17: ACM SRC abstracts Jun 12, Tutorials Jun 19, NIER abstract Jun 24, NIER paper Jul 1, Workshops Jul 3.
- https://conf.researchr.org/home/vlhcc-2026 — VL/HCC 2026 in Paderborn Sep 29 – Oct 2 2026; remaining HCSE technical papers May 22 2026 (after compile date); research-track rebuttal Jun 15–21 2026; main research paper submission already past.

---

**End of report.**
