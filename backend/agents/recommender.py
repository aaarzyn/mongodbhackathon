"""Recommender Agent - Ranks and filters final movie recommendations."""

import json
import logging
import time
from typing import Dict, List, Optional

from backend.agents.base import Agent, AgentContext, AgentOutput, ContextFormat

logger = logging.getLogger(__name__)


class RecommenderAgent(Agent):
    """Agent that ranks and filters final movie recommendations.
    
    This agent:
    1. Takes candidate movies from Content Analyzer
    2. Applies final ranking and filtering logic
    3. Selects top N recommendations
    4. Adds confidence scores
    
    Example:
        >>> recommender = RecommenderAgent(top_n=5)
        >>> output = recommender.process(content_analyzer_context)
    """

    def __init__(
        self,
        context_format: ContextFormat = ContextFormat.JSON,
        top_n: int = 5,
        min_score: float = 0.3,
    ):
        """Initialize Recommender Agent.
        
        Args:
            context_format: Format for context output (JSON or Markdown).
            top_n: Number of top recommendations to return.
            min_score: Minimum similarity score threshold.
        """
        super().__init__("RecommenderAgent", context_format)
        self.top_n = top_n
        self.min_score = min_score

    def process(self, input_context: Optional[AgentContext] = None) -> AgentOutput:
        """Process candidate movies and produce final recommendations.
        
        Args:
            input_context: Context from Content Analyzer with candidate movies.
            
        Returns:
            AgentOutput with final ranked recommendations.
        """
        start_time = time.time()

        try:
            if input_context is None:
                raise ValueError("RecommenderAgent requires input context from Content Analyzer")

            analysis_data = input_context.data
            candidates = analysis_data.get("candidate_movies", [])
            
            if not candidates:
                raise ValueError("No candidate movies found in input context")
            
            # Filter by minimum score
            filtered = [c for c in candidates if c.get("similarity_score", 0) >= self.min_score]
            
            # Take top N
            top_recommendations = filtered[:self.top_n]
            
            # Add confidence scores and ranking
            recommendations = []
            for rank, movie in enumerate(top_recommendations, 1):
                recommendations.append({
                    "rank": rank,
                    "movie_id": movie.get("movie_id"),
                    "title": movie.get("title"),
                    "year": movie.get("year"),
                    "genres": movie.get("genres", []),
                    "directors": movie.get("directors", []),
                    "cast": movie.get("cast", []),
                    "imdb_rating": movie.get("imdb_rating"),
                    "similarity_score": movie.get("similarity_score"),
                    "confidence": self._calculate_confidence(movie),
                    "match_reasons": movie.get("match_reasons", []),
                })
            
            # Build output data
            recommendation_data = {
                "user_id": analysis_data.get("user_id"),
                "user_name": analysis_data.get("user_name"),
                "total_candidates": len(candidates),
                "filtered_candidates": len(filtered),
                "recommendations": recommendations,
                "ranking_criteria": {
                    "min_score_threshold": self.min_score,
                    "top_n": self.top_n,
                    "algorithm": "hybrid_scoring_with_confidence",
                },
            }
            
            # Create context based on format
            if self.context_format == ContextFormat.JSON:
                context_text = json.dumps(recommendation_data, indent=2)
            else:
                context_text = self._format_as_markdown(recommendation_data)

            tokens = self._estimate_tokens(context_text)
            context = self._create_context(
                data=recommendation_data,
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
            logger.error(f"RecommenderAgent failed: {str(e)}")
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                context=self._create_context(data={}),
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )

    def _calculate_confidence(self, movie: Dict) -> float:
        """Calculate confidence score for a recommendation.
        
        Confidence is based on:
        - Similarity score strength
        - Number of match reasons
        - IMDb rating quality
        - Vote count (popularity)
        
        Args:
            movie: Movie dictionary with scores and metadata.
            
        Returns:
            Confidence score (0-1 scale).
        """
        confidence = 0.0
        
        # Base confidence from similarity score (0-0.5)
        similarity = movie.get("similarity_score", 0)
        confidence += min(0.5, similarity / 2)
        
        # Match reasons strength (0-0.25)
        match_reasons = len(movie.get("match_reasons", []))
        confidence += min(0.25, match_reasons * 0.05)
        
        # Rating quality (0-0.15)
        imdb_rating = movie.get("imdb_rating")
        if imdb_rating:
            confidence += min(0.15, (imdb_rating - 5) / 50)
        
        # Popularity bonus (0-0.10)
        imdb_votes = movie.get("imdb_votes")
        if imdb_votes:
            if imdb_votes > 100000:
                confidence += 0.10
            elif imdb_votes > 10000:
                confidence += 0.05
        
        return round(min(1.0, confidence), 3)

    def _format_as_markdown(self, recommendation_data: Dict) -> str:
        """Format recommendations as Markdown.
        
        Args:
            recommendation_data: Recommendation data dictionary.
            
        Returns:
            Markdown formatted string.
        """
        md = f"# Movie Recommendations for {recommendation_data['user_name']}\n\n"
        md += f"**Top {len(recommendation_data['recommendations'])} recommendations** "
        md += f"(from {recommendation_data['total_candidates']} candidates)\n\n"
        
        for rec in recommendation_data["recommendations"]:
            md += f"## {rec['rank']}. {rec['title']} ({rec['year']})\n"
            md += f"**Confidence:** {int(rec['confidence'] * 100)}%\n"
            md += f"**Match Score:** {rec['similarity_score']:.2f}\n"
            if rec['genres']:
                md += f"**Genres:** {', '.join(rec['genres'][:3])}\n"
            if rec['directors']:
                md += f"**Director:** {', '.join(rec['directors'])}\n"
            if rec['imdb_rating']:
                md += f"**IMDb Rating:** {rec['imdb_rating']}/10\n"
            md += "\n"
        
        return md

