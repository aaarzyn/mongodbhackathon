"""Test script for Content Analyzer Agent.

This script tests the Content Analyzer Agent with real users and shows
the end-to-end flow: User Profiler → Content Analyzer.

Usage:
    python test_content_analyzer.py
"""

import json
import logging
from typing import Optional

from backend.agents.base import ContextFormat
from backend.agents.content_analyzer import ContentAnalyzerAgent
from backend.agents.user_profiler import UserProfilerAgent
from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient
from backend.services.mflix_service import MflixService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_separator(title: str = "") -> None:
    """Print a nice separator."""
    if title:
        logger.info(f"\n{'=' * 70}")
        logger.info(f"  {title}")
        logger.info(f"{'=' * 70}\n")
    else:
        logger.info(f"{'=' * 70}\n")


def test_content_analyzer_json(
    profiler: UserProfilerAgent,
    analyzer: ContentAnalyzerAgent,
    email: str,
) -> Optional[dict]:
    """Test Content Analyzer with JSON format.
    
    Args:
        profiler: User Profiler Agent instance.
        analyzer: Content Analyzer Agent instance.
        email: User email to analyze.
        
    Returns:
        Analysis data if successful, None otherwise.
    """
    print_separator(f"Testing Content Analyzer (JSON) - {email}")
    
    try:
        # Step 1: Profile the user
        logger.info("Step 1: Profiling user...")
        profile_output = profiler.process_user(email)
        
        if not profile_output.success:
            logger.error(f"✗ User profiling failed: {profile_output.error_message}")
            return None
        
        logger.info(f"✓ User profiled in {profile_output.execution_time_ms:.2f}ms")
        profile_data = profile_output.context.data
        
        # Show user summary
        logger.info(f"\nUser: {profile_data['name']}")
        if profile_data.get("genre_affinities"):
            top_genres = [g["genre"] for g in profile_data["genre_affinities"][:3]]
            logger.info(f"  Top genres: {', '.join(top_genres)}")
        
        # Step 2: Analyze content and find candidates
        logger.info("\nStep 2: Finding candidate movies...")
        analysis_output = analyzer.process(profile_output.context)
        
        if not analysis_output.success:
            logger.error(f"✗ Content analysis failed: {analysis_output.error_message}")
            return None
        
        logger.info(f"✓ Analysis complete in {analysis_output.execution_time_ms:.2f}ms")
        analysis_data = analysis_output.context.data
        
        # Show analysis summary
        logger.info(f"\nAnalysis Results:")
        logger.info(f"  Candidates analyzed: {analysis_data['total_candidates_analyzed']}")
        logger.info(f"  Top candidates: {analysis_data['top_candidates_count']}")
        logger.info(f"  Token count: {analysis_output.context.tokens}")
        
        # Show top recommendations
        logger.info(f"\nTop 5 Candidate Movies:")
        for i, movie in enumerate(analysis_data["candidate_movies"][:5], 1):
            genres = ", ".join(movie["genres"][:2]) if movie["genres"] else "N/A"
            rating = f"{movie['imdb_rating']}/10" if movie['imdb_rating'] else "N/A"
            logger.info(
                f"  {i}. {movie['title']} ({movie['year']}) - {genres}"
            )
            logger.info(f"     Score: {movie['similarity_score']:.3f}, Rating: {rating}")
            if movie['match_reasons']:
                logger.info(f"     Reasons: {', '.join(movie['match_reasons'][:3])}")
        
        return analysis_data
        
    except Exception as e:
        logger.error(f"✗ Exception: {str(e)}")
        return None


def test_content_analyzer_markdown(
    profiler: UserProfilerAgent,
    analyzer: ContentAnalyzerAgent,
    email: str,
) -> Optional[str]:
    """Test Content Analyzer with Markdown format.
    
    Args:
        profiler: User Profiler Agent instance.
        analyzer: Content Analyzer Agent instance.
        email: User email to analyze.
        
    Returns:
        Markdown text if successful, None otherwise.
    """
    print_separator(f"Testing Content Analyzer (Markdown) - {email}")
    
    try:
        # Profile user
        logger.info("Step 1: Profiling user...")
        profile_output = profiler.process_user(email)
        
        if not profile_output.success:
            logger.error(f"✗ User profiling failed")
            return None
        
        logger.info(f"✓ User profiled")
        
        # Analyze content
        logger.info("\nStep 2: Finding candidate movies...")
        analysis_output = analyzer.process(profile_output.context)
        
        if not analysis_output.success:
            logger.error(f"✗ Content analysis failed")
            return None
        
        logger.info(f"✓ Analysis complete in {analysis_output.execution_time_ms:.2f}ms")
        logger.info(f"  Token count: {analysis_output.context.tokens}")
        
        # Show markdown output
        markdown_text = analysis_output.context.metadata.get("raw_text", "")
        logger.info("\nMarkdown Output:")
        logger.info("-" * 70)
        logger.info(markdown_text[:1000] + "..." if len(markdown_text) > 1000 else markdown_text)
        logger.info("-" * 70)
        
        return markdown_text
        
    except Exception as e:
        logger.error(f"✗ Exception: {str(e)}")
        return None


def compare_pipeline_outputs(json_data: dict, markdown_text: str) -> None:
    """Compare JSON vs Markdown pipeline outputs.
    
    Args:
        json_data: JSON analysis data.
        markdown_text: Markdown analysis text.
    """
    print_separator("Comparing JSON vs Markdown Pipeline")
    
    json_str = json.dumps(json_data, indent=2)
    
    logger.info(f"JSON size: {len(json_str)} characters")
    logger.info(f"Markdown size: {len(markdown_text)} characters")
    logger.info(f"Compression ratio: {len(markdown_text) / len(json_str):.2%}")
    
    # Check information preservation
    json_candidates = len(json_data.get("candidate_movies", []))
    markdown_candidate_count = markdown_text.count("###")
    
    logger.info(f"\nCandidate information:")
    logger.info(f"  JSON: {json_candidates} movies with full metadata")
    logger.info(f"  Markdown: {markdown_candidate_count} movies with summaries")
    
    # Check score preservation
    has_scores_json = all(
        "similarity_score" in m
        for m in json_data.get("candidate_movies", [])[:5]
    )
    has_scores_markdown = "Match Score" in markdown_text
    
    logger.info(f"\nSimilarity scores:")
    logger.info(f"  JSON: {'Present' if has_scores_json else 'Missing'} (quantitative)")
    logger.info(f"  Markdown: {'Present' if has_scores_markdown else 'Missing'} (in text)")


def main() -> int:
    """Main test function.
    
    Returns:
        Exit code.
    """
    print_separator("Content Analyzer Agent Test")
    
    # Connect to database
    try:
        settings = get_settings()
        client = MongoDBClient(settings)
        service = MflixService(client)
        logger.info("✓ Connected to MongoDB Atlas")
    except Exception as e:
        logger.error(f"✗ Failed to connect: {str(e)}")
        return 1
    
    # Find a user with comments
    logger.info("\nFinding users with viewing history...")
    users = service.list_users(limit=10)
    
    test_user_email = None
    for user in users:
        comments = service.get_comments_by_user(user.email, limit=1)
        if comments:
            test_user_email = user.email
            logger.info(f"✓ Found user with history: {user.name} ({user.email})")
            break
    
    if not test_user_email:
        logger.warning("No users with comments found. Using first user.")
        test_user_email = users[0].email if users else None
    
    if not test_user_email:
        logger.error("✗ No users found in database")
        return 1
    
    # Create agents
    json_profiler = UserProfilerAgent(service, ContextFormat.JSON)
    json_analyzer = ContentAnalyzerAgent(service, ContextFormat.JSON, max_candidates=20)
    
    markdown_profiler = UserProfilerAgent(service, ContextFormat.MARKDOWN)
    markdown_analyzer = ContentAnalyzerAgent(service, ContextFormat.MARKDOWN, max_candidates=20)
    
    # Test JSON pipeline
    json_analysis = test_content_analyzer_json(
        json_profiler, json_analyzer, test_user_email
    )
    
    if not json_analysis:
        logger.error("\n✗ JSON pipeline test failed")
        return 1
    
    # Test Markdown pipeline
    markdown_analysis = test_content_analyzer_markdown(
        markdown_profiler, markdown_analyzer, test_user_email
    )
    
    if not markdown_analysis:
        logger.error("\n✗ Markdown pipeline test failed")
        return 1
    
    # Compare outputs
    compare_pipeline_outputs(json_analysis, markdown_analysis)
    
    # Summary
    print_separator("Test Summary")
    logger.info("✓ All Content Analyzer tests passed!")
    logger.info("✓ JSON format: Successfully found and scored candidates")
    logger.info("✓ Markdown format: Successfully generated readable analysis")
    logger.info("✓ Pipeline: User Profiler → Content Analyzer working end-to-end")
    logger.info("\nNext step: Add Recommender Agent to rank and filter candidates")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

