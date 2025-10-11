import math

from backend.evaluator.metrics import (
    compute_compression_efficiency,
    compute_fidelity,
    compute_relevance_drift,
    compute_response_utility,
    compute_temporal_coherence,
    evaluate_handoff,
)


def test_compute_fidelity_vectors():
    v = [1.0, 0.0, 0.0]
    # identical -> cosine 1 -> mapped to 1.0
    assert compute_fidelity("a", "b", v, v) == 1.0


def test_compute_fidelity_text_fallback():
    a = "Denis Villeneuve sci fi dunes"
    b = "sci fi dunes Denis Villeneuve"
    assert compute_fidelity(a, b) > 0.8


def test_relevance_drift_low_for_similar_text():
    a = "Christopher Nolan Tenet time inversion thriller"
    b = "Tenet by Christopher Nolan is a thriller about time"
    drift = compute_relevance_drift(a, b)
    assert 0.0 <= drift <= 0.5


def test_compression_efficiency_basic():
    assert compute_compression_efficiency(100, 60) == 0.4
    assert compute_compression_efficiency(100, 120) == 0.0  # expansion


def test_temporal_coherence_years_and_dates():
    a = "Released in 2020 on 2020-08-26"
    b = "The 2020 release date was 2020-08-26 for this title"
    score = compute_temporal_coherence(a, b)
    assert score is not None and score > 0.5


def test_response_utility_modes():
    assert compute_response_utility(0.5, 0.6, mode="absolute") == 0.1
    rel = compute_response_utility(0.5, 0.6, mode="relative")
    assert abs(rel - 0.2) < 1e-9


def test_evaluate_handoff_tuple():
    f, d, c, t = evaluate_handoff(
        context_sent="Nolan sci fi thriller",
        context_received="thriller by Nolan in sci fi",
        tokens_before=4,
        tokens_after=4,
    )
    assert 0.0 <= f <= 1.0
    assert 0.0 <= d <= 1.0
    assert 0.0 <= c <= 1.0
    assert t is None or (0.0 <= t <= 1.0)

