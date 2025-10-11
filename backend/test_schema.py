"""Test the handoff schema."""

from backend.models.handoff import ContextHandoff, EvalScores, CompressionStats, PipelineRun
from datetime import datetime
import json


def test_context_handoff():
    """Test creating a ContextHandoff document."""
    
    # Create a handoff
    handoff = ContextHandoff(
        handoff_id="handoff_test123",
        pipeline_id="pipeline_test456",
        task_id="task_movies",
        agent_from="researcher",
        agent_to="summarizer",
        context_sent='{"movies": ["Inception", "Interstellar"]}',
        context_received='{"movies": ["Inception", "Interstellar"]}',
        output_generated="Nolan's films explore time and reality.",
        format_type="json",
        embeddings={
            "sent_vector": [0.1, 0.2, 0.3],
            "output_vector": [0.15, 0.22, 0.28]
        },
        eval_scores=EvalScores(
            fidelity=0.91,
            drift=0.08,
            compression_efficiency=0.45,
            fact_retention=0.87
        ),
        compression_stats=CompressionStats(
            sent_tokens=100,
            received_tokens=50,
            compression_ratio=0.5
        ),
        metadata={
            "test": True,
            "embedding_model": "all-MiniLM-L6-v2"
        }
    )
    
    # Convert to dict (MongoDB-ready format)
    doc = handoff.model_dump()
    
    print("✅ ContextHandoff Schema Test")
    print("="*60)
    print(json.dumps(doc, indent=2, default=str))
    print()
    
    return handoff


def test_pipeline_run():
    """Test creating a PipelineRun document."""
    
    pipeline = PipelineRun(
        pipeline_id="pipeline_test456",
        task_description="Test pipeline for Nolan films",
        format_type="json",
        agents=["researcher", "summarizer"],
        avg_fidelity=0.91,
        avg_drift=0.08,
        avg_compression_efficiency=0.45,
        avg_fact_retention=0.87,
        handoff_count=1,
        metadata={"test": True}
    )
    
    doc = pipeline.model_dump()
    
    print("✅ PipelineRun Schema Test")
    print("="*60)
    print(json.dumps(doc, indent=2, default=str))
    print()
    
    return pipeline


if __name__ == "__main__":
    test_context_handoff()
    test_pipeline_run()
    print("✅ All schema tests passed!")