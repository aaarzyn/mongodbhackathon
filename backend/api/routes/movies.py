"""Movie-related API endpoints."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.api.dependencies import get_mflix_service
from backend.models.movie import Movie
from backend.services.mflix_service import MflixServiceError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[Movie])
async def list_movies(
    skip: int = 0,
    limit: int = 20,
    genre: Optional[str] = None,
    director: Optional[str] = None,
    min_rating: float = 0.0,
    search: Optional[str] = None,
    with_embeddings: bool = Query(
        default=False,
        description="Only return movies with embeddings (for Action, Fantasy, Western)"
    ),
):
    """List movies with optional filtering.
    
    Args:
        skip: Number of movies to skip.
        limit: Maximum number of movies to return.
        genre: Filter by genre.
        director: Filter by director.
        min_rating: Minimum IMDb rating.
        search: Search query for title.
        with_embeddings: Only return movies with embeddings.
        
    Returns:
        List of movies.
    """
    try:
        service = get_mflix_service()
        
        # If with_embeddings is requested and genre is provided, use embedded_movies
        if with_embeddings and genre:
            movies = service.get_embedded_movies_by_genre(genre, limit=limit, skip=skip)
        # Apply filters
        elif search:
            movies = service.search_movies_by_title(search, limit=limit)
        elif genre:
            movies = service.get_movies_by_genre(genre, limit=limit, skip=skip)
        elif director:
            movies = service.get_movies_by_director(director, limit=limit)
        else:
            movies = service.get_top_rated_movies(
                limit=limit, min_rating=min_rating, min_votes=1000
            )
        
        return movies
    except MflixServiceError as e:
        logger.error(f"Failed to list movies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/genres")
async def list_genres():
    """Get list of available genres.
    
    Returns:
        List of genre names.
    """
    # Common movie genres
    genres = [
        "Action",
        "Adventure",
        "Animation",
        "Biography",
        "Comedy",
        "Crime",
        "Documentary",
        "Drama",
        "Family",
        "Fantasy",
        "Film-Noir",
        "History",
        "Horror",
        "Music",
        "Musical",
        "Mystery",
        "Romance",
        "Sci-Fi",
        "Sport",
        "Thriller",
        "War",
        "Western",
    ]
    return {"genres": genres}


@router.get("/top-rated", response_model=List[Movie])
async def get_top_rated_movies(
    limit: int = Query(default=20, le=100),
    min_rating: float = Query(default=7.0, ge=0, le=10),
    min_votes: int = Query(default=10000, ge=0),
):
    """Get top-rated movies.
    
    Args:
        limit: Maximum number of movies to return.
        min_rating: Minimum IMDb rating.
        min_votes: Minimum number of votes.
        
    Returns:
        List of top-rated movies.
    """
    try:
        service = get_mflix_service()
        movies = service.get_top_rated_movies(
            limit=limit, min_rating=min_rating, min_votes=min_votes
        )
        return movies
    except MflixServiceError as e:
        logger.error(f"Failed to get top rated movies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{movie_id}", response_model=Movie)
async def get_movie(movie_id: str):
    """Get movie by ID.
    
    Args:
        movie_id: Movie ID.
        
    Returns:
        Movie object.
    """
    try:
        service = get_mflix_service()
        movie = service.get_movie_by_id(movie_id)
        
        if not movie:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        return movie
    except MflixServiceError as e:
        logger.error(f"Failed to get movie: {e}")
        raise HTTPException(status_code=500, detail=str(e))

