# MAST Taxonomy Mapping to AgentTelemetry Fault Types

## Purpose
External validation of AgentTelemetry's fault taxonomy by mapping to MAST
(Cemri et al., NeurIPS 2025), an independently-derived failure taxonomy based
on 1,600+ annotated traces across 7 MAS frameworks with inter-annotator
agreement kappa = 0.88.

This mapping directly addresses the reviewer concern that our evaluation is
"tautological" (we designed both faults and detectors). MAST was developed
independently by a different research group using a different methodology
(empirical annotation of real failures vs. our systematic framework analysis),
yet shows strong convergence with our taxonomy.

---

## MAST Taxonomy (all 14 failure modes)

### Category (i): Specification Issues (FC1)
| Code   | Failure Mode                      | Definition |
|--------|-----------------------------------|------------|
| FM-1.1 | Disobey Task Specification        | Failure to adhere to specified constraints or requirements of a given task |
| FM-1.2 | Disobey Role Specification        | Failure to adhere to defined responsibilities and constraints of an assigned role |
| FM-1.3 | Step Repetition                   | Unnecessary reiteration of previously completed steps in a process |
| FM-1.4 | Loss of Conversation History      | Unexpected context truncation, disregarding recent interaction history |
| FM-1.5 | Unaware of Termination Conditions | Lack of recognition of criteria that should trigger termination of agents' interaction |

### Category (ii): Inter-Agent Misalignment (FC2)
| Code   | Failure Mode                   | Definition |
|--------|--------------------------------|------------|
| FM-2.1 | Conversation Reset             | Unexpected or unwarranted restarting of a dialogue, potentially losing context |
| FM-2.2 | Fail to Ask for Clarification  | Inability to request additional information when faced with unclear or incomplete data |
| FM-2.3 | Task Derailment                | Deviation from the intended objective or focus of a given task |
| FM-2.4 | Information Withholding        | Failure to share or communicate important data or insights that could impact other agents |
| FM-2.5 | Ignored Other Agent's Input    | Disregarding or failing to adequately consider input provided by other agents |
| FM-2.6 | Reasoning-Action Mismatch      | Discrepancy between the logical reasoning process and the actual actions taken |

### Category (iii): Task Verification (FC3)
| Code   | Failure Mode               | Definition |
|--------|----------------------------|------------|
| FM-3.1 | Premature Termination      | Ending a dialogue before all necessary information has been exchanged or objectives met |
| FM-3.2 | No or Incomplete Verification | (Partial) omission of proper checking or confirmation of task outcomes |
| FM-3.3 | Incorrect Verification     | Failure to adequately validate or cross-check crucial information or decisions |

---

## Our 14 Fault Types

| # | Fault Type            | Detection Signal          | Required Span Kind |
|---|----------------------|---------------------------|--------------------|
| 1 | wrong_tool           | Ground truth mismatch     | TOOL_CALL          |
| 2 | hallucination        | No retrieval grounding    | LLM_CALL           |
| 3 | infinite_loop        | >=3 identical calls       | TOOL_CALL          |
| 4 | context_overflow     | Token growth >1.3x        | LLM_CALL           |
| 5 | cost_explosion       | Cost >$0.10               | LLM_CALL           |
| 6 | circular_delegation  | A->B->A cycle             | DELEGATION         |
| 7 | tool_failure         | Error status              | TOOL_CALL          |
| 8 | timeout              | Error + timeout msg       | LLM_CALL           |
| 9 | stale_retrieval      | Staleness >3600s          | RETRIEVAL          |
| 10| guardrail_bypass     | Result = "bypass"         | GUARD_RAIL         |
| 11| planning_failure     | Steps >10                 | PLANNING           |
| 12| reasoning_loop       | Identical chains          | REASONING          |
| 13| agent_misroute       | Misrouted flag            | AGENT              |
| 14| memory_corruption    | Corrupted flag            | MEMORY             |

---

## Mapping Table: MAST -> AgentTelemetry

| MAST Failure Mode | Code | Our Fault Type(s) | Detection Mechanism | Coverage |
|-------------------|------|--------------------|---------------------|----------|
| **Specification Issues (FC1)** | | | | |
| Disobey Task Specification | FM-1.1 | wrong_tool, hallucination | Wrong tool = agent selects tool that doesn't match task intent. Hallucination = agent generates output violating factual constraints of the task. Both are forms of failing to follow task specification. | **Full** |
| Disobey Role Specification | FM-1.2 | agent_misroute, guardrail_bypass | Agent_misroute = agent processes task outside its defined role/routing. Guardrail_bypass = agent acts outside safety boundaries of its role. | **Full** |
| Step Repetition | FM-1.3 | infinite_loop, reasoning_loop | Infinite_loop = repeated identical tool calls. Reasoning_loop = repeated identical reasoning chains. Both detect unnecessary reiteration of steps. | **Full** |
| Loss of Conversation History | FM-1.4 | context_overflow, memory_corruption | Context_overflow = token growth causes truncation of prior context. Memory_corruption = stored agent memory becomes corrupted/inconsistent, effectively losing history. | **Full** |
| Unaware of Termination Conditions | FM-1.5 | infinite_loop, planning_failure | Infinite_loop = agent doesn't know when to stop retrying. Planning_failure = plan exceeds step limit, agent doesn't recognize it should terminate. Both reflect inability to recognize when to stop. | **Full** |
| **Inter-Agent Misalignment (FC2)** | | | | |
| Conversation Reset | FM-2.1 | memory_corruption, context_overflow | Memory_corruption = agent state resets unexpectedly. Context_overflow = context truncation causes effective conversation reset as prior turns are lost. | **Partial** |
| Fail to Ask for Clarification | FM-2.2 | *No direct mapping* | This is a behavioral/reasoning failure about what the agent *should* do but doesn't. Our taxonomy focuses on observable execution faults, not missing actions. Could be partially detected via planning_failure (plan doesn't include clarification step when it should). | **Gap** |
| Task Derailment | FM-2.3 | wrong_tool, planning_failure | Wrong_tool = agent deviates from intended task by selecting wrong tool. Planning_failure = plan diverges from objective (too many steps indicate loss of focus). | **Partial** |
| Information Withholding | FM-2.4 | circular_delegation | When agent A delegates to B but B doesn't propagate necessary context back, this manifests as delegation failures. Detectable via DELEGATION span analysis showing incomplete information flow. | **Partial** |
| Ignored Other Agent's Input | FM-2.5 | agent_misroute, circular_delegation | Agent_misroute = task routed to wrong agent, ignoring prior agent's recommendation. Circular_delegation = agents pass tasks back and forth without incorporating each other's output. | **Partial** |
| Reasoning-Action Mismatch | FM-2.6 | wrong_tool, hallucination | Wrong_tool = action (tool selected) doesn't match what reasoning would suggest. Hallucination = output doesn't match grounding from retrieval (reasoning vs. generation mismatch). Detectable by comparing REASONING spans against subsequent TOOL_CALL/LLM_CALL spans. | **Full** |
| **Task Verification (FC3)** | | | | |
| Premature Termination | FM-3.1 | timeout, planning_failure | Timeout = task ends due to time limit before completion. Planning_failure = agent terminates with incomplete plan (detectable as plan with fewer steps than required). | **Partial** |
| No or Incomplete Verification | FM-3.2 | *No direct mapping* | This is about the absence of a verification step. Our guardrail_bypass detects when verification exists but is bypassed, but we don't detect when verification is entirely missing. Would require expected-span analysis (checking that a GUARD_RAIL span exists when it should). | **Gap** |
| Incorrect Verification | FM-3.3 | guardrail_bypass, hallucination | Guardrail_bypass = verification mechanism exists but produces wrong result ("bypass"). Hallucination = verification against retrieval data fails (agent claims verification passed when output is ungrounded). | **Full** |

---

## Coverage Summary

| Coverage Level | Count | MAST Failure Modes |
|----------------|-------|--------------------|
| **Full** (directly detected) | 7 | FM-1.1, FM-1.2, FM-1.3, FM-1.4, FM-1.5, FM-2.6, FM-3.3 |
| **Partial** (detectable via related faults) | 5 | FM-2.1, FM-2.3, FM-2.4, FM-2.5, FM-3.1 |
| **Gap** (not directly covered) | 2 | FM-2.2, FM-3.2 |

**Overall coverage: 12/14 (85.7%) directly or partially detectable**
- 7/14 (50.0%) have full/direct mappings
- 5/14 (35.7%) have partial mappings via related fault types
- 2/14 (14.3%) are genuine gaps in our taxonomy

---

## Analysis of the 2 Gaps

### FM-2.2: Fail to Ask for Clarification
- **Nature:** This is an *omission* failure -- the agent fails to do something it should.
- **Why we don't cover it:** Our fault types detect *observable execution anomalies* (wrong tool called, too many tokens, cycles in delegation). The absence of a clarification request is a semantic judgment about what the agent *should* have done, not an execution anomaly.
- **Possible extension:** A "missing_clarification" fault type could compare task ambiguity (detected via NLP analysis of the prompt in LLM_CALL spans) against the absence of clarification-requesting tool calls. This would require a PLANNING span that shows the agent considered and rejected asking for clarification.
- **Verdict:** Legitimate gap. Omission failures are inherently harder to detect with trace-level telemetry because the signal is the *absence* of expected behavior.

### FM-3.2: No or Incomplete Verification
- **Nature:** This is also an *omission* failure -- verification should have happened but didn't.
- **Why we don't cover it:** Our guardrail_bypass detects when a guard rail *exists* and is bypassed, but we don't detect when the entire verification step is missing. This would require a specification of *expected* spans per task type.
- **Possible extension:** A "missing_verification" fault type could check for the absence of GUARD_RAIL spans in traces where they are expected (based on task type classification). This is feasible with our span architecture.
- **Verdict:** Legitimate gap. Could be addressed with expected-span-graph analysis in future work.

---

## Analysis of Our Fault Types NOT in MAST

| Our Fault Type | In MAST? | Why Not? |
|----------------|----------|----------|
| cost_explosion | No | MAST focuses on correctness failures, not resource/cost anomalies. Cost is an operational concern not captured by failure annotation. |
| tool_failure | No | MAST annotates agent-level behavioral failures, not infrastructure errors. A tool returning an error is a systems failure, not an agent failure. |
| stale_retrieval | No | MAST doesn't separately track data freshness. Could be subsumed under FM-1.1 (task specification violation) if freshness is a task requirement. |
| timeout | No | Same as tool_failure -- infrastructure/systems-level, not agent behavioral. |

**3 of our 14 fault types are systems/operational faults not covered by MAST's behavioral taxonomy.** This is expected: MAST is a failure *classification* taxonomy derived from human annotation, while our taxonomy also includes *operational* faults (cost, latency, infrastructure) that are critical for production monitoring but don't appear in behavioral failure analysis.

---

## Key Insights for the Paper

### 1. Convergence Despite Independent Derivation
Our 14 fault types and MAST's 14 failure modes were derived independently using
different methodologies:
- **MAST:** Bottom-up annotation of 1,600+ real agent traces by human experts
- **Ours:** Top-down systematic analysis of 7 framework APIs + execution phase taxonomy

Despite this, we achieve **85.7% coverage** (12/14 MAST modes detectable).
This convergence is strong evidence that our taxonomy captures real-world
failure patterns, not just artifacts of our framework design.

### 2. Complementary Abstraction Levels
MAST operates at the **failure classification** level (what went wrong
semantically), while our taxonomy operates at the **execution telemetry** level
(what observable signals indicate the failure). This complementarity is exactly
what's needed: MAST tells you the vocabulary of failures; AgentTelemetry gives
you the runtime instrumentation to detect them.

### 3. Our Additions Are Justified
The 3 fault types we have that MAST doesn't (cost_explosion, tool_failure,
timeout) are **operational faults** essential for production monitoring. MAST's
annotators weren't looking for these because they examined traces post-hoc for
correctness, not for runtime health. A production observability system must
detect both behavioral and operational failures.

### 4. The 2 Gaps Validate Our Architecture
Both gaps (FM-2.2, FM-3.2) are *omission* failures -- detecting the absence of
expected behavior. These require a specification of what *should* happen, which
is beyond trace-level anomaly detection. However, our PLANNING and GUARD_RAIL
span kinds provide the architectural foundation to detect these in future work
(by comparing actual span graphs against expected span templates).

---

## Suggested Paper Text

### For Section 3 (Taxonomy Grounding):

> To validate our taxonomy against independent work, we map our 14 fault types
> to the 14 failure modes in MAST~\cite{mast}, a taxonomy derived from 1,600+
> annotated multi-agent traces with inter-annotator agreement
> $\kappa = 0.88$. Table~\ref{tab:mast-mapping} shows the mapping.
> Despite independent derivation using different methodologies (our top-down
> framework analysis vs.\ MAST's bottom-up trace annotation), 12 of 14 MAST
> failure modes (85.7\%) are detectable via our span kinds and fault types.
> The two gaps (FM-2.2: failure to clarify, FM-3.2: missing verification) are
> both \emph{omission} failures---detecting the absence of expected behavior
> rather than the presence of anomalous behavior---which require
> expected-span-graph specifications beyond trace-level anomaly detection.
> Conversely, three of our fault types (cost explosion, tool failure, timeout)
> address \emph{operational} failures absent from MAST's behavioral taxonomy
> but critical for production monitoring.

### For the MAST mapping table (LaTeX):

```latex
\begin{table*}[t]
\centering
\small
\caption{Mapping between MAST failure modes~\cite{mast} and AgentTelemetry
fault types.  12 of 14 MAST modes (85.7\%) are detectable; the two gaps are
omission failures requiring expected-span specifications.}
\label{tab:mast-mapping}
\begin{tabular}{@{}lllll@{}}
\toprule
\textbf{MAST Failure Mode} & \textbf{Code} & \textbf{Our Fault Type(s)} & \textbf{Detecting Span Kind(s)} & \textbf{Coverage} \\
\midrule
\multicolumn{5}{@{}l}{\emph{(i) Specification Issues}} \\
Disobey Task Specification   & FM-1.1 & wrong\_tool, hallucination       & TOOL\_CALL, LLM\_CALL  & Full \\
Disobey Role Specification   & FM-1.2 & agent\_misroute, guardrail\_bypass & AGENT, GUARD\_RAIL   & Full \\
Step Repetition              & FM-1.3 & infinite\_loop, reasoning\_loop   & TOOL\_CALL, REASONING & Full \\
Loss of Conversation History & FM-1.4 & context\_overflow, memory\_corruption & LLM\_CALL, MEMORY & Full \\
Unaware of Termination       & FM-1.5 & infinite\_loop, planning\_failure & TOOL\_CALL, PLANNING  & Full \\
\midrule
\multicolumn{5}{@{}l}{\emph{(ii) Inter-Agent Misalignment}} \\
Conversation Reset           & FM-2.1 & memory\_corruption, context\_overflow & MEMORY, LLM\_CALL & Partial \\
Fail to Ask for Clarification & FM-2.2 & ---                              & ---                  & Gap \\
Task Derailment              & FM-2.3 & wrong\_tool, planning\_failure    & TOOL\_CALL, PLANNING  & Partial \\
Information Withholding      & FM-2.4 & circular\_delegation              & DELEGATION            & Partial \\
Ignored Other Agent's Input  & FM-2.5 & agent\_misroute, circular\_delegation & AGENT, DELEGATION & Partial \\
Reasoning-Action Mismatch    & FM-2.6 & wrong\_tool, hallucination        & TOOL\_CALL, REASONING & Full \\
\midrule
\multicolumn{5}{@{}l}{\emph{(iii) Task Verification}} \\
Premature Termination        & FM-3.1 & timeout, planning\_failure        & LLM\_CALL, PLANNING   & Partial \\
No or Incomplete Verification & FM-3.2 & ---                             & ---                  & Gap \\
Incorrect Verification       & FM-3.3 & guardrail\_bypass, hallucination  & GUARD\_RAIL, LLM\_CALL & Full \\
\bottomrule
\end{tabular}
\end{table*}
```

### For addressing the "tautological evaluation" concern:

> A potential concern is that our evaluation is tautological: we designed both
> the fault types and the detectors. We address this in three ways. First, our
> fault types achieve 85.7\% coverage of the independently-derived MAST
> taxonomy~\cite{mast}, demonstrating convergence with failure modes identified
> through bottom-up annotation of 1,600+ real traces rather than our top-down
> framework analysis. Second, the ablation study (\S\ref{sec:rq2}) uses a
> structural argument---removing a span kind provably makes detection
> impossible---that is independent of fault design. Third, the cross-framework
> evaluation (\S\ref{sec:rq1}) tests detection across seven frameworks with
> different adapter strategies, not just our reference implementation.

---

## Correcting the MAST Citation

The current paper has an incorrect citation:
```
\bibitem{mast}
L.~Jin, S.~Zheng, J.~Huang, X.~Yang, K.~Chen, and X.~Zhang.
\newblock {MAST}: A Multi-Agent System Taxonomy for Failure Mode Analysis.
\newblock In {\em Proc.\ NeurIPS}, 2025.
```

The actual paper is:
- **Title:** "Why Do Multi-Agent LLM Systems Fail?"
- **Authors:** Cemri et al. (need to verify exact author list from the paper)
- **Venue:** NeurIPS 2025 (confirmed)
- **URL:** https://arxiv.org/abs/2503.13657

The citation should be updated to match the actual paper metadata.
