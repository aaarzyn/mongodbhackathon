"""Evaluator service to compute metrics and persist evaluation records.

Wires together token counting, key-info extraction, metric computation,
and MongoDB persistence for handoff- and pipeline-level evaluations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

from backend.db.mongo_client import MongoDBClient
from backend.db.aggregation import (
    AggregationError,
    compute_pipeline_rollup,
    get_handoffs_by_pipeline,
    insert_handoff,
    upsert_pipeline_rollup,
)
from backend.evaluator.extract import compute_key_info_preserved
from backend.evaluator.metrics import evaluate_handoff
from backend.evaluator.schema import EvalScores, HandoffEvaluation, PipelineEvaluation

logger = logging.getLogger(__name__)


class EvaluatorServiceError(Exception):
    """Raised when evaluation service operations fail."""

    pass


def _count_tokens(text: str) -> int:
    # Simple whitespace tokenization; deterministic and model-agnostic
    if not text:
        return 0
    return len(text.strip().split())


class EvaluatorService:
    """High-level API for computing and storing evaluation metrics."""

    def __init__(self, client: MongoDBClient) -> None:
        self.client = client

    def evaluate_and_store_handoff(
        self,
        *,
        pipeline_id: str,
        handoff_id: str,
        agent_from: str,
        agent_to: str,
        context_sent: str,
        context_received: str,
        tokens_before: Optional[int] = None,
        tokens_after: Optional[int] = None,
        sent_vec: Optional[Sequence[float]] = None,
        received_vec: Optional[Sequence[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> HandoffEvaluation:
        """Compute metrics for a handoff and persist the document."""
        tb = tokens_before if tokens_before is not None else _count_tokens(context_sent)
        ta = tokens_after if tokens_after is not None else _count_tokens(context_received)

        fidelity, drift, compression, temporal = evaluate_handoff(
            context_sent=context_sent,
            context_received=context_received,
            tokens_before=tb,
            tokens_after=ta,
            sent_vec=sent_vec,
            received_vec=received_vec,
        )

        key_preserved = compute_key_info_preserved(context_sent, context_received)

        scores = EvalScores(
            fidelity=fidelity,
            drift=drift,
            compression=compression,
            temporal_coherence=temporal,
            response_utility=None,
        )

        doc = HandoffEvaluation(
            pipeline_id=pipeline_id,
            handoff_id=handoff_id,
            agent_from=agent_from,
            agent_to=agent_to,
            context_sent=context_sent,
            context_received=context_received,
            eval_scores=scores,
            vectors=None,
            key_info_preserved=key_preserved,
            metadata=metadata or {"format": metadata.get("format") if metadata else None, "tokens": {"before": tb, "after": ta}},
        )

        try:
            insert_handoff(self.client, doc)
        except AggregationError as e:
            raise EvaluatorServiceError(str(e)) from e
        return doc

    def finalize_pipeline(self, pipeline_id: str) -> PipelineEvaluation:
        """Compute pipeline rollup from stored handoffs and persist summary."""
        handoffs = get_handoffs_by_pipeline(self.client, pipeline_id)
        score = compute_pipeline_rollup(handoffs)
        summary = PipelineEvaluation(
            pipeline_id=pipeline_id, handoffs=handoffs, overall_pipeline_score=score
        )
        try:
            upsert_pipeline_rollup(self.client, pipeline_id, score, handoffs)
        except AggregationError as e:
            raise EvaluatorServiceError(str(e)) from e
        return summary

