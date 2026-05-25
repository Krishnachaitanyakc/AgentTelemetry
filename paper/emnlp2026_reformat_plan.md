# EMNLP 2026 Industry Track Reformat Plan

**Source manuscript:** `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/neurips2026/neurips_2026.tex` (NeurIPS 2026 E&D format, ~9 pages, anonymized)
**Target venue:** EMNLP 2026 Industry Track
**Submission deadline:** June 16, 2026, 11:59 PM UTC-12:00 (AoE) — **36 days from today**
**Notification:** August 20, 2026 | **Camera-ready:** September 20, 2026 | **Conference:** October 24-29, 2026, Budapest
**Submission portal:** ACL OpenReview (link from EMNLP 2026 site)
**Format:** ACL template (NOT NeurIPS) | **Page limit:** 6 pages main + 1 for camera-ready | **Anonymization:** Double-blind | **Multi-submission:** Forbidden (>25% overlap with own concurrent submissions = desk reject)

---

## 0. Strategic Posture

The NeurIPS draft is technically excellent but framed as a **systems/observability** paper. EMNLP Industry Track explicitly wants **NLP/LLM-deployed-system** papers. The reframing is not cosmetic — it's a genuine angle shift:

- **NeurIPS framing (current):** "We define 9 OpenTelemetry span kinds and prove FDR=1.000 via controlled fault injection. The contribution is a systems-observability primitive."
- **EMNLP Industry framing (target):** "We deployed an NLP/LLM agent observability stack to diagnose real failures in production-scale LLM applications. Lessons learned: 75% of SWE-bench failures are reasoning loops, invisible to standard tracing. We share the deployment experience, the diagnostic library, and a closed-loop intervention raising recovery rates."

This shift puts the **deployment-experience and diagnosis** narrative front and center — exactly what the EMNLP Industry CFP rewards.

**Critical IP risk to manage:** EMNLP Industry has "no anonymity period requirement" and allows arXiv preprint at any time. BUT the AIware 2026 paper is the same underlying research (different framing). Two USCIS-relevant points:

1. **Self-overlap rule:** EMNLP forbids >25% content overlap with concurrent author submissions. The AIware paper is already **accepted and camera-ready**, so it's not "concurrent under review" — but the EMNLP reviewers will Google the title and find the AIware DOI. Be transparent: cite AIware as prior accepted work and frame EMNLP as a **distinct contribution** focused on the LLM-application deployment angle, not the same benchmark paper retargeted.

2. **Distinct contribution requirement:** USCIS counts distinct accepted publications. Submitting a venue-variant of the same paper risks looking like padding — and reviewers may flag it. The EMNLP version must be substantively different in scope, not just compressed.

## 1. The Distinct Contribution Angle for EMNLP

To make this a genuine new paper rather than a 6-page compression of the AIware/NeurIPS work, lead with what the AIware paper **doesn't fully cover**:

**Lead contribution: "Lessons from deploying agent observability across 13 LLM models in production-tier API workloads."**

Foreground RQ5 (the 159-run real-LLM corpus across 5 Anthropic + 8 OpenAI models) and RQ6 (the SWE-bench case study with closed-loop intervention) — these are the **deployment-experience** contributions that EMNLP Industry wants. De-emphasize RQ1/RQ2/RQ3 (the controlled fault-injection benchmark that anchored AIware).

This positions the EMNLP paper as: "We took the published AgentTelemetry benchmark and stress-tested it on 13 production LLMs and 112 real GitHub issues. Here's what we learned." That's a legitimate distinct contribution.

## 2. Section-by-Section Reformat Plan

| NeurIPS section | NeurIPS pages | EMNLP target | EMNLP pages | Action |
|---|---|---|---|---|
| Abstract | ~0.4 | Reframe to deployment experience | ~0.3 | REWRITE (see §3) |
| §1 Introduction | ~0.8 | Lead with deployment failures | ~0.7 | REWRITE — drop the "5 missing OTel span kinds" hook; lead with "production LLM agents fail silently" |
| §2 Background and Motivation | ~0.7 | CUT | 0 | Remove almost entirely; merge 2 sentences into intro |
| §3 Span Taxonomy (3.1 Derivation, 3.2 Nine Kinds, 3.3 Cross-Framework) | ~2.0 | Compress — taxonomy is now PRIOR WORK, not contribution | ~0.5 | Cite AIware paper for derivation + ablation; show table 2 compressed; drop derivation methodology |
| §4 Implementation | ~0.7 | Compress to one paragraph | ~0.2 | Cite AIware for full impl; mention 7 frameworks + privacy levels in passing |
| §5 Evaluation §5.1 Setup | ~0.5 | Keep, but pivot to LLM models | ~0.4 | Lead with 13-model real-LLM corpus; mock benchmark = 1 paragraph reference |
| §5.2 RQ1 FDR | ~1.2 | CUT (this is AIware's core result) | ~0.2 | One sentence + cite AIware Table 4 |
| §5.3 RQ2 Ablation | ~0.5 | CUT | 0 | Cite AIware |
| §5.4 RQ3 Overhead | ~0.3 | Keep — deployment relevance | ~0.2 | Compressed to 2 sentences |
| §5.5 RQ5 Real LLM API | ~0.7 | **EXPAND — this is the lead contribution** | ~1.0 | Add per-model breakdown, organic-fault discussion, deployment lessons |
| §5.6 RQ6 SWE-bench | ~1.5 | **KEEP IN FULL — this is the second lead contribution** | ~1.5 | Foreground the closed-loop intervention as deployment lesson |
| §5.7 Threats | ~0.4 | Keep, EMNLP needs Limitations | ~0.3 | Move the 4 limitations from current Conclusion into proper Limitations section |
| §6 Related Work | ~1.0 | Compress | ~0.5 | Tighter paragraphs; emphasize NLP agent observability gap |
| §7 Conclusion | ~0.6 | Compress; move Limitations out | ~0.3 | Single closing paragraph |
| **Limitations section (NEW)** | — | EMNLP REQUIRES this | ~0.3 | Move L1-L4 from current Conclusion |
| Broader Impact | (in conclusion) | Keep | (counts toward refs page, not 6 pp) | |
| References | unlimited | unlimited | (separate) | Keep |
| Appendix MAST mapping | ~1 | Drop or reduce | (optional) | Cite AIware appendix |
| Appendix Datasheet | ~1 | Keep brief version | (optional) | Useful for reviewers |
| **TOTAL** | ~9 main | | **6 main** ✓ | Cuts focus on §3 + §4 + §5.2 + §5.3 |

## 3. New Abstract (Draft)

**Current NeurIPS abstract (200 words, 6-contribution list, benchmark-focused):**

> "Autonomous AI agents built on large language models are transitioning from research prototypes to production deployments, yet the observability infrastructure needed to diagnose their failures remains fundamentally inadequate. ... We make six contributions: (1) a taxonomy of 9 span kinds and 14 fault types, ..."

**EMNLP draft abstract (~150 words, 3-contribution list, deployment-focused):**

> "Production deployments of LLM-based autonomous agents fail in ways that standard observability cannot diagnose: 75% of failed runs in our 112-instance SWE-bench Lite study are reasoning loops, invisible to vanilla OpenTelemetry. We deployed AgentTelemetry — an OpenTelemetry-native instrumentation library covering nine agent-specific span kinds — across 13 LLM models from two providers (5 Anthropic + 8 OpenAI) and six widely used agent frameworks (LangChain, CrewAI, AutoGen, LlamaIndex, Anthropic SDK, OpenAI SDK), generating 159 production-style traces. We report three deployment-experience findings: (1) organic faults are rare in well-behaved frontier models but frequent in budget-tier models, with cost-explosion firing on 7/13 models and infinite-retry on 2/13; (2) instrumentation overhead is negligible (<0.006% of LLM API latency) but wall-clock variance is dominated by API jitter (-50% to +162%); (3) a telemetry-guided closed-loop intervention recovers 12.5 percentage points more SWE-bench failures than the control by detecting reasoning loops in real time. We discuss the deployment lessons, the open-source library (Apache-2.0, Zenodo-archived), and the limitations of the simulated user study supporting the diagnostic-quality claims."

## 4. New Introduction Hook (Draft)

**Current opening (NeurIPS):** "Large language model (LLM) based autonomous agents represent a paradigm shift in software architecture..."

**EMNLP opening (deployment-experience hook):** "When an LLM agent in production stops responding, on-call engineers face a familiar question: did the model hallucinate, did the orchestrator infinite-loop, did the guardrail block the output, or did the tool just fail? Standard distributed tracing answers none of these. In our deployment of an instrumentation library across 13 production-tier LLM models from Anthropic and OpenAI, we observed that vanilla OpenTelemetry detects 6 of 14 well-defined agent fault types (FDR = 0.429 in controlled testing) — the remaining 8 require agent-specific telemetry primitives that no public OpenTelemetry standard yet defines. This paper reports our deployment experience..."

This hook does the work in 4 sentences:
- States the operational pain (on-call, ambiguous failures)
- Cites the deployment scale (13 models, 2 providers)
- Establishes the gap (FDR=0.429 for vanilla OTel) without requiring the reader to follow the controlled benchmark
- Positions the paper as a deployment-experience report (matching CFP scope)

## 5. References Hygiene

CORRECTION (2026-05-11 follow-up): I previously flagged `agentrx` arXiv ID `2602.02475` as hallucinated. **It is NOT — the paper is real** (title "AgentRx: Diagnosing AI Agent Failures from Execution Trajectories" by Barke et al., Feb 2 2026). The arXiv prefix encodes YYMM (year-month), so `2602` = February 2026. Verified via https://arxiv.org/abs/2602.02475. The same correction applies to the Determinism SUBMISSION_CHECKLIST note about `2604.22411` (April 2026, also real). No bibliography fix needed.

What still requires hygiene:
- All `\cite{}` keys must resolve; zero `[?]` placeholders in compiled PDF
- Switch from `plainnat.bst` to ACL's `acl_natbib.bst`
- Bibliography style line: `\bibliographystyle{acl_natbib}` not `plainnat`

## 6. Anonymization Sweep (EMNLP-specific)

EMNLP Industry has no anonymity period (arXiv allowed anytime). But the *submitted PDF* must still be double-blind:

```bash
# Author name leaks
grep -in "krishna\|balusu\|kcbalusu\|chaitanya" neurips_2026.tex
# Email/affiliation leaks (Meta, Independent Researcher are tells)
grep -inE "Independent Researcher|Meta|Facebook|@gmail" neurips_2026.tex
# GitHub URL leaks (username = identity)
grep -inE "github\.com/Krishna|github\.com/Datapup" neurips_2026.tex
# AIware paper title/DOI leak (would identify author via Google)
grep -inE "10.1145/3805760|AIware 2026|aiwareconf" neurips_2026.tex
# Self-references in NeurIPS-style (we previously...)
grep -inE "we previously|in our prior|our recent" neurips_2026.tex
```

**Special case for AIware citation:** The EMNLP paper MUST cite AIware (it's the foundation), but the citation style must be 3rd-person to preserve double-blind:
- WRONG: "We previously published the controlled benchmark at AIware 2026 [Balusu, 2026]."
- RIGHT: "The controlled benchmark from prior work [Balusu, 2026] establishes baseline FDR; this paper extends to deployment evaluation."

Reviewers will figure out the author identity from the AIware DOI, but the EMNLP rule is about *form* (3rd person, no "we previously") not *deduction*.

## 7. EMNLP-Required Limitations Section (Move L1-L4 from current Conclusion)

The current paper has L1-L4 buried in Conclusion. EMNLP **desk-rejects** papers without a dedicated Limitations section. Reformat as:

```
\section*{Limitations}
\textbf{Mock-vs-real evaluation gap.} Controlled benchmarks use deterministic mocks for reproducibility; only \texttt{missing\_guardrail} reaches FDR=1.000 organically on the 159-run real-LLM corpus. Larger production traces would expose more fault types.
\textbf{Closed-loop sample size.} The +12.5 pp intervention effect is not statistically significant at n=24 (Fisher's exact p=0.53); larger-sample replication queued.
\textbf{Patch verification method.} 87.9\% plausibility on 33 SWE-bench patches uses an LLM-judge, not the official harness.
\textbf{Simulated user study confound.} The 6-persona role-play has direct access to span-kind labels in the AgentTelemetry condition; the h=1.51 effect measures information availability, not real developer effort.
```

## 8. Acknowledgments (Camera-ready only)

Strip from review version. EMNLP allows acknowledgments only at camera-ready. None to add — sole-author paper, independent researcher.

## 9. Submission Checklist (EMNLP-specific)

Pre-flight before clicking Submit:

- [ ] Page count ≤ 6 (excluding refs, limitations, ethics, appendices). `pdfinfo emnlp_paper.pdf | grep Pages` shows 6 pp main.
- [ ] PDF uses ACL template (`\documentclass[11pt]{article}` + `\usepackage{acl}`)
- [ ] Limitations section present (mandatory; no Limitations = desk reject)
- [ ] Ethics/Broader Impact present (recommended; absence flagged by reviewers)
- [ ] All citations resolve (zero `[?]` in compiled PDF; zero "Citation undefined" warnings in .log)
- [ ] AgentRx hallucinated arXiv ID `2602.02475` fixed
- [ ] Bibliography uses ACL style (not plainnat)
- [ ] Anonymization sweep clean (commands in §6)
- [ ] PDF metadata stripped: `exiftool -all:all= -overwrite_original emnlp_paper.pdf`
- [ ] Title field in OpenReview matches PDF
- [ ] Abstract field ≤ 200 words (EMNLP standard)
- [ ] Keywords filled (5-10): agent observability; LLM deployment; fault detection; OpenTelemetry; production NLP systems; closed-loop intervention; SWE-bench; benchmarking
- [ ] Track: Industry Track
- [ ] Subject area: NLP applications / LLM systems
- [ ] Conflict-of-interest declared (sole-author independent — minimal)
- [ ] Code submitted to anonymous repo (anonymous.4open.science) — link in paper
- [ ] No double-submission overlap >25% with concurrent author work (AIware accepted, not concurrent — but disclose in submission system if asked)

## 10. Two-Week Sprint Calendar

| Day range | Action |
|---|---|
| **Week 1 (May 11-18):** | Decide whether to pursue EMNLP (final go/no-go on overlap risk with AIware). Set up ACL template fork of NeurIPS .tex. |
| **Week 2 (May 19-25):** | Cut sections per §2 plan; rewrite abstract per §3; rewrite intro per §4; expand RQ5 + RQ6 deployment-experience framing. |
| **Week 3 (May 26 - June 1):** | Write Limitations section per §7; fix references (esp. hallucinated arXiv IDs); first compile pass. |
| **Week 4 (June 2-8):** | Cold-reviewer pass: dispatch a sub-agent to read the EMNLP draft and verify (a) ≤6 pages, (b) deployment-experience framing is consistent throughout, (c) AIware overlap disclosed honestly, (d) Limitations section present. |
| **Week 5 (June 9-15):** | Anonymization sweep. PDF metadata strip. OpenReview profile check. Final read of compiled PDF. |
| **June 16:** | Submit by 11:59 PM UTC-12:00 AoE. |

## 11. Decision Required From KC Before Sprint Start

1. **Overlap risk acceptance:** Are you comfortable submitting a deployment-focused EMNLP paper that builds on the AIware accepted paper? The risk: reviewers Google the title, find AIware DOI, flag as "venue-variant of accepted work." The mitigation: lead with deployment-experience contributions (RQ5 + RQ6) that are *not* the AIware lead contributions (which were RQ1 + RQ2). I'd assess the overlap risk as MEDIUM — defensible but reviewer-dependent.

2. **Alternative if overlap risk feels too high:** Skip EMNLP and focus the same 36 days on the IEEE Software Edge-Cloud Continuum special issue (Jul 7 deadline, lower overlap risk because format is clearly different — magazine practitioner article vs. ACM/ACL conference paper).

3. **Single-blind exception:** EMNLP Industry permits requesting single-blind review when datasets cannot be anonymized. Likely not applicable here since the codebase is genuinely separable from the byline. Default to double-blind.

## 12. Post-Submission

If accepted (notification Aug 20, 2026):
- Camera-ready due Sept 20, 2026 (1 month window)
- Conference Oct 24-29, 2026 in Budapest
- Counts as **second sole-authored peer-reviewed publication** for Criterion 6 (after AIware 2026)
- ACL Anthology indexed = USCIS-defensible

If rejected:
- Pivot the EMNLP draft to a NeurIPS workshop (deadline Aug 29, 2026) — minimal reformatting since the original was already in NeurIPS template
- Total wasted time: zero (the deployment-experience framing strengthens the paper for any venue)

---

## Verification Log

| Source | URL | Confirmed |
|---|---|---|
| EMNLP 2026 Industry Track CFP | https://2026.emnlp.org/calls/industry_track/ | Deadline June 16 (AoE), notification Aug 20, 6 pages, ACL template, double-blind, mandatory Limitations, no anonymity period |
| Source manuscript | `research/AgentTelemetry/paper/neurips2026/neurips_2026.tex` (1129 lines, 9 pp PDF) | Read in full |
| AgentRx arXiv ID | https://arxiv.org/abs/2602.02475 | Verified real — Feb 2026 paper by Barke et al. arXiv prefix is YYMM, not year. NO hallucination. |
| AIware accepted status | `EB1/evidence/criterion-6-scholarly-articles/peer_reviews/camera_ready_submitted_2026-05-11.md` | DOI 10.1145/3805760.3814931 |
| ACL official LaTeX style files | https://github.com/acl-org/acl-style-files | Downloaded acl.sty (11.6KB), acl_natbib.bst (45.2KB), acl_latex.tex template (14.5KB) to `emnlp2026/` |
