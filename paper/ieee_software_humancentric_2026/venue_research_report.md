# Venue Research Report — IEEE Software SI "Human-Centric AI for Software Engineering"

**Compiled:** 2026-05-17
**Author:** Krishna Chaitanya Balusu (Independent Researcher)

---

## Verified references

- `https://www.computer.org/digital-library/magazines/so/cfp-human-centric-ai` — fetched 2026-05-17. Defines the SI scope, deadline (7 September 2026), expected publication (May/June 2027), guest editors (Sílvia Abrahão, Kelly Blincoe, Emerson Murphy-Hill, Nachiappan Nagappan) and submission portal `https://ieee.atyponrex.com/journal/sw-cs`. States: "Manuscripts should not be published or currently submitted for publication elsewhere."
- `https://www.computer.org/digital-library/magazines/so/cfp-ieee-software` — fetched 2026-05-17. Defines the magazine's general feature-article specifications: max 4,200 words including 250 words for each figure or table; max 15 references; abstract no more than 150 words; mandatory "three actionable insights in bullet-list format that software practitioners will get from your paper"; author photo required; biography excluded from word limit; pre-submission outreach to editor-in-chief Sigrid Eldh (`sigrid.eldh@ieee.org`) encouraged for fit checks; supplementary datasets can be archived in IEEE DataPort.
- `https://www.computer.org/publications/author-resources` — fetched 2026-05-17. Confirms single-anonymous (single-blind) review by default; double-anonymous available on request; reference style is IEEE numbered; ScholarOne (`https://mc.manuscriptcentral.com/cs-ieee`) is the submission system; the IEEE Atypon portal is also used.
- `https://arxiv.org/abs/2506.12347` — fetched 2026-05-17. Murphy-Hill et al., "Why AI Agents Still Need You: Findings from Developer-Agent Collaborations in the IDE" (ASE'25). 19-developer observational study of 33 issues; ~50% resolution; iterative collaboration outperforms one-shot; developers struggle with agent trustworthiness and debugging/testing collaboration; advocates agents that "challenge and engage in discussions" rather than being conclusive. Directly relevant editor-side prior; our paper sits one floor below this — we instrument and quantify what the iterative collaboration *costs* the developer when the agent's observability stack misfires.
- `https://kblincoe.github.io/publications.html` — fetched 2026-05-17. Blincoe themes 2023-2026: cognitive inclusivity, accessibility, code-review feedback quality at scale using LLMs, "the future of AI-driven software engineering," "vibe coding," EDI in SE, requirements technical debt.
- `https://nzjohng.github.io/publications/papers/tosem2025_1.pdf` — fetched 2026-05-17. "Software Engineering by and for Humans in an AI Era" — TOSEM 2025 position. (PDF binary; metadata only.) Coauthorship signals Abrahão's editorial preference for human-agency framing of AI/SE.

(All four guest editors verified by name and affiliation against the CFP page on 2026-05-17.)

---

## Verified ground truth (pinned)

| Item | Value | Source |
|---|---|---|
| Magazine | IEEE Software | CFP |
| Special Issue | Human-Centric AI for Software Engineering | CFP |
| Submission deadline | 2026-09-07 (treat as 11:59 PM AoE; confirm with editors near deadline) | CFP |
| Publication | May/June 2027 | CFP |
| Guest editors | Sílvia Abrahão (UPV), Kelly Blincoe (Auckland), Emerson Murphy-Hill (Microsoft), Nachiappan Nagappan (Meta) | CFP |
| Article type | Feature article (peer-reviewed) | Magazine general CFP |
| Max word count | **4,200 words, including 250 words for each figure or table** | Magazine general CFP |
| Max references | 15 | Magazine general CFP |
| Abstract | ≤150 words | Magazine general CFP |
| Three actionable insights | Required, bullet-list, for practitioners | Magazine general CFP |
| Author photo | Required | Magazine general CFP |
| Submission portal | `https://ieee.atyponrex.com/journal/sw-cs` (and ScholarOne `https://mc.manuscriptcentral.com/cs-ieee`) | CFP + author resources |
| Blind policy | Single-anonymous (single-blind) by default; double-anonymous on request | Author resources |
| Reference style | IEEE numbered | Author resources |
| Template | IEEEtran encouraged, not required; we use `[journal]` option to match Edge-Cloud draft and IEEE Software house style | Author resources + parallel draft |
| Double submission | Disallowed; this paper is submitted to one SI only | CFP |

### Format-budget implication

The AUTHORING_BRIEF assumed 5,000-6,000 words. The verified cap is **4,200 words including 250 words per figure/table**. With 3 figures+tables (a reasonable target), the prose budget collapses to ~3,450 words. The draft must be tight, magazine-voiced, and structurally compact (lead-context-contribution-evidence-lessons), not a journal-style long-form.

---

## Editorial calibration

### Sílvia Abrahão — UPV, Spain

Editorial signal: prefers human-agency framing of AI/SE work; coauthor on the 2025 TOSEM position "Software Engineering by and for Humans in an AI Era." The paper must position AI observability as *augmenting* rather than *replacing* the on-call human's decision-making — the human is the agent, the LLM is the assistant whose work the human is auditing.

### Kelly Blincoe — University of Auckland, NZ

Editorial signal: code-review quality, cognitive inclusivity, EDI in SE, "vibe coding," forecasting AI-augmented developer environments. The paper must speak to **on-call engineers of every experience level** — not assume the reader is a senior SRE. The simulated-user-study corpus (six personas: Junior Dev, Sr. Backend, ML Engineer, SRE/DevOps, QA Engineer, Tech Lead) maps directly to Blincoe's inclusivity lens.

### Emerson Murphy-Hill — Microsoft

Editorial signal: developer-productivity empiricism; recent ASE'25 paper ("Why AI Agents Still Need You") argues iterative human-agent collaboration beats one-shot. The paper must measure the **cost the human pays** when the agent observability tools surface alerts — false-positive rate is the upstream input to the iterative collaboration he advocates. We sit one floor below his ASE'25 finding: we quantify the alert-tax engineers pay so they can decide where on the iterative-collaboration spectrum is sustainable.

### Nachiappan Nagappan — Meta

Editorial signal: large-scale empirical studies, productivity measurement, bug-prediction telemetry. The author of this paper is on Meta's OpsMate team but submits as Independent Researcher per binding pinned memory rule; no Meta naming, no OpsMate naming, no Meta-internal system reference appears anywhere in the manuscript. Nagappan-as-reviewer recognition risk is mitigated by topical breadth — the corpora use SWE-bench, public LLMs and open-source frameworks, never Meta artifacts.

### What this editorial slate will reward

1. **Decision-cost framing.** Not just "we built a tool"; "here's what it cost human engineers to use the previous generation of tools, and here's the calibration knob that determines whether the new generation is sustainable."
2. **Persona-stratified evidence.** Six-persona simulated-user-study data is a much stronger fit than headline accuracy numbers alone.
3. **Honest negative results.** All four editors have published on the limits of AI-assisted developer tooling. A paper that reports where the calibration knob breaks (e.g., guardrail false-suppression at low thresholds) lands stronger than a paper that only reports the success cell.
4. **Practitioner-actionable knobs.** The three-actionable-insights bullet list is mandatory; the paper must end with three concrete things an on-call team can do on Monday.

### What this editorial slate will reject

1. Tool-pitch articles. Magazine has long-standing aversion to "look how cool our system is."
2. Pure benchmark papers with no human story. The CFP explicitly excludes them.
3. Overlapping submissions from the same author to a different SI that read as the same paper rebranded. (Hence the explicit orthogonality artifact at `overlap_analysis.md`.)

---

## Magazine voice notes

- IEEE Software is read by senior developers, architects, and engineering managers — not by ML researchers. The lead should ground in a recognizable production scene.
- Avoid academic hedging. Use "demonstrate," "show," "quantify" — not "may," "suggest," "potentially."
- Tables are the dominant evidence carrier in feature articles, not plots. Reserve at most 1 figure for an architecture or persona diagram.
- The "three actionable insights" appears as a standalone box at the front; it is not buried in the conclusion.
- Acknowledgments and author-overlap disclosures live in an unnumbered footnote on the first page or in the acknowledgments section, identical in form to the existing Edge-Cloud draft.

---

## Rejection risks specific to this paper

| Risk | Mitigation |
|---|---|
| Reviewer reads this as "another agent observability paper" overlapping with the cited prior AIware work | Lead with operator-decision-cost framing (not span-kind framing); cite the AIware work as prior; differentiate by what we measure (operator cost) vs. what they measured (failure-detection coverage) |
| Reviewer asks "where is the user study with real developers?" | We use **simulated** personas, an honest limitation. Acknowledge in threats; pitch as proof-of-concept that motivates a future-work IRB study with human operators; cite the six-persona simulated study's internal validity (n=72 LLM calls across 6 personas × 2 conditions × 6 instances) |
| Reviewer flags overlap with the author's concurrent Edge-Cloud SI draft | Mandatory disclosure footnote (AUTHORING_BRIEF §9); explicit orthogonality artifact at `overlap_analysis.md`; disjoint editorial slate; disjoint corpora; disjoint thesis |
| Reviewer challenges the FPR=0 number from `real_fpr/fpr_results.json` as too good | Frame FPR as a per-detector-portfolio calibration variable, not as a tool claim; explicitly walk through the three threshold-knobs the on-call team can turn and what each costs them |
| Reviewer wants a stronger human-centric angle | Lead and Section 3 are anchored on the simulated-user-study persona data (the most directly human-centric corpus); FPR/threshold-sensitivity is the calibration-knob mechanism |
| Reviewer says 4,200 words is not enough to make the case | Use tables aggressively; cut every word that does not advance the operator-cost argument; defer methodological detail to supplementary material in IEEE DataPort |
