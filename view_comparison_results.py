"""View Context Evaluation Comparison Results from MongoDB.

This script queries the eval_handoffs and eval_pipelines collections
to display a summary comparison of JSON vs Markdown pipelines.

Usage:
    python view_comparison_results.py
    python view_comparison_results.py --latest  # Show only latest run
    python view_comparison_results.py --json <pipeline_id>  # Show specific pipeline
"""

import argparse
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from backend.config import get_settings
from backend.db.mongo_client import MongoDBClient

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def print_separator(char="=", length=70):
    """Print a separator line."""
    logger.info(char * length)


def format_timestamp(ts_str: str) -> str:
    """Format ISO timestamp to readable string."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return ts_str


def display_pipeline_summary(pipeline_doc: Dict) -> None:
    """Display summary for a single pipeline."""
    pipeline_id = pipeline_doc.get("pipeline_id", "unknown")
    scores = pipeline_doc.get("overall_pipeline_score", {})
    handoffs = pipeline_doc.get("handoffs", [])
    
    logger.info(f"\n📋 Pipeline: {pipeline_id}")
    logger.info(f"   Handoffs: {len(handoffs)}")
    logger.info(f"   Avg Fidelity: {scores.get('avg_fidelity', 0):.4f}")
    logger.info(f"   Avg Drift: {scores.get('avg_drift', 0):.4f}")
    logger.info(f"   Total Compression: {scores.get('total_compression', 0):.4f}")
    logger.info(f"   End-to-End Fidelity: {scores.get('end_to_end_fidelity', 0):.4f}")


def display_handoff_details(handoff_doc: Dict) -> None:
    """Display details for a single handoff."""
    handoff_id = handoff_doc.get("handoff_id", "unknown")
    agent_from = handoff_doc.get("agent_from", "?")
    agent_to = handoff_doc.get("agent_to", "?")
    scores = handoff_doc.get("eval_scores", {})
    metadata = handoff_doc.get("metadata", {})
    
    logger.info(f"\n  🔗 {agent_from} → {agent_to}")
    logger.info(f"     Handoff ID: {handoff_id}")
    logger.info(f"     Format: {metadata.get('format', 'unknown')}")
    logger.info(f"     Fidelity: {scores.get('fidelity', 0):.4f}")
    logger.info(f"     Drift: {scores.get('drift', 0):.4f}")
    logger.info(f"     Compression: {scores.get('compression', 0):.4f}")
    
    key_info = handoff_doc.get("key_info_preserved", [])
    if key_info:
        logger.info(f"     Key Info Preserved: {len(key_info)} items")


def compare_formats(json_doc: Dict, md_doc: Dict) -> None:
    """Compare JSON and Markdown pipeline results."""
    print_separator()
    logger.info("📊 JSON vs MARKDOWN COMPARISON")
    print_separator()
    
    json_scores = json_doc.get("overall_pipeline_score", {})
    md_scores = md_doc.get("overall_pipeline_score", {})
    
    logger.info("\n🎯 Context Quality Metrics:")
    logger.info(f"\n  Context Fidelity (higher is better):")
    logger.info(f"    JSON:     {json_scores.get('avg_fidelity', 0):.4f}")
    logger.info(f"    Markdown: {md_scores.get('avg_fidelity', 0):.4f}")
    
    if md_scores.get('avg_fidelity', 0) > 0:
        diff_pct = ((json_scores.get('avg_fidelity', 0) - md_scores.get('avg_fidelity', 0)) / md_scores.get('avg_fidelity', 1) * 100)
        logger.info(f"    → JSON preserves {diff_pct:+.1f}% more information")
    
    logger.info(f"\n  Relevance Drift (lower is better):")
    logger.info(f"    JSON:     {json_scores.get('avg_drift', 0):.4f}")
    logger.info(f"    Markdown: {md_scores.get('avg_drift', 0):.4f}")
    logger.info(f"    → Winner: {'JSON' if json_scores.get('avg_drift', 1) < md_scores.get('avg_drift', 1) else 'Markdown'}")
    
    logger.info(f"\n  End-to-End Fidelity (compounding):")
    logger.info(f"    JSON:     {json_scores.get('end_to_end_fidelity', 0):.4f}")
    logger.info(f"    Markdown: {md_scores.get('end_to_end_fidelity', 0):.4f}")
    
    logger.info(f"\n  Compression Efficiency:")
    logger.info(f"    JSON:     {json_scores.get('total_compression', 0):.4f}")
    logger.info(f"    Markdown: {md_scores.get('total_compression', 0):.4f}")
    
    # Handoff-by-handoff comparison
    json_handoffs = json_doc.get("handoffs", [])
    md_handoffs = md_doc.get("handoffs", [])
    
    if json_handoffs and md_handoffs:
        logger.info(f"\n📈 Handoff-by-Handoff Comparison:")
        for i, (jh, mh) in enumerate(zip(json_handoffs, md_handoffs), 1):
            j_from = jh.get("agent_from", "?")
            j_to = jh.get("agent_to", "?")
            j_fid = jh.get("eval_scores", {}).get("fidelity", 0)
            m_fid = mh.get("eval_scores", {}).get("fidelity", 0)
            j_drift = jh.get("eval_scores", {}).get("drift", 0)
            m_drift = mh.get("eval_scores", {}).get("drift", 0)
            
            logger.info(f"\n  Handoff {i}: {j_from} → {j_to}")
            logger.info(f"    Fidelity:    JSON {j_fid:.4f}  |  MD {m_fid:.4f}  |  Δ {(j_fid - m_fid):+.4f}")
            logger.info(f"    Drift:       JSON {j_drift:.4f}  |  MD {m_drift:.4f}  |  Δ {(j_drift - m_drift):+.4f}")
    
    print_separator()


def main():
    parser = argparse.ArgumentParser(description="View context evaluation results from MongoDB")
    parser.add_argument("--latest", action="store_true", help="Show only the latest pipeline pair")
    parser.add_argument("--json", dest="json_id", help="Show specific JSON pipeline ID")
    parser.add_argument("--markdown", dest="md_id", help="Show specific Markdown pipeline ID")
    parser.add_argument("--all", action="store_true", help="Show all pipelines")
    args = parser.parse_args()
    
    # Connect to MongoDB
    try:
        settings = get_settings()
        client = MongoDBClient(settings)
        logger.info("✓ Connected to MongoDB Atlas\n")
    except Exception as e:
        logger.error(f"✗ Failed to connect: {e}")
        return 1
    
    pipelines_coll = client.get_collection("eval_pipelines")
    
    # Query based on arguments
    if args.json_id and args.md_id:
        # Show specific pipeline pair
        json_doc = pipelines_coll.find_one({"pipeline_id": args.json_id})
        md_doc = pipelines_coll.find_one({"pipeline_id": args.md_id})
        
        if not json_doc or not md_doc:
            logger.error("Pipeline(s) not found")
            return 1
        
        compare_formats(json_doc, md_doc)
    
    elif args.latest:
        # Find latest JSON and Markdown pipelines
        json_pipelines = list(pipelines_coll.find({"pipeline_id": {"$regex": "^json-"}}).sort("_id", -1).limit(1))
        md_pipelines = list(pipelines_coll.find({"pipeline_id": {"$regex": "^md-"}}).sort("_id", -1).limit(1))
        
        if not json_pipelines or not md_pipelines:
            logger.error("No pipelines found. Run demo_recommendation_pipeline.py --compare first.")
            return 1
        
        logger.info("📊 Latest Pipeline Comparison\n")
        compare_formats(json_pipelines[0], md_pipelines[0])
    
    elif args.all:
        # Show all pipelines
        all_pipelines = list(pipelines_coll.find().sort("_id", -1))
        
        if not all_pipelines:
            logger.error("No pipelines found.")
            return 1
        
        print_separator()
        logger.info(f"📚 ALL PIPELINES ({len(all_pipelines)} total)")
        print_separator()
        
        for doc in all_pipelines:
            display_pipeline_summary(doc)
        
        # Try to find matching pairs for comparison
        json_pipes = [p for p in all_pipelines if p["pipeline_id"].startswith("json-")]
        md_pipes = [p for p in all_pipelines if p["pipeline_id"].startswith("md-")]
        
        if json_pipes and md_pipes:
            logger.info("\n\n")
            compare_formats(json_pipes[0], md_pipes[0])
    
    else:
        # Default: show latest with details
        json_pipelines = list(pipelines_coll.find({"pipeline_id": {"$regex": "^json-"}}).sort("_id", -1).limit(1))
        md_pipelines = list(pipelines_coll.find({"pipeline_id": {"$regex": "^md-"}}).sort("_id", -1).limit(1))
        
        if not json_pipelines or not md_pipelines:
            # Show what's available
            all_pipelines = list(pipelines_coll.find().sort("_id", -1).limit(10))
            if all_pipelines:
                logger.info("Available pipelines:")
                for p in all_pipelines:
                    display_pipeline_summary(p)
                logger.info("\n💡 Run: python demo_recommendation_pipeline.py --compare")
            else:
                logger.error("No evaluation results found.")
                logger.info("\n💡 Run: python demo_recommendation_pipeline.py --compare")
            return 1
        
        compare_formats(json_pipelines[0], md_pipelines[0])
        
        # Show handoff details
        logger.info("\n\n")
        print_separator()
        logger.info("🔍 DETAILED HANDOFF ANALYSIS")
        print_separator()
        
        logger.info("\n📘 JSON Pipeline Handoffs:")
        for handoff in json_pipelines[0].get("handoffs", []):
            display_handoff_details(handoff)
        
        logger.info("\n\n📗 Markdown Pipeline Handoffs:")
        for handoff in md_pipelines[0].get("handoffs", []):
            display_handoff_details(handoff)
    
    logger.info("\n")
    print_separator()
    logger.info("✓ Query complete")
    print_separator()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
