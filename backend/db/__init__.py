"""Database layer for MongoDB Atlas integration."""

from backend.db.mongo_client import MongoDBClient, get_mongo_client

__all__ = ["MongoDBClient", "get_mongo_client"]

