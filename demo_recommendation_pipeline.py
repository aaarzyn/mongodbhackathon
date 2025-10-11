"""Complete End-to-End Recommendation Pipeline Demo.

This script demonstrates the full multi-agent pipeline:
User Profiler → Content Analyzer → Recommender → Explainer

Usage:
    python demo_recommendation_pipeline.py [email]
"""

import json
import logging
import sys
from typing import Optional

from backend.agents import (
    ContentAnalyzerAgent,
    ExplainerAgent,
    RecommenderAgent,
    UserProfilerAgent,
)
from backend.agents.base import ContextFormat
from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient
from backend.services.mflix_service import MflixService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_header(title: str) -> None:
    """Print a nice header."""
    logger.info("\n" + "=" * 70)
    logger.info(f"  {title}")
    logger.info("=" * 70)


def run_pipeline(user_email: str, service: MflixService) -> None:
    """Run the complete recommendation pipeline.
    
    Args:
        user_email: User email to generate recommendations for.
        service: Mflix service instance.
    """
    print_header("MOVIE RECOMMENDATION PIPELINE DEMO")
    
    # Initialize agents
    logger.info("\nInitializing agents...")
    profiler = UserProfilerAgent(service, ContextFormat.JSON)
    analyzer = ContentAnalyzerAgent(service, ContextFormat.JSON, max_candidates=30)
    recommender = RecommenderAgent(ContextFormat.JSON, top_n=5)
    explainer = ExplainerAgent(ContextFormat.JSON)
    
    logger.info("✓ All agents initialized")
    
    # Step 1: User Profiler
    print_header("STEP 1: USER PROFILER AGENT")
    logger.info(f"Profiling user: {user_email}")
    
    profile_output = profiler.process_user(user_email)
    if not profile_output.success:
        logger.error(f"✗ User profiling failed: {profile_output.error_message}")
        return
    
    logger.info(f"✓ User profiled in {profile_output.execution_time_ms:.0f}ms")
    logger.info(f"  Tokens: {profile_output.context.tokens}")
    
    profile = profile_output.context.data
    logger.info(f"\nUser: {profile['name']}")
    if profile.get("genre_affinities"):
        top_genres = [g["genre"] for g in profile["genre_affinities"][:3]]
        logger.info(f"  Top genres: {', '.join(top_genres)}")
    if profile.get("director_preferences"):
        top_directors = [d["name"] for d in profile["director_preferences"][:2]]
        logger.info(f"  Favorite directors: {', '.join(top_directors)}")
    
    # Step 2: Content Analyzer
    print_header("STEP 2: CONTENT ANALYZER AGENT")
    logger.info("Finding candidate movies...")
    
    analysis_output = analyzer.process(profile_output.context)
    if not analysis_output.success:
        logger.error(f"✗ Content analysis failed: {analysis_output.error_message}")
        return
    
    logger.info(f"✓ Analysis complete in {analysis_output.execution_time_ms:.0f}ms")
    logger.info(f"  Tokens: {analysis_output.context.tokens}")
    
    analysis = analysis_output.context.data
    logger.info(f"\n  Candidates analyzed: {analysis['total_candidates_analyzed']}")
    logger.info(f"  Top candidates: {analysis['top_candidates_count']}")
    
    # Step 3: Recommender
    print_header("STEP 3: RECOMMENDER AGENT")
    logger.info("Ranking and filtering recommendations...")
    
    recommendation_output = recommender.process(analysis_output.context)
    if not recommendation_output.success:
        logger.error(f"✗ Recommendation failed: {recommendation_output.error_message}")
        return
    
    logger.info(f"✓ Recommendations generated in {recommendation_output.execution_time_ms:.0f}ms")
    logger.info(f"  Tokens: {recommendation_output.context.tokens}")
    
    recommendations = recommendation_output.context.data
    logger.info(f"\n  Final recommendations: {len(recommendations['recommendations'])}")
    
    # Step 4: Explainer
    print_header("STEP 4: EXPLAINER AGENT")
    logger.info("Generating explanations...")
    
    explanation_output = explainer.process(recommendation_output.context)
    if not explanation_output.success:
        logger.error(f"✗ Explanation failed: {explanation_output.error_message}")
        return
    
    logger.info(f"✓ Explanations generated in {explanation_output.execution_time_ms:.0f}ms")
    logger.info(f"  Tokens: {explanation_output.context.tokens}")
    
    # Display final results
    print_header("FINAL RECOMMENDATIONS")
    
    explanations = explanation_output.context.data
    for rec in explanations["recommendations_with_explanations"]:
        logger.info(f"\n{rec['rank']}. {rec['title']} ({rec['year']})")
        logger.info(f"   {rec['explanation']}")
        if rec['key_appeal_points']:
            logger.info(f"   Key points:")
            for point in rec['key_appeal_points']:
                logger.info(f"     • {point}")
    
    # Pipeline summary
    print_header("PIPELINE SUMMARY")
    
    total_time = (
        profile_output.execution_time_ms +
        analysis_output.execution_time_ms +
        recommendation_output.execution_time_ms +
        explanation_output.execution_time_ms
    )
    
    total_tokens = (
        profile_output.context.tokens +
        analysis_output.context.tokens +
        recommendation_output.context.tokens +
        explanation_output.context.tokens
    )
    
    logger.info(f"\nTotal execution time: {total_time:.0f}ms")
    logger.info(f"Total tokens processed: {total_tokens}")
    logger.info(f"\nAgent execution times:")
    logger.info(f"  User Profiler:     {profile_output.execution_time_ms:>6.0f}ms ({profile_output.context.tokens:>4} tokens)")
    logger.info(f"  Content Analyzer:  {analysis_output.execution_time_ms:>6.0f}ms ({analysis_output.context.tokens:>4} tokens)")
    logger.info(f"  Recommender:       {recommendation_output.execution_time_ms:>6.0f}ms ({recommendation_output.context.tokens:>4} tokens)")
    logger.info(f"  Explainer:         {explanation_output.execution_time_ms:>6.0f}ms ({explanation_output.context.tokens:>4} tokens)")
    
    # Context flow analysis
    print_header("CONTEXT FLOW ANALYSIS")
    logger.info("\nInformation flow through pipeline:")
    logger.info(f"  User Profiler   → Content Analyzer: {profile_output.context.tokens:>4} tokens")
    logger.info(f"  Content Analyzer → Recommender:     {analysis_output.context.tokens:>4} tokens")
    logger.info(f"  Recommender     → Explainer:        {recommendation_output.context.tokens:>4} tokens")
    logger.info(f"  Final Output:                       {explanation_output.context.tokens:>4} tokens")
    
    logger.info(f"\n✓ Pipeline completed successfully!")
    logger.info(f"✓ Ready to build frontend visualization")


def main() -> int:
    """Main function.
    
    Returns:
        Exit code.
    """
    # Get user email from command line or use default
    if len(sys.argv) > 1:
        user_email = sys.argv[1]
    else:
        user_email = None
    
    # Connect to database
    try:
        settings = get_settings()
        client = MongoDBClient(settings)
        service = MflixService(client)
        logger.info("✓ Connected to MongoDB Atlas")
    except Exception as e:
        logger.error(f"✗ Failed to connect: {str(e)}")
        return 1
    
    # Find a user if none specified
    if not user_email:
        logger.info("\nFinding a user with viewing history...")
        users = service.list_users(limit=10)
        
        for user in users:
            comments = service.get_comments_by_user(user.email, limit=1)
            if comments:
                user_email = user.email
                logger.info(f"✓ Using user: {user.name} ({user.email})")
                break
        
        if not user_email:
            logger.warning("No users with comments found, using first user")
            user_email = users[0].email if users else None
    
    if not user_email:
        logger.error("✗ No users found in database")
        return 1
    
    # Run the pipeline
    try:
        run_pipeline(user_email, service)
        return 0
    except Exception as e:
        logger.error(f"✗ Pipeline failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

