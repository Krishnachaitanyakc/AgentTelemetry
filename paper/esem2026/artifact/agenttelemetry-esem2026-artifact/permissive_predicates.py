"""Compatibility wrapper for the permissive secondary scoring rule.

The executable permissive predicates live in ``trace_detectors.py`` and
``analysis.py`` recomputes all permissive TCR/FPR counts from
``traces_full.jsonl``. This module is retained as a manifest target for
reviewers who expect a named permissive predicate bank; it intentionally
contains no precomputed result counts.
"""

from trace_detectors import detect_permissive, fires_any_permissive

REGEX_SUMMARY = r"/plan|reason|deleg|guardrail|memory/i"

__all__ = ["REGEX_SUMMARY", "detect_permissive", "fires_any_permissive"]
