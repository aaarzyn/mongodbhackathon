"""Service layer for Mflix dataset operations."""

import logging
from typing import Optional, Dict, Any

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from backend.db.mongo_client import MongoDBClient
from backend.models.movie import Movie, MovieComment
from backend.models.user import User
from backend.utils.mongo_helpers import convert_objectid_to_str

logger = logging.getLogger(__name__)


class MflixServiceError(Exception):
    """Raised when Mflix service operations fail."""

    pass


class MflixService:
    """Service for accessing Mflix dataset collections.
    
    This service provides high-level operations for working with
    users, movies, and comments from the MongoDB Mflix sample dataset.
    
    Example:
        >>> from backend.db import get_mongo_client
        >>> client = get_mongo_client()
        >>> service = MflixService(client)
        >>> user = service.get_user_by_email("sean_bean@gameofthron.es")
        >>> movies = service.get_movies_by_genre("Sci-Fi", limit=10)
    
    Vector Search:
        If your cluster has a Vector Search index on the `plot_embedding` field
        (e.g., index name `plot_embedding_index`), you can use
        `search_similar_movies_by_embedding` to find semantically similar movies.
    """

    def __init__(self, mongo_client: MongoDBClient) -> None:
        """Initialize Mflix service.
        
        Args:
            mongo_client: MongoDB client instance.
        """
        self.mongo_client = mongo_client
        self.db = mongo_client.database

    @property
    def users_collection(self) -> Collection:
        """Get the users collection."""
        return self.db["users"]

    @property
    def movies_collection(self) -> Collection:
        """Get the movies collection."""
        return self.db["movies"]

    @property
    def comments_collection(self) -> Collection:
        """Get the comments collection."""
        return self.db["comments"]
    
    @property
    def embedded_movies_collection(self) -> Collection:
        """Get the embedded_movies collection with plot embeddings."""
        return self.db["embedded_movies"]
    
    @property
    def recommendations_collection(self) -> Collection:
        """Get the recommendations collection for storing generated recommendations."""
        return self.db["recommendations"]

    def _clean_movie_data(self, movie_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Clean movie document data before validation.
        
        Ensures all fields have the correct types and handles None/missing values.
        
        Args:
            movie_doc: Raw movie document from MongoDB
            
        Returns:
            Cleaned movie data dictionary
        """
        # Ensure title is a string
        if 'title' in movie_doc:
            if movie_doc['title'] is None:
                movie_doc['title'] = "Unknown"
            else:
                movie_doc['title'] = str(movie_doc['title'])
        else:
            movie_doc['title'] = "Unknown"
        
        # Ensure year is int or None
        if 'year' in movie_doc and movie_doc['year'] is not None:
            try:
                movie_doc['year'] = int(movie_doc['year'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid year value for movie {movie_doc.get('_id')}: {movie_doc['year']}")
                movie_doc['year'] = None
        
        # Ensure runtime is int or None
        if 'runtime' in movie_doc and movie_doc['runtime'] is not None:
            try:
                movie_doc['runtime'] = int(movie_doc['runtime'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid runtime value for movie {movie_doc.get('_id')}: {movie_doc['runtime']}")
                movie_doc['runtime'] = None
        
        # Ensure list fields are lists of strings
        for field in ['genres', 'cast', 'directors']:
            if field in movie_doc:
                if movie_doc[field] is None:
                    movie_doc[field] = []
                elif not isinstance(movie_doc[field], list):
                    movie_doc[field] = [str(movie_doc[field])]
                else:
                    movie_doc[field] = [str(item) for item in movie_doc[field] if item is not None]
            else:
                movie_doc[field] = []
        
        # Ensure plot is a string or None
        if 'plot' in movie_doc and movie_doc['plot'] is not None:
            movie_doc['plot'] = str(movie_doc['plot'])
        
        # Ensure rated is a string or None
        if 'rated' in movie_doc and movie_doc['rated'] is not None:
            movie_doc['rated'] = str(movie_doc['rated'])
        
        # Handle nested imdb fields
        if 'imdb' in movie_doc and isinstance(movie_doc['imdb'], dict):
            imdb = movie_doc['imdb']
            
            # Clean rating
            if 'rating' in imdb and imdb['rating'] is not None:
                try:
                    imdb['rating'] = float(imdb['rating'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid IMDB rating for movie {movie_doc.get('_id')}: {imdb['rating']}")
                    imdb['rating'] = None
            
            # Clean votes
            if 'votes' in imdb and imdb['votes'] is not None:
                try:
                    imdb['votes'] = int(imdb['votes'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid IMDB votes for movie {movie_doc.get('_id')}: {imdb['votes']}")
                    imdb['votes'] = None
        
        return movie_doc

    def _create_movie_from_doc(self, movie_doc: Dict[str, Any]) -> Optional[Movie]:
        """Create a Movie object from a MongoDB document.
        
        Args:
            movie_doc: Raw movie document from MongoDB
            
        Returns:
            Movie object or None if creation fails
        """
        try:
            # Convert ObjectId to string
            movie_doc = convert_objectid_to_str(movie_doc)
            # Clean the data
            movie_doc = self._clean_movie_data(movie_doc)
            return Movie(**movie_doc)
        except Exception as e:
            logger.error(f"Failed to create Movie from document {movie_doc.get('_id')}: {e}")
            logger.debug(f"Problematic document: {movie_doc}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by their ID.
        
        Args:
            user_id: User ID (MongoDB ObjectId as string).
            
        Returns:
            User object if found, None otherwise.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            user_doc = self.users_collection.find_one({"_id": user_id})
            if user_doc:
                user_doc = convert_objectid_to_str(user_doc)
                return User(**user_doc)
            return None
        except PyMongoError as e:
            raise MflixServiceError(f"Failed to get user by ID: {str(e)}") from e

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by their email address.
        
        Args:
            email: User's email address.
            
        Returns:
            User object if found, None otherwise.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            user_doc = self.users_collection.find_one({"email": email})
            if user_doc:
                user_doc = convert_objectid_to_str(user_doc)
                return User(**user_doc)
            return None
        except PyMongoError as e:
            raise MflixServiceError(f"Failed to get user by email: {str(e)}") from e

    def list_users(self, limit: int = 10, skip: int = 0) -> list[User]:
        """List users with pagination.
        
        Args:
            limit: Maximum number of users to return.
            skip: Number of users to skip.
            
        Returns:
            List of User objects.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = self.users_collection.find().skip(skip).limit(limit)
            return [User(**convert_objectid_to_str(doc)) for doc in cursor]
        except PyMongoError as e:
            raise MflixServiceError(f"Failed to list users: {str(e)}") from e

    def get_movie_by_id(self, movie_id) -> Optional[Movie]:
        """Get a movie by its ID.
        
        Args:
            movie_id: Movie ID (MongoDB ObjectId or string).
            
        Returns:
            Movie object if found, None otherwise.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            from bson import ObjectId
            
            # Handle both ObjectId and string
            if isinstance(movie_id, str):
                try:
                    search_id = ObjectId(movie_id)
                except:
                    search_id = movie_id
            else:
                search_id = movie_id
            
            movie_doc = self.movies_collection.find_one({"_id": search_id})
            if movie_doc:
                return self._create_movie_from_doc(movie_doc)
            return None
        except PyMongoError as e:
            raise MflixServiceError(f"Failed to get movie by ID: {str(e)}") from e

    def get_movie_by_title(self, title: str) -> Optional[Movie]:
        """Get a movie by its exact title.
        
        Args:
            title: Movie title (case-sensitive).
            
        Returns:
            Movie object if found, None otherwise.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            movie_doc = self.movies_collection.find_one({"title": title})
            if movie_doc:
                return self._create_movie_from_doc(movie_doc)
            return None
        except PyMongoError as e:
            raise MflixServiceError(f"Failed to get movie by title: {str(e)}") from e

    def search_movies_by_title(
        self, title_query: str, limit: int = 10
    ) -> list[Movie]:
        """Search movies by title (case-insensitive partial match).
        
        Args:
            title_query: Title search query.
            limit: Maximum number of results.
            
        Returns:
            List of Movie objects matching the query.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = self.movies_collection.find(
                {"title": {"$regex": title_query, "$options": "i"}}
            ).limit(limit)
            
            movies = []
            for doc in cursor:
                movie = self._create_movie_from_doc(doc)
                if movie:
                    movies.append(movie)
            return movies
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to search movies by title: {str(e)}"
            ) from e

    def get_movies_by_genre(
        self, genre: str, limit: int = 20, skip: int = 0
    ) -> list[Movie]:
        """Get movies by genre, prioritizing movies with embeddings.
        
        Args:
            genre: Genre name (e.g., "Sci-Fi", "Drama").
            limit: Maximum number of movies to return.
            skip: Number of movies to skip.
            
        Returns:
            List of Movie objects sorted by embedding availability, then rating.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            # First get embedded movies (they have embeddings)
            embedded_movies = self.get_embedded_movies_by_genre(genre, limit=limit, skip=skip)
            
            # If we got enough movies, return them
            if len(embedded_movies) >= limit:
                return embedded_movies
            
            # Otherwise, supplement with movies from main collection
            remaining = limit - len(embedded_movies)
            embedded_ids = {m.id for m in embedded_movies if m.id}
            
            cursor = (
                self.movies_collection.find({
                    "genres": genre,
                    "imdb.rating": {"$ne": None, "$exists": True},
                    "imdb.votes": {"$gt": 100},
                    "_id": {"$nin": list(embedded_ids)} if embedded_ids else {},
                })
                .sort("imdb.rating", -1)
                .skip(0)
                .limit(remaining)
            )
            
            for doc in cursor:
                movie = self._create_movie_from_doc(doc)
                if movie:
                    embedded_movies.append(movie)
            
            return embedded_movies
            
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get movies by genre: {str(e)}"
            ) from e

    def get_movies_by_director(
        self, director: str, limit: int = 20
    ) -> list[Movie]:
        """Get movies by director.
        
        Args:
            director: Director name.
            limit: Maximum number of movies to return.
            
        Returns:
            List of Movie objects sorted by rating.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = (
                self.movies_collection.find({"directors": director})
                .sort("imdb.rating", -1)
                .limit(limit)
            )
            
            movies = []
            for doc in cursor:
                movie = self._create_movie_from_doc(doc)
                if movie:
                    movies.append(movie)
            return movies
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get movies by director: {str(e)}"
            ) from e

    def get_top_rated_movies(
        self,
        limit: int = 20,
        min_rating: float = 7.0,
        min_votes: int = 1000,
    ) -> list[Movie]:
        """Get top-rated movies.
        
        Args:
            limit: Maximum number of movies to return.
            min_rating: Minimum IMDb rating.
            min_votes: Minimum number of votes.
            
        Returns:
            List of top-rated Movie objects.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = (
                self.movies_collection.find(
                    {
                        "imdb.rating": {"$gte": min_rating},
                        "imdb.votes": {"$gte": min_votes},
                    }
                )
                .sort("imdb.rating", -1)
                .limit(limit)
            )
            
            movies = []
            for doc in cursor:
                movie = self._create_movie_from_doc(doc)
                if movie:
                    movies.append(movie)
            return movies
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get top rated movies: {str(e)}"
            ) from e

    def get_movies_by_year_range(
        self, start_year: int, end_year: int, limit: int = 20
    ) -> list[Movie]:
        """Get movies released within a year range.
        
        Args:
            start_year: Start year (inclusive).
            end_year: End year (inclusive).
            limit: Maximum number of movies to return.
            
        Returns:
            List of Movie objects.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = (
                self.movies_collection.find(
                    {"year": {"$gte": start_year, "$lte": end_year}}
                )
                .sort([("imdb.rating", -1), ("year", -1)])
                .limit(limit)
            )
            
            movies = []
            for doc in cursor:
                movie = self._create_movie_from_doc(doc)
                if movie:
                    movies.append(movie)
            return movies
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get movies by year range: {str(e)}"
            ) from e

    def get_comments_for_movie(
        self, movie_id: str, limit: int = 50
    ) -> list[MovieComment]:
        """Get comments for a specific movie.
        
        Args:
            movie_id: Movie ID.
            limit: Maximum number of comments to return.
            
        Returns:
            List of MovieComment objects.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = (
                self.comments_collection.find({"movie_id": movie_id})
                .sort("date", -1)
                .limit(limit)
            )
            return [MovieComment(**convert_objectid_to_str(doc)) for doc in cursor]
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get comments for movie: {str(e)}"
            ) from e

    def get_comments_by_user(
        self, email: str, limit: int = 50
    ) -> list[MovieComment]:
        """Get comments by a specific user.
        
        Args:
            email: User's email address.
            limit: Maximum number of comments to return.
            
        Returns:
            List of MovieComment objects.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = (
                self.comments_collection.find({"email": email})
                .sort("date", -1)
                .limit(limit)
            )
            return [MovieComment(**convert_objectid_to_str(doc)) for doc in cursor]
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get comments by user: {str(e)}"
            ) from e

    def search_similar_movies_by_embedding(
        self,
        embedding: list[float],
        *,
        k: int = 20,
        index_name: str = "plot_embedding_index",
        include_self: bool = False,
    ) -> list[Movie]:
        """Find movies similar to a query embedding using Atlas Vector Search.
        
        Args:
            embedding: Query embedding vector (same dimension as plot_embedding).
            k: Number of nearest neighbors to return.
            index_name: Atlas Search index name configured for vector search.
            include_self: Whether to include the seed movie itself in results.
        
        Returns:
            List of Movie objects ordered by similarity.
        
        Notes:
            - Requires an Atlas Search index on `plot_embedding`.
            - Silently returns an empty list if the operation fails.
        """
        try:
            pipeline = [
                {
                    "$search": {
                        "index": index_name,
                        "knnBeta": {
                            "vector": embedding,
                            "path": "plot_embedding",
                            "k": max(int(k), 1),
                        },
                    }
                },
                {"$limit": max(int(k), 1)},
            ]
            cursor = self.movies_collection.aggregate(pipeline)
            
            movies = []
            for doc in cursor:
                movie = self._create_movie_from_doc(doc)
                if movie:
                    movies.append(movie)
            
            if not include_self and movies and len(embedding) > 0:
                movies = movies
            return movies
        except PyMongoError as e:
            logger.warning(f"Vector search failed or unavailable: {e}")
            return []

    def get_embedded_movies_by_genre(
        self, genre: str, limit: int = 20, skip: int = 0
    ) -> list[Movie]:
        """Get movies with embeddings by genre.
        
        Args:
            genre: Genre name (e.g., "Sci-Fi", "Drama").
            limit: Maximum number of movies to return.
            skip: Number of movies to skip.
            
        Returns:
            List of Movie objects with embeddings sorted by rating.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = (
                self.embedded_movies_collection.find({
                    "genres": genre,
                    "imdb.rating": {"$ne": None, "$exists": True},
                    "imdb.votes": {"$gt": 100},
                })
                .sort("imdb.rating", -1)
                .skip(skip)
                .limit(limit)
            )
            
            movies = []
            for doc in cursor:
                movie = self._create_movie_from_doc(doc)
                if movie:
                    movies.append(movie)
            return movies
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get embedded movies by genre: {str(e)}"
            ) from e
    
    def get_embedding_stats(self) -> dict:
        """Get statistics about movies with embeddings.
        
        Returns:
            Dictionary with embedding statistics.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            total_movies = self.movies_collection.count_documents({})
            embedded_count = self.embedded_movies_collection.count_documents({})
            
            stats = {
                "total_movies": total_movies,
                "embedded_movies": embedded_count,
                "embedding_coverage": round(embedded_count / total_movies * 100, 1) if total_movies > 0 else 0,
                "genres": {},
            }
            
            # Get counts by genre
            for genre in ["Action", "Fantasy", "Western", "Sci-Fi", "Drama"]:
                genre_total = self.movies_collection.count_documents({"genres": genre})
                genre_embedded = self.embedded_movies_collection.count_documents({"genres": genre})
                stats["genres"][genre] = {
                    "total": genre_total,
                    "with_embeddings": genre_embedded,
                    "coverage": round(genre_embedded / genre_total * 100, 1) if genre_total > 0 else 0,
                }
            
            return stats
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get embedding stats: {str(e)}"
            ) from e

    def save_recommendation(self, recommendation_data: dict) -> str:
        """Save a recommendation to the database.
        
        Args:
            recommendation_data: Recommendation data dictionary.
            
        Returns:
            ID of the saved recommendation.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            result = self.recommendations_collection.insert_one(recommendation_data)
            logger.info(
                f"Saved recommendation for {recommendation_data.get('user_email')}: {result.inserted_id}"
            )
            return str(result.inserted_id)
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to save recommendation: {str(e)}"
            ) from e
    
    def get_user_recommendations(
        self, user_email: str, limit: int = 10
    ) -> list[dict]:
        """Get saved recommendations for a user.
        
        Args:
            user_email: User's email address.
            limit: Maximum number of recommendation sets to return.
            
        Returns:
            List of saved recommendation documents.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = (
                self.recommendations_collection.find({"user_email": user_email})
                .sort("created_at", -1)
                .limit(limit)
            )
            return [convert_objectid_to_str(doc) for doc in cursor]
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get user recommendations: {str(e)}"
            ) from e
    
    def get_all_recommendations(self, limit: int = 50) -> list[dict]:
        """Get all saved recommendations.
        
        Args:
            limit: Maximum number of recommendations to return.
            
        Returns:
            List of saved recommendation documents.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            cursor = (
                self.recommendations_collection.find()
                .sort("created_at", -1)
                .limit(limit)
            )
            return [convert_objectid_to_str(doc) for doc in cursor]
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get all recommendations: {str(e)}"
            ) from e

    def get_database_stats(self) -> dict:
        """Get statistics about the Mflix database.
        
        Returns:
            Dictionary with collection counts and basic stats.
            
        Raises:
            MflixServiceError: If database operation fails.
        """
        try:
            stats = {
                "database": self.db.name,
                "collections": {},
            }

            # Count documents in each collection
            stats["collections"]["users"] = self.users_collection.count_documents({})
            stats["collections"]["movies"] = self.movies_collection.count_documents({})
            stats["collections"]["comments"] = self.comments_collection.count_documents({})

            # Get sample movie stats
            pipeline = [
                {"$group": {"_id": None, "avg_rating": {"$avg": "$imdb.rating"}}}
            ]
            result = list(self.movies_collection.aggregate(pipeline))
            if result:
                stats["average_movie_rating"] = round(result[0]["avg_rating"], 2)

            return stats
        except PyMongoError as e:
            raise MflixServiceError(
                f"Failed to get database stats: {str(e)}"
            ) from e