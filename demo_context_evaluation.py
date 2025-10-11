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
    # Helper function to get formatted context string
    def get_formatted_context(context) -> str:
        """Get the formatted context string based on format type."""
        return context.to_string()
    
    # Handoff 1: User Profiler → Content Analyzer
    logger.info(f"\n[{format_name}] Evaluating: User Profiler → Content Analyzer...")
    
    context_sent_1 = get_formatted_context(profile_output.context)
    context_received_1 = get_formatted_context(analysis_output.context)
    
    eval_1 = judge_handoff_via_fireworks(
        context_sent=context_sent_1,
        context_received=context_received_1,
        temperature=0.0,
        max_tokens=384
    )
    
    # Handoff 1: User Profiler → Content Analyzer
    logger.info(f"\n[{format_name}] Evaluating: User Profiler → Content Analyzer...")
    
    context_sent_1 = get_formatted_context(profile_output.context)
    context_received_1 = get_formatted_context(analysis_output.context)
    
    eval_1 = judge_handoff_via_fireworks(
        context_sent=context_sent_1,
        context_received=context_received_1,
        temperature=0.0,
        max_tokens=384
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
    
    context_sent_2 = get_formatted_context(analysis_output.context)
    context_received_2 = get_formatted_context(recommendation_output.context)
    
    eval_2 = judge_handoff_via_fireworks(
        context_sent=context_sent_2,
        context_received=context_received_2,
        temperature=0.0,
        max_tokens=384
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
    
    context_sent_3 = get_formatted_context(recommendation_output.context)
    context_received_3 = get_formatted_context(explanation_output.context)
    
    eval_3 = judge_handoff_via_fireworks(
        context_sent=context_sent_3,
        context_received=context_received_3,
        temperature=0.0,
        max_tokens=384
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
        logger.info(f"  JSON Fidelity:     {json_fid:.3f}")
        logger.info(f"  Markdown Fidelity: {md_fid:.3f}")
        logger.info(f"  Difference:        {diff:+.3f}")
    
    # Key insights
    print_header("KEY INSIGHTS")
    
    if quality_diff > 0.1:
        logger.info(f"\n✓ JSON format preserves {quality_diff*100:.1f}% more information end-to-end")
    elif quality_diff < -0.1:
        logger.info(f"\n⚠ Markdown format preserves {abs(quality_diff)*100:.1f}% more information end-to-end")
    else:
        logger.info(f"\n≈ Both formats perform similarly (within 10% difference)")
    
    if fidelity_diff > 0.15:
        logger.info(f"✓ JSON shows significantly better fidelity ({fidelity_diff*100:.1f}% higher)")
    
    if drift_diff < -0.15:
        logger.info(f"⚠ JSON shows higher drift ({abs(drift_diff)*100:.1f}% more semantic deviation)")
    
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
    if overlap < 3:
        logger.info("⚠ Low overlap suggests format affects recommendation quality")


def save_results(json_results: Dict, markdown_results: Dict, output_file: str = "reports/context_evaluation.json") -> None:
    """Save evaluation results to file.
    
    Args:
        json_results: JSON pipeline results.
        markdown_results: Markdown pipeline results.
        output_file: Output file path.
    """
    # Ensure reports directory exists
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    combined = {
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "json_pipeline": json_results,
        "markdown_pipeline": markdown_results,
        "comparison": {
            "fidelity_improvement": json_results["summary"]["avg_fidelity"] - markdown_results["summary"]["avg_fidelity"],
            "drift_difference": json_results["summary"]["avg_drift"] - markdown_results["summary"]["avg_drift"],  # Fixed typo
            "quality_improvement": json_results["summary"]["end_to_end_quality"] - markdown_results["summary"]["end_to_end_quality"],
        }
    }
    
    with open(output_file, "w") as f:
        json.dump(combined, f, indent=2)
    
    logger.info(f"\n✓ Results saved to {output_file}")

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
        
        # Save results
        save_results(json_results, markdown_results)
        
        print_header("EVALUATION COMPLETE")
        logger.info("\n✓ Context quality evaluation successful!")
        logger.info("✓ Ready for demo video recording")
        
        return 0
        
    except Exception as e:
        logger.error(f"✗ Evaluation failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())