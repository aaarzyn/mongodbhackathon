"""MongoDB Atlas client with connection pooling and error handling."""

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import (
    ConnectionFailure,
    ConfigurationError,
    OperationFailure,
    ServerSelectionTimeoutError,
)

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)


class MongoDBConnectionError(Exception):
    """Raised when MongoDB connection fails."""

    pass


class MongoDBClient:
    """MongoDB Atlas client with connection pooling and proper resource management.
    
    This client provides a context manager interface for database operations
    and handles connection errors gracefully.
    
    Example:
        >>> settings = get_settings()
        >>> client = MongoDBClient(settings)
        >>> with client.get_database() as db:
        ...     movies = db.movies.find_one({"title": "Inception"})
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize MongoDB client.
        
        Args:
            settings: Application settings containing MongoDB configuration.
            
        Raises:
            MongoDBConnectionError: If connection to MongoDB fails.
        """
        self.settings = settings
        self._client: Optional[MongoClient] = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to MongoDB Atlas.
        
        Raises:
            MongoDBConnectionError: If connection fails.
        """
        try:
            self._client = MongoClient(
                self.settings.mongo_uri,
                serverSelectionTimeoutMS=self.settings.mongo_timeout_ms,
                maxPoolSize=50,
                minPoolSize=10,
            )
            # Test connection
            self._client.admin.command("ping")
            logger.info(
                f"Successfully connected to MongoDB Atlas: {self.settings.mongo_database}"
            )
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            raise MongoDBConnectionError(
                f"Failed to connect to MongoDB: {str(e)}"
            ) from e
        except ConfigurationError as e:
            raise MongoDBConnectionError(
                f"MongoDB configuration error: {str(e)}"
            ) from e

    @property
    def client(self) -> MongoClient:
        """Get the underlying MongoDB client.
        
        Returns:
            MongoDB client instance.
            
        Raises:
            MongoDBConnectionError: If client is not initialized.
        """
        if self._client is None:
            raise MongoDBConnectionError("MongoDB client not initialized")
        return self._client

    @property
    def database(self) -> Database:
        """Get the configured database.
        
        Returns:
            MongoDB database instance.
        """
        return self.client[self.settings.mongo_database]

    def get_collection(self, collection_name: str) -> Collection:
        """Get a collection from the database.
        
        Args:
            collection_name: Name of the collection.
            
        Returns:
            MongoDB collection instance.
            
        Example:
            >>> client = MongoDBClient(settings)
            >>> movies = client.get_collection("movies")
            >>> movie = movies.find_one({"title": "Inception"})
        """
        return self.database[collection_name]
    
    @property
    def movies(self) -> Collection:
        """Get the movies collection (read-only sample data).
        
        Returns:
            Movies collection from sample_mflix.
            
        Example:
            >>> client = get_mongo_client()
            >>> inception = client.movies.find_one({"title": "Inception"})
        """
        return self.get_collection("movies")
    
    @property
    def handoffs(self) -> Collection:
        """Get the handoffs collection.
        
        Returns:
            Collection for storing HandoffEvaluation documents.
            
        Example:
            >>> client = get_mongo_client()
            >>> client.handoffs.insert_one(handoff_doc)
        """
        return self.get_collection("handoffs")
    
    @property
    def pipeline_results(self) -> Collection:
        """Get the pipeline_results collection.
        
        Returns:
            Collection for storing PipelineEvaluation documents.
            
        Example:
            >>> client = get_mongo_client()
            >>> client.pipeline_results.insert_one(pipeline_doc)
        """
        return self.get_collection("pipeline_results")
    
    def ensure_indexes(self) -> None:
        """Create indexes for ContextScope collections if they don't exist.
        
        This method is idempotent and safe to call multiple times.
        Should be called during application startup.
        """
        logger.info("Ensuring indexes for ContextScope collections...")
        
        # Handoffs collection indexes
        self.handoffs.create_index("handoff_id", unique=True)
        self.handoffs.create_index("pipeline_id")
        self.handoffs.create_index("task_id")
        self.handoffs.create_index("timestamp")
        self.handoffs.create_index([("agent_from", 1), ("agent_to", 1)])
        
        # Pipeline results collection indexes
        self.pipeline_results.create_index("pipeline_id", unique=True)
        self.pipeline_results.create_index("task_id")
        
        logger.info("Indexes created successfully")

    @contextmanager
    def get_database(self) -> Iterator[Database]:
        """Context manager for database operations.
        
        Yields:
            MongoDB database instance.
            
        Example:
            >>> with client.get_database() as db:
            ...     result = db.movies.find_one({"title": "Inception"})
        """
        try:
            yield self.database
        except OperationFailure as e:
            logger.error(f"MongoDB operation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during database operation: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """Test if MongoDB connection is working.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    def list_collections(self) -> list[str]:
        """List all collections in the database.
        
        Returns:
            List of collection names.
        """
        return self.database.list_collection_names()

    def close(self) -> None:
        """Close MongoDB connection and release resources."""
        if self._client is not None:
            self._client.close()
            logger.info("MongoDB connection closed")
            self._client = None


# Global client instance
_mongo_client: Optional[MongoDBClient] = None


def get_mongo_client() -> MongoDBClient:
    """Get or create the global MongoDB client instance.
    
    Returns:
        Singleton MongoDBClient instance.
        
    Example:
        >>> client = get_mongo_client()
        >>> movies = client.get_collection("movies")
    """
    global _mongo_client
    if _mongo_client is None:
        settings = get_settings()
        _mongo_client = MongoDBClient(settings)
    return _mongo_client


def close_mongo_client() -> None:
    """Close the global MongoDB client instance."""
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None