"""Evaluation API endpoints for dashboard visualization."""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.api.dependencies import get_mongo_client
from backend.db.aggregation import rollup_by_format

logger = logging.getLogger(__name__)

router = APIRouter()


class HandoffScore(BaseModel):
    """Handoff evaluation scores."""
    fidelity: float = Field(..., ge=0, le=1)
    drift: float = Field(..., ge=0, le=1)
    compression: float = Field(..., ge=0, le=1)
    temporal_coherence: Optional[float] = Field(None, ge=0, le=1)


class HandoffSummary(BaseModel):
    """Summary of a single handoff."""
    handoff_id: str
    pipeline_id: str
    agent_from: str
    agent_to: str
    eval_scores: HandoffScore
    key_info_preserved: List[str] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)


class PipelineScore(BaseModel):
    """Pipeline aggregate scores."""
    avg_fidelity: float = Field(..., ge=0, le=1)
    avg_drift: float = Field(..., ge=0, le=1)
    total_compression: float = Field(..., ge=0, le=1)
    end_to_end_fidelity: float = Field(..., ge=0, le=1)


class PipelineSummary(BaseModel):
    """Summary of a complete pipeline."""
    pipeline_id: str
    format: Optional[str] = None
    handoff_count: int
    overall_pipeline_score: PipelineScore


class ComparisonResult(BaseModel):
    """Comparison between two pipelines."""
    json_pipeline: PipelineSummary
    markdown_pipeline: PipelineSummary
    fidelity_delta: float
    drift_delta: float
    compression_delta: float
    winner: str


@router.get("/pipelines", response_model=List[PipelineSummary])
async def list_pipelines(
    limit: int = Query(default=20, le=100),
    skip: int = Query(default=0, ge=0),
    format_filter: Optional[str] = Query(default=None, alias="format"),
):
    """List evaluation pipelines with pagination.
    
    Args:
        limit: Maximum number of pipelines to return.
        skip: Number of pipelines to skip.
        format_filter: Filter by format (json or markdown).
        
    Returns:
        List of pipeline summaries.
    """
    try:
        client = get_mongo_client()
        coll = client.get_collection("eval_pipelines")
        
        query = {}
        if format_filter:
            query["pipeline_id"] = {"$regex": f"^{format_filter.lower()}-"}
        
        cursor = coll.find(query).sort("_id", -1).skip(skip).limit(limit)
        
        pipelines = []
        for doc in cursor:
            # Extract format from pipeline_id
            pid = doc.get("pipeline_id", "")
            fmt = "json" if pid.startswith("json-") else "markdown" if pid.startswith("md-") else None
            
            pipelines.append(PipelineSummary(
                pipeline_id=doc["pipeline_id"],
                format=fmt,
                handoff_count=len(doc.get("handoffs", [])),
                overall_pipeline_score=PipelineScore(**doc.get("overall_pipeline_score", {}))
            ))
        
        return pipelines
        
    except Exception as e:
        logger.error(f"Failed to list pipelines: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipelines/{pipeline_id}", response_model=Dict)
async def get_pipeline_detail(pipeline_id: str):
    """Get detailed information about a pipeline.
    
    Args:
        pipeline_id: Pipeline identifier.
        
    Returns:
        Complete pipeline document with handoffs.
    """
    try:
        client = get_mongo_client()
        coll = client.get_collection("eval_pipelines")
        
        doc = coll.find_one({"pipeline_id": pipeline_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        # Convert ObjectId to string
        doc["_id"] = str(doc["_id"])
        
        return doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/handoffs", response_model=List[HandoffSummary])
async def list_handoffs(
    pipeline_id: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    skip: int = Query(default=0, ge=0),
):
    """List evaluation handoffs with optional pipeline filter.
    
    Args:
        pipeline_id: Filter by pipeline ID.
        limit: Maximum number of handoffs to return.
        skip: Number of handoffs to skip.
        
    Returns:
        List of handoff summaries.
    """
    try:
        client = get_mongo_client()
        coll = client.get_collection("eval_handoffs")
        
        query = {}
        if pipeline_id:
            query["pipeline_id"] = pipeline_id
        
        cursor = coll.find(query).sort("_id", -1).skip(skip).limit(limit)
        
        handoffs = []
        for doc in cursor:
            handoffs.append(HandoffSummary(
                handoff_id=doc["handoff_id"],
                pipeline_id=doc["pipeline_id"],
                agent_from=doc["agent_from"],
                agent_to=doc["agent_to"],
                eval_scores=HandoffScore(**doc.get("eval_scores", {})),
                key_info_preserved=doc.get("key_info_preserved", []),
                metadata=doc.get("metadata", {})
            ))
        
        return handoffs
        
    except Exception as e:
        logger.error(f"Failed to list handoffs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comparison/latest", response_model=ComparisonResult)
async def get_latest_comparison():
    """Get the latest JSON vs Markdown comparison.
    
    Returns:
        Comparison result with metrics.
    """
    try:
        client = get_mongo_client()
        coll = client.get_collection("eval_pipelines")
        
        # Find latest JSON and Markdown pipelines
        json_doc = coll.find_one(
            {"pipeline_id": {"$regex": "^json-"}},
            sort=[("_id", -1)]
        )
        md_doc = coll.find_one(
            {"pipeline_id": {"$regex": "^md-"}},
            sort=[("_id", -1)]
        )
        
        if not json_doc or not md_doc:
            raise HTTPException(
                status_code=404,
                detail="No comparison available. Run demo_recommendation_pipeline.py --compare"
            )
        
        json_scores = json_doc.get("overall_pipeline_score", {})
        md_scores = md_doc.get("overall_pipeline_score", {})
        
        json_summary = PipelineSummary(
            pipeline_id=json_doc["pipeline_id"],
            format="json",
            handoff_count=len(json_doc.get("handoffs", [])),
            overall_pipeline_score=PipelineScore(**json_scores)
        )
        
        md_summary = PipelineSummary(
            pipeline_id=md_doc["pipeline_id"],
            format="markdown",
            handoff_count=len(md_doc.get("handoffs", [])),
            overall_pipeline_score=PipelineScore(**md_scores)
        )
        
        fidelity_delta = json_scores.get("avg_fidelity", 0) - md_scores.get("avg_fidelity", 0)
        drift_delta = json_scores.get("avg_drift", 0) - md_scores.get("avg_drift", 0)
        compression_delta = json_scores.get("total_compression", 0) - md_scores.get("total_compression", 0)
        
        # Determine winner based on fidelity and drift
        json_better = fidelity_delta > 0 and drift_delta < 0
        winner = "json" if json_better else "markdown" if fidelity_delta < 0 else "tie"
        
        return ComparisonResult(
            json_pipeline=json_summary,
            markdown_pipeline=md_summary,
            fidelity_delta=round(fidelity_delta, 4),
            drift_delta=round(drift_delta, 4),
            compression_delta=round(compression_delta, 4),
            winner=winner
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get comparison: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/by-format")
async def get_stats_by_format():
    """Get aggregate statistics grouped by format.
    
    Returns:
        Statistics for JSON and Markdown formats.
    """
    try:
        client = get_mongo_client()
        results = rollup_by_format(client)
        
        return {
            "formats": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Failed to get format stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_evaluation_summary():
    """Get overall evaluation summary statistics.
    
    Returns:
        Summary of all evaluations in the database.
    """
    try:
        client = get_mongo_client()
        handoffs_coll = client.get_collection("eval_handoffs")
        pipelines_coll = client.get_collection("eval_pipelines")
        
        total_handoffs = handoffs_coll.count_documents({})
        total_pipelines = pipelines_coll.count_documents({})
        
        # Aggregate average scores across all handoffs
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "avg_fidelity": {"$avg": "$eval_scores.fidelity"},
                    "avg_drift": {"$avg": "$eval_scores.drift"},
                    "avg_compression": {"$avg": "$eval_scores.compression"},
                    "min_fidelity": {"$min": "$eval_scores.fidelity"},
                    "max_fidelity": {"$max": "$eval_scores.fidelity"},
                }
            }
        ]
        
        agg_result = list(handoffs_coll.aggregate(pipeline))
        stats = agg_result[0] if agg_result else {}
        
        return {
            "total_handoffs": total_handoffs,
            "total_pipelines": total_pipelines,
            "overall_stats": {
                "avg_fidelity": round(stats.get("avg_fidelity", 0), 4),
                "avg_drift": round(stats.get("avg_drift", 0), 4),
                "avg_compression": round(stats.get("avg_compression", 0), 4),
                "min_fidelity": round(stats.get("min_fidelity", 0), 4),
                "max_fidelity": round(stats.get("max_fidelity", 0), 4),
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    """Delete a pipeline and its handoffs.
    
    Args:
        pipeline_id: Pipeline identifier.
        
    Returns:
        Deletion confirmation.
    """
    try:
        client = get_mongo_client()
        
        # Delete handoffs first
        handoffs_coll = client.get_collection("eval_handoffs")
        handoff_result = handoffs_coll.delete_many({"pipeline_id": pipeline_id})
        
        # Delete pipeline
        pipelines_coll = client.get_collection("eval_pipelines")
        pipeline_result = pipelines_coll.delete_one({"pipeline_id": pipeline_id})
        
        if pipeline_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Pipeline not found")
        
        return {
            "deleted_pipeline": pipeline_id,
            "deleted_handoffs": handoff_result.deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
