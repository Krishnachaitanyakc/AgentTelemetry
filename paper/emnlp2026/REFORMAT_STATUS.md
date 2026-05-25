# EMNLP 2026 Reformat — Status Snapshot

**Date:** 2026-05-12
**Source manuscript:** `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/emnlp2026/emnlp_paper.tex`
**Compiled PDF:** 7 pages total (~5 pages main content + Limitations + Broader Impact + Reproducibility + References)
**EMNLP main-content limit:** 6 pages (excluding refs, limitations, ethics, appendices) — **WELL UNDER LIMIT**

## What's done (executed today during experiment 1 wall-clock)

- [x] Document class migration from `\documentclass{article} + neurips_2026` → `\documentclass[11pt]{article} + acl[review]`
- [x] Title rewritten: "AgentTelemetry in Production: Deployment Experience with Span-Kind Observability Across 13 LLMs and Three Multi-Agent Topologies"
- [x] Abstract rewritten — deployment-experience framing, 3-contribution list (was 6-contribution benchmark list)
- [x] Introduction rewritten — on-call diagnostic hook, leads with prior-work AIware citation as foundation (per overlap-management strategy)
- [x] §2 Background compressed: 250 lines → 70 lines (taxonomy is now cited prior work, not derived contribution)
- [x] §3 Implementation compressed: 33 lines → 17 lines (one paragraph)
- [x] §4 Evaluation reframed as "Deployment Experience" with new RQ structure (RQ1+RQ2 cut, RQ3 overhead kept, RQ4=real-LLM, RQ5=SWE-bench, RQ6=topology)
- [x] §5.2 RQ1 (FDR table) cut — AIware's lead result; cite prior work
- [x] §5.3 RQ2 (Ablation) cut — AIware's lead result; cite prior work
- [x] §RQ6 (Multi-Agent Topology Comparison) NEW section added with method + placeholder for experiment 2 results
- [x] Conclusion compressed and rewritten around deployment-experience axes
- [x] **EMNLP-mandatory \section*{Limitations} added** as dedicated unnumbered section (L1-L5)
- [x] Appendix dropped (MAST mapping table + Datasheet — both no longer cited from main text)
- [x] Bibliography style changed `plainnat` → `acl_natbib`
- [x] Orphan citations removed (`agentbench`, `agentboard`, `strauss_corbin`, `datasheets`)
- [x] New `aiware2026` bibitem added (referenced 7+ times in deployment-experience reframing)
- [x] First compile pass: 10 pages
- [x] After cuts: 7 pages, zero undefined refs, zero undefined citations
- [x] Second compile pass: confirmed clean, 7 pages

## What's left

### Blocking on experiment 2 results
- §RQ6 (Multi-Agent Topology Comparison) currently has a placeholder paragraph in italic for results. After experiment 2 finishes (~2.5h after exp 1 done):
  - Insert per-(topology × model) results table from `results/multi_agent_topology_cli/summary.json`
  - Add organic-fault counts from AnomalyDetector
  - Add 1-2 qualitative trace examples (e.g., a hierarchical run that exhibited circular delegation; a parallel run that hit cost explosion at the aggregator)

### Blocking on experiment 1 results
- §RQ5 SWE-bench section: current text references the prior n=24 result with intervention. After exp 1 finishes (~10h):
  - Add new paragraph reporting n=60 Fisher's exact p-value
  - Update L2 in Limitations from "queued" → actual finding
  - Add brief comparison: n=24 ↔ n=60 effect direction + magnitude

### Anonymization sweep (do before submission)
- Author block currently shows "Anonymous / Anonymous Affiliation / anon@anon.anon" — correct for review
- Need to grep .tex for any KC name leaks, GitHub URL leaks, or AIware DOI leaks before submit
- The AIware citation MUST stay as `\citep{aiware2026}` — bib entry already says "Anonymous" for byline, so it doesn't leak identity (reviewers will figure it out via Google, but the form passes blind)

### Final hygiene before June 16
- Strip PDF metadata: `exiftool -all:all= -overwrite_original emnlp_paper.pdf`
- Verify ACL template constraints (font embedding, paper margins, etc. — `acl.sty` enforces most automatically)
- Submit to ACL OpenReview EMNLP 2026 Industry Track portal
- Add Keywords (5-10) on submission form
- Track: Industry; Subject area: NLP applications / LLM systems

## Risk register

1. **Overlap-with-AIware risk: MEDIUM.** Reviewers will cross-reference. The reframing is a real angle shift (deployment focus vs. benchmark focus) and the AIware citation is foreground, not buried. Defensible but reviewer-dependent.
2. **Page count headroom: GOOD.** 7 total pages with all required sections; main content estimated ~5 pages; up to 1 page of slack to absorb experiment 2 results table and exp 1 follow-up paragraph.
3. **Experiment 1 timing: TIGHT.** ~10h projected from smoke test. If it stalls or rate-limits hit, smoke-test backup of n=3 control + intervention is on disk and could be cited as preliminary if needed.
4. **Experiment 2 timing: comfortable.** ~2.5h, can fit anywhere after exp 1 frees the CLI.

## Verified compile state

```
Output written on emnlp_paper.pdf (7 pages, 195038 bytes).
Zero undefined references.
Zero undefined citations.
Bibliography style: acl_natbib (matches ACL template).
Document class: article + acl[review] (correct for EMNLP submission).
```
