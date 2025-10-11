"""Schema for agent-to-agent context handoffs."""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class EvalScores(BaseModel):
    """Evaluation scores for context quality.
    
    These will be computed after the handoff is stored.
    """
    
    fidelity: Optional[float] = Field(
        default=None,
        description="Context fidelity score (0-1). How well context was preserved.",
        ge=0.0,
        le=1.0
    )
    
    drift: Optional[float] = Field(
        default=None,
        description="Relevance drift score (0-1). How much context diverged from original.",
        ge=0.0,
        le=1.0
    )
    
    compression_efficiency: Optional[float] = Field(
        default=None,
        description="Compression efficiency (0-1). Token reduction vs information loss.",
        ge=0.0,
        le=1.0
    )
    
    fact_retention: Optional[float] = Field(
        default=None,
        description="Fact retention score (0-1). Percentage of key facts preserved.",
        ge=0.0,
        le=1.0
    )


class CompressionStats(BaseModel):
    """Statistics about context compression."""
    
    sent_tokens: int = Field(..., description="Number of tokens in sent context")
    received_tokens: int = Field(..., description="Number of tokens in received context")
    compression_ratio: float = Field(..., description="Ratio of compression (0-1)")


class ContextHandoff(BaseModel):
    """Document schema for agent-to-agent context transfer.
    
    This represents a single handoff of context from one agent to another
    in a multi-agent pipeline.
    
    Example:
        Researcher (agent_from) → Summarizer (agent_to)
        - context_sent: JSON formatted movie data
        - context_received: Same data received by summarizer
        - output_generated: Summary text produced by summarizer
    """
    
    # Required identifiers
    handoff_id: str = Field(
        ...,
        description="Unique identifier for this handoff"
    )
    
    pipeline_id: str = Field(
        ...,
        description="Identifier for the pipeline run this handoff belongs to"
    )
    
    task_id: Optional[str] = Field(
        default=None,
        description="Identifier for the specific task being executed"
    )
    
    # Agent information
    agent_from: str = Field(
        ...,
        description="Name/ID of the agent sending context"
    )
    
    agent_to: str = Field(
        ...,
        description="Name/ID of the agent receiving context"
    )
    
    # Context data
    context_sent: str = Field(
        ...,
        description="The context/data sent by agent_from"
    )
    
    context_received: str = Field(
        ...,
        description="The context/data as received by agent_to (may differ due to formatting)"
    )
    
    output_generated: Optional[str] = Field(
        default=None,
        description="Output produced by agent_to after processing the context"
    )
    
    # Format information
    format_type: str = Field(
        ...,
        description="Format of the context (json, markdown, plaintext, etc.)"
    )
    
    # Embeddings (stored as lists for MongoDB)
    embeddings: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="Vector embeddings for semantic search. Keys: sent_vector, received_vector, output_vector"
    )
    
    # Evaluation results
    eval_scores: EvalScores = Field(
        default_factory=EvalScores,
        description="Computed evaluation metrics for this handoff"
    )
    
    compression_stats: Optional[CompressionStats] = Field(
        default=None,
        description="Token compression statistics"
    )
    
    # Metadata
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this handoff occurred"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (model names, task description, etc.)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "handoff_id": "handoff_abc123",
                "pipeline_id": "pipeline_json_xyz789",
                "task_id": "task_nolan_films",
                "agent_from": "researcher",
                "agent_to": "summarizer",
                "context_sent": '{"title": "Inception", "year": 2010, "rating": 8.8}',
                "context_received": '{"title": "Inception", "year": 2010, "rating": 8.8}',
                "output_generated": "Christopher Nolan's Inception explores dreams and reality...",
                "format_type": "json",
                "embeddings": {
                    "sent_vector": [0.1, 0.2, 0.3],
                    "received_vector": [0.1, 0.2, 0.3],
                    "output_vector": [0.15, 0.22, 0.28]
                },
                "eval_scores": {
                    "fidelity": 0.91,
                    "drift": 0.08,
                    "compression_efficiency": 0.45,
                    "fact_retention": 0.87
                },
                "compression_stats": {
                    "sent_tokens": 450,
                    "received_tokens": 450,
                    "compression_ratio": 0.0
                },
                "timestamp": "2025-01-11T10:30:00Z",
                "metadata": {
                    "embedding_model": "all-MiniLM-L6-v2",
                    "llm_model": "llama3.1:8b",
                    "task_description": "Summarize Nolan films"
                }
            }
        }


class PipelineRun(BaseModel):
    """Summary document for a complete pipeline execution.
    
    This aggregates metrics across all handoffs in a pipeline run.
    """
    
    pipeline_id: str = Field(..., description="Unique pipeline identifier")
    
    task_description: str = Field(..., description="Description of the task")
    
    format_type: str = Field(..., description="Context format used (json/markdown)")
    
    agents: List[str] = Field(
        default_factory=list,
        description="List of agents in the pipeline"
    )
    
    # Aggregated metrics
    avg_fidelity: float = Field(
        default=0.0,
        description="Average fidelity score across all handoffs"
    )
    
    avg_drift: float = Field(
        default=0.0,
        description="Average drift score across all handoffs"
    )
    
    avg_compression_efficiency: float = Field(
        default=0.0,
        description="Average compression efficiency"
    )
    
    avg_fact_retention: float = Field(
        default=0.0,
        description="Average fact retention"
    )
    
    handoff_count: int = Field(
        default=0,
        description="Number of handoffs in this pipeline"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the pipeline was executed"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional pipeline metadata"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "pipeline_id": "pipeline_json_xyz789",
                "task_description": "Summarize Christopher Nolan films",
                "format_type": "json",
                "agents": ["researcher", "summarizer"],
                "avg_fidelity": 0.91,
                "avg_drift": 0.08,
                "avg_compression_efficiency": 0.45,
                "avg_fact_retention": 0.87,
                "handoff_count": 1,
                "timestamp": "2025-01-11T10:30:00Z",
                "metadata": {
                    "embedding_model": "all-MiniLM-L6-v2",
                    "source_database": "sample_mflix"
                }
            }
        }