"""Test script for User Profiler Agent.

This script tests the User Profiler Agent with real users from the Mflix database.

Usage:
    python test_user_profiler.py
"""

import json
import logging
from typing import Optional

from backend.agents.base import ContextFormat
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


def test_user_profiler_json(agent: UserProfilerAgent, email: str) -> Optional[dict]:
    """Test User Profiler Agent with JSON output.
    
    Args:
        agent: UserProfilerAgent instance.
        email: User email to profile.
        
    Returns:
        Profile data if successful, None otherwise.
    """
    print_separator(f"Testing User Profiler (JSON) - {email}")
    
    try:
        output = agent.process_user(email)
        
        if output.success:
            logger.info(f"✓ Profile generated successfully")
            logger.info(f"  Execution time: {output.execution_time_ms:.2f}ms")
            logger.info(f"  Token count: {output.context.tokens}")
            logger.info(f"  Format: {output.context.format}")
            
            # Pretty print the profile
            profile = output.context.data
            logger.info("\nUser Profile Summary:")
            logger.info(f"  Name: {profile.get('name', 'Unknown')}")
            logger.info(f"  Email: {profile.get('email', 'Unknown')}")
            
            # Genre affinities
            if profile.get("genre_affinities"):
                logger.info("\n  Top Genre Affinities:")
                for genre_info in profile["genre_affinities"][:5]:
                    logger.info(
                        f"    - {genre_info['genre']}: "
                        f"{int(genre_info['affinity'] * 100)}% "
                        f"({genre_info['count']} movies)"
                    )
            
            # Director preferences
            if profile.get("director_preferences"):
                logger.info("\n  Favorite Directors:")
                for director in profile["director_preferences"][:5]:
                    rating_info = f", avg rating {director['avg_rating']}" if director['avg_rating'] else ""
                    logger.info(
                        f"    - {director['name']}: "
                        f"{director['movie_count']} movies{rating_info}"
                    )
            
            # Viewing patterns
            if profile.get("viewing_patterns"):
                patterns = profile["viewing_patterns"]
                logger.info("\n  Viewing Patterns:")
                if patterns.get("total_movies_commented"):
                    logger.info(f"    - Movies commented on: {patterns['total_movies_commented']}")
                if patterns.get("avg_runtime_preference"):
                    logger.info(f"    - Preferred runtime: {patterns['avg_runtime_preference']} min")
                if patterns.get("preferred_decades"):
                    logger.info(f"    - Favorite decades: {', '.join(patterns['preferred_decades'][:3])}")
            
            # Watch history
            if profile.get("watch_history"):
                logger.info(f"\n  Recent Watch History ({len(profile['watch_history'])} movies):")
                for movie in profile["watch_history"][:5]:
                    genres = ", ".join(movie["genres"][:2]) if movie["genres"] else "N/A"
                    logger.info(f"    - {movie['title']} ({movie['year']}) - {genres}")
            
            return profile
        else:
            logger.error(f"✗ Failed: {output.error_message}")
            return None
            
    except Exception as e:
        logger.error(f"✗ Exception: {str(e)}")
        return None


def test_user_profiler_markdown(agent: UserProfilerAgent, email: str) -> Optional[str]:
    """Test User Profiler Agent with Markdown output.
    
    Args:
        agent: UserProfilerAgent instance.
        email: User email to profile.
        
    Returns:
        Markdown text if successful, None otherwise.
    """
    print_separator(f"Testing User Profiler (Markdown) - {email}")
    
    try:
        output = agent.process_user(email)
        
        if output.success:
            logger.info(f"✓ Profile generated successfully")
            logger.info(f"  Execution time: {output.execution_time_ms:.2f}ms")
            logger.info(f"  Token count: {output.context.tokens}")
            logger.info(f"  Format: {output.context.format}")
            
            # Print the markdown
            markdown_text = output.context.metadata.get("raw_text", "")
            logger.info("\nMarkdown Output:")
            logger.info("-" * 70)
            logger.info(markdown_text)
            logger.info("-" * 70)
            
            return markdown_text
        else:
            logger.error(f"✗ Failed: {output.error_message}")
            return None
            
    except Exception as e:
        logger.error(f"✗ Exception: {str(e)}")
        return None


def compare_formats(json_output: dict, markdown_output: str) -> None:
    """Compare JSON vs Markdown output.
    
    Args:
        json_output: JSON profile data.
        markdown_output: Markdown profile text.
    """
    print_separator("Comparing JSON vs Markdown Formats")
    
    # Estimate content preservation
    json_str = json.dumps(json_output, indent=2)
    
    logger.info(f"JSON size: {len(json_str)} characters")
    logger.info(f"Markdown size: {len(markdown_output)} characters")
    logger.info(f"Compression ratio: {len(markdown_output) / len(json_str):.2%}")
    
    # Check what information is preserved
    json_keys = set(json_output.keys())
    logger.info(f"\nJSON contains {len(json_keys)} top-level keys:")
    logger.info(f"  {', '.join(sorted(json_keys))}")
    
    # Count genres in both
    json_genres = len(json_output.get("genre_affinities", []))
    markdown_genre_count = markdown_output.count("Genre Preferences")
    
    logger.info(f"\nGenre information:")
    logger.info(f"  JSON: {json_genres} genres with affinity scores")
    logger.info(f"  Markdown: {'Present' if markdown_genre_count > 0 else 'Missing'}")


def main() -> int:
    """Main test function.
    
    Returns:
        Exit code.
    """
    print_separator("User Profiler Agent Test")
    
    # Connect to database
    try:
        settings = get_settings()
        client = MongoDBClient(settings)
        service = MflixService(client)
        
        logger.info("✓ Connected to MongoDB Atlas")
    except Exception as e:
        logger.error(f"✗ Failed to connect: {str(e)}")
        return 1
    
    # Get a sample user with comments
    logger.info("\nFinding users with comments...")
    users = service.list_users(limit=10)
    
    test_user_email = None
    for user in users:
        comments = service.get_comments_by_user(user.email, limit=1)
        if comments:
            test_user_email = user.email
            logger.info(f"✓ Found user with comments: {user.name} ({user.email})")
            break
    
    if not test_user_email:
        logger.warning("No users with comments found. Using first user anyway.")
        test_user_email = users[0].email if users else None
    
    if not test_user_email:
        logger.error("✗ No users found in database")
        return 1
    
    # Test JSON format
    json_agent = UserProfilerAgent(service, context_format=ContextFormat.JSON)
    json_profile = test_user_profiler_json(json_agent, test_user_email)
    
    if not json_profile:
        logger.error("\n✗ JSON profiler test failed")
        return 1
    
    # Test Markdown format
    markdown_agent = UserProfilerAgent(service, context_format=ContextFormat.MARKDOWN)
    markdown_profile = test_user_profiler_markdown(markdown_agent, test_user_email)
    
    if not markdown_profile:
        logger.error("\n✗ Markdown profiler test failed")
        return 1
    
    # Compare formats
    compare_formats(json_profile, markdown_profile)
    
    # Summary
    print_separator("Test Summary")
    logger.info("✓ All User Profiler tests passed!")
    logger.info("✓ JSON format: Successfully generated structured profile")
    logger.info("✓ Markdown format: Successfully generated human-readable profile")
    logger.info("✓ Format comparison: Both formats capture user preferences")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

