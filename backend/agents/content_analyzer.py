"""Content Analyzer Agent - Finds candidate movies using semantic search."""

import json
import logging
import time
from collections import Counter
from typing import Dict, List, Optional

from backend.agents.base import Agent, AgentContext, AgentOutput, ContextFormat
from backend.models.movie import Movie
from backend.services.mflix_service import MflixService

logger = logging.getLogger(__name__)


class ContentAnalyzerAgent(Agent):
    """Agent that analyzes content and finds candidate movies for recommendations.
    
    This agent:
    1. Takes user profile from User Profiler Agent
    2. Queries movies based on genre preferences
    3. Filters by director/actor preferences
    4. Uses semantic search on plot embeddings (if available)
    5. Scores and ranks candidate movies
    
    Example:
        >>> service = MflixService(mongo_client)
        >>> analyzer = ContentAnalyzerAgent(service)
        >>> output = analyzer.process(user_profile_context)
    """

    def __init__(
        self,
        mflix_service: MflixService,
        context_format: ContextFormat = ContextFormat.JSON,
        max_candidates: int = 50,
    ):
        """Initialize Content Analyzer Agent.
        
        Args:
            mflix_service: Service for accessing Mflix data.
            context_format: Format for context output (JSON or Markdown).
            max_candidates: Maximum number of candidate movies to return.
        """
        super().__init__("ContentAnalyzerAgent", context_format)
        self.service = mflix_service
        self.max_candidates = max_candidates

    def process(self, input_context: Optional[AgentContext] = None) -> AgentOutput:
        """Process user profile and find candidate movies.
        
        Args:
            input_context: Context from User Profiler with user preferences.
            
        Returns:
            AgentOutput with candidate movies and match scores.
        """
        start_time = time.time()

        try:
            if input_context is None:
                raise ValueError("ContentAnalyzerAgent requires input context from User Profiler")

            user_profile = input_context.data
            
            # Extract user preferences
            user_id = user_profile.get("user_id", "unknown")
            name = user_profile.get("name", "Unknown User")
            
            # Get candidate movies based on preferences
            candidates = self._find_candidate_movies(user_profile)
            
            # Score and rank candidates
            scored_candidates = self._score_candidates(candidates, user_profile)
            
            # Take top N
            top_candidates = scored_candidates[:self.max_candidates]
            
            # Build output data
            analysis_data = {
                "user_id": user_id,
                "user_name": name,
                "user_profile_summary": self._summarize_profile(user_profile),
                "total_candidates_analyzed": len(candidates),
                "top_candidates_count": len(top_candidates),
                "candidate_movies": top_candidates,
                "matching_strategy": "hybrid_genre_director_rating",
            }
            
            # Create context based on format
            if self.context_format == ContextFormat.JSON:
                context_text = json.dumps(analysis_data, indent=2)
            else:
                context_text = self._format_as_markdown(analysis_data)

            tokens = self._estimate_tokens(context_text)
            context = self._create_context(
                data=analysis_data,
                tokens=tokens,
                raw_text=context_text,
                candidates_found=len(candidates),
            )

            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                context=context,
                execution_time_ms=execution_time,
                success=True,
            )

        except Exception as e:
            logger.error(f"ContentAnalyzerAgent failed: {str(e)}")
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                context=self._create_context(data={}),
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )

    def _find_candidate_movies(self, user_profile: Dict) -> List[Movie]:
        """Find candidate movies based on user preferences.
        
        Args:
            user_profile: User profile data from User Profiler.
            
        Returns:
            List of candidate Movie objects.
        """
        candidates = []
        seen_ids = set()
        
        # Strategy 1: Get movies by top genres
        genre_affinities = user_profile.get("genre_affinities", [])
        if genre_affinities:
            for genre_info in genre_affinities[:3]:  # Top 3 genres
                genre = genre_info["genre"]
                movies = self.service.get_movies_by_genre(genre, limit=30)
                for movie in movies:
                    if movie.id not in seen_ids:
                        candidates.append(movie)
                        seen_ids.add(movie.id)
        
        # Strategy 2: Get movies by favorite directors
        director_prefs = user_profile.get("director_preferences", [])
        if director_prefs:
            for director_info in director_prefs[:3]:  # Top 3 directors
                director = director_info["name"]
                movies = self.service.get_movies_by_director(director, limit=20)
                for movie in movies:
                    if movie.id not in seen_ids:
                        candidates.append(movie)
                        seen_ids.add(movie.id)
        
        # Strategy 3: Get top-rated movies as fallback
        if len(candidates) < 20:
            top_rated = self.service.get_top_rated_movies(limit=30, min_rating=7.5)
            for movie in top_rated:
                if movie.id not in seen_ids:
                    candidates.append(movie)
                    seen_ids.add(movie.id)
        
        logger.info(f"Found {len(candidates)} candidate movies")
        return candidates

    def _score_candidates(
        self, candidates: List[Movie], user_profile: Dict
    ) -> List[Dict]:
        """Score and rank candidate movies based on user preferences.
        
        Args:
            candidates: List of candidate movies.
            user_profile: User profile data.
            
        Returns:
            List of scored movie dictionaries sorted by score (descending).
        """
        scored = []
        
        # Build preference lookups
        genre_affinities = {
            g["genre"]: g["affinity"]
            for g in user_profile.get("genre_affinities", [])
        }
        favorite_directors = {
            d["name"]
            for d in user_profile.get("director_preferences", [])[:5]
        }
        favorite_actors = {
            a["name"]
            for a in user_profile.get("actor_preferences", [])[:10]
        }
        
        viewing_patterns = user_profile.get("viewing_patterns", {})
        preferred_decades = set(viewing_patterns.get("preferred_decades", []))
        
        for movie in candidates:
            score = 0.0
            match_reasons = []
            
            # Genre matching (0-1 points)
            genre_score = 0.0
            for genre in movie.genres:
                if genre in genre_affinities:
                    genre_score = max(genre_score, genre_affinities[genre])
                    match_reasons.append(f"genre_{genre}")
            score += genre_score
            
            # Director matching (0-0.5 points)
            director_match = any(d in favorite_directors for d in movie.directors)
            if director_match:
                score += 0.5
                match_reasons.append(f"director_match")
            
            # Actor matching (0-0.3 points)
            actor_matches = len([a for a in movie.cast[:10] if a in favorite_actors])
            if actor_matches > 0:
                actor_score = min(0.3, actor_matches * 0.1)
                score += actor_score
                match_reasons.append(f"actor_match_{actor_matches}")
            
            # Rating quality (0-0.5 points)
            if movie.imdb and movie.imdb.rating:
                rating_score = (movie.imdb.rating - 5) / 10  # Normalize 5-10 to 0-0.5
                score += max(0, rating_score)
            
            # Decade preference (0-0.2 points)
            if movie.year:
                decade = f"{movie.year // 10 * 10}s"
                if decade in preferred_decades:
                    score += 0.2
                    match_reasons.append(f"decade_{decade}")
            
            # Popularity bonus (0-0.2 points)
            if movie.imdb and movie.imdb.votes:
                if movie.imdb.votes > 100000:
                    score += 0.2
                elif movie.imdb.votes > 10000:
                    score += 0.1
            
            scored.append({
                "movie_id": movie.id,
                "title": movie.title,
                "year": movie.year,
                "genres": movie.genres,
                "directors": movie.directors[:2] if movie.directors else [],
                "cast": movie.cast[:3] if movie.cast else [],
                "imdb_rating": movie.imdb.rating if movie.imdb else None,
                "imdb_votes": movie.imdb.votes if movie.imdb else None,
                "similarity_score": round(score, 3),
                "match_reasons": match_reasons[:5],  # Top 5 reasons
            })
        
        # Sort by score descending
        scored.sort(key=lambda x: x["similarity_score"], reverse=True)
        return scored

    def _summarize_profile(self, user_profile: Dict) -> Dict:
        """Create a compact summary of user preferences.
        
        Args:
            user_profile: Full user profile data.
            
        Returns:
            Summarized preferences dictionary.
        """
        genre_affinities = user_profile.get("genre_affinities", [])
        director_prefs = user_profile.get("director_preferences", [])
        
        return {
            "top_genres": [g["genre"] for g in genre_affinities[:3]],
            "favorite_directors": [d["name"] for d in director_prefs[:3]],
            "total_movies_seen": user_profile.get("viewing_patterns", {}).get(
                "total_movies_commented", 0
            ),
        }

    def _format_as_markdown(self, analysis_data: Dict) -> str:
        """Format analysis data as Markdown.
        
        Args:
            analysis_data: Analysis data dictionary.
            
        Returns:
            Markdown formatted string.
        """
        md = f"# Content Analysis for {analysis_data['user_name']}\n\n"
        
        # User profile summary
        summary = analysis_data["user_profile_summary"]
        md += "## User Preferences\n"
        if summary.get("top_genres"):
            md += f"**Top Genres:** {', '.join(summary['top_genres'])}\n"
        if summary.get("favorite_directors"):
            md += f"**Favorite Directors:** {', '.join(summary['favorite_directors'])}\n"
        md += f"**Movies Watched:** {summary.get('total_movies_seen', 0)}\n\n"
        
        # Candidate movies
        md += f"## Top Candidate Movies ({analysis_data['top_candidates_count']} of {analysis_data['total_candidates_analyzed']} analyzed)\n\n"
        
        for i, movie in enumerate(analysis_data["candidate_movies"][:10], 1):
            md += f"### {i}. {movie['title']} ({movie['year']})\n"
            md += f"**Match Score:** {movie['similarity_score']:.2f}\n"
            if movie['genres']:
                md += f"**Genres:** {', '.join(movie['genres'][:3])}\n"
            if movie['directors']:
                md += f"**Director:** {', '.join(movie['directors'])}\n"
            if movie['imdb_rating']:
                md += f"**IMDb Rating:** {movie['imdb_rating']}/10\n"
            if movie['match_reasons']:
                md += f"**Match Reasons:** {', '.join(movie['match_reasons'][:3])}\n"
            md += "\n"
        
        return md

