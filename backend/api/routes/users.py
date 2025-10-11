"""User-related API endpoints."""

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from backend.api.app import get_mongo_client_instance
from backend.models.user import User
from backend.services.mflix_service import MflixService, MflixServiceError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[User])
async def list_users(skip: int = 0, limit: int = 10):
    """List users with pagination.
    
    Args:
        skip: Number of users to skip.
        limit: Maximum number of users to return.
        
    Returns:
        List of users.
    """
    try:
        client = get_mongo_client_instance()
        service = MflixService(client)
        users = service.list_users(limit=limit, skip=skip)
        return users
    except MflixServiceError as e:
        logger.error(f"Failed to list users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{email}", response_model=User)
async def get_user(email: str):
    """Get user by email.
    
    Args:
        email: User's email address.
        
    Returns:
        User object.
    """
    try:
        client = get_mongo_client_instance()
        service = MflixService(client)
        user = service.get_user_by_email(email)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    except MflixServiceError as e:
        logger.error(f"Failed to get user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

