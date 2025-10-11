"""Recommendation model for storing generated recommendations."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class RecommendationItem(BaseModel):
    """Individual movie recommendation."""

    rank: int = Field(..., description="Recommendation rank")
    movie_id: Optional[str] = Field(default=None, description="Movie ID")
    title: str = Field(..., description="Movie title")
    year: Optional[int] = Field(default=None, description="Release year")
    genres: List[str] = Field(default_factory=list, description="Movie genres")
    directors: List[str] = Field(default_factory=list, description="Directors")
    imdb_rating: Optional[float] = Field(default=None, description="IMDb rating")
    confidence: float = Field(..., description="Recommendation confidence score")
    similarity_score: Optional[float] = Field(
        default=None, description="Similarity score from content analyzer"
    )
    explanation: str = Field(..., description="Natural language explanation")
    key_appeal_points: List[str] = Field(
        default_factory=list, description="Key appeal points"
    )


class PipelineMetrics(BaseModel):
    """Metrics from the recommendation pipeline execution."""

    total_execution_time_ms: float = Field(
        ..., description="Total pipeline execution time"
    )
    user_profiler_time_ms: float = Field(..., description="User profiler time")
    content_analyzer_time_ms: float = Field(..., description="Content analyzer time")
    recommender_time_ms: float = Field(..., description="Recommender time")
    explainer_time_ms: float = Field(..., description="Explainer time")
    user_profiler_tokens: int = Field(..., description="User profiler tokens")
    content_analyzer_tokens: int = Field(..., description="Content analyzer tokens")
    recommender_tokens: int = Field(..., description="Recommender tokens")
    explainer_tokens: int = Field(..., description="Explainer tokens")
    total_tokens: int = Field(..., description="Total tokens processed")
    candidates_analyzed: int = Field(..., description="Number of candidates analyzed")


class SavedRecommendation(BaseModel):
    """Saved recommendation document for MongoDB."""

    id: Optional[str] = Field(default=None, alias="_id", description="Document ID")
    user_email: EmailStr = Field(..., description="User email")
    user_name: str = Field(..., description="User name")
    recommendations: List[RecommendationItem] = Field(
        ..., description="List of recommended movies"
    )
    pipeline_metrics: PipelineMetrics = Field(..., description="Pipeline metrics")
    context_format: str = Field(
        default="json", description="Context format used (json or markdown)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When recommendations were created"
    )
    user_profile_summary: Dict = Field(
        default_factory=dict, description="Summary of user preferences"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "user_email": "mark_addy@gameofthron.es",
                "user_name": "Robert Baratheon",
                "recommendations": [
                    {
                        "rank": 1,
                        "title": "Men in Black",
                        "year": 1997,
                        "confidence": 0.89,
                        "explanation": "We recommend...",
                    }
                ],
                "created_at": "2025-10-11T16:00:00Z",
            }
        }

