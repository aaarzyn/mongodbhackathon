"""Test the handoff schema."""

from backend.evaluator.schema import EvalScores, HandoffEvaluation, PipelineEvaluation, PipelineScore
from datetime import datetime
import json


def test_context_handoff():
    """Test creating a HandoffEvaluation document (canonical schema)."""
    
    s = EvalScores(
        fidelity=0.91,
        drift=0.08,
        compression=0.45,
    )
    handoff = HandoffEvaluation(
        handoff_id="handoff_test123",
        pipeline_id="pipeline_test456",
        agent_from="researcher",
        agent_to="summarizer",
        context_sent='{"movies": ["Inception", "Interstellar"]}',
        context_received='{"movies": ["Inception", "Interstellar"]}',
        eval_scores=s,
        key_info_preserved=["Inception", "Interstellar"],
        metadata={
            "test": True,
            "format": "json",
            "tokens": {"before": 6, "after": 6},
        },
    )
    
    # Convert to dict (MongoDB-ready format)
    doc = handoff.model_dump()
    
    print("✅ HandoffEvaluation Schema Test")
    print("="*60)
    print(json.dumps(doc, indent=2, default=str))
    print()
    
    return handoff


def test_pipeline_run():
    """Test creating a PipelineEvaluation document (canonical schema)."""
    
    pipeline = PipelineEvaluation(
        pipeline_id="pipeline_test456",
        handoffs=[],
        overall_pipeline_score=PipelineScore(
            avg_fidelity=0.91,
            avg_drift=0.08,
            total_compression=0.45,
            end_to_end_fidelity=0.90,
        ),
    )
    
    doc = pipeline.model_dump()
    
    print("✅ PipelineEvaluation Schema Test")
    print("="*60)
    print(json.dumps(doc, indent=2, default=str))
    print()
    
    return pipeline


if __name__ == "__main__":
    test_context_handoff()
    test_pipeline_run()
    print("✅ All schema tests passed!")