"""Hallucination tracing: find LLM outputs not grounded in retrieved content.

Compares LLM completions with content from sibling/child RETRIEVAL spans.
Uses simple token-overlap heuristics -- no external model required.

Note: requires FULL privacy level for ``llm.completion`` and retrieval
content to be recorded in spans.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from agenttelemetry.core.spans import (
    AGENT_SPAN_KIND,
    LLM_COMPLETION,
    LLM_MODEL,
    RETRIEVAL_QUERY,
    RETRIEVAL_SOURCE,
    TOOL_OUTPUT,
    AgentSpanKind,
)


@dataclass
class HallucinationCandidate:
    """A segment of LLM output potentially not grounded in retrieval data."""

    claim: str
    llm_span_id: str
    llm_model: str
    retrieval_span_ids: List[str] = field(default_factory=list)
    retrieved_content: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0-1, higher = more likely hallucinated
    trace_id: str = ""


# Minimum sentence length to consider (skip very short fragments)
_MIN_SENTENCE_LEN = 20

# Stop words excluded from overlap scoring
_STOP_WORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "and", "but", "or",
    "nor", "not", "so", "yet", "for", "to", "of", "in", "on", "at", "by",
    "with", "from", "as", "into", "through", "about", "that", "this",
    "it", "its", "i", "we", "you", "he", "she", "they", "me", "him",
    "her", "us", "them", "my", "your", "his", "our", "their",
}


class HallucinationTracer:
    """Detect LLM output segments not grounded in retrieved content.

    For each LLM_CALL span that has nearby RETRIEVAL spans, this tracer
    extracts sentences from the LLM completion and scores each one against
    the retrieved content using token overlap. Sentences with low overlap
    are flagged as hallucination candidates.

    Args:
        min_confidence: Minimum confidence threshold (0-1) to report.
            Default 0.5.
    """

    def __init__(self, min_confidence: float = 0.5):
        self._min_confidence = min_confidence

    def analyze(
        self, spans: List[Dict[str, Any]]
    ) -> List[HallucinationCandidate]:
        """Return hallucination candidates from the given spans."""
        # Build indexes
        by_id: Dict[str, Dict[str, Any]] = {}
        children: Dict[Optional[str], List[str]] = defaultdict(list)

        for span in spans:
            sid = span.get("span_id", "")
            by_id[sid] = span
            parent = span.get("parent_span_id")
            children[parent].append(sid)

        candidates: List[HallucinationCandidate] = []

        for span in spans:
            kind = span.get("agent_span_kind") or ""
            if kind != AgentSpanKind.LLM_CALL:
                continue

            attrs = span.get("attributes") or {}
            completion = str(attrs.get(LLM_COMPLETION, "") or "")
            if not completion:
                continue

            llm_span_id = span.get("span_id", "")
            llm_model = str(attrs.get(LLM_MODEL, "unknown"))
            trace_id = span.get("trace_id", "unknown")

            # Collect retrieval content from sibling and child RETRIEVAL spans
            retrieval_spans = self._find_retrieval_spans(
                span, by_id, children
            )
            if not retrieval_spans:
                continue

            retrieval_span_ids = [
                r.get("span_id", "") for r in retrieval_spans
            ]
            retrieved_content = self._extract_retrieval_content(
                retrieval_spans
            )
            if not retrieved_content:
                continue

            # Build token set from all retrieved content
            reference_tokens = self._tokenize_all(retrieved_content)

            # Split completion into sentences and score each
            sentences = self._split_sentences(completion)
            for sentence in sentences:
                if len(sentence) < _MIN_SENTENCE_LEN:
                    continue

                confidence = self._score_hallucination(
                    sentence, reference_tokens
                )
                if confidence >= self._min_confidence:
                    candidates.append(
                        HallucinationCandidate(
                            claim=sentence,
                            llm_span_id=llm_span_id,
                            llm_model=llm_model,
                            retrieval_span_ids=retrieval_span_ids,
                            retrieved_content=retrieved_content,
                            confidence=confidence,
                            trace_id=trace_id,
                        )
                    )

        return candidates

    # ------------------------------------------------------------------
    # Retrieval span discovery
    # ------------------------------------------------------------------

    def _find_retrieval_spans(
        self,
        llm_span: Dict[str, Any],
        by_id: Dict[str, Dict[str, Any]],
        children: Dict[Optional[str], List[str]],
    ) -> List[Dict[str, Any]]:
        """Find RETRIEVAL spans that are siblings or children of the LLM span."""
        results: List[Dict[str, Any]] = []
        llm_span_id = llm_span.get("span_id", "")

        # Children of the LLM span
        for child_id in children.get(llm_span_id, []):
            child = by_id.get(child_id)
            if child and (child.get("agent_span_kind") or "") == AgentSpanKind.RETRIEVAL:
                results.append(child)

        # Siblings (children of the same parent)
        parent_id = llm_span.get("parent_span_id")
        if parent_id is not None:
            for sibling_id in children.get(parent_id, []):
                if sibling_id == llm_span_id:
                    continue
                sibling = by_id.get(sibling_id)
                if sibling and (sibling.get("agent_span_kind") or "") == AgentSpanKind.RETRIEVAL:
                    results.append(sibling)

        return results

    @staticmethod
    def _extract_retrieval_content(
        retrieval_spans: List[Dict[str, Any]],
    ) -> List[str]:
        """Extract text content from RETRIEVAL spans.

        Tries tool.output first (common pattern for retrieval results),
        then falls back to retrieval.source.
        """
        content: List[str] = []
        for span in retrieval_spans:
            attrs = span.get("attributes") or {}
            text = str(attrs.get(TOOL_OUTPUT, "") or "")
            if not text:
                text = str(attrs.get(RETRIEVAL_SOURCE, "") or "")
            if text:
                content.append(text)
        return content

    # ------------------------------------------------------------------
    # Text processing
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        """Lowercase word tokenization excluding stop words."""
        words = re.findall(r"[a-zA-Z0-9]+", text.lower())
        return {w for w in words if w not in _STOP_WORDS and len(w) > 1}

    @classmethod
    def _tokenize_all(cls, texts: List[str]) -> Set[str]:
        """Build a combined token set from multiple texts."""
        tokens: Set[str] = set()
        for text in texts:
            tokens.update(cls._tokenize(text))
        return tokens

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentence-like segments."""
        # Split on sentence boundaries
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    def _score_hallucination(
        self, sentence: str, reference_tokens: Set[str]
    ) -> float:
        """Score how likely a sentence is hallucinated (0 = grounded, 1 = hallucinated).

        Uses 1 - (overlap ratio) where overlap ratio is the fraction of
        content tokens in the sentence that appear in the reference set.
        """
        sentence_tokens = self._tokenize(sentence)
        if not sentence_tokens:
            return 0.0

        if not reference_tokens:
            return 1.0

        overlap = sentence_tokens & reference_tokens
        overlap_ratio = len(overlap) / len(sentence_tokens)

        # Invert: high overlap means grounded, low overlap means hallucinated
        return round(1.0 - overlap_ratio, 4)
