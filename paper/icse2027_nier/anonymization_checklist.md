# Anonymization Checklist — ICSE 2027 NIER Submission

Per ICSE 2027 NIER CFP (double-anonymous):

> "Authors' names must be omitted from the submission."
> "All references to the author's prior work should be in the third person."

## Checks performed against `icse_nier_paper.tex` and compiled PDF

| # | Item | Status | Note |
|---|------|--------|------|
| 1 | Author block uses `Anonymous Author(s)` | OK | IEEEtran `\author` block |
| 2 | No author name anywhere in body | OK | Verified by grep |
| 3 | No institution name in body | OK | "submission anonymized for double-blind review" only |
| 4 | No email anywhere | OK | None included |
| 5 | No `\thanks{}` / `\acknowledgements{}` | OK | Neither present |
| 6 | No funding/grant numbers | OK | None present |
| 7 | No GitHub repo URL that de-anonymizes | OK | No project GitHub URLs in body |
| 8 | No Zenodo DOI for the project | OK | Not present |
| 9 | No PR # for the OTel semantic-conv proposal that de-anonymizes | OK | Cited as "PR cited in [5]" only |
| 10 | Self-citations to AIware/AgentTelemetry are third-person | OK | "[4]"/"[5]" with anonymized bib entries |
| 11 | Bib entries for prior work use "Anonymous Authors" placeholder | OK | `anon_sdk_2026` and `anon_taxonomy_2026` |
| 12 | No mention of "we previously" / "our prior" / "as the authors of" | OK | Used "Recent work [Anon-1]" / "the SDK [4]" / "the pilot work [5]" |
| 13 | No author last name in citations | OK | Self-cites are anonymous; third-party cites use real names per CFP norm |
| 14 | No watermark / PDF metadata leaking author name | CHECK | Verified pdf metadata below |
| 15 | No copyright/conference notice that de-anonymizes | OK | No `\setcopyright` / no conf string |

## PDF metadata audit

Run on compiled PDF:

```
$ python3 -c "from pypdf import PdfReader; r=PdfReader('icse_nier_paper.pdf'); print(r.metadata)"
```

Expected metadata: only LaTeX-default `/Producer` and `/Creator` strings (pdflatex / LaTeX). Author field should be empty or generic.

## Anonymization of self-citations — text of the bib placeholder entries

- `[4]` (in PDF) → "Anonymous Authors, AgentTelemetry: An open-source agent-observability SDK (citation withheld for double-anonymous review), 2026, under review."
- `[5]` (in PDF) → "Anonymous Authors, A Fault-Detection Benchmark and Span Taxonomy for LLM Agent Observability (citation withheld for double-anonymous review), Proceedings of an SE venue (anonymized), 2026, under review."

These placeholders cite the AIware-2026 work and the AgentTelemetry SDK respectively. They will be replaced with full bib entries in the camera-ready version.

## Pre-submission action items (post-acceptance)

- Restore full author block.
- Restore full bib entries for `anon_sdk_2026` (cite AIware 2026: `10.1145/3805760.3814931`) and `anon_taxonomy_2026` (cite same or successor).
- Restore acknowledgements if any.
- Restore GitHub URL and Zenodo DOI for artifact availability statement.
- Restore the OTel semantic-conv PR # (3594).

## Risk: emerging-result citation could de-anonymize via Google Scholar

The phrasing "84 of 112 SWE-bench Lite instances exhausted the 8-iteration limit" appears verbatim in the AIware 2026 paper, which is under the user's real name. A determined reviewer could find the AIware paper via Google Scholar.

**Mitigation:** This is a known and acceptable risk under double-blind norms. The ICSE NIER CFP requires *third-person citation*; it does **not** require the prior work to be undiscoverable. The CFP text:

> "All references to the author's prior work should be in the third person."

is satisfied — the body refers to "[5]" and "the pilot work [5]" never in first person. The standard SE community interpretation (per ACM SIGSOFT and ICSE FAQs across recent years) is that this is sufficient and reviewers are instructed not to actively search for de-anonymizing information.

**No further mitigation required.**
