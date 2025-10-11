"""Recommendation API endpoints."""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from backend.agents import (
    ContentAnalyzerAgent,
    ExplainerAgent,
    RecommenderAgent,
    UserProfilerAgent,
)
from backend.agents.base import ContextFormat
from backend.api.app import get_mongo_client_instance
from backend.services.mflix_service import MflixService, MflixServiceError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{email}")
async def get_recommendations(email: str, top_n: int = 5) -> Dict:
    """Get personalized movie recommendations for a user.
    
    This endpoint runs the complete multi-agent pipeline:
    User Profiler → Content Analyzer → Recommender → Explainer
    
    Args:
        email: User's email address.
        top_n: Number of recommendations to return.
        
    Returns:
        Recommendations with explanations and pipeline metrics.
    """
    try:
        client = get_mongo_client_instance()
        service = MflixService(client)
        
        # Check if user exists
        user = service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Initialize agents
        profiler = UserProfilerAgent(service, ContextFormat.JSON)
        analyzer = ContentAnalyzerAgent(service, ContextFormat.JSON, max_candidates=30)
        recommender = RecommenderAgent(ContextFormat.JSON, top_n=top_n)
        explainer = ExplainerAgent(ContextFormat.JSON)
        
        # Run pipeline
        logger.info(f"Running recommendation pipeline for {email}")
        
        # Step 1: Profile user
        profile_output = profiler.process_user(email)
        if not profile_output.success:
            raise HTTPException(
                status_code=500,
                detail=f"User profiling failed: {profile_output.error_message}"
            )
        
        # Step 2: Analyze content
        analysis_output = analyzer.process(profile_output.context)
        if not analysis_output.success:
            raise HTTPException(
                status_code=500,
                detail=f"Content analysis failed: {analysis_output.error_message}"
            )
        
        # Step 3: Generate recommendations
        recommendation_output = recommender.process(analysis_output.context)
        if not recommendation_output.success:
            raise HTTPException(
                status_code=500,
                detail=f"Recommendation failed: {recommendation_output.error_message}"
            )
        
        # Step 4: Generate explanations
        explanation_output = explainer.process(recommendation_output.context)
        if not explanation_output.success:
            raise HTTPException(
                status_code=500,
                detail=f"Explanation failed: {explanation_output.error_message}"
            )
        
        # Build response
        total_time = (
            profile_output.execution_time_ms +
            analysis_output.execution_time_ms +
            recommendation_output.execution_time_ms +
            explanation_output.execution_time_ms
        )
        
        return {
            "user": {
                "name": user.name,
                "email": user.email,
            },
            "recommendations": explanation_output.context.data["recommendations_with_explanations"],
            "pipeline_metrics": {
                "total_execution_time_ms": total_time,
                "agents": {
                    "user_profiler": {
                        "execution_time_ms": profile_output.execution_time_ms,
                        "tokens": profile_output.context.tokens,
                    },
                    "content_analyzer": {
                        "execution_time_ms": analysis_output.execution_time_ms,
                        "tokens": analysis_output.context.tokens,
                        "candidates_found": analysis_output.context.data["total_candidates_analyzed"],
                    },
                    "recommender": {
                        "execution_time_ms": recommendation_output.execution_time_ms,
                        "tokens": recommendation_output.context.tokens,
                    },
                    "explainer": {
                        "execution_time_ms": explanation_output.execution_time_ms,
                        "tokens": explanation_output.context.tokens,
                    },
                },
            },
        }
        
    except HTTPException:
        raise
    except MflixServiceError as e:
        logger.error(f"Service error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/profile/{email}")
async def get_user_profile(email: str) -> Dict:
    """Get user profile analysis.
    
    Args:
        email: User's email address.
        
    Returns:
        User profile with preferences.
    """
    try:
        client = get_mongo_client_instance()
        service = MflixService(client)
        
        # Check if user exists
        user = service.get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Run user profiler
        profiler = UserProfilerAgent(service, ContextFormat.JSON)
        profile_output = profiler.process_user(email)
        
        if not profile_output.success:
            raise HTTPException(
                status_code=500,
                detail=f"Profiling failed: {profile_output.error_message}"
            )
        
        return {
            "profile": profile_output.context.data,
            "execution_time_ms": profile_output.execution_time_ms,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

