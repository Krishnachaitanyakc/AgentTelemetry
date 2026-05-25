# ICSE 2027 Tool Demonstration & Data Showcase — Pre-Submission Compliance Audit

**Audit date:** 2026-05-18
**Paper:** `icse_tool_demo_paper.tex` / `icse_tool_demo_paper.pdf`
**Target:** ICSE 2027 Tool Demonstration and Data Showcase Track
**Deadline:** Friday 23 Oct 2026, 23:59:59 AoE (UTC−12) — **158 days** from today
**Verdict:** **READY TO SUBMIT** with one operational reminder (paste screencast URL at end of abstract field in HotCRP). One low-risk fix has been applied (refs.bib URL/DOI alignment).

---

## Verified References

(All URLs fetched live on 2026-05-18 before this audit was written.)

- `https://conf.researchr.org/track/icse-2027/icse-2027-demonstrations` — Official ICSE 2027 Tool Demonstration and Data Showcase track page. Confirms: HotCRP portal at `https://icse27demos.hotcrp.com/`; deadline 23 Oct 2026 AoE; **4 pages inclusive of all references, figures, tables, appendices**; IEEEtran `\documentclass[10pt,conference]{IEEEtran}` (no compsoc); **single-anonymous** ("the reviewers do know the authors", so author identities must appear); mandatory **YouTube** screencast **3–5 minutes**; artifact must be in easy-to-use form (PyPI / container / Zenodo / Figshare); **ORCID** required for the publishing process; co-chairs Shin Hwei Tan (Concordia) and Mel Ó Cinnéide (UCD/Lero). Notifications 11 Dec 2026; camera-ready 20 Jan 2027.
- `https://icse27demos.hotcrp.com/` — HotCRP submission portal (confirmed in CFP).
- `https://doi.org/10.5281/zenodo.20129005` — HTTP 200; **concept DOI** that redirects to the latest version (currently 20129006). Confirmed via Zenodo API: `conceptdoi = 10.5281/zenodo.20129005` for the record. Resolves cleanly.
- `https://doi.org/10.5281/zenodo.20129006` — HTTP 200; **pinned version DOI** for v0.1.0-aiware2026, dated 2026-05-12, title "AgentTelemetry: A Fault Detection Benchmark and Toolkit for LLM Agent Observability", author Balusu, Krishna Chaitanya. Resolves cleanly.
- `https://pypi.org/pypi/agenttelemetry/json` — HTTP 200; `version: 0.1.0`; upload time `2026-03-25T15:48:27`; summary "OpenTelemetry-based observability for autonomous AI agent systems". The `pip install agenttelemetry==0.1.0` pin is valid.

---

## CFP Requirements — Authoritative Summary

| # | Requirement | Source quote / decision |
|---|---|---|
| R1 | Submission portal | `https://icse27demos.hotcrp.com/` |
| R2 | Deadline | Friday 23 Oct 2026, AoE (UTC−12) |
| R3 | Page limit | "not exceed **four pages for the main text, inclusive of all references, figures, tables, appendices, etc.**" |
| R4 | Template | "IEEE conference submission and formatting instructions"; LaTeX: `\documentclass[10pt,conference]{IEEEtran}` (no compsoc/compsocconf); 24pt title, 10pt main text |
| R5 | Review model | **Single-anonymous** — authors must include their identities |
| R6 | Screencast | **Mandatory**, **3–5 min**, **YouTube**, must be accessible during reviewing. URL is appended to the **end of the abstract field at HotCRP** at submission time |
| R7 | Artifact availability | Easy-to-use form (PyPI / Docker / VM); datasets via Zenodo, Figshare, etc.; "Do not expect reviewers to have to build your code" |
| R8 | ORCID | All authors must obtain an ORCID ID (for the publishing process, not in the PDF) |
| R9 | Required content | Tool: envisioned users, SE challenge addressed, methodology/workflow, validation results / planned-study design. Data showcases: relevance, motivation, source & methodology, format/schema, use-cases, limitations/ethics. **No mandated section headers.** |
| R10 | Co-chairs | Shin Hwei Tan (Concordia, CA); Mel Ó Cinnéide (UCD & Lero, IE) |
| R11 | Timeline | Submission 23 Oct 2026; notification 11 Dec 2026; camera-ready 20 Jan 2027. **No separate abstract deadline.** |

---

## Per-Item Checklist — `icse_tool_demo_paper.tex`

| # | Item | Status | Evidence |
|---|---|---|---|
| C1 | `\documentclass[10pt,conference]{IEEEtran}` | PASS | line 10 of .tex |
| C2 | Page count = 4 exact | PASS | `pdflatex` (3 passes + bibtex) → `Output written on icse_tool_demo_paper.pdf (4 pages, 167122 bytes)` |
| C3 | Single-anonymous: author identities present | PASS | `\IEEEauthorblockN{Krishna Chaitanya Balusu}` + "Independent Researcher, San Francisco, USA, krishnabkc15@gmail.com" |
| C4 | PyPI pin `agenttelemetry==0.1.0` | PASS | PDF text contains the exact string; PyPI JSON confirms 0.1.0 uploaded 2026-03-25 |
| C5 | Zenodo concept DOI `10.5281/zenodo.20129005` | PASS | Cited in abstract, §Availability; resolves HTTP 200 today |
| C6 | Zenodo pinned DOI `10.5281/zenodo.20129006` | PASS | Cited in §Evidence and §Availability; resolves HTTP 200 today |
| C7 | Screencast URL placeholder in PDF | PASS | `https://youtu.be/AGENTTELEMETRY-ICSE27-DEMO` in §Availability |
| C8 | Competitor comparison table (5 rows) | PASS | Table II contains rows for LangSmith, Langfuse, AgentOps, Phoenix, OpenLIT, plus AgentTelemetry — each with concrete OSS / OTel-native / span-type / adapter / analysis / semconv / self-host wedge |
| C9 | Listings 1, 2, 3 present | PASS | `lst:manual` (manual instrumentation), `lst:auto` (LangChain auto), `lst:trace` (Jaeger-style trace + AnomalyDetector REPL transcript) |
| C10 | Tool Availability statement | PASS | §V "Availability and Reproducibility" — install, source, archived artifact, screencast, semantic conventions |
| C11 | IEEE Index Terms / Keywords | PASS | `\begin{IEEEkeywords}` block on line 92 |
| C12 | No `[?]` undefined-reference markers in PDF | PASS | grep of extracted PDF text returns 0 matches |
| C13 | Bib compiles, all `\cite{}` resolve | PASS | bibtex exit 0; 0 LaTeX warnings on final pass |
| C14 | Required content for tool demonstrations (envisioned users / SE challenge / methodology / validation) | PASS | Abstract + §I + §II + §III + §IV + §V cover all four explicitly |

---

## Fixes Applied This Pass

**FIX-01 (low-risk, already applied):** `refs.bib` had a mismatched `doi`/`url` pair in the `agenttelemetry_zenodo` entry — `doi = 10.5281/zenodo.20129006` but `url = https://doi.org/10.5281/zenodo.20129005`. Both DOIs resolve so this was not a desk-reject hazard, but the asymmetry could confuse reviewers verifying the artifact. The `url` now matches the `doi` (`20129006`). The PDF re-compiled cleanly to exactly 4 pages with zero warnings.

---

## Fixes NOT Applied (out of scope / would risk pagination)

- **ORCID line in author block** — CFP only requires ORCID "for the publishing process" (post-acceptance metadata), not in the submitted PDF. No change to the .tex is needed pre-submission.
- **Add explicit "Tool Availability" / "Reproducibility" section header phrasing** — CFP does not mandate specific section headers. §V is already titled "Availability and Reproducibility", which covers both expectations.

---

## Submission-Day Steps (one-page runbook)

1. **HotCRP login**
   - URL: `https://icse27demos.hotcrp.com/`
   - Ensure HotCRP account email matches the `krishnabkc15@gmail.com` author email.

2. **Author metadata**
   - Add author: Krishna Chaitanya Balusu, Independent Researcher, San Francisco, USA.
   - Attach ORCID ID in the author profile (required by the publishing process — get one at `https://orcid.org/` if not already obtained; it takes ~5 minutes).

3. **Abstract field**
   - Paste the paper's abstract text.
   - **CRITICAL:** Append the screencast URL on the last line of the abstract field, exactly as the CFP requires: e.g., `Screencast: https://youtu.be/<ACTUAL_VIDEO_ID>`. Replace the placeholder `AGENTTELEMETRY-ICSE27-DEMO` with the real YouTube video ID before submission.

4. **Artifact / data link**
   - Paste the Zenodo concept DOI (`https://doi.org/10.5281/zenodo.20129005`) into the artifact-link field. The concept DOI always resolves to the latest version; reviewers can click through to the pinned 20129006 from there.
   - List the PyPI page (`https://pypi.org/project/agenttelemetry/`) and GitHub repo (`https://github.com/Krishnachaitanyakc/AgentTelemetry`) as additional artifact links.

5. **PDF upload**
   - Upload `icse_tool_demo_paper.pdf` (4 pages, 167122 bytes as of this audit).
   - Confirm IEEE PDF eXpress validation if HotCRP runs it (optional, not required pre-acceptance).

6. **Screencast (must be live before reviewing begins)**
   - Record the 3–5 minute demo per `REQUEST_FOR_SCREENCAST.md`.
   - Upload to YouTube as **Unlisted** (NOT private — reviewers without accounts must be able to play it).
   - Replace `AGENTTELEMETRY-ICSE27-DEMO` placeholder in (a) the abstract field at HotCRP and (b) §V of the PDF (re-upload PDF after edit) with the real YouTube video ID.

7. **Final pre-click verification**
   - Open the PDF on a clean machine, confirm 4 pages, confirm both Zenodo DOIs resolve, confirm YouTube link plays in an incognito window, confirm `pip install agenttelemetry==0.1.0` works in a fresh venv.
   - Submit.

---

## Zenodo DOI Resolve Status — Confirmed 2026-05-18

| DOI | Type | HTTP status | Resolves to |
|---|---|---|---|
| `10.5281/zenodo.20129005` | Concept (all versions) | **200 OK** | `https://zenodo.org/records/20129006` (latest version) |
| `10.5281/zenodo.20129006` | Pinned v0.1.0-aiware2026 | **200 OK** | `https://zenodo.org/records/20129006` |

Both resolve. No desk-reject hazard. Zenodo API confirms `conceptdoi = 10.5281/zenodo.20129005` for the record, validating that the paper correctly distinguishes concept vs. pinned DOI in its claims.

---

## Final Verdict

**READY TO SUBMIT.** Paper is fully compliant with the official CFP. Page count is 4 exact, references resolve, artifact URLs resolve, screencast placeholder is in place, comparison table is concrete, single-anonymous review model is satisfied (author identity present). One low-risk URL/DOI consistency fix has been applied to `refs.bib`.

**Two operational reminders for submission day:**
1. Append the real YouTube screencast URL to the end of the HotCRP **abstract field** (per CFP wording), in addition to leaving it in §V of the PDF.
2. Obtain an ORCID ID for the publishing process.

158 days remain until deadline.
