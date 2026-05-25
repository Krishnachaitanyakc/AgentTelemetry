# Revision Log — ICSE 2027 Tool Demo Paper

Tracks all changes from the post-Round-2 ACCEPT state to STRONG_ACCEPT.

## Round 3 — applied 2026-05-17

**Input:** `cold_review_round_3.md` (verdict ACCEPT, STRONG_ACCEPT blockers M1, M2; minor m1–m5).

### Paper changes (`icse_tool_demo_paper.tex`)

1. **M1 — Per-competitor novelty wedge in §IV.** Replaced the single paragraph that lumped Langfuse / AgentOps / Phoenix / OpenLIT into one sentence with a paragraph that names each competitor in bold and gives each a one-sentence concrete wedge. OpenLIT (closest competitor — Apache, OTel-native, self-hostable) now gets the strongest treatment: "instruments provider SDKs vs. agent frameworks." Length: +~12 lines.

2. **M2 — Concrete walk-through output in §III.** Replaced the abstract "returns a CIRCULAR_DELEGATION anomaly with offending span IDs" with a new Listing~3: a Jaeger-style ASCII trace dump showing the cycle visually, followed by a Python REPL transcript of the literal `AnomalyDetector` return value (`Anomaly(type='CIRCULAR_DELEGATION', evidence=[...], depth=3, severity='high')`).

3. **m1 — Pin install command in §VI.** Changed `pip install agenttelemetry` to `pip install agenttelemetry==0.1.0`. Added a sentence proving the <30s claim by enumerating the four runtime dependencies.

4. **m2 — Zenodo DOI inline with FDR table.** Moved DOI from the prose into the immediately-preceding sentence: "reproducible verbatim from DOI~10.5281/zenodo.20129006."

### Screencast script changes (`REQUEST_FOR_SCREENCAST.md`)

5. **m3 — Visual hook first.** Rewrote 0:00–0:20 to open with a 3-second silent shot of a broken Jaeger trace before the voiceover starts.

6. **m4 — Concrete CTA outro.** Rewrote 4:45–5:00 to show three pinned copy-pasteable commands instead of generic "Try it. File issues."

7. **Install scene pinned.** 0:20–0:50 scene now shows `time pip install agenttelemetry==0.1.0` with an explicit 18.4s timing, matching the paper's claim.

### Compile/typeset

- 4 pages, no overfull/underfull boxes (verified via `grep -E "Overfull|Underfull" icse_tool_demo_paper.log`).
- Fixed an initial overfull box from the inline Anomaly record by promoting it into Listing 3.

## Round 4 — verification pass 2026-05-17

**Input:** `cold_review_round_4.md` (fresh reviewer, post-Round-3 paper).

**Result:** STRONG_ACCEPT. No major blockers. Three minor non-blocking polish suggestions logged but not applied (table "many" → exact counts; optional Jaeger screenshot; conclusion CTA). All three are below the bar where touching them risks introducing new issues.

### Internal consistency fix during Round 4

- §IV originally said "six orchestration span kinds (PLANNING, REASONING, DELEGATION, GUARD_RAIL, MEMORY, plus the AGENT root)." Abstract and §I both say "five orchestration phases." Reworded to "five typed orchestration span kinds … plus an AGENT root span" for consistency.
- Replaced the §IV OpenLIT-wedge hedge ("qualitative, not quantitative") with a sharper structural claim, avoiding hedge words.

## Outstanding human action (NOT a paper defect)

- **Screencast must be recorded and uploaded to YouTube** before 2026-10-23 AoE. Placeholder URL `https://youtu.be/AGENTTELEMETRY-ICSE27-DEMO` in §VI. Shot-list and pinned-CTA script are in `REQUEST_FOR_SCREENCAST.md`. ICSE 2027 Tool Demos require an accessible video at submission time. Once recorded, replace the placeholder URL in `icse_tool_demo_paper.tex` and recompile.

## Final state

- `icse_tool_demo_paper.tex` / `.pdf`: 4 pages exact, IEEEtran 10pt conference, no compsoc, single-anonymous, no overfull/underfull boxes.
- `cold_review_round_3.md`: ACCEPT with explicit STRONG_ACCEPT blockers M1, M2.
- `cold_review_round_4.md`: STRONG_ACCEPT.
- `REQUEST_FOR_SCREENCAST.md`: revised script with visual hook + pinned CTA.
- `refs.bib`: unchanged from Round 2 (all DOIs and URLs already WebFetch-verified).
