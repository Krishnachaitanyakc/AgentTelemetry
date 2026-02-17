# Submitting the AgentTelemetry OTEP to OpenTelemetry

Step-by-step guide for submitting the **Semantic Conventions for Autonomous AI Agent Workloads** OTEP to the [open-telemetry/oteps](https://github.com/open-telemetry/oteps) repository.

---

## Prerequisites

Before starting, ensure you have:

- A GitHub account
- Git installed locally
- Familiarity with the OTEP content in `0000-agent-semantic-conventions.md`
- (Recommended) Read the [OpenTelemetry OTEP repository README](https://github.com/open-telemetry/oteps#readme) for the latest process details

---

## Step 1: Fork the OTEP Repository

1. Navigate to [https://github.com/open-telemetry/oteps](https://github.com/open-telemetry/oteps).
2. Click **"Fork"** in the top-right corner to create a fork under your GitHub account.
3. Clone your fork locally:

   ```bash
   git clone https://github.com/<YOUR_USERNAME>/oteps.git
   cd oteps
   ```

4. Add the upstream remote:

   ```bash
   git remote add upstream https://github.com/open-telemetry/oteps.git
   git fetch upstream
   ```

---

## Step 2: Create a Branch

Create a feature branch for your OTEP:

```bash
git checkout -b otep-agent-semantic-conventions upstream/main
```

---

## Step 3: Determine the OTEP Number

OTEPs are numbered sequentially. To find the next available number:

1. List existing OTEPs in the `text/` directory:

   ```bash
   ls text/ | sort -n | tail -10
   ```

2. Check open pull requests at [https://github.com/open-telemetry/oteps/pulls](https://github.com/open-telemetry/oteps/pulls) to see if any pending PRs have claimed a number.

3. The OTEP number is typically the **PR number** assigned by GitHub when you open the pull request. The common convention is:
   - Start with `0000-` in your file name when drafting.
   - After you open the PR, GitHub assigns a PR number (e.g., `#265`).
   - Rename the file to use that PR number: `text/0265-agent-semantic-conventions.md`.
   - Update the OTEP number inside the document to match.
   - Push the rename as an additional commit to the PR.

> **Important**: Some OTEPs use the PR number as the OTEP number. Check the latest convention in the repository. As of early 2026, the pattern has been to use the PR number.

---

## Step 4: Copy the Formatted OTEP into the Repository

Copy the pre-formatted OTEP file into the `text/` directory of your fork:

```bash
cp /path/to/AgentTelemetry/otep/0000-agent-semantic-conventions.md text/0000-agent-semantic-conventions.md
```

The file `0000-agent-semantic-conventions.md` in this directory has already been formatted to match the OTel OTEP template structure with the following sections:

- Summary
- Motivation
- Explanation
- Internal Details
- Trade-offs and Mitigations
- Prior Art and Alternatives
- Open Questions
- Future Possibilities

---

## Step 5: Verify the Content

Before committing, review the OTEP to ensure:

- [ ] The OTEP number placeholder (`NNNN`) is present (will be updated after PR is opened)
- [ ] All section headings match the OTEP template (`Summary`, `Motivation`, `Explanation`, `Internal details`, `Trade-offs and mitigations`, `Prior art and alternatives`, `Open questions`, `Future possibilities`)
- [ ] The metadata table at the top is complete (status, authors, sponsoring SIG, related OTEPs, created date)
- [ ] All links are valid (especially references to OTEP 0248, the AgentTelemetry GitHub repo, and the Zenodo DOI)
- [ ] Code examples are syntactically correct
- [ ] Tables render correctly in GitHub Markdown preview

---

## Step 6: Commit and Push

```bash
cd /path/to/oteps
git add text/0000-agent-semantic-conventions.md
git commit -m "OTEP: Semantic Conventions for AI Agent Observability

Proposes semantic conventions for observing autonomous AI agent workloads
within OpenTelemetry, including agent-specific span classification, cost
tracking, multi-agent context propagation, and standardized attribute
namespaces for agent, LLM, and tool instrumentation."

git push origin otep-agent-semantic-conventions
```

---

## Step 7: Open the Pull Request

1. Go to your fork on GitHub: `https://github.com/<YOUR_USERNAME>/oteps`
2. Click **"Compare & pull request"** for the `otep-agent-semantic-conventions` branch.
3. Set the **base repository** to `open-telemetry/oteps` and **base branch** to `main`.
4. Use the pre-written PR description from `pr_description.md` in this directory.

### PR Title Format

Use this exact title:

```
OTEP: Semantic Conventions for AI Agent Observability
```

The convention in the oteps repo is: `OTEP: <Short descriptive title>` or simply the title of the proposal.

---

## Step 8: Rename the File with the PR Number

After GitHub assigns a PR number (e.g., `#265`):

1. Rename the file:

   ```bash
   git mv text/0000-agent-semantic-conventions.md text/0265-agent-semantic-conventions.md
   ```

2. Update the OTEP number inside the document (line near the top):

   Change `| **OTEP** | NNNN (draft) |` to `| **OTEP** | 0265 (draft) |`

3. Commit and push:

   ```bash
   git add -A
   git commit -m "Rename OTEP file to match PR number 0265"
   git push origin otep-agent-semantic-conventions
   ```

---

## Step 9: Tag the Relevant SIGs and Maintainers

After opening the PR, add a comment tagging the relevant SIGs for review:

```markdown
cc @open-telemetry/specs-semconv-approvers
cc @open-telemetry/semconv-genai-approvers

This OTEP proposes semantic conventions for AI agent observability, building on top of
the GenAI semantic conventions (OTEP 0248). Requesting review from the Semantic
Conventions SIG and GenAI SIG.
```

### Key SIGs to Engage

| SIG | Relevance | GitHub Team |
|-----|-----------|-------------|
| **Semantic Conventions SIG** | Primary -- this is a semconv proposal | `@open-telemetry/specs-semconv-approvers` |
| **GenAI SIG** | Direct -- extends GenAI conventions for agents | `@open-telemetry/semconv-genai-approvers` |
| **Specification SIG** | Advisory -- context propagation (`agentstate` header) | `@open-telemetry/specs-approvers` |

---

## Step 10: Engage with the OTel Community

### Slack

Join the CNCF Slack workspace and participate in these channels:

- **`#otel-semconv`** -- Semantic Conventions discussions. Post a link to your PR here.
- **`#otel-genai`** -- GenAI-specific discussions. This is the most relevant channel for agent observability.
- **`#otel-specification`** -- For questions about context propagation extensions.

To join CNCF Slack: [https://communityinviter.com/apps/cloud-native/cncf](https://communityinviter.com/apps/cloud-native/cncf)

### SIG Meetings

Attend the relevant SIG meetings to present the OTEP and answer questions:

- **Semantic Conventions SIG**: Meets weekly (check the [OTel community calendar](https://github.com/open-telemetry/community#calendar) for current schedule).
- **GenAI SIG**: Meets regularly (check the community calendar). This is the best venue to present the agent observability proposal.

Meeting agendas are typically managed in Google Docs linked from the [community repository](https://github.com/open-telemetry/community). Add your OTEP to the agenda of an upcoming meeting.

### Mailing List

Subscribe to the OpenTelemetry mailing list on the [CNCF Lists](https://lists.cncf.io/g/cncf-opentelemetry-community) for broader community announcements.

---

## What to Expect During Review

### Timeline

- **Initial feedback**: Expect comments within 1-2 weeks of opening the PR.
- **Active review period**: Typically 2-6 weeks of discussion and iteration.
- **Approval**: Requires approval from the relevant SIG approvers. For semconv OTEPs, this typically means approval from `specs-semconv-approvers`.
- **Merge**: After approval and any required changes.

### Common Review Feedback Areas

Based on the nature of this OTEP, expect discussion on:

1. **Namespace convergence**: The relationship between `llm.*` and existing `gen_ai.*` attributes will likely be the most discussed topic. Be prepared to justify the separate namespace or propose a migration path.

2. **`agentstate` header**: Reviewers may prefer using W3C `tracestate` with a vendor key (e.g., `otel=agent:router`) instead of a new header. Have arguments ready for why a separate header is preferable.

3. **Scope**: Reviewers may suggest splitting this into multiple OTEPs:
   - One for `agent.span_kind` and core agent attributes
   - One for cost tracking conventions
   - One for the `agentstate` propagation header

   Be open to this if the community prefers a more incremental approach.

4. **Requirement levels**: Expect scrutiny on which attributes are `Required` vs `Recommended` vs `Opt-In`. The bar for `Required` is high in OTel semconv.

5. **Compatibility with existing GenAI semconv**: Reviewers will want to ensure this proposal does not conflict with or duplicate OTEP 0248.

### OTEP Lifecycle States

| State | Meaning |
|-------|---------|
| **Draft** | PR is open and under discussion |
| **Approved** | PR has been approved by the relevant SIG |
| **Merged** | OTEP has been merged into the repository |
| **Implemented** | Conventions have been added to the OpenTelemetry Specification |
| **Rejected** | OTEP was closed without merging |
| **Withdrawn** | Author withdrew the proposal |

---

## After the OTEP is Merged

Once the OTEP is merged, the next steps are:

1. **Open a PR to the semantic conventions repository** ([open-telemetry/semantic-conventions](https://github.com/open-telemetry/semantic-conventions)) to add the actual attribute definitions in YAML format.

2. **Implement the conventions** in at least one OpenTelemetry SDK or instrumentation library as a proof of concept. The AgentTelemetry reference implementation serves this purpose.

3. **Update the OTEP status** to reflect implementation progress.

---

## Quick Reference: Key URLs

| Resource | URL |
|----------|-----|
| OTEP Repository | [github.com/open-telemetry/oteps](https://github.com/open-telemetry/oteps) |
| OTEP Template | [text/0000-template.md](https://github.com/open-telemetry/oteps/blob/main/text/0000-template.md) |
| OTEP 0248 (GenAI SemConv) | [text/0248-genai-semconv.md](https://github.com/open-telemetry/oteps/blob/main/text/0248-genai-semconv.md) |
| Semantic Conventions Repo | [github.com/open-telemetry/semantic-conventions](https://github.com/open-telemetry/semantic-conventions) |
| OTel Community Repo | [github.com/open-telemetry/community](https://github.com/open-telemetry/community) |
| CNCF Slack | [communityinviter.com/apps/cloud-native/cncf](https://communityinviter.com/apps/cloud-native/cncf) |
| OTel Community Calendar | [community#calendar](https://github.com/open-telemetry/community#calendar) |
| AgentTelemetry (Reference Impl.) | [github.com/AgentTelemetry](https://github.com/AgentTelemetry) |
| Research Paper (Zenodo) | *Insert Zenodo DOI link when available* |
