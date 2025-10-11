"""User Profiler Agent - Analyzes user behavior and extracts preferences."""

import json
import logging
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple

from backend.agents.base import Agent, AgentContext, AgentOutput, ContextFormat
from backend.models.movie import MovieComment
from backend.models.user import User
from backend.services.mflix_service import MflixService

logger = logging.getLogger(__name__)


class UserProfilerAgent(Agent):
    """Agent that profiles users based on their viewing history and preferences.
    
    This agent:
    1. Retrieves user information from the database
    2. Analyzes user comments to infer preferences
    3. Extracts genre affinities, favorite directors/actors
    4. Builds a comprehensive user profile for downstream agents
    
    Example:
        >>> service = MflixService(mongo_client)
        >>> profiler = UserProfilerAgent(service, context_format=ContextFormat.JSON)
        >>> output = profiler.process_user("user@example.com")
    """

    def __init__(
        self,
        mflix_service: MflixService,
        context_format: ContextFormat = ContextFormat.JSON,
    ):
        """Initialize User Profiler Agent.
        
        Args:
            mflix_service: Service for accessing Mflix data.
            context_format: Format for context output (JSON or Markdown).
        """
        super().__init__("UserProfilerAgent", context_format)
        self.service = mflix_service

    def process(self, input_context: Optional[AgentContext] = None) -> AgentOutput:
        """Process user profiling request.
        
        Args:
            input_context: Context with user_id or email to profile.
            
        Returns:
            AgentOutput with user profile context.
        """
        start_time = time.time()

        try:
            if input_context is None:
                raise ValueError("UserProfilerAgent requires input context with user identifier")

            user_id = input_context.data.get("user_id")
            email = input_context.data.get("email")

            if not user_id and not email:
                raise ValueError("Input context must contain 'user_id' or 'email'")

            # Get user and build profile
            if email:
                profile_data = self._build_profile_by_email(email)
            else:
                profile_data = self._build_profile_by_id(user_id)

            # Create context based on format
            if self.context_format == ContextFormat.JSON:
                context_text = json.dumps(profile_data, indent=2)
            else:
                context_text = self._format_as_markdown(profile_data)

            tokens = self._estimate_tokens(context_text)
            context = self._create_context(
                data=profile_data,
                tokens=tokens,
                raw_text=context_text,
            )

            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                context=context,
                execution_time_ms=execution_time,
                success=True,
            )

        except Exception as e:
            logger.error(f"UserProfilerAgent failed: {str(e)}")
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                context=self._create_context(data={}),
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )

    def process_user(self, email: str) -> AgentOutput:
        """Convenience method to process a user by email.
        
        Args:
            email: User's email address.
            
        Returns:
            AgentOutput with user profile.
        """
        input_context = AgentContext(
            agent_name="System",
            format=ContextFormat.JSON,
            data={"email": email},
        )
        return self.process(input_context)

    def _build_profile_by_email(self, email: str) -> Dict:
        """Build user profile from email.
        
        Args:
            email: User's email address.
            
        Returns:
            User profile dictionary.
        """
        user = self.service.get_user_by_email(email)
        if not user:
            raise ValueError(f"User not found: {email}")

        return self._build_user_profile(user, email)

    def _build_profile_by_id(self, user_id: str) -> Dict:
        """Build user profile from user ID.
        
        Args:
            user_id: User ID.
            
        Returns:
            User profile dictionary.
        """
        user = self.service.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        # Get email from user object for fetching comments
        email = user.email if hasattr(user, 'email') else None
        return self._build_user_profile(user, email)

    def _build_user_profile(self, user: User, email: Optional[str]) -> Dict:
        """Build comprehensive user profile.
        
        Args:
            user: User object.
            email: User's email for fetching comments.
            
        Returns:
            Complete user profile dictionary.
        """
        profile = {
            "user_id": user.id or "unknown",
            "name": user.name,
            "email": user.email,
        }

        # Get user's comments and analyze viewing history
        if email:
            comments = self.service.get_comments_by_user(email, limit=100)
            
            # Get movies the user has commented on
            movie_ids = [comment.movie_id for comment in comments]
            movies = []
            for movie_id in movie_ids:
                movie = self.service.get_movie_by_id(movie_id)
                if movie:
                    movies.append(movie)

            # Analyze preferences
            profile["watch_history"] = self._analyze_watch_history(comments, movies)
            profile["genre_affinities"] = self._compute_genre_affinities(movies)
            profile["director_preferences"] = self._extract_director_preferences(movies)
            profile["actor_preferences"] = self._extract_actor_preferences(movies)
            profile["viewing_patterns"] = self._analyze_viewing_patterns(comments, movies)
        else:
            # No comments available, use basic preferences if available
            profile["watch_history"] = []
            profile["genre_affinities"] = []
            profile["director_preferences"] = []
            profile["actor_preferences"] = []
            profile["viewing_patterns"] = {}

        # Include user preferences if available
        if user.preferences:
            profile["stated_preferences"] = {
                "favorite_genres": user.preferences.favorite_genres,
                "disliked_genres": user.preferences.disliked_genres,
                "preferred_decades": user.preferences.preferred_decades,
                "favorite_directors": user.preferences.favorite_directors,
                "favorite_actors": user.preferences.favorite_actors,
            }

        return profile

    def _analyze_watch_history(
        self, comments: List[MovieComment], movies: List
    ) -> List[Dict]:
        """Analyze user's watch history from comments.
        
        Args:
            comments: User's comments.
            movies: Movies the user has commented on.
            
        Returns:
            List of watched movies with metadata.
        """
        history = []
        movie_map = {movie.id: movie for movie in movies}

        for comment in comments[:20]:  # Limit to most recent 20
            movie = movie_map.get(comment.movie_id)
            if movie:
                history.append({
                    "movie_id": movie.id,
                    "title": movie.title,
                    "year": movie.year,
                    "genres": movie.genres,
                    "directors": movie.directors[:2] if movie.directors else [],
                    "comment_date": comment.date.isoformat() if comment.date else None,
                    "comment_preview": comment.text[:100] if comment.text else "",
                })

        return history

    def _compute_genre_affinities(self, movies: List) -> List[Dict]:
        """Compute user's genre affinities based on viewed movies.
        
        Args:
            movies: Movies the user has viewed.
            
        Returns:
            List of genres with affinity scores.
        """
        genre_counts = Counter()
        total_movies = len(movies)

        for movie in movies:
            for genre in movie.genres:
                genre_counts[genre] += 1

        # Convert to affinity scores (0-1 scale)
        affinities = []
        for genre, count in genre_counts.most_common(10):
            affinity = count / total_movies if total_movies > 0 else 0
            affinities.append({
                "genre": genre,
                "affinity": round(affinity, 2),
                "count": count,
            })

        return affinities

    def _extract_director_preferences(self, movies: List) -> List[Dict]:
        """Extract user's favorite directors.
        
        Args:
            movies: Movies the user has viewed.
            
        Returns:
            List of directors with statistics.
        """
        director_stats = {}

        for movie in movies:
            for director in movie.directors:
                if director not in director_stats:
                    director_stats[director] = {
                        "name": director,
                        "movie_count": 0,
                        "avg_rating": 0,
                        "ratings": [],
                    }
                
                director_stats[director]["movie_count"] += 1
                if movie.imdb and movie.imdb.rating:
                    director_stats[director]["ratings"].append(movie.imdb.rating)

        # Calculate average ratings
        preferences = []
        for director, stats in director_stats.items():
            if stats["ratings"]:
                stats["avg_rating"] = round(
                    sum(stats["ratings"]) / len(stats["ratings"]), 1
                )
            del stats["ratings"]  # Remove raw ratings list
            preferences.append(stats)

        # Sort by movie count and rating
        preferences.sort(
            key=lambda x: (x["movie_count"], x["avg_rating"]), reverse=True
        )
        return preferences[:10]

    def _extract_actor_preferences(self, movies: List) -> List[Dict]:
        """Extract user's favorite actors.
        
        Args:
            movies: Movies the user has viewed.
            
        Returns:
            List of actors with statistics.
        """
        actor_counts = Counter()

        for movie in movies:
            for actor in movie.cast[:5]:  # Consider top 5 billed actors
                actor_counts[actor] += 1

        preferences = []
        for actor, count in actor_counts.most_common(10):
            preferences.append({
                "name": actor,
                "appearance_count": count,
            })

        return preferences

    def _analyze_viewing_patterns(
        self, comments: List[MovieComment], movies: List
    ) -> Dict:
        """Analyze viewing patterns (runtime preferences, decades, etc.).
        
        Args:
            comments: User's comments.
            movies: Movies the user has viewed.
            
        Returns:
            Dictionary of viewing patterns.
        """
        if not movies:
            return {}

        runtimes = [m.runtime for m in movies if m.runtime]
        decades = [str(m.year // 10 * 10) + "s" for m in movies if m.year]
        ratings = [m.imdb.rating for m in movies if m.imdb and m.imdb.rating]

        patterns = {
            "total_movies_commented": len(comments),
            "avg_runtime_preference": round(sum(runtimes) / len(runtimes)) if runtimes else None,
            "preferred_decades": [decade for decade, _ in Counter(decades).most_common(3)],
            "avg_rating_watched": round(sum(ratings) / len(ratings), 1) if ratings else None,
        }

        return patterns

    def _format_as_markdown(self, profile_data: Dict) -> str:
        """Format profile data as Markdown.
        
        Args:
            profile_data: Profile dictionary.
            
        Returns:
            Markdown formatted string.
        """
        md = f"# User Profile: {profile_data['name']}\n\n"
        md += f"**Email:** {profile_data['email']}\n\n"

        # Genre affinities
        if profile_data.get("genre_affinities"):
            md += "## Genre Preferences\n"
            for genre_info in profile_data["genre_affinities"][:5]:
                md += f"- **{genre_info['genre']}**: {int(genre_info['affinity'] * 100)}% affinity ({genre_info['count']} movies)\n"
            md += "\n"

        # Director preferences
        if profile_data.get("director_preferences"):
            md += "## Favorite Directors\n"
            for director in profile_data["director_preferences"][:5]:
                md += f"- **{director['name']}**: {director['movie_count']} movies"
                if director["avg_rating"]:
                    md += f", avg rating {director['avg_rating']}"
                md += "\n"
            md += "\n"

        # Viewing patterns
        if profile_data.get("viewing_patterns"):
            patterns = profile_data["viewing_patterns"]
            md += "## Viewing Patterns\n"
            if patterns.get("total_movies_commented"):
                md += f"- Total movies commented on: {patterns['total_movies_commented']}\n"
            if patterns.get("avg_runtime_preference"):
                md += f"- Preferred runtime: ~{patterns['avg_runtime_preference']} minutes\n"
            if patterns.get("preferred_decades"):
                md += f"- Favorite decades: {', '.join(patterns['preferred_decades'])}\n"
            md += "\n"

        # Recent watch history
        if profile_data.get("watch_history"):
            md += "## Recent Viewing History\n"
            for movie in profile_data["watch_history"][:5]:
                md += f"- **{movie['title']}** ({movie['year']})"
                if movie['genres']:
                    md += f" - {', '.join(movie['genres'][:3])}"
                md += "\n"

        return md

