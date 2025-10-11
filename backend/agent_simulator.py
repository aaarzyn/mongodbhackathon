"""Lightweight simulation to run evals on Mflix data.

This focuses only on evaluation: it crafts minimal handoffs for two
pipelines (structured JSON vs freeform Markdown), computes metrics, and
persists results via the EvaluatorService.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Dict, List, Tuple
import argparse

from backend.db.mongo_client import get_mongo_client
from backend.evaluator.service import EvaluatorService
from backend.services.mflix_service import MflixService

logger = logging.getLogger(__name__)


def _pick_user_and_movies(service: MflixService, *, user_skip: int = 0, movie_skip: int = 0) -> Tuple[Dict, List[Dict]]:
    users = service.list_users(limit=1, skip=user_skip)
    user = users[0] if users else None
    movies = service.get_movies_by_genre("Sci-Fi", limit=3, skip=movie_skip)
    # Convert to simple dicts for templating
    user_d = user.model_dump(by_alias=True) if user else {
        "_id": "unknown",
        "name": "Sci-Fi Fan",
        "email": "sci_fi@example.com",
        "preferences": {"favorite_genres": ["Sci-Fi", "Drama"]},
    }
    movies_d = [m.model_dump(by_alias=True) for m in movies]
    return user_d, movies_d


def _build_json_pipeline_contexts(user: Dict, movies: List[Dict]) -> List[Tuple[str, str, Dict]]:
    # Agent 1 -> Agent 2
    profiler_out = {
        "user_id": user.get("_id"),
        "profile": {
            "name": user.get("name"),
            "top_genres": [{"genre": "Sci-Fi", "affinity": 0.9}, {"genre": "Drama", "affinity": 0.7}],
            "director_preferences": [],
            "watch_history": [],
            "avg_runtime_preference": 130,
            "decade_preference": ["2010s", "2020s"],
            "language_preference": ["English"],
        },
        "context_metadata": {"tokens": 200, "embedding_dim": 768},
    }
    analyzer_in = json.dumps(profiler_out)

    # Agent 2 -> Agent 3
    candidates = []
    for m in movies:
        candidates.append(
            {
                "movie_id": m.get("_id"),
                "title": m.get("title"),
                "year": m.get("year"),
                "genres": m.get("genres", [])[:3],
                "director": (m.get("directors") or ["Unknown"])[0],
                "imdb_rating": (m.get("imdb") or {}).get("rating", None),
                "similarity_score": 0.85,
                "match_reasons": ["genre_overlap", "high_rating"],
            }
        )
    analyzer_out = {
        "user_profile_summary": {
            "primary_interests": ["Sci-Fi", "Drama"],
            "profile_embedding": [0.1, 0.2, 0.3],
        },
        "candidate_movies": candidates,
        "context_metadata": {"tokens": 450, "candidates_analyzed": len(candidates)},
    }
    recommender_in = json.dumps(analyzer_out)

    # Agent 3 -> Agent 4
    recs = []
    for rank, c in enumerate(candidates[:2], start=1):
        recs.append(
            {
                "rank": rank,
                "movie_id": c["movie_id"],
                "title": c["title"],
                "confidence_score": 0.85 - 0.02 * rank,
                "relevance_factors": {
                    "genre_match": 0.9,
                    "director_match": 0.8,
                    "rating_quality": 0.85,
                    "recency": 0.8,
                },
            }
        )
    recommender_out = {
        "recommendations": recs,
        "context_metadata": {"tokens": 300, "ranking_algorithm": "weighted_hybrid"},
    }
    explainer_in = json.dumps(recommender_out)

    # Return handoff pairs (sent, received, metadata)
    return [
        (json.dumps(profiler_out), analyzer_in, {"format": "json"}),
        (json.dumps(analyzer_out), recommender_in, {"format": "json"}),
        (json.dumps(recommender_out), explainer_in, {"format": "json"}),
    ]


def _build_markdown_pipeline_contexts(user: Dict, movies: List[Dict]) -> List[Tuple[str, str, Dict]]:
    # Agent 1 -> Agent 2
    profiler_out = f"""
User: {user.get('name', 'Unknown')}
Likes Sci-Fi and Drama. Prefers 2010s–2020s, ~130min runtime, English.
Recent interests include modern sci-fi epics with strong visuals.
""".strip()
    analyzer_in = profiler_out

    # Agent 2 -> Agent 3
    lines = ["Candidates:"]
    for m in movies:
        title = m.get("title", "Unknown")
        year = m.get("year", "?")
        genres = ", ".join(m.get("genres", [])[:3])
        director = (m.get("directors") or ["Unknown"])[0]
        rating = (m.get("imdb") or {}).get("rating", "?")
        lines.append(f"- {title} ({year}) — {genres}; Dir: {director}; IMDb {rating}")
    analyzer_out = (profiler_out + "\n\n" + "\n".join(lines)).strip()
    recommender_in = analyzer_out

    # Agent 3 -> Agent 4
    recs = [m.get("title", "Unknown") for m in movies[:2]]
    recommender_out = (
        analyzer_out
        + "\n\nTop picks:\n"
        + "\n".join(f"{i+1}. {t}" for i, t in enumerate(recs))
    )
    explainer_in = recommender_out

    return [
        (profiler_out, analyzer_in, {"format": "markdown"}),
        (analyzer_out, recommender_in, {"format": "markdown"}),
        (recommender_out, explainer_in, {"format": "markdown"}),
    ]


def run_demo_evals() -> None:
    client = get_mongo_client()
    service = MflixService(client)
    evaluator = EvaluatorService(client)

    user, movies = _pick_user_and_movies(service)

    # JSON pipeline
    pipeline_id_json = f"json-{uuid.uuid4().hex[:8]}"
    logger.info("Running JSON pipeline: %s", pipeline_id_json)
    json_handoffs = _build_json_pipeline_contexts(user, movies)
    agents = [
        ("User Profiler", "Content Analyzer"),
        ("Content Analyzer", "Recommender"),
        ("Recommender", "Explainer"),
    ]
    for idx, ((sent, recv, meta), (a_from, a_to)) in enumerate(zip(json_handoffs, agents), start=1):
        evaluator.evaluate_and_store_handoff(
            pipeline_id=pipeline_id_json,
            handoff_id=f"{pipeline_id_json}-h{idx}",
            agent_from=a_from,
            agent_to=a_to,
            context_sent=sent,
            context_received=recv,
            metadata=meta,
            use_llm_judge=True,
        )
    summary_json = evaluator.finalize_pipeline(pipeline_id_json)
    logger.info("JSON pipeline rollup: %s", summary_json.overall_pipeline_score.model_dump())

    # Markdown pipeline
    pipeline_id_md = f"md-{uuid.uuid4().hex[:8]}"
    logger.info("Running Markdown pipeline: %s", pipeline_id_md)
    md_handoffs = _build_markdown_pipeline_contexts(user, movies)
    for idx, ((sent, recv, meta), (a_from, a_to)) in enumerate(zip(md_handoffs, agents), start=1):
        evaluator.evaluate_and_store_handoff(
            pipeline_id=pipeline_id_md,
            handoff_id=f"{pipeline_id_md}-h{idx}",
            agent_from=a_from,
            agent_to=a_to,
            context_sent=sent,
            context_received=recv,
            metadata=meta,
            use_llm_judge=True,
        )
    summary_md = evaluator.finalize_pipeline(pipeline_id_md)
    logger.info("Markdown pipeline rollup: %s", summary_md.overall_pipeline_score.model_dump())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Run evaluation pipelines on Mflix data")
    parser.add_argument("--batch", type=int, default=0, help="Number of pipeline pairs (JSON+MD) to run")
    args = parser.parse_args()

    if args.batch and args.batch > 0:
        client = get_mongo_client()
        service = MflixService(client)
        evaluator = EvaluatorService(client)

        for i in range(args.batch):
            # Vary user/movie selection to diversify contexts
            user, movies = _pick_user_and_movies(service, user_skip=i % 20, movie_skip=i % 50)

            # JSON pipeline
            pipeline_id_json = f"json-b{i}-{uuid.uuid4().hex[:6]}"
            logger.info("Running JSON pipeline: %s", pipeline_id_json)
            json_handoffs = _build_json_pipeline_contexts(user, movies)
            agents = [
                ("User Profiler", "Content Analyzer"),
                ("Content Analyzer", "Recommender"),
                ("Recommender", "Explainer"),
            ]
            for idx, ((sent, recv, meta), (a_from, a_to)) in enumerate(zip(json_handoffs, agents), start=1):
                evaluator.evaluate_and_store_handoff(
                    pipeline_id=pipeline_id_json,
                    handoff_id=f"{pipeline_id_json}-h{idx}",
                    agent_from=a_from,
                    agent_to=a_to,
                    context_sent=sent,
                    context_received=recv,
                    metadata=meta,
                    use_llm_judge=True,
                )
            summary_json = evaluator.finalize_pipeline(pipeline_id_json)
            logger.info("JSON pipeline rollup: %s", summary_json.overall_pipeline_score.model_dump())

            # Markdown pipeline
            pipeline_id_md = f"md-b{i}-{uuid.uuid4().hex[:6]}"
            logger.info("Running Markdown pipeline: %s", pipeline_id_md)
            md_handoffs = _build_markdown_pipeline_contexts(user, movies)
            for idx, ((sent, recv, meta), (a_from, a_to)) in enumerate(zip(md_handoffs, agents), start=1):
                evaluator.evaluate_and_store_handoff(
                    pipeline_id=pipeline_id_md,
                    handoff_id=f"{pipeline_id_md}-h{idx}",
                    agent_from=a_from,
                    agent_to=a_to,
                    context_sent=sent,
                    context_received=recv,
                    metadata=meta,
                    use_llm_judge=True,
                )
            summary_md = evaluator.finalize_pipeline(pipeline_id_md)
            logger.info("Markdown pipeline rollup: %s", summary_md.overall_pipeline_score.model_dump())
    else:
        run_demo_evals()
