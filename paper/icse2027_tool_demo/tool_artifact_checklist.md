# Tool Artifact Checklist — AgentTelemetry ICSE 2027 Tool Demo Submission

ICSE 2027 Tool Demonstrations require **all four** of the items below to be live and publicly reachable at submission time (2026-10-23 AoE).

## 1. Publicly installable tool — **READY**

- **PyPI**: https://pypi.org/project/agenttelemetry/
  - Version 0.1.0 (released 2026-03-25, Apache-2.0).
  - One-command install: `pip install agenttelemetry`.
  - Optional extras: `agenttelemetry[langchain|crewai|autogen|anthropic|openai|llamaindex|all]`.
- **GitHub source**: https://github.com/Krishnachaitanyakc/AgentTelemetry
  - License: Apache-2.0.
  - README has Quickstart + framework adapter table + analysis module table.
  - CONTRIBUTING.md present.
- **Status**: GREEN. No action required before submission.

## 2. Public dataset — **READY** (Zenodo)

- **Concept DOI**: https://doi.org/10.5281/zenodo.20129005
- **Pinned version DOI** (recommended to cite): https://doi.org/10.5281/zenodo.20129006
- Title: "AgentTelemetry: A Fault Detection Benchmark and Toolkit for LLM Agent Observability."
- Snapshot version: `v0.1.0-aiware2026`, 2.9 MB zip.
- Contains source + benchmarks (3,780-row `results_full.tsv`).
- **Status**: GREEN. Cite the version DOI on the title page.

## 3. Screencast (3–5 minutes, YouTube) — **MUST BE RECORDED**

The screencast does not yet exist. The paper LaTeX includes a placeholder URL `https://youtu.be/AGENTTELEMETRY-ICSE27-DEMO` to be replaced.

See `REQUEST_FOR_SCREENCAST.md` for the exact shot-list and script.

- **Status**: RED — blocks submission. Owner: human, before 2026-10-23.

## 4. HotCRP submission — **PORTAL READY**

- URL: https://icse27demos.hotcrp.com/
- Single-anonymous (author names appear).
- Expected uploads: paper PDF, video URL (in PDF + on HotCRP), supplementary archive (optional).

## Bonus — Artifact Evaluation Track

Accepted papers may separately submit to the ICSE 2027 Artifact Evaluation track for `Available`, `Reusable`, `Replicated`, `Reproduced` badges. The AgentTelemetry artifact is already structured for this — same Zenodo archive + pinned `requirements.lock` + reproduction commands in README — and should be submitted after acceptance.

## Pre-submission gate

- [x] PyPI v0.1.0 reachable
- [x] GitHub repo public with README + LICENSE
- [x] Zenodo DOI resolves to the v0.1.0-aiware2026 snapshot
- [ ] YouTube screencast uploaded (3–5 min, public or unlisted)
- [ ] PDF compiled cleanly to exactly 4 pages
- [ ] HotCRP submission entered
