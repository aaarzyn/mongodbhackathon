"""Dependency injection for FastAPI routes."""

from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient
from backend.services.mflix_service import MflixService

# Global client instance
_mongo_client = None


def get_mongo_client() -> MongoDBClient:
    """Get or create MongoDB client instance."""
    global _mongo_client
    if _mongo_client is None:
        settings = get_settings()
        _mongo_client = MongoDBClient(settings)
    return _mongo_client


def get_mflix_service() -> MflixService:
    """Get MflixService instance."""
    client = get_mongo_client()
    return MflixService(client)


def close_mongo_client() -> None:
    """Close the MongoDB client instance."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None

