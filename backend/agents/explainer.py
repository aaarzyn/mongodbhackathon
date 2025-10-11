"""Explainer Agent - Generates natural language explanations for recommendations."""

import json
import logging
import time
from typing import Dict, List, Optional

from backend.agents.base import Agent, AgentContext, AgentOutput, ContextFormat

logger = logging.getLogger(__name__)


class ExplainerAgent(Agent):
    """Agent that explains why movies were recommended.
    
    This agent:
    1. Takes recommendations from Recommender Agent
    2. Generates natural language explanations
    3. Provides reasoning for each recommendation
    
    Example:
        >>> explainer = ExplainerAgent()
        >>> output = explainer.process(recommender_context)
    """

    def __init__(self, context_format: ContextFormat = ContextFormat.JSON):
        """Initialize Explainer Agent.
        
        Args:
            context_format: Format for context output (JSON or Markdown).
        """
        super().__init__("ExplainerAgent", context_format)

    def process(self, input_context: Optional[AgentContext] = None) -> AgentOutput:
        """Process recommendations and generate explanations.
        
        Args:
            input_context: Context from Recommender with final recommendations.
            
        Returns:
            AgentOutput with recommendations and explanations.
        """
        start_time = time.time()

        try:
            if input_context is None:
                raise ValueError("ExplainerAgent requires input context from Recommender")

            recommendation_data = input_context.data
            recommendations = recommendation_data.get("recommendations", [])
            
            if not recommendations:
                raise ValueError("No recommendations found in input context")
            
            # Generate explanations for each recommendation
            explained_recommendations = []
            for rec in recommendations:
                explanation = self._generate_explanation(rec)
                explained_recommendations.append({
                    "rank": rec["rank"],
                    "title": rec["title"],
                    "year": rec["year"],
                    "genres": rec.get("genres", []),
                    "directors": rec.get("directors", []),
                    "imdb_rating": rec.get("imdb_rating"),
                    "confidence": rec.get("confidence"),
                    "explanation": explanation,
                    "key_appeal_points": self._extract_appeal_points(rec),
                })
            
            # Build output data
            explanation_data = {
                "user_id": recommendation_data.get("user_id"),
                "user_name": recommendation_data.get("user_name"),
                "recommendations_with_explanations": explained_recommendations,
            }
            
            # Create context based on format
            if self.context_format == ContextFormat.JSON:
                context_text = json.dumps(explanation_data, indent=2)
            else:
                context_text = self._format_as_markdown(explanation_data)

            tokens = self._estimate_tokens(context_text)
            context = self._create_context(
                data=explanation_data,
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
            logger.error(f"ExplainerAgent failed: {str(e)}")
            execution_time = (time.time() - start_time) * 1000
            return AgentOutput(
                context=self._create_context(data={}),
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e),
            )

    def _generate_explanation(self, recommendation: Dict) -> str:
        """Generate natural language explanation for a recommendation.
        
        Args:
            recommendation: Recommendation dictionary with metadata and scores.
            
        Returns:
            Explanation string.
        """
        title = recommendation["title"]
        year = recommendation["year"]
        genres = recommendation.get("genres", [])
        directors = recommendation.get("directors", [])
        match_reasons = recommendation.get("match_reasons", [])
        confidence = recommendation.get("confidence", 0)
        imdb_rating = recommendation.get("imdb_rating")
        
        # Build explanation based on match reasons
        explanation_parts = []
        
        # Start with genre match
        genre_matches = [r for r in match_reasons if r.startswith("genre_")]
        if genre_matches:
            matched_genres = [r.split("_")[1] for r in genre_matches]
            explanation_parts.append(
                f"This {', '.join(matched_genres[:2])} film matches your genre preferences"
            )
        
        # Director match
        if "director_match" in match_reasons and directors:
            explanation_parts.append(
                f"directed by {', '.join(directors[:2])}, a filmmaker you enjoy"
            )
        
        # Actor match
        actor_matches = [r for r in match_reasons if r.startswith("actor_match")]
        if actor_matches:
            explanation_parts.append(
                "featuring actors from movies you've watched"
            )
        
        # Decade preference
        decade_matches = [r for r in match_reasons if r.startswith("decade_")]
        if decade_matches:
            explanation_parts.append(
                f"from a decade you prefer"
            )
        
        # High rating
        if imdb_rating and imdb_rating >= 8.0:
            explanation_parts.append(
                f"with an excellent {imdb_rating}/10 IMDb rating"
            )
        
        # Build final explanation
        if explanation_parts:
            explanation = f"We recommend '{title}' ({year}) because it's " + ", ".join(explanation_parts) + "."
        else:
            explanation = f"We recommend '{title}' ({year}) based on your viewing preferences."
        
        # Add confidence note
        if confidence >= 0.8:
            explanation += " This is a highly confident match for your taste."
        elif confidence >= 0.6:
            explanation += " This is a good match for your taste."
        
        return explanation

    def _extract_appeal_points(self, recommendation: Dict) -> List[str]:
        """Extract key appeal points for the recommendation.
        
        Args:
            recommendation: Recommendation dictionary.
            
        Returns:
            List of appeal points.
        """
        appeal_points = []
        
        genres = recommendation.get("genres", [])
        if genres:
            appeal_points.append(f"Genres: {', '.join(genres[:3])}")
        
        directors = recommendation.get("directors", [])
        if directors:
            appeal_points.append(f"Director: {', '.join(directors[:2])}")
        
        imdb_rating = recommendation.get("imdb_rating")
        if imdb_rating:
            appeal_points.append(f"IMDb Rating: {imdb_rating}/10")
        
        confidence = recommendation.get("confidence")
        if confidence and confidence >= 0.7:
            appeal_points.append(f"Match Confidence: {int(confidence * 100)}%")
        
        return appeal_points

    def _format_as_markdown(self, explanation_data: Dict) -> str:
        """Format explanations as Markdown.
        
        Args:
            explanation_data: Explanation data dictionary.
            
        Returns:
            Markdown formatted string.
        """
        md = f"# Personalized Recommendations for {explanation_data['user_name']}\n\n"
        
        for rec in explanation_data["recommendations_with_explanations"]:
            md += f"## {rec['rank']}. {rec['title']} ({rec['year']})\n\n"
            md += f"{rec['explanation']}\n\n"
            
            if rec['key_appeal_points']:
                md += "**Why you'll love it:**\n"
                for point in rec['key_appeal_points']:
                    md += f"- {point}\n"
                md += "\n"
        
        return md

