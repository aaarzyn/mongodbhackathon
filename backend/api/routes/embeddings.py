"""Embedding-related API endpoints."""

import logging
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query

from backend.api.dependencies import get_mflix_service
from backend.models.movie import Movie
from backend.services.mflix_service import MflixServiceError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats")
async def get_embedding_stats() -> Dict:
    """Get statistics about movies with embeddings.
    
    Returns:
        Dictionary with embedding coverage statistics.
    """
    try:
        service = get_mflix_service()
        stats = service.get_embedding_stats()
        return stats
    except MflixServiceError as e:
        logger.error(f"Failed to get embedding stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/movies", response_model=List[Movie])
async def get_embedded_movies(
    genre: str = Query(..., description="Genre to filter by"),
    limit: int = Query(default=20, le=100),
    skip: int = Query(default=0, ge=0),
):
    """Get movies with embeddings by genre.
    
    These movies from the embedded_movies collection have plot_embedding data
    that can be used for semantic search and context evaluation.
    
    Args:
        genre: Genre to filter by (e.g., "Action", "Fantasy", "Western").
        limit: Maximum number of movies to return.
        skip: Number of movies to skip.
        
    Returns:
        List of movies with embeddings.
    """
    try:
        service = get_mflix_service()
        movies = service.get_embedded_movies_by_genre(genre, limit=limit, skip=skip)
        return movies
    except MflixServiceError as e:
        logger.error(f"Failed to get embedded movies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

