"""Context Quality Evaluation Demo - Comparing JSON vs Markdown Format.

This demonstrates ContextScope's core value proposition:
Different context formats lead to different information preservation quality.

Usage:
    python demo_context_evaluation.py [email]
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timezone

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

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
from backend.evaluator.judge import judge_handoff_via_fireworks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_header(title: str, char: str = "=") -> None:
    """Print a formatted header."""
    logger.info("\n" + char * 70)
    logger.info(f"  {title}")
    logger.info(char * 70)


def evaluate_pipeline(
    user_email: str, 
    service: MflixService, 
    format_type: ContextFormat,
    format_name: str
) -> Dict:
    """Run pipeline with specific context format and evaluate handoffs.
    
    Args:
        user_email: User email for recommendations.
        service: Mflix service instance.
        format_type: ContextFormat (JSON or MARKDOWN).
        format_name: Human-readable format name for logging.
        
    Returns:
        Dictionary with pipeline results and evaluations.
    """
    print_header(f"PIPELINE: {format_name} FORMAT", char="-")
    
    start_time = time.time()
    
    # Initialize agents with specified format
    profiler = UserProfilerAgent(service, format_type)
    analyzer = ContentAnalyzerAgent(service, format_type, max_candidates=30)
    recommender = RecommenderAgent(format_type, top_n=5)
    explainer = ExplainerAgent(format_type)
    
    # Step 1: User Profiler
    logger.info(f"\n[{format_name}] Step 1: User Profiler...")
    profile_output = profiler.process_user(user_email)
    if not profile_output.success:
        raise Exception(f"User profiling failed: {profile_output.error_message}")
    logger.info(f"  ✓ Complete ({profile_output.context.tokens} tokens)")
    
    # Step 2: Content Analyzer
    logger.info(f"[{format_name}] Step 2: Content Analyzer...")
    analysis_output = analyzer.process(profile_output.context)
    if not analysis_output.success:
        raise Exception(f"Analysis failed: {analysis_output.error_message}")
    logger.info(f"  ✓ Complete ({analysis_output.context.tokens} tokens)")
    
    # Step 3: Recommender
    logger.info(f"[{format_name}] Step 3: Recommender...")
    recommendation_output = recommender.process(analysis_output.context)
    if not recommendation_output.success:
        raise Exception(f"Recommendation failed: {recommendation_output.error_message}")
    logger.info(f"  ✓ Complete ({recommendation_output.context.tokens} tokens)")
    
    # Step 4: Explainer
    logger.info(f"[{format_name}] Step 4: Explainer...")
    explanation_output = explainer.process(recommendation_output.context)
    if not explanation_output.success:
        raise Exception(f"Explanation failed: {explanation_output.error_message}")
    logger.info(f"  ✓ Complete ({explanation_output.context.tokens} tokens)")
    
    # Now evaluate each handoff
    print_header(f"EVALUATING {format_name} HANDOFFS", char="-")
    
    evaluations = []
    
    # Helper function to get formatted context string
    def get_formatted_context(context) -> str:
        """Get the formatted context string based on format type."""
        return context.to_string()
    
    # Handoff 1: User Profiler → Content Analyzer
    logger.info(f"\n[{format_name}] Evaluating: User Profiler → Content Analyzer...")

    eval_1 = judge_handoff_via_fireworks(
        context_sent=get_formatted_context(profile_output.context),
        context_received=get_formatted_context(analysis_output.context),
        temperature=0.0,
        max_tokens=1024
    )

    time.sleep(2)

    if eval_1:
        eval_1_record = {
            "from": "User Profiler",
            "to": "Content Analyzer",
            "tokens_sent": profile_output.context.tokens,
            "tokens_received": analysis_output.context.tokens,
            **eval_1
        }
        evaluations.append(eval_1_record)
        logger.info(f"  Fidelity: {eval_1.get('fidelity', 'N/A')}")
        logger.info(f"  Drift: {eval_1.get('drift', 'N/A')}")
        logger.info(f"  Preserved: {len(eval_1.get('preserved', []))} key facts")

    # Handoff 2: Content Analyzer → Recommender
    logger.info(f"\n[{format_name}] Evaluating: Content Analyzer → Recommender...")

    eval_2 = judge_handoff_via_fireworks(
        context_sent=get_formatted_context(analysis_output.context),
        context_received=get_formatted_context(recommendation_output.context),
        temperature=0.0,
        max_tokens=1024
    )
    time.sleep(2)

    if eval_2:
        eval_2_record = {
            "from": "Content Analyzer",
            "to": "Recommender",
            "tokens_sent": analysis_output.context.tokens,
            "tokens_received": recommendation_output.context.tokens,
            **eval_2
        }
        evaluations.append(eval_2_record)
        logger.info(f"  Fidelity: {eval_2.get('fidelity', 'N/A')}")
        logger.info(f"  Drift: {eval_2.get('drift', 'N/A')}")
        logger.info(f"  Preserved: {len(eval_2.get('preserved', []))} key facts")

    # Handoff 3: Recommender → Explainer
    logger.info(f"\n[{format_name}] Evaluating: Recommender → Explainer...")

    eval_3 = judge_handoff_via_fireworks(
        context_sent=get_formatted_context(recommendation_output.context),
        context_received=get_formatted_context(explanation_output.context),
        temperature=0.0,
        max_tokens=1024
    )
    time.sleep(2)

    if eval_3:
        eval_3_record = {
            "from": "Recommender",
            "to": "Explainer",
            "tokens_sent": recommendation_output.context.tokens,
            "tokens_received": explanation_output.context.tokens,
            **eval_3
        }
        evaluations.append(eval_3_record)
        logger.info(f"  Fidelity: {eval_3.get('fidelity', 'N/A')}")
        logger.info(f"  Drift: {eval_3.get('drift', 'N/A')}")
        logger.info(f"  Preserved: {len(eval_3.get('preserved', []))} key facts")
    
    # Calculate aggregate metrics
    if evaluations:
        fidelities = [e.get('fidelity') for e in evaluations if e.get('fidelity') is not None]
        drifts = [e.get('drift') for e in evaluations if e.get('drift') is not None]
        
        avg_fidelity = sum(fidelities) / len(fidelities) if fidelities else 0
        avg_drift = sum(drifts) / len(drifts) if drifts else 0
        
        # End-to-end quality: fidelity weighted by inverse drift
        e2e_quality = avg_fidelity * (1 - avg_drift) if (avg_fidelity and avg_drift is not None) else avg_fidelity
    else:
        avg_fidelity = 0
        avg_drift = 0
        e2e_quality = 0
    
    total_time = time.time() - start_time
    
    return {
        "format": format_name,
        "format_type": format_type.value,
        "user_email": user_email,
        "handoffs": evaluations,
        "summary": {
            "avg_fidelity": round(avg_fidelity, 3),
            "avg_drift": round(avg_drift, 3),
            "end_to_end_quality": round(e2e_quality, 3),
            "total_execution_time_sec": round(total_time, 2),
        },
        "final_recommendations": [
            {
                "rank": r["rank"],
                "title": r["title"],
                "year": r["year"],
                "explanation": r["explanation"]
            }
            for r in explanation_output.context.data.get("recommendations_with_explanations", [])
        ]
    }


def generate_comparison_report(json_results: Dict, markdown_results: Dict) -> None:
    """Generate and display comparison report.
    
    Args:
        json_results: Results from JSON pipeline.
        markdown_results: Results from Markdown pipeline.
    """
    print_header("CONTEXT FORMAT COMPARISON REPORT")
    
    json_summary = json_results["summary"]
    md_summary = markdown_results["summary"]
    
    logger.info("\n" + "=" * 70)
    logger.info("AGGREGATE METRICS COMPARISON")
    logger.info("=" * 70)
    
    logger.info(f"\n{'Metric':<30} {'JSON':<15} {'Markdown':<15} {'Difference':<15}")
    logger.info("-" * 70)
    
    # Fidelity
    fidelity_diff = json_summary["avg_fidelity"] - md_summary["avg_fidelity"]
    logger.info(
        f"{'Average Fidelity':<30} "
        f"{json_summary['avg_fidelity']:<15.3f} "
        f"{md_summary['avg_fidelity']:<15.3f} "
        f"{fidelity_diff:+.3f}"
    )
    
    # Drift
    drift_diff = json_summary["avg_drift"] - md_summary["avg_drift"]
    logger.info(
        f"{'Average Drift':<30} "
        f"{json_summary['avg_drift']:<15.3f} "
        f"{md_summary['avg_drift']:<15.3f} "
        f"{drift_diff:+.3f}"
    )
    
    # End-to-end quality
    quality_diff = json_summary["end_to_end_quality"] - md_summary["end_to_end_quality"]
    logger.info(
        f"{'End-to-End Quality':<30} "
        f"{json_summary['end_to_end_quality']:<15.3f} "
        f"{md_summary['end_to_end_quality']:<15.3f} "
        f"{quality_diff:+.3f}"
    )
    
    logger.info("-" * 70)
    
    # Token efficiency comparison
    logger.info("\n" + "=" * 70)
    logger.info("TOKEN EFFICIENCY COMPARISON")
    logger.info("=" * 70)
    
    # Calculate total tokens for each pipeline
    json_total_tokens = sum(h["tokens_sent"] for h in json_results["handoffs"])
    md_total_tokens = sum(h["tokens_sent"] for h in markdown_results["handoffs"])
    token_savings = ((json_total_tokens - md_total_tokens) / json_total_tokens) * 100
    
    logger.info(f"\n{'Stage':<30} {'JSON Tokens':<15} {'Markdown Tokens':<15} {'Savings':<15}")
    logger.info("-" * 70)
    
    for json_h, md_h in zip(json_results["handoffs"], markdown_results["handoffs"]):
        stage = f"{json_h['from']} →"
        json_tokens = json_h["tokens_sent"]
        md_tokens = md_h["tokens_sent"]
        savings = ((json_tokens - md_tokens) / json_tokens * 100) if json_tokens > 0 else 0
        
        logger.info(
            f"{stage:<30} "
            f"{json_tokens:<15} "
            f"{md_tokens:<15} "
            f"{savings:>6.1f}%"
        )
    
    logger.info("-" * 70)
    logger.info(
        f"{'TOTAL':<30} "
        f"{json_total_tokens:<15} "
        f"{md_total_tokens:<15} "
        f"{token_savings:>6.1f}%"
    )
    
    # Cost estimation (assuming ~$0.50 per 1M tokens for input)
    cost_per_million = 0.50
    json_cost = (json_total_tokens / 1_000_000) * cost_per_million
    md_cost = (md_total_tokens / 1_000_000) * cost_per_million
    cost_savings = json_cost - md_cost
    
    logger.info(f"\n{'Estimated Cost Comparison:':<30}")
    logger.info(f"  JSON format:     ${json_cost:.4f}")
    logger.info(f"  Markdown format: ${md_cost:.4f}")
    logger.info(f"  Cost savings:    ${cost_savings:.4f} ({token_savings:.1f}%)")
    
    # Efficiency score: quality per token
    json_efficiency = json_summary["end_to_end_quality"] / (json_total_tokens / 1000)
    md_efficiency = md_summary["end_to_end_quality"] / (md_total_tokens / 1000)
    
    logger.info(f"\n{'Efficiency (Quality/1K tokens):':<30}")
    logger.info(f"  JSON format:     {json_efficiency:.3f}")
    logger.info(f"  Markdown format: {md_efficiency:.3f}")
    logger.info(f"  Improvement:     {((md_efficiency / json_efficiency - 1) * 100):+.1f}%")
    
    # Per-handoff comparison
    logger.info("\n" + "=" * 70)
    logger.info("PER-HANDOFF FIDELITY COMPARISON")
    logger.info("=" * 70)
    
    for i, (json_handoff, md_handoff) in enumerate(zip(json_results["handoffs"], markdown_results["handoffs"])):
        handoff_name = f"{json_handoff['from']} → {json_handoff['to']}"
        json_fid = json_handoff.get('fidelity', 0)
        md_fid = md_handoff.get('fidelity', 0)
        diff = json_fid - md_fid
        
        logger.info(f"\n{handoff_name}")
        logger.info(f"  JSON:     Fidelity={json_fid:.3f}, Drift={json_handoff.get('drift', 0):.3f}, Tokens={json_handoff['tokens_sent']}")
        logger.info (f"  Markdown: Fidelity={md_fid:.3f}, Drift={md_handoff.get('drift', 0):.3f}, Tokens={md_handoff['tokens_sent']}")
        logger.info(f"  Difference: Fidelity={diff:+.3f}, Token savings={((json_handoff['tokens_sent'] - md_handoff['tokens_sent']) / json_handoff['tokens_sent'] * 100):.1f}%")
    
    # Key insights
    print_header("KEY INSIGHTS")
    
    if token_savings > 50:
        logger.info(f"\n🎯 EFFICIENCY WINNER: Markdown saves {token_savings:.1f}% tokens!")
    
    if quality_diff > 0.1:
        logger.info(f"🎯 QUALITY WINNER: JSON preserves {quality_diff*100:.1f}% more information")
    elif quality_diff < -0.1:
        logger.info(f"🎯 QUALITY WINNER: Markdown preserves {abs(quality_diff)*100:.1f}% more information")
    else:
        logger.info(f"⚖️  Quality is similar (within 10% difference)")
    
    if md_efficiency > json_efficiency * 1.5:
        logger.info(f"⚡ Markdown is {((md_efficiency / json_efficiency - 1) * 100):.0f}% more efficient (quality per token)")
    elif json_efficiency > md_efficiency * 1.5:
        logger.info(f"⚡ JSON is {((json_efficiency / md_efficiency - 1) * 100):.0f}% more efficient (quality per token)")
    
    # The real value proposition
    logger.info(f"\n💡 VALUE PROPOSITION:")
    if token_savings > 30 and abs(quality_diff) < 0.15:
        logger.info(f"   Markdown achieves similar quality with {token_savings:.0f}% fewer tokens")
        logger.info(f"   This translates to {token_savings:.0f}% lower costs and faster processing")
    elif quality_diff > 0.15:
        logger.info(f"   JSON provides {quality_diff*100:.0f}% better information preservation")
        logger.info(f"   Trade-off: {token_savings:.0f}% higher token usage")
    
    # Recommendation quality comparison
    logger.info(f"\n" + "=" * 70)
    logger.info("FINAL RECOMMENDATIONS COMPARISON")
    logger.info("=" * 70)
    
    logger.info("\nJSON Pipeline Recommendations:")
    for rec in json_results["final_recommendations"][:3]:
        logger.info(f"  {rec['rank']}. {rec['title']} ({rec['year']})")
    
    logger.info("\nMarkdown Pipeline Recommendations:")
    for rec in markdown_results["final_recommendations"][:3]:
        logger.info(f"  {rec['rank']}. {rec['title']} ({rec['year']})")
    
    # Check overlap
    json_titles = {r["title"] for r in json_results["final_recommendations"]}
    md_titles = {r["title"] for r in markdown_results["final_recommendations"]}
    overlap = len(json_titles & md_titles)
    
    logger.info(f"\nRecommendation Overlap: {overlap}/5 movies")
    if overlap >= 4:
        logger.info("✓ High overlap - both formats produce similar recommendations")
    elif overlap < 3:
        logger.info("⚠ Low overlap suggests format significantly affects recommendations")


def save_results_to_mongodb(
    json_results: Dict, 
    markdown_results: Dict, 
    client: MongoDBClient
) -> str:
    """Save evaluation results to MongoDB.
    
    Args:
        json_results: JSON pipeline results.
        markdown_results: Markdown pipeline results.
        client: MongoDB client instance.
        
    Returns:
        Inserted document ID as string.
    """
    # Calculate comparison metrics
    json_total_tokens = sum(h["tokens_sent"] for h in json_results["handoffs"])
    md_total_tokens = sum(h["tokens_sent"] for h in markdown_results["handoffs"])
    token_savings_pct = ((json_total_tokens - md_total_tokens) / json_total_tokens * 100) if json_total_tokens > 0 else 0
    
    cost_per_million = 0.50
    json_cost = (json_total_tokens / 1_000_000) * cost_per_million
    md_cost = (md_total_tokens / 1_000_000) * cost_per_million
    
    # Prepare document
    document = {
        "evaluation_timestamp": datetime.now(timezone.utc),  # Fixed deprecation warning
        "user_email": json_results["user_email"],
        "json_pipeline": json_results,
        "markdown_pipeline": markdown_results,
        "comparison": {
            "fidelity_improvement": json_results["summary"]["avg_fidelity"] - markdown_results["summary"]["avg_fidelity"],
            "drift_difference": json_results["summary"]["avg_drift"] - markdown_results["summary"]["avg_drift"],
            "quality_improvement": json_results["summary"]["end_to_end_quality"] - markdown_results["summary"]["end_to_end_quality"],
            "token_savings_percent": round(token_savings_pct, 2),
            "token_savings_absolute": json_total_tokens - md_total_tokens,
            "cost_savings_dollars": round(json_cost - md_cost, 6),
            "json_efficiency": round(json_results["summary"]["end_to_end_quality"] / (json_total_tokens / 1000), 3),
            "markdown_efficiency": round(markdown_results["summary"]["end_to_end_quality"] / (md_total_tokens / 1000), 3),
        },
        "metadata": {
            "evaluation_version": "1.0.0",
            "max_candidates": 30,
            "top_n_recommendations": 5,
        }
    }
    
    # Insert into MongoDB - Fixed the database access
    try:
        # Use the database property directly
        db = client.database
        collection = db["full_results"]
        result = collection.insert_one(document)
        
        logger.info(f"\n✓ Results saved to MongoDB collection 'full_results'")
        logger.info(f"  Document ID: {result.inserted_id}")
        
        return str(result.inserted_id)
        
    except Exception as e:
        logger.error(f"✗ Failed to save to MongoDB: {e}")
        raise


def main() -> int:
    """Main entry point."""
    print_header("CONTEXTSCOPE EVAL - CONTEXT QUALITY EVALUATION DEMO")
    
    # Get user email
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
    
    # Find a user if not specified
    if not user_email:
        logger.info("\nFinding user with viewing history...")
        users = service.list_users(limit=10)
        
        for user in users:
            comments = service.get_comments_by_user(user.email, limit=1)
            if comments:
                user_email = user.email
                logger.info(f"✓ Using user: {user.name} ({user.email})")
                break
        
        if not user_email and users:
            user_email = users[0].email
    
    if not user_email:
        logger.error("✗ No users found")
        return 1
    
    try:
        # Run JSON pipeline
        print_header("RUNNING JSON FORMAT PIPELINE")
        json_results = evaluate_pipeline(user_email, service, ContextFormat.JSON, "JSON")
        
        # Run Markdown pipeline
        print_header("RUNNING MARKDOWN FORMAT PIPELINE")
        markdown_results = evaluate_pipeline(user_email, service, ContextFormat.MARKDOWN, "Markdown")
        
        # Generate comparison report
        generate_comparison_report(json_results, markdown_results)
        
        # Save results to MongoDB
        doc_id = save_results_to_mongodb(json_results, markdown_results, client)
        
        print_header("EVALUATION COMPLETE")
        logger.info("\n✓ Context quality evaluation successful!")
        logger.info(f"✓ Results stored in MongoDB (ID: {doc_id})")
        logger.info("✓ Ready for demo video recording")
        
        return 0
        
    except Exception as e:
        logger.error(f"✗ Evaluation failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())