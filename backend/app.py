"""CLI entrypoint to run movie recommendation pipelines and store evals.

Usage examples:
  python app.py --task movie_recommendations --email "sean_bean@gameofthron.es"
  python app.py --task movie_recommendations --user-id "59b99db4cfa9a34dcd7885b6"

This runs two pipelines in parallel (JSON and Markdown), evaluates
context fidelity at each handoff, and stores results in MongoDB.
"""

from __future__ import annotations

import argparse
import json
import logging
import threading
import uuid
from typing import Optional, Tuple

from backend.agents import (
    ContentAnalyzerAgent,
    ExplainerAgent,
    RecommenderAgent,
    UserProfilerAgent,
)
from backend.agents.base import ContextFormat
from backend.api.dependencies import get_mflix_service
from backend.db.mongo_client import get_mongo_client
from backend.evaluator.service import EvaluatorService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _choose_user_email(service, user_id: Optional[str], email: Optional[str]) -> Optional[str]:
    if email:
        return email
    if user_id:
        user = service.get_user_by_id(user_id)
        return user.email if user else None
    # pick a user with at least one comment
    users = service.list_users(limit=20)
    for u in users:
        comments = service.get_comments_by_user(u.email, limit=1)
        if comments:
            return u.email
    return users[0].email if users else None


def _context_text(output) -> str:
    # Prefer raw_text in metadata if agents provided it, else JSON dump
    md = output.context.metadata or {}
    raw = md.get("raw_text")
    if isinstance(raw, str) and raw.strip():
        return raw
    return json.dumps(output.context.data, ensure_ascii=False)


def run_pipeline_pair(email: str) -> Tuple[str, str]:
    """Run JSON and Markdown pipelines and store handoff evals.

    Returns:
        Tuple of (json_pipeline_id, md_pipeline_id)
    """
    client = get_mongo_client()
    service = get_mflix_service()
    evaluator = EvaluatorService(client)

    # Build agents for both formats
    profiler_json = UserProfilerAgent(service, ContextFormat.JSON)
    analyzer_json = ContentAnalyzerAgent(service, ContextFormat.JSON, max_candidates=30)
    recommender_json = RecommenderAgent(ContextFormat.JSON, top_n=5)
    explainer_json = ExplainerAgent(ContextFormat.JSON)

    profiler_md = UserProfilerAgent(service, ContextFormat.MARKDOWN)
    analyzer_md = ContentAnalyzerAgent(service, ContextFormat.MARKDOWN, max_candidates=30)
    recommender_md = RecommenderAgent(ContextFormat.MARKDOWN, top_n=5)
    explainer_md = ExplainerAgent(ContextFormat.MARKDOWN)

    json_pipeline_id = f"json-{uuid.uuid4().hex[:8]}"
    md_pipeline_id = f"md-{uuid.uuid4().hex[:8]}"

    def _run_json():
        logger.info("Running JSON pipeline: %s", json_pipeline_id)
        p = profiler_json.process_user(email)
        if not p.success:
            logger.error("User profiling failed (JSON): %s", p.error_message)
            return
        a = analyzer_json.process(p.context)
        if not a.success:
            logger.error("Content analysis failed (JSON): %s", a.error_message)
            return
        r = recommender_json.process(a.context)
        if not r.success:
            logger.error("Recommendation failed (JSON): %s", r.error_message)
            return
        e = explainer_json.process(r.context)
        if not e.success:
            logger.error("Explanation failed (JSON): %s", e.error_message)
            return
        # Handoffs
        evaluator.evaluate_and_store_handoff(
            pipeline_id=json_pipeline_id,
            handoff_id=f"{json_pipeline_id}-h1",
            agent_from="User Profiler",
            agent_to="Content Analyzer",
            context_sent=_context_text(p),
            context_received=_context_text(p),
            metadata={"format": "json"},
        )
        evaluator.evaluate_and_store_handoff(
            pipeline_id=json_pipeline_id,
            handoff_id=f"{json_pipeline_id}-h2",
            agent_from="Content Analyzer",
            agent_to="Recommender",
            context_sent=_context_text(a),
            context_received=_context_text(a),
            metadata={"format": "json"},
        )
        evaluator.evaluate_and_store_handoff(
            pipeline_id=json_pipeline_id,
            handoff_id=f"{json_pipeline_id}-h3",
            agent_from="Recommender",
            agent_to="Explainer",
            context_sent=_context_text(r),
            context_received=_context_text(r),
            metadata={"format": "json"},
        )
        evaluator.finalize_pipeline(json_pipeline_id)
        logger.info("JSON pipeline complete: %s", json_pipeline_id)

    def _run_md():
        logger.info("Running Markdown pipeline: %s", md_pipeline_id)
        p = profiler_md.process_user(email)
        if not p.success:
            logger.error("User profiling failed (MD): %s", p.error_message)
            return
        a = analyzer_md.process(p.context)
        if not a.success:
            logger.error("Content analysis failed (MD): %s", a.error_message)
            return
        r = recommender_md.process(a.context)
        if not r.success:
            logger.error("Recommendation failed (MD): %s", r.error_message)
            return
        e = explainer_md.process(r.context)
        if not e.success:
            logger.error("Explanation failed (MD): %s", e.error_message)
            return
        # Handoffs
        evaluator.evaluate_and_store_handoff(
            pipeline_id=md_pipeline_id,
            handoff_id=f"{md_pipeline_id}-h1",
            agent_from="User Profiler",
            agent_to="Content Analyzer",
            context_sent=_context_text(p),
            context_received=_context_text(p),
            metadata={"format": "markdown"},
        )
        evaluator.evaluate_and_store_handoff(
            pipeline_id=md_pipeline_id,
            handoff_id=f"{md_pipeline_id}-h2",
            agent_from="Content Analyzer",
            agent_to="Recommender",
            context_sent=_context_text(a),
            context_received=_context_text(a),
            metadata={"format": "markdown"},
        )
        evaluator.evaluate_and_store_handoff(
            pipeline_id=md_pipeline_id,
            handoff_id=f"{md_pipeline_id}-h3",
            agent_from="Recommender",
            agent_to="Explainer",
            context_sent=_context_text(r),
            context_received=_context_text(r),
            metadata={"format": "markdown"},
        )
        evaluator.finalize_pipeline(md_pipeline_id)
        logger.info("Markdown pipeline complete: %s", md_pipeline_id)

    # Run both pipelines in parallel threads
    t1 = threading.Thread(target=_run_json, daemon=True)
    t2 = threading.Thread(target=_run_md, daemon=True)
    t1.start(); t2.start()
    t1.join(); t2.join()

    return json_pipeline_id, md_pipeline_id


def main() -> int:
    parser = argparse.ArgumentParser(description="ContextScope backend entrypoint")
    parser.add_argument("--task", default="movie_recommendations", help="Task to run")
    parser.add_argument("--user-id", dest="user_id", default=None, help="User ID to target")
    parser.add_argument("--email", dest="email", default=None, help="User email to target")
    args = parser.parse_args()

    if args.task != "movie_recommendations":
        logger.error("Unsupported task: %s", args.task)
        return 1

    client = get_mongo_client()
    service = get_mflix_service()
    email = _choose_user_email(service, args.user_id, args.email)
    if not email:
        logger.error("No suitable user found to run recommendations")
        return 1

    logger.info("Running recommendation pipelines for %s", email)
    json_id, md_id = run_pipeline_pair(email)
    logger.info("Pipeline IDs → JSON: %s, Markdown: %s", json_id, md_id)
    logger.info("Done. View results in MongoDB collections 'eval_handoffs' and 'eval_pipelines'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
