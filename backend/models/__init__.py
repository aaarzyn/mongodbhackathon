"""Data models for MongoDB collections."""

from backend.models.movie import Movie, MovieComment, MovieRating
from backend.models.user import User, UserPreferences

__all__ = ["Movie", "MovieComment", "MovieRating", "User", "UserPreferences"]

