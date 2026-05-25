# Venue Research Report — ICSE 2027 NIER

Generated: 2026-05-17 by sub-agent A (verified via WebFetch against
`https://conf.researchr.org/track/icse-2027/icse-2027-new-ideas-and-emerging-results--nier-`).

## 1. Verified scope (verbatim)

> The track invites "innovative, groundbreaking new ideas supported by promising
> initial results."
>
> Includes "Forward-looking ideas" with "preliminary results" and
> "Thought-provoking reflections" with "bold and unexpected results."

## 2. Verified deadlines (AoE, UTC-12h)

| Milestone        | Date                 |
|------------------|----------------------|
| Submission       | **Fri 23 Oct 2026**  |
| Acceptance       | Fri 18 Dec 2026      |
| Camera-ready     | Wed 20 Jan 2027      |

All times **23:59:59 AoE (UTC-12h)**. Conference: Dublin, May 2027.

## 3. Verified page limits

- **4 pages** main text + **1 page** for references only.
- Reference page may contain references only — no overflow body text.

## 4. Verified template

- **IEEE conference proceedings template** (NOT acmart — important).
- LaTeX: `\documentclass[10pt,conference]{IEEEtran}`
- Title: 24pt; body 10pt.
- Authors **must not** include `compsoc` or `compsocconf` options.

## 5. Verified double-anonymous requirements (verbatim)

> "The ICSE 2027 NIER track will employ a double-anonymous review process.
> Thus, no submission may reveal its authors' identities."
> "Authors' names must be omitted from the submission."
> "All references to the author's prior work should be in the third person."

Implications for AgentTelemetry:
- Do **not** name the author.
- Do **not** name the SDK by its public GitHub identity if the URL/name
  de-anonymizes (the AIware paper is public under the author's name and ties
  the SDK to the author). Refer to it as "a recently-released agent-telemetry
  toolkit [Anon]" / "the SDK [Anon]" / cite as "Anonymous Authors, 2026
  (under review)" or omit the link entirely.
- Anonymize prior-work citations to AIware paper: cite in third person, e.g.,
  "Recent work [Anon-1] introduced a 9-kind agent span taxonomy..."

## 6. Submission portal

`https://icse2027-nier.hotcrp.com/`

## 7. Preprint policy (verbatim)

> "Authors have the right to upload preprints on ArXiV or similar sites,
> they must avoid specifying that the manuscript was submitted to ICSE 2027."

## 8. Required section

> Each submission needs a section titled **"Future Plans"** where authors
> outline work to advance their emerging ideas into full papers.

This is mandatory. Reserve ~half a page.

## 9. Verified review criteria (verbatim, 5 axes)

| Axis           | What reviewers assess                                           |
|----------------|-----------------------------------------------------------------|
| **Impact**     | "significance and potential to disrupt current practice"        |
| **Novelty**    | "originality relative to state of the art"                      |
| **Relevance**  | "connection to software engineering"                            |
| **Rigour**     | "soundness and clarity of contribution"                         |
| **Presentation** | "quality of exposition"                                       |

## 10. Attendance

> "At least one author of the paper is required to register for ICSE 2027
> and present the paper."

## 11. PC composition (ICSE 2026 NIER as proxy)

PC chairs (2026): Alessandro Garcia (PUC-Rio), Carolyn Seaman (UMBC).
PC: ~75 senior SE researchers from across NA, EU, AU, BR, IL, IN, CN, JP.
Notable for AgentTelemetry-relevant expertise:
- Tim Menzies (NCSU) — SE empirical methods, will scrutinize evidence
- Prem Devanbu (UC Davis) — LLMs for SE, likely to scrutinize "agent" framing
- Marsha Chechik (Toronto) — formal methods / verification angle
- Cristian Cadar (Imperial) — testing/debugging
- Denys Poshyvanyk (W&M) — program analysis, debugging
- Sebastiano Panichella (Bern) — has authored an ICSE-NIER 2024 paper on
  LLM threats in SE; will recognize this style and demand bold claims with
  honest scope

## 12. NIER style observations (from 2024 prior art)

Reviewing Panichella et al. ICSE-NIER 2024 ("Breaking the Silence: the
Threats of Using LLMs in Software Engineering"):
- Position-oriented; "initiates an open discussion" and "proposes a set of
  guidelines."
- Vision-heavy (~70% vision, 30% illustrative example).
- Frames open problems as researcher and provider guidelines.
- The contribution is the *framing*, not the empirical finding.

NIER reviewers expect:
- A *genuinely novel* framing (not a re-skinned position from prior workshop
  papers).
- A *concrete emerging result* (1 datapoint, surprising, that motivates the
  vision).
- A *tractable* research agenda — 3-5 questions the SE community can pick up
  immediately, not "more research is needed."
- *Tight* writing in 4 pages — no fluff, every paragraph load-bearing.

## 13. Most common NIER rejection reasons (synthesis)

1. **"Not actually new"** — the idea is a variant of an existing position.
   The paper must distinguish from microservice observability, from MLOps
   monitoring, from existing LLM tracing tools (LangSmith, Langfuse,
   AgentOps, OpenLLMetry).
2. **"Too speculative"** — the open questions are too vague to be tractable.
   Each open question must name a concrete artifact (benchmark, formalism,
   metric).
3. **"Padded"** — repetition or excess background eats the 4-page budget.
4. **"Disguised tool paper"** — using NIER to publish a system that should
   have gone to the tool demo track. We must keep the system in the
   background and lead with the *vision*.
5. **"De-anonymized"** — accidental author hints (acknowledgements, GitHub
   URLs, "we previously showed in [Citation Author 2026]").

## 14. Strategy implications for our draft

- Lead with a **concrete vignette** of an agent failure mode that current
  microservice observability cannot represent.
- Position the **emerging result** as one finding (e.g., "84/112 SWE-bench
  agent runs were reasoning loops invisible to vanilla OTel; this fault
  class has no analog in microservice tracing"), not the full benchmark.
- The **vision claim** is: "Agent observability is fundamentally a model of
  open-ended, model-of-the-world reasoning — not request/response telemetry
  — and SE research must develop new abstractions (e.g., typed cognitive
  span kinds, conformance gates, expected-trace specifications)."
- The **research agenda** must include 4-5 *tractable* open questions, each
  naming an artifact to build.
- Keep AgentTelemetry in the background — reference it as "the SDK [Anon]"
  and never cite the AIware paper by author name; cite as third-person
  "[Anon-2026]" or "[Anon-1]".
- Do NOT include the project GitHub URL.
- Do NOT include the author's email or institution.
