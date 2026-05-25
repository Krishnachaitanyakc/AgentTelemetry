"""Compatibility wrapper for the extended-attribute secondary rule.

The executable extended-attribute predicates live in ``trace_detectors.py``
and ``analysis.py`` recomputes all extended TCR/FPR counts from
``traces_full.jsonl``. This module is retained as a manifest target for
reviewers who expect a named extended-attribute predicate bank; it
intentionally contains no precomputed result counts.
"""

from trace_detectors import detect_extended, fires_any_extended

STANDARDIZED_EXTRA_ATTRIBUTES = {
    "otel_genai": ["gen_ai.tool.name", "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"],
    "openinference": ["retrieval.documents", "tool.parameters"],
}

__all__ = ["STANDARDIZED_EXTRA_ATTRIBUTES", "detect_extended", "fires_any_extended"]
