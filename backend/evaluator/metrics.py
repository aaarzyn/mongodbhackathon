"""Evaluation metric utilities for ContextScope Eval.

This module implements scoring functions aligned with PROJECT.md:
- Context Transmission Fidelity
- Relevance Drift
- Compression Efficiency
- Temporal Coherence
- Response Utility

Design goals:
- Pure-Python, dependency-light fallbacks for restricted environments
- Optional use of precomputed embeddings (vectors) when available
- Clear, typed interfaces and specific exceptions
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np


class EvaluationMetricError(Exception):
    """Raised when metric computation fails due to invalid inputs."""

    pass


# -------------------------
# Utility helpers
# -------------------------


def _cosine_similarity(vec1: Sequence[float], vec2: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns 0.0 if any vector has near-zero norm.
    """
    a = np.asarray(vec1, dtype=float)
    b = np.asarray(vec2, dtype=float)
    if a.shape != b.shape:
        raise EvaluationMetricError(
            f"Vector shapes must match, got {a.shape} vs {b.shape}"
        )
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer to avoid heavy dependencies."""
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _top_k_terms(tokens: List[str], k: int = 10) -> List[str]:
    counts = Counter(tokens)
    return [t for t, _ in counts.most_common(k)]


def _cosine_on_term_freq(a_tokens: List[str], b_tokens: List[str]) -> float:
    """Cosine similarity on term-frequency vectors as a fallback.

    This approximates semantic similarity when embeddings are unavailable.
    """
    a_counts = Counter(a_tokens)
    b_counts = Counter(b_tokens)
    vocab = list({*a_counts.keys(), *b_counts.keys()})
    if not vocab:
        return 0.0
    a_vec = np.array([a_counts.get(t, 0) for t in vocab], dtype=float)
    b_vec = np.array([b_counts.get(t, 0) for t in vocab], dtype=float)
    return _cosine_similarity(a_vec, b_vec)


def _safe_ratio(numer: float, denom: float) -> float:
    return 0.0 if abs(denom) < 1e-12 else float(numer / denom)


# -------------------------
# Metric functions
# -------------------------


def compute_fidelity(
    context_sent: str,
    context_received: str,
    sent_vec: Optional[Sequence[float]] = None,
    received_vec: Optional[Sequence[float]] = None,
) -> float:
    """Compute Context Transmission Fidelity in [0, 1].

    Priority order:
    1) If both vectors are provided, use cosine similarity.
    2) Otherwise, fallback to cosine over term-frequency vectors.
    """
    if sent_vec is not None and received_vec is not None:
        sim = _cosine_similarity(sent_vec, received_vec)
        # Map cosine [-1,1] to [0,1] conservatively
        return max(0.0, min(1.0, 0.5 * (sim + 1.0)))

    a_tokens = _tokenize(context_sent)
    b_tokens = _tokenize(context_received)
    sim = _cosine_on_term_freq(a_tokens, b_tokens)
    return max(0.0, min(1.0, sim))


def compute_relevance_drift(
    context_sent: str,
    context_received: str,
    sent_vec: Optional[Sequence[float]] = None,
    received_vec: Optional[Sequence[float]] = None,
    topk: int = 10,
) -> float:
    """Compute Relevance Drift in [0, 1] (higher = more drift).

    Combines 1 - fidelity with divergence of top terms to penalize focus shift.
    """
    fidelity = compute_fidelity(context_sent, context_received, sent_vec, received_vec)
    base_drift = 1.0 - fidelity

    a_tokens = _tokenize(context_sent)
    b_tokens = _tokenize(context_received)
    a_top = set(_top_k_terms(a_tokens, k=topk))
    b_top = set(_top_k_terms(b_tokens, k=topk))
    if not a_top and not b_top:
        return base_drift

    jacc = _safe_ratio(len(a_top & b_top), len(a_top | b_top))
    term_drift = 1.0 - jacc

    # Blend: emphasize fidelity but account for topic shifts.
    drift = 0.5 * base_drift + 0.5 * term_drift
    return max(0.0, min(1.0, drift))


def compute_compression_efficiency(tokens_before: int, tokens_after: int) -> float:
    """Compute Compression Efficiency in [0, 1].

    Defined as (before - after) / max(before, 1). Negative values are clipped to 0.
    """
    if tokens_before < 0 or tokens_after < 0:
        raise EvaluationMetricError("Token counts must be non-negative")
    if tokens_after > tokens_before:
        # Expansion rather than compression
        return 0.0
    return max(0.0, _safe_ratio(tokens_before - tokens_after, max(tokens_before, 1)))


_YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
_ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def compute_temporal_coherence(context_sent: str, context_received: str) -> Optional[float]:
    """Approximate temporal coherence based on year/date preservation.

    Returns None if no temporal cues are present in both texts; otherwise
    returns a score in [0, 1] measuring preservation of years/dates.
    """
    years_a = set(_YEAR_RE.findall(context_sent or ""))
    years_b = set(_YEAR_RE.findall(context_received or ""))

    dates_a = set(_ISO_DATE_RE.findall(context_sent or ""))
    dates_b = set(_ISO_DATE_RE.findall(context_received or ""))

    # Each findall for years returns tuples due to grouping; normalize.
    years_a_norm = {"".join(y) for y in years_a} if years_a else set()
    years_b_norm = {"".join(y) for y in years_b} if years_b else set()

    have_signal = bool(years_a_norm or dates_a) and bool(years_b_norm or dates_b)
    if not have_signal:
        return None

    # Jaccard on union of temporal markers
    a_markers = years_a_norm | dates_a
    b_markers = years_b_norm | dates_b
    inter = len(a_markers & b_markers)
    union = len(a_markers | b_markers)
    return max(0.0, min(1.0, _safe_ratio(inter, union)))


def compute_response_utility(
    baseline_score: float,
    with_context_score: float,
    mode: str = "relative",
) -> float:
    """Compute Response Utility improvement.

    Modes:
    - "relative": (with - baseline) / max(|baseline|, eps)
    - "absolute": with - baseline
    """
    if mode not in {"relative", "absolute"}:
        raise EvaluationMetricError("mode must be 'relative' or 'absolute'")

    delta = with_context_score - baseline_score
    if mode == "absolute":
        return float(delta)
    denom = max(abs(baseline_score), 1e-8)
    return float(delta / denom)


# -------------------------
# High-level evaluation helper
# -------------------------


def evaluate_handoff(
    *,
    context_sent: str,
    context_received: str,
    tokens_before: Optional[int] = None,
    tokens_after: Optional[int] = None,
    sent_vec: Optional[Sequence[float]] = None,
    received_vec: Optional[Sequence[float]] = None,
) -> Tuple[float, float, float, Optional[float]]:
    """Evaluate a single handoff and return core metrics.

    Returns:
        (fidelity, drift, compression, temporal_coherence)
    """
    fidelity = compute_fidelity(context_sent, context_received, sent_vec, received_vec)
    drift = compute_relevance_drift(
        context_sent, context_received, sent_vec, received_vec
    )

    compression: float
    if tokens_before is None or tokens_after is None:
        compression = 0.0
    else:
        compression = compute_compression_efficiency(tokens_before, tokens_after)

    temporal = compute_temporal_coherence(context_sent, context_received)
    return fidelity, drift, compression, temporal
