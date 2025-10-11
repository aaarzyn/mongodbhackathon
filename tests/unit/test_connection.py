"""Test script to verify MongoDB Atlas connection and query sample data.

This script tests the connection to MongoDB Atlas and performs basic
queries on the Mflix sample dataset.

Usage:
    python test_connection.py
"""

import logging
import sys
from typing import Optional

from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient, MongoDBConnectionError
from backend.services.mflix_service import MflixService, MflixServiceError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_connection() -> Optional[MongoDBClient]:
    """Test MongoDB Atlas connection.
    
    Returns:
        MongoDBClient instance if successful, None otherwise.
    """
    logger.info("Testing MongoDB Atlas connection...")
    try:
        settings = get_settings()
        logger.info(f"Connecting to database: {settings.mongo_database}")
        
        client = MongoDBClient(settings)
        
        if client.test_connection():
            logger.info("✓ Successfully connected to MongoDB Atlas!")
            return client
        else:
            logger.error("✗ Connection test failed")
            return None
            
    except MongoDBConnectionError as e:
        logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"✗ Unexpected error: {str(e)}")
        return None


def test_collections(client: MongoDBClient) -> bool:
    """Test listing collections in the database.
    
    Args:
        client: MongoDB client instance.
        
    Returns:
        True if successful, False otherwise.
    """
    logger.info("\nListing collections in the database...")
    try:
        collections = client.list_collections()
        logger.info(f"✓ Found {len(collections)} collections:")
        for collection in collections:
            logger.info(f"  - {collection}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to list collections: {str(e)}")
        return False


def test_database_stats(service: MflixService) -> bool:
    """Test getting database statistics.
    
    Args:
        service: Mflix service instance.
        
    Returns:
        True if successful, False otherwise.
    """
    logger.info("\nGetting database statistics...")
    try:
        stats = service.get_database_stats()
        logger.info(f"✓ Database: {stats['database']}")
        logger.info(f"  Collections:")
        for coll, count in stats["collections"].items():
            logger.info(f"    - {coll}: {count:,} documents")
        if "average_movie_rating" in stats:
            logger.info(f"  Average movie rating: {stats['average_movie_rating']}")
        return True
    except MflixServiceError as e:
        logger.error(f"✗ Failed to get database stats: {str(e)}")
        return False


def test_query_users(service: MflixService) -> bool:
    """Test querying users.
    
    Args:
        service: Mflix service instance.
        
    Returns:
        True if successful, False otherwise.
    """
    logger.info("\nQuerying sample users...")
    try:
        users = service.list_users(limit=3)
        logger.info(f"✓ Retrieved {len(users)} users:")
        for user in users:
            logger.info(f"  - {user.name} ({user.email})")
        return True
    except MflixServiceError as e:
        logger.error(f"✗ Failed to query users: {str(e)}")
        return False


def test_query_movies(service: MflixService) -> bool:
    """Test querying movies.
    
    Args:
        service: Mflix service instance.
        
    Returns:
        True if successful, False otherwise.
    """
    logger.info("\nQuerying top-rated movies...")
    try:
        movies = service.get_top_rated_movies(limit=5, min_rating=8.0, min_votes=100000)
        logger.info(f"✓ Retrieved {len(movies)} top-rated movies:")
        for movie in movies:
            rating = movie.imdb.rating if movie.imdb else "N/A"
            logger.info(
                f"  - {movie.title} ({movie.year}) - Rating: {rating}"
            )
        return True
    except MflixServiceError as e:
        logger.error(f"✗ Failed to query movies: {str(e)}")
        return False


def test_query_by_genre(service: MflixService) -> bool:
    """Test querying movies by genre.
    
    Args:
        service: Mflix service instance.
        
    Returns:
        True if successful, False otherwise.
    """
    logger.info("\nQuerying Sci-Fi movies...")
    try:
        movies = service.get_movies_by_genre("Sci-Fi", limit=5)
        logger.info(f"✓ Retrieved {len(movies)} Sci-Fi movies:")
        for movie in movies:
            rating = movie.imdb.rating if movie.imdb else "N/A"
            directors = ", ".join(movie.directors[:2]) if movie.directors else "Unknown"
            logger.info(
                f"  - {movie.title} ({movie.year}) by {directors} - Rating: {rating}"
            )
        return True
    except MflixServiceError as e:
        logger.error(f"✗ Failed to query movies by genre: {str(e)}")
        return False


def test_query_by_director(service: MflixService) -> bool:
    """Test querying movies by director.
    
    Args:
        service: Mflix service instance.
        
    Returns:
        True if successful, False otherwise.
    """
    logger.info("\nQuerying Christopher Nolan movies...")
    try:
        movies = service.get_movies_by_director("Christopher Nolan", limit=5)
        logger.info(f"✓ Retrieved {len(movies)} Christopher Nolan movies:")
        for movie in movies:
            rating = movie.imdb.rating if movie.imdb else "N/A"
            logger.info(f"  - {movie.title} ({movie.year}) - Rating: {rating}")
        return True
    except MflixServiceError as e:
        logger.error(f"✗ Failed to query movies by director: {str(e)}")
        return False


def main() -> int:
    """Main test function.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    logger.info("=" * 60)
    logger.info("MongoDB Atlas Connection Test")
    logger.info("=" * 60)

    # Test connection
    client = test_connection()
    if not client:
        logger.error("\nConnection test failed. Please check your configuration.")
        logger.error("Make sure you have a .env file with MONGO_URI set.")
        return 1

    # Create service
    service = MflixService(client)

    # Run tests
    tests = [
        ("Collections", lambda: test_collections(client)),
        ("Database Stats", lambda: test_database_stats(service)),
        ("Query Users", lambda: test_query_users(service)),
        ("Query Movies", lambda: test_query_movies(service)),
        ("Query by Genre", lambda: test_query_by_genre(service)),
        ("Query by Director", lambda: test_query_by_director(service)),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        if test_func():
            passed += 1
        else:
            failed += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"Passed: {passed}/{len(tests)}")
    logger.info(f"Failed: {failed}/{len(tests)}")

    if failed == 0:
        logger.info("\n✓ All tests passed! Your MongoDB Atlas connection is working.")
        return 0
    else:
        logger.warning(f"\n✗ {failed} test(s) failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

