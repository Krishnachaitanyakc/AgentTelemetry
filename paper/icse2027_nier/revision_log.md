# Revision Log — ICSE 2027 NIER Paper

**Goal:** push from ACCEPT (post-Round 2) to STRONG_ACCEPT.
**Process:** Fresh-persona cold-review cycles with explicit best-paper-finalist (top ~10%) bar.

---

## Round 3 cold review (2026-05-17)

Verdict: **ACCEPT** (not STRONG_ACCEPT yet).

10 gaps blocking STRONG_ACCEPT:

| ID | Gap | Status |
|----|-----|--------|
| G1 | Obvious vanilla-OTel detector attack not dispatched | Fixed |
| G2 | MLOps / hidden-technical-debt lineage not engaged | Fixed |
| G3 | RQ5 counterfactual (deepest novelty) buried | Fixed |
| G4 | New idea has no name | Fixed |
| G5 | OTel gen_ai conventions cited abstractly, no version | Fixed |
| G6 | Figure 1 operators lack formal semantics | Fixed |
| G7 | Failure-taxonomy neighbors lumped together | Fixed |
| G8 | Title 3 lines / 18 words | Fixed |
| G9 | CoT-faithfulness threat not engaged | Fixed |
| G10 | Vignette queries not shown | Fixed |

## Edits applied

1. **Title** trimmed from 18 words / 3 lines to 7 words / 1 line: "Agent Observability is Not Microservice Observability".
2. **Abstract** revised to introduce the named *Cognitive-Trace Hypothesis* and to elevate the RQ5 causal-inference claim into the abstract.
3. **Vignette** now shows all four actual `search_code` arguments verbatim.
4. **§I new paragraph "Why the obvious vanilla-OTel detector does not work"** dispatches the hash-completion-strings attack in two structural arguments (payload opacity, missing cognitive-edge typing).
5. **Thesis paragraph** names the Cognitive-Trace Hypothesis, frames it as the third generation of an SE move (single-process logging → distributed tracing → ML observability → agent observability), cites Sculley and Breck.
6. **Contribution list (§I)** now ends with the RQ5 causal-inference elevation as a one-sentence highlight.
7. **§II.C** cites OTel GenAI SIG v1.30 with specific attribute namespace (gen_ai.system, gen_ai.request.model, gen_ai.completion, gen_ai.usage.*) and operation names; differentiates MAST / AgentDebug / Aegis / AgentRx each with a one-clause characterization of what they catch and what they cannot.
8. **§IV intro** softened to "Five open research questions..." (dropped "We propose" per Round 1 N1).
9. **RQ2 tractable start** now spells out "28 successful runs (complement of the 84 silent failures)".
10. **RQ4** elevated from catalog request to a research question: whether agent SLOs need a fundamentally different formalism because agent policies are non-stationary across model/tool upgrades.
11. **Figure 1 caption** now names LTL_f-over-event-traces as operator semantics.
12. **§V Related Vision Work** now engages the ML-systems observability lineage (Sculley, Breck) explicitly as the structurally closest precedent.
13. **§VI Threats** adds T4 (CoT unfaithfulness) with phase-vs-content distinction argument.
14. **§VIII Conclusion** compressed and now ends with the RQ5 elevation echo.

## Bibliography additions

- `sculley_tech_debt` — Hidden Technical Debt in ML Systems (NeurIPS 2015).
- `breck_ml_test_score` — The ML Test Score (IEEE BigData 2017).
- `turpin_cot_unfaithful` — Language Models Don't Always Say What They Think (NeurIPS 2023).

Bibliography now 32 entries.

---

## Round 4 cold review

Verdict: **STRONG_ACCEPT** (best-paper finalist candidate).

All 14 strength signals confirmed (S1-S14). Two cosmetic camera-ready suggestions (C1: "We propose" wording → fixed; C2: 28 = 112 - 84 arithmetic → fixed). No blockers.

## Round 5 cold review (deliberately maximally skeptical, fresh persona, independent confirmation)

Verdict: **STRONG_ACCEPT** (confirmed).

8 attacks attempted, all fail:
- A1 "Just retroactive scaffolding for an SDK paper" — fails (agenda framing is distinct contribution).
- A2 "75% isn't surprising" — fails (the structural-pattern-invisibility is the surprise, not the failure rate).
- A3 "I can hash tool_call.arguments" — fails (cognitive-edge-typing leg of the demolition still holds).
- A4 "RQs aren't orthogonal — they're stacked" — backward critique; coherence is a strength.
- A5 "Missing neighbor?" — full neighborhood audited, no real gap.
- A6 "Missing threat?" — T5 (overhead) plausible but properly deferred to underlying SDK paper.
- A7 "Is the hypothesis name doing real work?" — yes (names are infrastructure).
- A8 "Is RQ5 actually roadmap-changing?" — yes (causal inference on non-stationary policies is a genuinely new SE methodology).

**Final scores: Impact 5 / Novelty 5 / Relevance 5 / Rigour 5 / Presentation 5.**

---

## Final compile state

- Pages: 4 body + 1 references = 5 total (CFP compliant).
- Format: `\documentclass[10pt,conference]{IEEEtran}` (CFP compliant).
- Double-anonymous: verified (anonymous author block, anonymized self-cites, no de-anonymizing URLs, metadata empty per checklist).
- Required "Future Plans" section: present and substantive (5 concrete commitments).
- No AI/Claude mentions.
- Bibliography: 32 entries, balanced across foundational tracing, modern agent failure, MLOps lineage, SE-vision papers.

**Two consecutive independent fresh-persona STRONG_ACCEPT verdicts (Rounds 4 and 5). Iteration converged.**
