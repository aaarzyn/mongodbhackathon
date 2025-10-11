"""Movie models for the Mflix dataset."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IMDbInfo(BaseModel):
    """IMDb rating information."""

    rating: Optional[float] = Field(default=None, description="IMDb rating (0-10)")
    votes: Optional[int] = Field(default=None, description="Number of votes")
    id: Optional[int] = Field(default=None, description="IMDb ID")


class TomatoesViewer(BaseModel):
    """Rotten Tomatoes viewer ratings."""

    rating: Optional[float] = Field(default=None, description="Viewer rating")
    numReviews: Optional[int] = Field(default=None, description="Number of reviews")
    meter: Optional[int] = Field(default=None, description="Viewer meter score")


class TomatoesCritic(BaseModel):
    """Rotten Tomatoes critic ratings."""

    rating: Optional[float] = Field(default=None, description="Critic rating")
    numReviews: Optional[int] = Field(default=None, description="Number of reviews")
    meter: Optional[int] = Field(default=None, description="Critic meter score")


class TomatoesInfo(BaseModel):
    """Rotten Tomatoes information."""

    viewer: Optional[TomatoesViewer] = Field(
        default=None, description="Viewer ratings"
    )
    critic: Optional[TomatoesCritic] = Field(default=None, description="Critic ratings")
    lastUpdated: Optional[datetime] = Field(
        default=None, description="Last update timestamp"
    )
    rotten: Optional[int] = Field(default=None, description="Rotten tomatoes count")
    fresh: Optional[int] = Field(default=None, description="Fresh tomatoes count")
    production: Optional[str] = Field(default=None, description="Production company")


class Movie(BaseModel):
    """Movie model representing a movie from the Mflix dataset.
    
    Example document from sample_mflix.movies:
    {
      "_id": ObjectId("573a1390f29313caabcd413b"),
      "title": "The Arrival of a Train",
      "year": 1896,
      "runtime": 1,
      "released": ISODate("1896-01-25T00:00:00Z"),
      "poster": "http://...",
      "plot": "A group of people...",
      "fullplot": "A group of people...",
      "directors": ["Auguste Lumière", "Louis Lumière"],
      "cast": ["Madeleine Koehler"],
      "countries": ["France"],
      "genres": ["Documentary", "Short"],
      "imdb": { "rating": 7.3, "votes": 5043, "id": 12 },
      "tomatoes": { ... }
    }
    """

    id: Optional[str] = Field(default=None, alias="_id", description="Movie ID")
    title: str = Field(..., description="Movie title")
    year: Optional[int] = Field(default=None, description="Release year")
    runtime: Optional[int] = Field(default=None, description="Runtime in minutes")
    released: Optional[datetime] = Field(default=None, description="Release date")
    poster: Optional[str] = Field(default=None, description="Poster URL")
    plot: Optional[str] = Field(default=None, description="Short plot summary")
    fullplot: Optional[str] = Field(default=None, description="Full plot description")
    directors: list[str] = Field(
        default_factory=list, description="List of directors"
    )
    cast: list[str] = Field(default_factory=list, description="List of cast members")
    writers: list[str] = Field(default_factory=list, description="List of writers")
    countries: list[str] = Field(default_factory=list, description="Countries of origin")
    genres: list[str] = Field(default_factory=list, description="Movie genres")
    languages: list[str] = Field(default_factory=list, description="Languages")
    rated: Optional[str] = Field(default=None, description="MPAA rating")
    imdb: Optional[IMDbInfo] = Field(default=None, description="IMDb information")
    tomatoes: Optional[TomatoesInfo] = Field(
        default=None, description="Rotten Tomatoes information"
    )
    type: Optional[str] = Field(default=None, description="Type (movie, series, etc)")
    num_mflix_comments: Optional[int] = Field(
        default=None, description="Number of comments"
    )
    plot_embedding: Optional[list[float]] = Field(
        default=None, description="Plot embedding vector for semantic search"
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": "573a1390f29313caabcd413b",
                "title": "Inception",
                "year": 2010,
                "runtime": 148,
                "genres": ["Action", "Adventure", "Sci-Fi"],
                "directors": ["Christopher Nolan"],
                "cast": ["Leonardo DiCaprio", "Joseph Gordon-Levitt"],
                "imdb": {"rating": 8.8, "votes": 2000000, "id": 1375666},
                "plot": "A thief who steals corporate secrets...",
            }
        }


class MovieComment(BaseModel):
    """Comment/review on a movie from the Mflix dataset.
    
    Example document from sample_mflix.comments:
    {
      "_id": ObjectId("5a9427648b0beebeb69579e7"),
      "name": "Andrea Le",
      "email": "andrea_le@fakegmail.com",
      "movie_id": ObjectId("573a1390f29313caabcd4323"),
      "text": "Rem officiis eaque repellendus...",
      "date": ISODate("2012-03-26T23:20:16Z")
    }
    """

    id: Optional[str] = Field(default=None, alias="_id", description="Comment ID")
    name: str = Field(..., description="Commenter name")
    email: str = Field(..., description="Commenter email")
    movie_id: str = Field(..., description="ID of the movie being commented on")
    text: str = Field(..., description="Comment text")
    date: datetime = Field(..., description="Comment timestamp")

    class Config:
        populate_by_name = True


class MovieRating(BaseModel):
    """User rating for a movie (derived from comments)."""

    user_id: str = Field(..., description="User ID")
    movie_id: str = Field(..., description="Movie ID")
    rating: float = Field(..., ge=0, le=5, description="Rating (0-5)")
    date: datetime = Field(..., description="Rating timestamp")
    comment: Optional[str] = Field(default=None, description="Optional comment text")

