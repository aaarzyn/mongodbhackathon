"""FastAPI application for movie recommendation system."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import movies, recommendations, users
from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient, close_mongo_client

logger = logging.getLogger(__name__)

# Global client instance
_mongo_client = None


def get_mongo_client_instance() -> MongoDBClient:
    """Get or create MongoDB client instance."""
    global _mongo_client
    if _mongo_client is None:
        settings = get_settings()
        _mongo_client = MongoDBClient(settings)
    return _mongo_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI."""
    # Startup
    logger.info("Starting up application...")
    try:
        client = get_mongo_client_instance()
        logger.info("MongoDB connection established")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    close_mongo_client()
    logger.info("MongoDB connection closed")


# Create FastAPI app
app = FastAPI(
    title="ContextScope Movie Recommendations",
    description="Multi-agent movie recommendation system with context evaluation",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(movies.router, prefix="/api/movies", tags=["movies"])
app.include_router(recommendations.router, prefix="/api/recommendations", tags=["recommendations"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ContextScope Movie Recommendations API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        client = get_mongo_client_instance()
        is_healthy = client.test_connection()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "database": "connected" if is_healthy else "disconnected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }

