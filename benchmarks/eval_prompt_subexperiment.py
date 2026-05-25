"""
EVALUATOR/PROMPT extension sub-experiment for OpenInference.

Design: extend the OpenInference workload to exercise the four currently-unused
typed kinds (EVALUATOR, PROMPT, RERANKER, EMBEDDING) and re-score per-fault
detection under typed-only and extended-attribute rules.

For each fault, we determine:
- Whether an OpenInference EVALUATOR / PROMPT typed kind, dispatched on its
  standardized attributes (eval.score, eval.label, prompt.template, prompt.role,
  reranker.score, embedding.vector_dims), allows detection.
- This is a CAPABILITY analysis (per-fault binary), not a per-instance recall.

We model adapter conformance honestly:
- Frameworks with explicit verifier/evaluator patterns (LangChain, CrewAI,
  AutoGen, LlamaIndex) CAN plausibly emit EVALUATOR via documented hooks:
    - LangChain: RunnableEval, RunEvalConfig
    - CrewAI: Task with evaluator callback
    - AutoGen: GroupChat with critic agent
    - LlamaIndex: Response evaluators (FaithfulnessEvaluator, etc.)
- Bare LLM SDKs (anthropic_sdk, openai_sdk) have no built-in evaluator pattern;
  they emit only LLM spans.
- Same logic for PROMPT (frameworks have prompt templates; bare SDKs do not).

This is a counterfactual: "what would the realized OpenInference TCR look like
if practitioners adopted the EVALUATOR and PROMPT kinds via documented framework
hooks?"
"""

import csv

# ---------------------------------------------------------------------------
# Capability analysis: for each fault, can EVALUATOR/PROMPT/RERANKER/EMBEDDING
# enable detection at the metamodel-capability envelope (i.e., assuming the
# workload is extended to exercise the kind)?
# ---------------------------------------------------------------------------

FAULTS = [
    "wrong_tool", "tool_failure", "timeout", "infinite_loop",
    "context_overflow", "cost_explosion",
    "circular_delegation", "agent_misroute",
    "planning_failure", "reasoning_loop",
    "guardrail_bypass", "hallucination",
    "memory_corruption", "stale_retrieval",
]

# Existing OpenInference typed-only detection (verified from results_full.tsv)
OI_TYPED6 = {
    "wrong_tool": True, "tool_failure": True, "timeout": True,
    "infinite_loop": True, "context_overflow": True, "cost_explosion": True,
    "circular_delegation": False, "agent_misroute": False,
    "planning_failure": False, "reasoning_loop": False,
    "guardrail_bypass": False, "hallucination": False,
    "memory_corruption": False, "stale_retrieval": False,
}

# Capability-envelope: with EVALUATOR + PROMPT + RERANKER + EMBEDDING typed kinds
# added, what additional faults can OpenInference detect?
#
# EVALUATOR (eval.score, eval.label):
#   - hallucination: YES. A FaithfulnessEvaluator span with eval.label = "hallucination"
#     or eval.score below threshold dispatches a typed predicate.
#   - reasoning_loop: PARTIAL — an evaluator firing on each reasoning step could
#     detect repeated identical evaluations, but this requires per-step evaluator
#     emission which is not the documented pattern. Mark NO for typed-only.
#   - guardrail_bypass: NO (this is the GUARDRAIL kind's job, already in the 6).
#
# PROMPT (prompt.template, prompt.role):
#   - planning_failure: YES. A prompt with prompt.role = "planner" or
#     prompt.template tagged as a planning step lets a typed predicate dispatch
#     when the planner-prompt is followed by no tool execution.
#
# RERANKER and EMBEDDING are not relevant to any of the 8 missing faults.
#
# So at the capability envelope, OpenInference + EVALUATOR + PROMPT lifts from
# 6/14 to 8/14 (gaining hallucination and planning_failure).

OI_TYPED_EXTENDED_CAPABILITY = dict(OI_TYPED6)
OI_TYPED_EXTENDED_CAPABILITY["hallucination"] = True
OI_TYPED_EXTENDED_CAPABILITY["planning_failure"] = True

# ---------------------------------------------------------------------------
# Realized cross-adapter analysis: per-adapter EVALUATOR/PROMPT emission.
# ---------------------------------------------------------------------------

# Adapter capability for emitting EVALUATOR and PROMPT spans via documented
# framework hooks (not exotic patches, just what the framework's published API
# supports for hook-based emission):

ADAPTERS = ["langchain", "llamaindex", "anthropic_sdk", "openai_sdk",
            "autogen", "crewai"]

# EVALUATOR-capable adapters (those with documented evaluator/critic patterns):
EVAL_CAPABLE = {"langchain", "llamaindex", "autogen", "crewai"}

# PROMPT-capable adapters (those with explicit prompt-template hooks):
PROMPT_CAPABLE = {"langchain", "llamaindex", "autogen", "crewai"}
# (anthropic_sdk and openai_sdk have raw .messages = [...] arrays, not
# template-tagged prompts; they could emit PROMPT spans only via custom
# instrumentation, which is the same threshold as DSM conformance.)

# Existing OpenInference per-adapter detection (typed-only, currently 6/14 on every
# adapter, mechanically determined by which of the 6 "easy" faults the adapter
# emits LLM/TOOL/AGENT spans for; verified from results_full.tsv all adapters at
# 6/14 = 0.429).

def realized_oi_extended(adapter):
    """Per-fault realized detection under OpenInference + EVALUATOR + PROMPT
    typed-only extension."""
    detect = {f: OI_TYPED6[f] for f in FAULTS}
    if adapter in EVAL_CAPABLE:
        detect["hallucination"] = True
    if adapter in PROMPT_CAPABLE:
        detect["planning_failure"] = True
    return detect

# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------

print("=" * 72)
print("EVALUATOR/PROMPT extension sub-experiment")
print("=" * 72)

print("\n[A] Capability envelope (workload exercises EVALUATOR + PROMPT):")
gain_envelope = sum(OI_TYPED_EXTENDED_CAPABILITY.values()) - sum(OI_TYPED6.values())
print(f"    OpenInference typed-only-6 capability: {sum(OI_TYPED6.values())}/14 = {sum(OI_TYPED6.values())/14:.3f}")
print(f"    OpenInference + EVAL + PROMPT capability: {sum(OI_TYPED_EXTENDED_CAPABILITY.values())}/14 = {sum(OI_TYPED_EXTENDED_CAPABILITY.values())/14:.3f}")
print(f"    Capability lift: +{gain_envelope}/14 (hallucination via EVALUATOR; planning_failure via PROMPT)")

print("\n[B] Realized per-adapter (third-party adapters only):")
total_third_party_pairs = 0
oi_extended_detections = 0
oi_baseline_detections = 0
for a in ADAPTERS:
    det = realized_oi_extended(a)
    n = sum(det.values())
    n_base = sum(OI_TYPED6.values())  # = 6 always
    total_third_party_pairs += 14
    oi_extended_detections += n
    oi_baseline_detections += n_base
    extras = []
    if a in EVAL_CAPABLE: extras.append("EVAL")
    if a in PROMPT_CAPABLE: extras.append("PROMPT")
    print(f"    {a:18s}: typed-only-6 = 6/14 = 0.429; extended typed = {n}/14 = {n/14:.3f}  ({'+'.join(extras) or 'no extra typed kinds'})")

print(f"\n    Third-party adapter aggregate: realized OI-extended = {oi_extended_detections}/{total_third_party_pairs} = {oi_extended_detections/total_third_party_pairs:.3f}")
print(f"    Baseline OI-typed-only-6 aggregate = {oi_baseline_detections}/{total_third_party_pairs} = {oi_baseline_detections/total_third_party_pairs:.3f}")

# ---------------------------------------------------------------------------
# Comparison vs realized DSM
# ---------------------------------------------------------------------------
# Realized DSM cross-adapter mean = 0.548 (= 46/84), per the paper.
# Realized DSM per-adapter:
#   anthropic_sdk, autogen, crewai, openai_sdk: 8/14
#   langchain, llamaindex: 7/14
DSM_REALIZED = {
    "anthropic_sdk": 8/14, "autogen": 8/14, "crewai": 8/14, "openai_sdk": 8/14,
    "langchain": 7/14, "llamaindex": 7/14,
}

print("\n[C] Pareto comparison: OpenInference + EVAL/PROMPT (typed-only) vs realized DSM:")
for a in ADAPTERS:
    oi_ext = sum(realized_oi_extended(a).values()) / 14
    dsm = DSM_REALIZED[a]
    print(f"    {a:18s}: OI-extended typed = {oi_ext:.3f}, DSM = {dsm:.3f}  -> "
          f"{'OI ≥ DSM' if oi_ext >= dsm else 'DSM > OI'}")

print(f"\n    Cross-adapter mean: OI-extended typed = {oi_extended_detections/total_third_party_pairs:.3f}; "
      f"DSM = 46/84 = {46/84:.3f}")

# Cluster mean for OI-extended typed
oi_ext_per_adapter = [sum(realized_oi_extended(a).values()) for a in ADAPTERS]
print(f"\n[D] OI-extended typed per-adapter detections: {oi_ext_per_adapter}")
print(f"    Sum: {sum(oi_ext_per_adapter)} of {6*14} = {sum(oi_ext_per_adapter)/(6*14):.4f}")

# Output a TSV row matrix for use in the paper
print("\n[E] Per-fault, per-adapter detection matrix for OI-extended-typed:")
print("    " + "fault".ljust(22) + " | " + " | ".join(a.ljust(13) for a in ADAPTERS))
for f in FAULTS:
    row = [str(int(realized_oi_extended(a).get(f, False))) for a in ADAPTERS]
    print(f"    {f.ljust(22)} | " + " | ".join(c.ljust(13) for c in row))
