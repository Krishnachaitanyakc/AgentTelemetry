# ICSE 2027 Tool Demonstration & Data Showcase — Venue Research

## Track identity

ICSE 2027 collapses Tool Demonstrations and the Data Showcase into a **single combined track**, titled "Tool Demonstration and Data Showcase Track."

- Official URL: https://conf.researchr.org/track/icse-2027/icse-2027-demonstrations
- HotCRP submission portal: https://icse27demos.hotcrp.com/
- Co-chairs:
  - Shin Hwei Tan (Concordia University, Canada)
  - Mel Ó Cinnéide (University College Dublin & Lero, Ireland)
- Venue: ICSE 2027, Dublin, Ireland, May 2027

## Hard constraints (verified)

| Constraint | Value | Source |
|---|---|---|
| Submission deadline | **2026-10-23 (Fri), 23:59:59 AoE (UTC-12)** | ICSE 2027 demos CFP |
| Page limit | **4 pages MAX, inclusive of references, figures, tables, appendices** | ICSE 2027 demos CFP |
| Template | **IEEE conference, `\documentclass[10pt,conference]{IEEEtran}`** (NO `compsoc`) | ICSE 2027 demos CFP |
| Font sizes | Title 24pt, body 10pt | ICSE 2027 demos CFP |
| Review model | **Single-anonymous** (author names appear on submission) | ICSE 2027 demos CFP |
| Video | **MANDATORY 3–5 minute screencast on YouTube**, accessible during review | ICSE 2027 demos CFP |
| Public availability | **Mandatory.** Tool must be a live website / VM / Docker image / system config; dataset must be in an online repo (Zenodo, Figshare, etc.) | ICSE 2027 demos CFP |
| Optional artifact track | Accepted papers may separately submit to ICSE 2027 Artifact Evaluation for available/reusable/replicated/reproduced badges | ICSE 2027 demos CFP |

## Evaluation criteria (quoted)

> relevance, technical soundness, novelty, video quality, potential applications, and consideration of relevant literature.

## Two paper subtypes within the same track

- **Tool demonstration**: novel aspects of early prototypes or mature tools.
- **Data showcase**: well-motivated, reusable datasets with detailed provenance, methodology, schema, format, access procedure, use cases, limitations, and ethical considerations.

This paper pitches AgentTelemetry as a **tool demonstration** with the 3,780-row benchmark referenced as a downloadable, reusable artifact (light data-showcase flavor inside a tool-demo frame). It is not a full data-showcase paper — that framing is held in reserve for a separate submission if needed.

## Recent ICSE Tool Demo papers (style reference, ICSE 2025 program)

Read for format conventions:
- *A-COBREX: A Tool for Identifying Business Rules in COBOL Programs*
- *AutoRestTest: A Tool for Automated REST API Testing Using LLMs and MARL*
- *GeMTest: A General Metamorphic Testing Framework*
- *HyperCRX 2.0: A Comprehensive and Automated Tool for Empowering GitHub Insights*
- *The Software Librarian: Python Package Insights for Copilot*
- *OptCD: Optimizing Continuous Development*

Pattern observed in titles: short tool name + colon + descriptive subtitle naming the artifact category and domain. Several papers received Artifact Evaluation badges (available/reusable). All are 4 pages IEEE-formatted.

## What kills a Tool Demo at ICSE (PC failure modes)

1. **Not actually publicly available** at submission time (broken pip install, private repo, login wall).
2. **No screencast** or screencast that doesn't show the tool actually running.
3. **No novelty over existing tools** — fatal if the paper does not compare against LangSmith / Langfuse / AgentOps / Phoenix / OpenLIT explicitly.
4. **Vague use case** — every tool demo must lead with one concrete user scenario, not "applies to many domains."
5. **Show, don't tell** — missing code listings, screenshots, or architecture diagrams.
6. **Wrong template** — submissions in the ACM `acmart` or other formats are desk-rejected at IEEEtran venues.
7. **Over-length** — even half a page over 4 is desk-rejected.
8. **Submitting an in-flight research paper compressed into 4 pages** — the demo bar is about installable usability, not novel research findings.

## Single-anonymous notes

- Author names MUST appear on the title page.
- Affiliations may appear.
- No need to redact self-references, GitHub URLs, or screencast links.
- The repo, PyPI package, Zenodo DOI may all carry the author's real identity.

## Submission package required

1. PDF (≤4 pages, IEEEtran 10pt conference).
2. YouTube video URL (3–5 min, public or unlisted but accessible without login).
3. Public tool URL (PyPI + GitHub + Zenodo DOI all qualify).
4. (For data flavor) Dataset URL on Zenodo/Figshare with schema documentation.

## Verified external references (used in artifacts)

- PyPI package: https://pypi.org/project/agenttelemetry/ — version 0.1.0, Apache-2.0, released 2026-03-25, Python ≥3.9 (verified via WebFetch 2026-05-17).
- GitHub: https://github.com/Krishnachaitanyakc/AgentTelemetry — verified from PyPI metadata.
- Zenodo concept DOI: 10.5281/zenodo.20129005 — "AgentTelemetry: A Fault Detection Benchmark and Toolkit for LLM Agent Observability," Balusu, K.C., v0.1.0-aiware2026, 2026-05-12 (verified via Zenodo 2026-05-17).
- Zenodo version DOI: 10.5281/zenodo.20129006 — same snapshot, version-pinned (verified 2026-05-17).
- ICSE 2027 demos CFP: https://conf.researchr.org/track/icse-2027/icse-2027-demonstrations (verified 2026-05-17).
- ICSE 2027 demos HotCRP: https://icse27demos.hotcrp.com/ (verified 2026-05-17).

## Comparison-table competitor verification

| Tool | OSS? | OTel-native? | Source verified |
|---|---|---|---|
| LangSmith | No (SaaS, commercial, no OTel mention) | No | https://docs.langchain.com/langsmith |
| Langfuse | Yes (self-hostable) | Yes (built on OTel) | https://langfuse.com/docs |
| AgentOps | Yes (OSS app) | Not documented as OTel-native | https://docs.agentops.ai/ |
| Arize Phoenix | Yes (community + Arize) | Yes (OTel + OpenInference) | https://arize.com/docs/phoenix |
| OpenLIT | Yes (Apache, self-hosted) | Yes (OTel-native) | https://openlit.io/ |
| **AgentTelemetry** | Yes (Apache-2.0) | Yes (OTel SDK; adds 9 agent span kinds) | this repo |
