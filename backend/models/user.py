"""User model for the Mflix dataset."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserPreferences(BaseModel):
    """User preferences for movie recommendations."""

    favorite_genres: list[str] = Field(
        default_factory=list, description="User's favorite movie genres"
    )
    disliked_genres: list[str] = Field(
        default_factory=list, description="Genres the user dislikes"
    )
    preferred_decades: list[str] = Field(
        default_factory=list, description="Preferred movie decades (e.g., '2000s')"
    )
    favorite_directors: list[str] = Field(
        default_factory=list, description="Favorite directors"
    )
    favorite_actors: list[str] = Field(
        default_factory=list, description="Favorite actors"
    )
    min_rating: Optional[float] = Field(
        default=None, description="Minimum IMDb rating preference"
    )
    max_runtime: Optional[int] = Field(
        default=None, description="Maximum movie runtime in minutes"
    )


class User(BaseModel):
    """User model representing a user from the Mflix dataset.
    
    Example document from sample_mflix.users:
    {
      "_id": ObjectId("59b99db4cfa9a34dcd7885b6"),
      "name": "Ned Stark",
      "email": "sean_bean@gameofthron.es",
      "password": "$2b$12$UREFwsRUoyF0CRqGNK0LzO0HM/jLhgUCNNIJ9RJAqMUQ74crlJ1Vu"
    }
    """

    id: Optional[str] = Field(default=None, alias="_id", description="User ID")
    name: str = Field(..., description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: Optional[str] = Field(
        default=None, description="Hashed password (not used for recommendations)"
    )
    preferences: UserPreferences = Field(
        default_factory=UserPreferences,
        description="User's movie preferences",
    )
    created_at: Optional[datetime] = Field(
        default=None, description="Account creation date"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "59b99db4cfa9a34dcd7885b6",
                "name": "Sarah Chen",
                "email": "sarah.chen@example.com",
                "preferences": {
                    "favorite_genres": ["Sci-Fi", "Thriller", "Drama"],
                    "disliked_genres": ["Horror"],
                    "preferred_decades": ["2000s", "2010s"],
                    "favorite_directors": ["Christopher Nolan", "Denis Villeneuve"],
                },
            }
        }

