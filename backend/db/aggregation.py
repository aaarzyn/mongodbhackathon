"""Aggregation and persistence utilities for evaluation data.

Provides helper functions to store and roll up handoff-level and
pipeline-level evaluation metrics in MongoDB.
"""

from __future__ import annotations

import logging
from math import prod
from statistics import geometric_mean
from typing import Any, Dict, List, Optional

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from backend.db.mongo_client import MongoDBClient
from backend.evaluator.schema import HandoffEvaluation, PipelineEvaluation, PipelineScore

logger = logging.getLogger(__name__)


class AggregationError(Exception):
    """Raised when aggregation or persistence operations fail."""

    pass


def _eval_handoffs_collection(client: MongoDBClient) -> Collection:
    return client.get_collection("eval_handoffs")


def _eval_pipelines_collection(client: MongoDBClient) -> Collection:
    return client.get_collection("eval_pipelines")


def insert_handoff(client: MongoDBClient, doc: HandoffEvaluation) -> str:
    """Insert a handoff evaluation document.

    Returns the inserted document ID.
    """
    try:
        result = _eval_handoffs_collection(client).insert_one(doc.model_dump(by_alias=True))
        return str(result.inserted_id)
    except PyMongoError as e:
        raise AggregationError(f"Failed to insert handoff eval: {e}") from e


def get_handoffs_by_pipeline(client: MongoDBClient, pipeline_id: str) -> List[HandoffEvaluation]:
    try:
        cursor = _eval_handoffs_collection(client).find({"pipeline_id": pipeline_id})
        return [HandoffEvaluation(**doc) for doc in cursor]
    except PyMongoError as e:
        raise AggregationError(f"Failed to fetch handoffs: {e}") from e


def compute_pipeline_rollup(handoffs: List[HandoffEvaluation]) -> PipelineScore:
    if not handoffs:
        return PipelineScore(
            avg_fidelity=0.0, avg_drift=0.0, total_compression=0.0, end_to_end_fidelity=0.0
        )
    fidelities = [h.eval_scores.fidelity for h in handoffs]
    drifts = [h.eval_scores.drift for h in handoffs]
    compressions = [h.eval_scores.compression for h in handoffs]

    avg_fidelity = sum(fidelities) / len(fidelities)
    avg_drift = sum(drifts) / len(drifts)
    total_compression = sum(compressions) / len(compressions)

    # Geometric mean reflects compounding preservation across handoffs.
    try:
        end_to_end_fidelity = geometric_mean([max(f, 1e-6) for f in fidelities])
    except Exception:
        end_to_end_fidelity = avg_fidelity

    return PipelineScore(
        avg_fidelity=round(avg_fidelity, 4),
        avg_drift=round(avg_drift, 4),
        total_compression=round(total_compression, 4),
        end_to_end_fidelity=round(end_to_end_fidelity, 4),
    )


def insert_pipeline(client: MongoDBClient, doc: PipelineEvaluation) -> str:
    try:
        result = _eval_pipelines_collection(client).insert_one(
            doc.model_dump(by_alias=True)
        )
        return str(result.inserted_id)
    except PyMongoError as e:
        raise AggregationError(f"Failed to insert pipeline eval: {e}") from e


def upsert_pipeline_rollup(
    client: MongoDBClient, pipeline_id: str, score: PipelineScore, handoffs: List[HandoffEvaluation]
) -> str:
    """Upsert a pipeline evaluation summary document."""
    try:
        payload: Dict[str, Any] = {
            "pipeline_id": pipeline_id,
            "handoffs": [h.model_dump(by_alias=True) for h in handoffs],
            "overall_pipeline_score": score.model_dump(),
        }
        result = _eval_pipelines_collection(client).update_one(
            {"pipeline_id": pipeline_id},
            {"$set": payload},
            upsert=True,
        )
        # Return a synthetic ID string for traceability
        return pipeline_id
    except PyMongoError as e:
        raise AggregationError(f"Failed to upsert pipeline rollup: {e}") from e


def rollup_by_format(client: MongoDBClient) -> List[Dict[str, Any]]:
    """Aggregate average scores by context format if present in metadata.

    Expects documents to include `metadata.format` set to values like
    "json" or "markdown".
    """
    try:
        pipeline = [
            {"$match": {"metadata.format": {"$exists": True}}},
            {
                "$group": {
                    "_id": "$metadata.format",
                    "avg_fidelity": {"$avg": "$eval_scores.fidelity"},
                    "avg_drift": {"$avg": "$eval_scores.drift"},
                    "avg_compression": {"$avg": "$eval_scores.compression"},
                }
            },
            {"$sort": {"avg_fidelity": -1}},
        ]
        cursor = _eval_handoffs_collection(client).aggregate(pipeline)
        return list(cursor)
    except PyMongoError as e:
        raise AggregationError(f"Failed to roll up by format: {e}") from e

