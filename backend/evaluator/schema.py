"""Pydantic schemas for evaluation records and aggregates.

These models define how evaluation data is structured when stored in
MongoDB and exchanged within the backend. They follow the ContextScope
Eval design in PROJECT.md, focusing on handoff-level and pipeline-level
metrics.

Core metrics tracked:
- Context Transmission Fidelity
- Relevance Drift
- Compression Efficiency
- Temporal Coherence (optional)
- Response Utility (optional)

All models include comprehensive type hints and validation-friendly
defaults to support robust usage across the codebase.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class EvaluationSchemaError(Exception):
    """Base exception for evaluation schema errors."""

    pass


class VectorBundle(BaseModel):
    """Embedding vectors for different stages of a handoff.

    Attributes:
        sent: Embedding for the context that was sent.
        received: Embedding for the context that was received.
        output: Embedding for the downstream agent output (optional).
    """

    sent: Optional[List[float]] = Field(default=None, description="Sent context vector")
    received: Optional[List[float]] = Field(
        default=None, description="Received context vector"
    )
    output: Optional[List[float]] = Field(default=None, description="Output vector")

    @field_validator("sent", "received", "output")
    @classmethod
    def validate_vector(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is None:
            return v
        if not v:
            raise EvaluationSchemaError("Embedding vector must not be empty")
        return v


class EvalScores(BaseModel):
    """Scores computed for a single handoff.

    All scores are normalized to [0, 1], unless explicitly noted as optional.
    """

    fidelity: float = Field(..., ge=0.0, le=1.0, description="Context fidelity")
    drift: float = Field(..., ge=0.0, le=1.0, description="Relevance drift")
    compression: float = Field(
        ..., ge=0.0, le=1.0, description="Compression efficiency (0-1)"
    )
    temporal_coherence: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Temporal coherence score"
    )
    response_utility: Optional[float] = Field(
        default=None,
        description="Utility improvement vs baseline (e.g., relative delta)",
    )


class HandoffEvaluation(BaseModel):
    """Evaluation document for a single context handoff between agents.

    Mirrors the structure described in PROJECT.md and is intended to be stored
    in MongoDB. Embedding vectors are optional to support environments where
    model downloads are restricted.
    """

    handoff_id: str = Field(..., description="Unique ID for the handoff")
    agent_from: str = Field(..., description="Upstream agent name")
    agent_to: str = Field(..., description="Downstream agent name")

    context_sent: str = Field(..., description="Raw context provided to downstream")
    context_received: str = Field(..., description="What downstream perceived/used")

    eval_scores: EvalScores = Field(..., description="Computed evaluation scores")
    vectors: Optional[VectorBundle] = Field(
        default=None, description="Optional embedding vectors"
    )

    key_info_preserved: List[str] = Field(
        default_factory=list,
        description="List of key info units judged as preserved",
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (token counts, formats, etc)",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="UTC timestamp of evaluation"
    )


class PipelineScore(BaseModel):
    """Aggregate scores across a pipeline for quick rollups."""

    avg_fidelity: float = Field(..., ge=0.0, le=1.0)
    avg_drift: float = Field(..., ge=0.0, le=1.0)
    total_compression: float = Field(..., ge=0.0, le=1.0)
    end_to_end_fidelity: float = Field(..., ge=0.0, le=1.0)


class PipelineEvaluation(BaseModel):
    """Pipeline-level evaluation summary.

    Useful for dashboard rollups and experiment tracking.
    """

    pipeline_id: str = Field(..., description="Unique ID for the pipeline run")
    handoffs: List[HandoffEvaluation] = Field(
        default_factory=list, description="All handoff evaluations in order"
    )
    overall_pipeline_score: PipelineScore = Field(
        ..., description="Aggregate pipeline metrics"
    )
