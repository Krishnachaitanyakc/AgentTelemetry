# Trace Schema

The benchmark corpus is newline-delimited JSON. Each line is one run:

```json
{
  "run_id": "adapter:model:condition:fault",
  "framework": "langchain",
  "model": "model-A1",
  "condition": "metadata_only",
  "fault_type": "wrong_tool",
  "control_scenario": "",
  "adapter_profile": "langchain",
  "spans": [
    {
      "span_id": "s0",
      "parent_id": null,
      "kind": "AGENT",
      "name": "agent.run",
      "attributes": {"agent.id": "agent-main", "agent.role": "worker"}
    }
  ]
}
```

`adapter_profile` records the adapter profile in `adapter_harness.py`
that emitted the spans. `control_scenario` is empty for fault-bearing
traces and records the no-fault workflow name in the supplemental
`no_fault_suite_traces.jsonl` corpus. `score_traces.py` recomputes
`results_full.tsv` from this corpus using the executable predicates in
`trace_detectors.py`.
