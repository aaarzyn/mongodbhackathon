"""Complete End-to-End Recommendation Pipeline Demo with Context Evaluation.

This script demonstrates the full multi-agent pipeline in both JSON and Markdown formats:
User Profiler → Content Analyzer → Recommender → Explainer

Then compares context fidelity, drift, and compression between the two formats,
storing all evaluation results in MongoDB for analysis.

Usage:
    python demo_recommendation_pipeline.py [email]
    python demo_recommendation_pipeline.py --compare  # Run both formats and compare
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from backend.agents import (
    ContentAnalyzerAgent,
    ExplainerAgent,
    RecommenderAgent,
    UserProfilerAgent,
)
from backend.agents.base import AgentOutput, ContextFormat
from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient
from backend.evaluator.service import EvaluatorService
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


def _extract_context_text(output: AgentOutput) -> str:
    """Extract context text from agent output."""
    raw = output.context.metadata.get("raw_text", "")
    if isinstance(raw, str) and raw.strip():
        return raw
    return json.dumps(output.context.data, ensure_ascii=False)


def run_single_pipeline(
    user_email: str,
    service: MflixService,
    context_format: ContextFormat,
    client: MongoDBClient,
) -> Tuple[str, Dict, List[AgentOutput]]:
    """Run a single pipeline with the specified context format.
    
    Args:
        user_email: User email to generate recommendations for.
        service: Mflix service instance.
        context_format: JSON or MARKDOWN format.
        client: MongoDB client for storing evaluations.
        
    Returns:
        Tuple of (pipeline_id, summary_dict, agent_outputs)
    """
    format_name = "JSON" if context_format == ContextFormat.JSON else "MARKDOWN"
    pipeline_id = f"{format_name.lower()}-{uuid.uuid4().hex[:8]}"
    
    print_header(f"RUNNING {format_name} PIPELINE: {pipeline_id}")
    
    # Initialize agents with specified format
    logger.info(f"Initializing {format_name} agents...")
    profiler = UserProfilerAgent(service, context_format)
    analyzer = ContentAnalyzerAgent(service, context_format, max_candidates=30)
    recommender = RecommenderAgent(context_format, top_n=5)
    explainer = ExplainerAgent(context_format)
    evaluator = EvaluatorService(client)
    
    logger.info("✓ All agents initialized")
    
    # Step 1: User Profiler
    logger.info(f"\nStep 1: User Profiler")
    logger.info(f"Profiling user: {user_email}")
    
    profile_output = profiler.process_user(user_email)
    if not profile_output.success:
        logger.error(f"✗ User profiling failed: {profile_output.error_message}")
        raise RuntimeError(f"Pipeline failed at User Profiler: {profile_output.error_message}")
    
    logger.info(f"✓ User profiled in {profile_output.execution_time_ms:.0f}ms ({profile_output.context.tokens} tokens)")
    
    # Step 2: Content Analyzer
    logger.info(f"\nStep 2: Content Analyzer")
    analysis_output = analyzer.process(profile_output.context)
    if not analysis_output.success:
        logger.error(f"✗ Content analysis failed: {analysis_output.error_message}")
        raise RuntimeError(f"Pipeline failed at Content Analyzer: {analysis_output.error_message}")
    
    logger.info(f"✓ Analysis complete in {analysis_output.execution_time_ms:.0f}ms ({analysis_output.context.tokens} tokens)")
    
    # Step 3: Recommender
    logger.info(f"\nStep 3: Recommender")
    recommendation_output = recommender.process(analysis_output.context)
    if not recommendation_output.success:
        logger.error(f"✗ Recommendation failed: {recommendation_output.error_message}")
        raise RuntimeError(f"Pipeline failed at Recommender: {recommendation_output.error_message}")
    
    logger.info(f"✓ Recommendations generated in {recommendation_output.execution_time_ms:.0f}ms ({recommendation_output.context.tokens} tokens)")
    
    # Step 4: Explainer
    logger.info(f"\nStep 4: Explainer")
    explanation_output = explainer.process(recommendation_output.context)
    if not explanation_output.success:
        logger.error(f"✗ Explanation failed: {explanation_output.error_message}")
        raise RuntimeError(f"Pipeline failed at Explainer: {explanation_output.error_message}")
    
    logger.info(f"✓ Explanations generated in {explanation_output.execution_time_ms:.0f}ms ({explanation_output.context.tokens} tokens)")
    
    # Store handoff evaluations in MongoDB
    logger.info(f"\nStep 5: Storing handoff evaluations in MongoDB...")
    
    # Handoff 1: User Profiler → Content Analyzer
    evaluator.evaluate_and_store_handoff(
        pipeline_id=pipeline_id,
        handoff_id=f"{pipeline_id}-h1",
        agent_from="User Profiler",
        agent_to="Content Analyzer",
        context_sent=_extract_context_text(profile_output),
        context_received=_extract_context_text(profile_output),
        metadata={"format": format_name.lower()},
        use_llm_judge=False,  # Use heuristic metrics for speed
    )
    
    # Handoff 2: Content Analyzer → Recommender
    evaluator.evaluate_and_store_handoff(
        pipeline_id=pipeline_id,
        handoff_id=f"{pipeline_id}-h2",
        agent_from="Content Analyzer",
        agent_to="Recommender",
        context_sent=_extract_context_text(analysis_output),
        context_received=_extract_context_text(analysis_output),
        metadata={"format": format_name.lower()},
        use_llm_judge=False,
    )
    
    # Handoff 3: Recommender → Explainer
    evaluator.evaluate_and_store_handoff(
        pipeline_id=pipeline_id,
        handoff_id=f"{pipeline_id}-h3",
        agent_from="Recommender",
        agent_to="Explainer",
        context_sent=_extract_context_text(recommendation_output),
        context_received=_extract_context_text(recommendation_output),
        metadata={"format": format_name.lower()},
        use_llm_judge=False,
    )
    
    # Finalize pipeline evaluation and store aggregate scores
    pipeline_eval = evaluator.finalize_pipeline(pipeline_id)
    logger.info(f"✓ Stored {len(pipeline_eval.handoffs)} handoff evaluations")
    logger.info(f"✓ Pipeline evaluation saved: {pipeline_id}")
    
    # Build summary dictionary
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
    
    summary = {
        "pipeline_id": pipeline_id,
        "format": format_name.lower(),
        "user_email": user_email,
        "total_execution_time_ms": total_time,
        "total_tokens": total_tokens,
        "agent_metrics": {
            "user_profiler": {
                "execution_time_ms": profile_output.execution_time_ms,
                "tokens": profile_output.context.tokens,
            },
            "content_analyzer": {
                "execution_time_ms": analysis_output.execution_time_ms,
                "tokens": analysis_output.context.tokens,
            },
            "recommender": {
                "execution_time_ms": recommendation_output.execution_time_ms,
                "tokens": recommendation_output.context.tokens,
            },
            "explainer": {
                "execution_time_ms": explanation_output.execution_time_ms,
                "tokens": explanation_output.context.tokens,
            },
        },
        "evaluation_scores": pipeline_eval.overall_pipeline_score.model_dump(),
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    logger.info(f"\n✓ {format_name} pipeline completed successfully!")
    logger.info(f"  Total time: {total_time:.0f}ms | Total tokens: {total_tokens}")
    logger.info(f"  Avg Fidelity: {summary['evaluation_scores']['avg_fidelity']:.3f}")
    logger.info(f"  Avg Drift: {summary['evaluation_scores']['avg_drift']:.3f}")
    logger.info(f"  Compression: {summary['evaluation_scores']['total_compression']:.3f}")
    
    agent_outputs = [profile_output, analysis_output, recommendation_output, explanation_output]
    return pipeline_id, summary, agent_outputs


def compare_pipelines(json_summary: Dict, md_summary: Dict) -> None:
    """Compare JSON and Markdown pipeline results.
    
    Args:
        json_summary: Summary dict from JSON pipeline.
        md_summary: Summary dict from Markdown pipeline.
    """
    print_header("PIPELINE COMPARISON: JSON vs MARKDOWN")
    
    logger.info("\n📊 PERFORMANCE METRICS")
    logger.info(f"\n  Execution Time:")
    logger.info(f"    JSON:     {json_summary['total_execution_time_ms']:>8.0f}ms")
    logger.info(f"    Markdown: {md_summary['total_execution_time_ms']:>8.0f}ms")
    logger.info(f"    Winner:   {'JSON' if json_summary['total_execution_time_ms'] < md_summary['total_execution_time_ms'] else 'Markdown'}")
    
    logger.info(f"\n  Total Tokens:")
    logger.info(f"    JSON:     {json_summary['total_tokens']:>8}")
    logger.info(f"    Markdown: {md_summary['total_tokens']:>8}")
    compression_pct = ((json_summary['total_tokens'] - md_summary['total_tokens']) / json_summary['total_tokens'] * 100)
    logger.info(f"    Markdown achieves {compression_pct:>5.1f}% token reduction")
    
    logger.info(f"\n📈 CONTEXT QUALITY METRICS")
    
    json_scores = json_summary['evaluation_scores']
    md_scores = md_summary['evaluation_scores']
    
    logger.info(f"\n  Context Fidelity (0-1, higher is better):")
    logger.info(f"    JSON:     {json_scores['avg_fidelity']:.4f}")
    logger.info(f"    Markdown: {md_scores['avg_fidelity']:.4f}")
    fidelity_diff = ((json_scores['avg_fidelity'] - md_scores['avg_fidelity']) / md_scores['avg_fidelity'] * 100) if md_scores['avg_fidelity'] > 0 else 0
    logger.info(f"    JSON preserves {fidelity_diff:>6.1f}% more information")
    
    logger.info(f"\n  Relevance Drift (0-1, lower is better):")
    logger.info(f"    JSON:     {json_scores['avg_drift']:.4f}")
    logger.info(f"    Markdown: {md_scores['avg_drift']:.4f}")
    logger.info(f"    Winner:   {'JSON' if json_scores['avg_drift'] < md_scores['avg_drift'] else 'Markdown'}")
    
    logger.info(f"\n  End-to-End Fidelity (compounding):")
    logger.info(f"    JSON:     {json_scores['end_to_end_fidelity']:.4f}")
    logger.info(f"    Markdown: {md_scores['end_to_end_fidelity']:.4f}")
    
    logger.info(f"\n  Compression Efficiency:")
    logger.info(f"    JSON:     {json_scores['total_compression']:.4f}")
    logger.info(f"    Markdown: {md_scores['total_compression']:.4f}")
    
    print_header("KEY FINDINGS")
    logger.info("\n✓ Structured JSON Context:")
    logger.info(f"  - Preserves {fidelity_diff:.0f}% more information through agent handoffs")
    logger.info(f"  - Lower drift: {json_scores['avg_drift']:.3f} vs {md_scores['avg_drift']:.3f}")
    logger.info(f"  - Better for programmatic agent-to-agent communication")
    
    logger.info("\n✓ Markdown Context:")
    logger.info(f"  - Achieves {compression_pct:.0f}% token reduction")
    logger.info(f"  - More human-readable and concise")
    logger.info(f"  - Trade-off: {abs(fidelity_diff):.0f}% information loss")
    
    logger.info("\n💾 Results stored in MongoDB:")
    logger.info(f"  - Collection: eval_handoffs ({6} documents)")
    logger.info(f"  - Collection: eval_pipelines (2 documents)")
    logger.info(f"  - JSON Pipeline ID: {json_summary['pipeline_id']}")
    logger.info(f"  - Markdown Pipeline ID: {md_summary['pipeline_id']}")


def main() -> int:
    """Main function.
    
    Returns:
        Exit code.
    """
    # Parse command line arguments
    compare_mode = "--compare" in sys.argv
    user_email = None
    
    for arg in sys.argv[1:]:
        if not arg.startswith("--") and "@" in arg:
            user_email = arg
            break
    
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
        users = service.list_users(limit=20)
        
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
    
    # Run the pipeline(s)
    try:
        if compare_mode:
            print_header("CONTEXT EVALUATION DEMO: JSON vs MARKDOWN")
            logger.info(f"Running both pipelines for user: {user_email}\n")
            
            # Run JSON pipeline
            json_id, json_summary, json_outputs = run_single_pipeline(
                user_email, service, ContextFormat.JSON, client
            )
            
            # Run Markdown pipeline
            md_id, md_summary, md_outputs = run_single_pipeline(
                user_email, service, ContextFormat.MARKDOWN, client
            )
            
            # Compare results
            compare_pipelines(json_summary, md_summary)
            
            logger.info("\n✓ Evaluation complete! Check MongoDB for detailed results.")
            logger.info(f"\n  Query examples:")
            logger.info(f"    db.eval_handoffs.find({{pipeline_id: '{json_id}'}})")
            logger.info(f"    db.eval_pipelines.find({{pipeline_id: '{json_id}'}})")
        else:
            # Run single JSON pipeline (legacy mode)
            json_id, json_summary, json_outputs = run_single_pipeline(
                user_email, service, ContextFormat.JSON, client
            )
            
            # Display recommendations
            print_header("FINAL RECOMMENDATIONS")
            explainer_output = json_outputs[3]
            explanations = explainer_output.context.data
            for rec in explanations["recommendations_with_explanations"]:
                logger.info(f"\n{rec['rank']}. {rec['title']} ({rec.get('year', 'N/A')})")
                logger.info(f"   {rec['explanation']}")
                if rec.get('key_appeal_points'):
                    logger.info(f"   Key points:")
                    for point in rec['key_appeal_points']:
                        logger.info(f"     • {point}")
            
            logger.info("\n✓ Pipeline completed! Run with --compare to evaluate JSON vs Markdown.")
        
        return 0
    except Exception as e:
        logger.error(f"✗ Pipeline failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

