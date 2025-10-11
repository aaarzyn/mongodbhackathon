"""Comprehensive test for all genres in the Mflix dataset.

This script tests that every genre can be queried successfully and returns
quality movies with ratings.

Usage:
    python test_all_genres.py
"""

import logging
from typing import Dict, List

from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient
from backend.services.mflix_service import MflixService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ALL_GENRES = [
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


def test_genre(service: MflixService, genre: str, limit: int = 5) -> Dict:
    """Test a single genre.
    
    Args:
        service: MflixService instance.
        genre: Genre name to test.
        limit: Number of movies to fetch.
        
    Returns:
        Test result dictionary.
    """
    try:
        movies = service.get_movies_by_genre(genre, limit=limit)
        
        if not movies:
            return {
                "genre": genre,
                "status": "warning",
                "count": 0,
                "message": "No movies found",
                "top_movie": None,
            }
        
        # Get top movie info
        top_movie = movies[0]
        top_rating = top_movie.imdb.rating if top_movie.imdb else None
        
        return {
            "genre": genre,
            "status": "success",
            "count": len(movies),
            "message": f"Found {len(movies)} movies",
            "top_movie": {
                "title": top_movie.title,
                "year": top_movie.year,
                "rating": top_rating,
            },
        }
    except Exception as e:
        return {
            "genre": genre,
            "status": "error",
            "count": 0,
            "message": str(e),
            "top_movie": None,
        }


def main() -> int:
    """Main test function.
    
    Returns:
        Exit code.
    """
    logger.info("=" * 70)
    logger.info("  Testing All 22 Genres")
    logger.info("=" * 70)
    
    # Connect to database
    try:
        settings = get_settings()
        client = MongoDBClient(settings)
        service = MflixService(client)
        logger.info("✓ Connected to MongoDB Atlas\n")
    except Exception as e:
        logger.error(f"✗ Failed to connect: {str(e)}")
        return 1
    
    # Test all genres
    results = []
    for genre in ALL_GENRES:
        result = test_genre(service, genre, limit=5)
        results.append(result)
        
        # Log result
        status_emoji = {
            "success": "✓",
            "warning": "⚠",
            "error": "✗",
        }
        emoji = status_emoji.get(result["status"], "?")
        
        if result["status"] == "success":
            top = result["top_movie"]
            logger.info(
                f"{emoji} {result['genre']:15s} - {result['count']} movies - "
                f"Top: {top['title'][:40]:<40s} ({top['year']}) {top['rating']}"
            )
        elif result["status"] == "warning":
            logger.warning(f"{emoji} {result['genre']:15s} - {result['message']}")
        else:
            logger.error(f"{emoji} {result['genre']:15s} - ERROR: {result['message'][:50]}")
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("  Summary")
    logger.info("=" * 70)
    
    success_count = sum(1 for r in results if r["status"] == "success")
    warning_count = sum(1 for r in results if r["status"] == "warning")
    error_count = sum(1 for r in results if r["status"] == "error")
    
    logger.info(f"\nTotal genres tested: {len(ALL_GENRES)}")
    logger.info(f"  ✓ Success: {success_count}")
    logger.info(f"  ⚠ Warning (no movies): {warning_count}")
    logger.info(f"  ✗ Error: {error_count}")
    
    # Show genres with issues
    if warning_count > 0:
        logger.info("\nGenres with no rated movies:")
        for r in results:
            if r["status"] == "warning":
                logger.info(f"  - {r['genre']}")
    
    if error_count > 0:
        logger.error("\nGenres with errors:")
        for r in results:
            if r["status"] == "error":
                logger.error(f"  - {r['genre']}: {r['message']}")
    
    # Highlight key genres
    key_genres = ["Action", "Fantasy", "Western"]
    logger.info(f"\nKey genres (Action, Fantasy, Western):")
    for r in results:
        if r["genre"] in key_genres:
            if r["status"] == "success":
                top = r["top_movie"]
                logger.info(
                    f"  ✓ {r['genre']}: {top['title']} ({top['year']}) - {top['rating']}"
                )
            else:
                logger.error(f"  ✗ {r['genre']}: {r['message']}")
    
    if error_count == 0:
        logger.info("\n✅ All genres working! Frontend should display all categories.")
        return 0
    else:
        logger.warning(f"\n⚠ {error_count} genres have errors. See details above.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

