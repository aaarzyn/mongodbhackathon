import pytest

from backend.evaluator.schema import EvalScores, HandoffEvaluation, VectorBundle


def test_eval_scores_range_validation():
    s = EvalScores(fidelity=0.9, drift=0.1, compression=0.4)
    assert s.fidelity == 0.9 and s.drift == 0.1 and s.compression == 0.4
    with pytest.raises(Exception):
        EvalScores(fidelity=1.2, drift=0.1, compression=0.4)


def test_vector_bundle_validation():
    vb = VectorBundle(sent=[0.1, 0.2], received=[0.2, 0.1])
    assert vb.sent and vb.received


def test_handoff_evaluation_minimum():
    s = EvalScores(fidelity=0.8, drift=0.2, compression=0.5)
    h = HandoffEvaluation(
        pipeline_id="pipe-1",
        handoff_id="h-1",
        agent_from="User Profiler",
        agent_to="Content Analyzer",
        context_sent="Sci-Fi preferences",
        context_received="Sci-Fi preferences",
        eval_scores=s,
    )
    assert h.handoff_id == "h-1"

