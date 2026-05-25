# OVERLAP_RISK.md — STOP CONDITION TRIGGERED

**Date:** 2026-05-17
**Target directory:** `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_edgecloud_2026/`
**Triggered by:** CLAUDE.md rule + user task brief explicit instruction:
> "If overlap with existing IEEE Software draft cannot be cleanly distinguished, STOP and write `OVERLAP_RISK.md`."

---

## 1. Bottom line

**The existing draft at `paper/ieee_software_2026/ieee_software_paper.tex` is already targeted at the IEEE Software Special Issue: "The Edge-Cloud Continuum" — the same SI the user is now asking for a second paper for.** Same target journal, same special issue, same deadline (2026-07-07), same submission portal, same guest editors, same author. Proceeding would constitute a **double submission of two papers by one author to one editorial slate**, which is a serious venue-conduct problem that should not be initiated without the user's explicit acknowledgement of the situation.

The user's task brief describes the existing draft as "an ACTIVE DRAFT for a DIFFERENT IEEE Software submission" with a "DIFFERENT special issue." That description does not match the ground truth in the repo. I am stopping per the rule rather than guessing which side is correct.

---

## 2. Verified evidence (read directly from the repo this session)

### 2.1 The existing draft explicitly names the same SI

File: `paper/ieee_software_2026/ieee_software_paper.tex`, lines 1–6:
```
% IEEE Software Magazine Feature Article — Special Issue: The Edge-Cloud Continuum
% Submission deadline: July 7, 2026
% Submission portal: https://ieee.atyponrex.com/journal/sw-cs
% Article type: Feature article (Empirical study + practitioner experience report)
% Target length: ~5,000-6,000 words (IEEE Software feature article convention)
% Author: Krishna Chaitanya Balusu — Independent Researcher
```

The title (line 19) is:
> "When Telemetry-Driven Interventions Don't Transfer: A Cross-Tier Replication Study of Closed-Loop Agent Recovery via Vendor Agent CLIs for Edge-Cloud Deployments"

The IEEEkeywords (line 37) include `edge-cloud continuum`.

### 2.2 The existing OUTLINE.md confirms the SI is the same

File: `paper/ieee_software_2026/OUTLINE.md`, lines 4–7:
```
**Document date:** 2026-05-13
**Target deadline:** July 7, 2026 (8 weeks from today)
**Target venue:** IEEE Software, Special Issue: "The Edge-Cloud Continuum: Software Challenges and Innovations" (Mar/Apr 2027 publication)
**Submission portal:** https://ieee.atyponrex.com/journal/sw-cs
```

Line 184 confirms the guest editors are verified:
> "Guest editors: Davide Taibi, Schahram Dustdar, Guodong Wang, Adel N. Toosi | Same | YES"

### 2.3 Side-by-side comparison

| Dimension | Existing draft (`ieee_software_2026/`) | Proposed new paper (`ieee_software_edgecloud_2026/`) |
|---|---|---|
| Target journal | IEEE Software | IEEE Software |
| Special issue | "The Edge-Cloud Continuum: Software Challenges and Innovations" | "Edge–Cloud Continuum" (per user brief) |
| Deadline | July 7, 2026 | July 7, 2026 (per user brief) |
| Submission portal | `https://ieee.atyponrex.com/journal/sw-cs` | (same — only one IEEE Software portal) |
| Guest editors | Taibi, Dustdar, Wang, Toosi | (same — same SI) |
| Author | Krishna Chaitanya Balusu (Independent Researcher) | Krishna Chaitanya Balusu (Independent Researcher) |
| SDK / project | AgentTelemetry | AgentTelemetry |
| CFP scope keyword being hit | "Observability, SRE & AIOps for edge-cloud systems" | "Observability and SRE/AIOps" (per user brief) |
| Status | Drafted; 3 cold-review rounds done by 2026-05-16; PDF compiled | Not started |

These are not two different special issues. They are one SI described two ways.

---

## 3. Why I am stopping rather than proceeding

The user's task brief gives me an explicit instruction:

> "STEP 6 — Outputs … RULES: … If overlap with existing IEEE Software draft cannot be cleanly distinguished, STOP and write OVERLAP_RISK.md."

The task brief also asserts the existing draft is "for a DIFFERENT IEEE Software submission" and a "DIFFERENT special issue." Both of these claims contradict the actual contents of the existing draft and outline files.

There are three live possibilities, only the user can resolve:

1. **The user mis-remembered the existing draft's target SI.** The existing draft is in fact the IEEE Software Edge-Cloud Continuum submission, and writing a second one would be a duplicate submission to the same editorial slate. Action: do not write a second paper.
2. **The user intends to retarget the existing draft to a different IEEE Software issue** (e.g., a regular issue, a different SI on AI/ML, or a different magazine entirely) and wants this new paper to take over the Edge-Cloud Continuum slot. Action: confirm and reassign before writing.
3. **A new SI titled something like "Edge–Cloud Continuum" exists at IEEE Software that is distinct from "The Edge-Cloud Continuum: Software Challenges and Innovations" (Mar/Apr 2027).** I have not verified this. The naming would be almost identical, the deadline would coincide, and the scope ("Observability and SRE/AIOps", "MLOps on the continuum") matches the existing SI verbatim. This is the least likely interpretation, but cannot be excluded without a fresh web fetch of the IEEE Software CFP list.

The OUTLINE.md in the existing draft (line 188) notes that some metadata items (page limit, anonymization policy) are unverified, but the **identity of the SI** is verified (line 183–184 of that outline). The existing draft has been actively iterated this month — three cold-review rounds dated 2026-05-16 are in the folder.

Proceeding without resolving this would risk:
- Submitting two papers by the same author to the same Special Issue editorial team (a venue-conduct problem; IEEE Software, like most magazines, expects one submission per author per SI).
- Wasted effort if the new paper duplicates the existing one's framing (both would naturally land on AIOps + observability across the continuum, the only AgentTelemetry-related angle that fits the CFP scope).
- Producing content that genuinely cannot be made non-overlapping, because the only practitioner-facing IEEE Software story that AgentTelemetry supports — agent observability across heterogeneous deployment tiers — is exactly the existing draft's story.

---

## 4. Could a non-overlapping paper exist for the same SI from the same author?

Briefly considered before stopping. The CFP scope (per user brief) lists:
- Observability and SRE/AIOps — taken by the existing draft.
- MLOps on the continuum — possible angle, but AgentTelemetry is not an MLOps tool; it is an agent observability SDK. Any MLOps framing would be strained.
- (Other CFP items not enumerated in the brief; verifying would require fresh fetch of the IEEE Software CFP page.)

Even if an angle were technically distinguishable, the same author submitting two papers to the same SI editorial team is not standard practice and should be the user's call, not mine.

---

## 5. What I need from the user to unblock

Please confirm one of the following so I can proceed correctly:

**Option A — One submission only.** The existing `paper/ieee_software_2026/` draft is your Edge-Cloud Continuum submission. Cancel this new task; no second paper.

**Option B — Retarget the existing draft.** You want the existing `paper/ieee_software_2026/` draft to go to a different venue (which one?), and you want this new `ieee_software_edgecloud_2026/` paper to be the Edge-Cloud Continuum submission. If so, confirm the existing draft's new venue, and I'll proceed with this new one as the sole Edge-Cloud Continuum submission.

**Option C — Different SI than I think.** You have evidence of a *different* IEEE Software SI also called "Edge–Cloud Continuum" with a 2026-07-07 deadline that is distinct from the existing draft's "The Edge-Cloud Continuum: Software Challenges and Innovations" (Mar/Apr 2027 publication). Please share the CFP URL so I can verify and proceed.

**Option D — Override.** Acknowledge the duplicate-submission concern and explicitly instruct me to write the second paper anyway. I will proceed, but the new draft will need a genuinely orthogonal angle (e.g., MLOps-on-continuum, or a methods/tooling-only piece) and the cover letter will need to disclose the parallel submission.

---

## 6. What I did NOT do (per the STOP rule)

- Did not run the venue-research sub-agent (would have re-verified the same CFP the existing OUTLINE already verified).
- Did not run the reviewer-persona sub-agent.
- Did not write `outline.md`, `ieee_sw_edgecloud_paper.tex`, `refs.bib`, `venue_research_report.md`, or any other artifact in the new directory beyond this file.
- Did not begin any cold-review loop.
- Did not compile any PDF.

The target directory `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_edgecloud_2026/` was created and contains only this `OVERLAP_RISK.md`.

---

## 7. Verified references (per CLAUDE.md verified-references-block ritual)

- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/ieee_software_paper.tex` — read in full this session. Header comments lines 1–6 name the SI as "Edge-Cloud Continuum" and the deadline as July 7, 2026. Title (line 19) and keywords (line 37) confirm edge-cloud focus.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/ieee_software_2026/OUTLINE.md` — read in full this session. Lines 4–7 name the SI as "The Edge-Cloud Continuum: Software Challenges and Innovations" with Mar/Apr 2027 publication and 2026-07-07 deadline. Verification log (lines 178–188) confirms the SI identity, submission portal, and guest editors were verified on 2026-05-13.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/paper/` directory listing — checked this session. The `ieee_software_2026/` directory contains three cold-review reports dated 2026-05-16, a data-inventory verification, and a compiled PDF, confirming the draft is actively in flight.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/CLAUDE.md` — read this session. Contains GitHub-engagement guidance for the project but no instructions overriding the OVERLAP_RISK STOP rule.
- `/Users/kcbalusu/Desktop/Project/research/AgentTelemetry/README.md` — read this session. Confirms AgentTelemetry's scope (9 span kinds, 7 adapters, 4 analysis modules, 3,780-row benchmark) but does not bear on the overlap question.
- Workspace graph (`/Users/kcbalusu/Desktop/Project/artifacts/workspace-graph/GRAPH_REPORT.md`) freshness check: last modified 2026-05-11, 6 days old — within the 7-day freshness window. Not consulted for SI metadata, which was verified from the in-repo OUTLINE.md instead.

External CFP URLs *not* refetched this session: `https://www.computer.org/digital-library/magazines/so/cfp-edge-cloud-continuum` (the OUTLINE.md already verified this on 2026-05-13 and recorded the SI title, deadline, portal, and guest editors). If the user wants me to refetch and confirm the SI is still open and has not been split into two issues, I can do so on the next turn.
