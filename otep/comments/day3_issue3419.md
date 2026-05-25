@lmolkova's point about derivation from tool_call patterns is fair for the simple case,
but there's a failure mode where it breaks down completely.

In a study we conducted on SWE-bench agent traces (112 instances across 12 repos), the
dominant failure pattern wasn't tool-related at all — it was reflection-only loops. The
agent evaluates its own output, decides it's insufficient, calls the LLM again, evaluates
again, never converges. There's no tool call in the loop, so there's no tool→LLM pair to
derive iteration boundaries from. Every span in the loop is just `chat`.

This accounted for roughly 75% of the failures we observed. The agent is stuck, burning
tokens, and the trace looks like a sequence of identical `chat` spans with no indication
anything is wrong.

A `reflect` operation with a simple pass/fail verdict would make these loops immediately
visible — you'd see repeated `reflect` spans with `verdict: fail` and could set a circuit
breaker policy on iteration count.

On the opt-in question — agreed. These should only be emitted when detailed debugging is
enabled. The overhead per span is negligible relative to LLM latency, but the volume
concern is valid.
