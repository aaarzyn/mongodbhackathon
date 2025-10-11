"""Generate a human-readable HTML report of recent evaluation runs.

Usage:
    python scripts/generate_eval_report.py --limit 20 --output reports/eval_report.html
"""

from __future__ import annotations

import argparse
import html
import os
from typing import Any, Dict, List

from backend.db.mongo_client import get_mongo_client


def fetch_recent_pipelines(limit: int) -> List[Dict[str, Any]]:
    client = get_mongo_client()
    db = client.database
    cursor = db["eval_pipelines"].find({}).sort([("_id", -1)]).limit(limit)
    return list(cursor)


def fetch_handoffs_for_pipeline(pipeline_id: str) -> List[Dict[str, Any]]:
    client = get_mongo_client()
    db = client.database
    cursor = db["eval_handoffs"].find({"pipeline_id": pipeline_id}).sort([("_id", 1)])
    return list(cursor)


def _esc(x: Any) -> str:
    return html.escape(str(x) if x is not None else "")


def render_report(pipelines: List[Dict[str, Any]], output: str) -> None:
    parts: List[str] = []
    parts.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
    parts.append("<title>ContextScope Eval Report</title>")
    parts.append(
        "<style>body{font-family:system-ui, -apple-system, Segoe UI, Roboto, sans-serif;padding:20px;}"
        "h1{margin-bottom:0} h2{margin-top:32px} table{border-collapse:collapse;width:100%;margin-top:8px;}"
        "th,td{border:1px solid #ddd;padding:8px;vertical-align:top;} th{background:#fafafa;text-align:left;}"
        ".score{white-space:nowrap} details{margin-top:6px} code{white-space:pre-wrap; display:block; background:#f7f7f7; padding:8px; border:1px solid #eee;}" 
        "</style>"
    )
    parts.append("</head><body>")
    parts.append("<h1>ContextScope Eval Report</h1>")

    for p in pipelines:
        pid = _esc(p.get("pipeline_id"))
        score = p.get("overall_pipeline_score", {})
        parts.append(f"<h2>Pipeline: {pid}</h2>")
        parts.append(
            "<div class='score'>"
            f"avg_fidelity={_esc(score.get('avg_fidelity'))} • "
            f"avg_drift={_esc(score.get('avg_drift'))} • "
            f"total_compression={_esc(score.get('total_compression'))} • "
            f"end_to_end_fidelity={_esc(score.get('end_to_end_fidelity'))}"
            "</div>"
        )

        handoffs = fetch_handoffs_for_pipeline(p.get("pipeline_id"))
        parts.append("<table><thead><tr>"
                     "<th>From → To</th><th>Fidelity</th><th>Drift</th><th>Compression</th><th>Temporal</th>"
                     "<th>Preserved (sample)</th><th>Format</th><th>Contexts</th></tr></thead><tbody>")
        for h in handoffs:
            scores = h.get("eval_scores", {})
            preserved = h.get("key_info_preserved", [])
            meta = h.get("metadata", {}) or {}
            fmt = meta.get("format", "?")
            sent = (h.get("context_sent") or "")[:800]
            recv = (h.get("context_received") or "")[:800]
            parts.append("<tr>")
            parts.append(
                f"<td>{_esc(h.get('agent_from'))} → {_esc(h.get('agent_to'))}</td>"
                f"<td>{_esc(scores.get('fidelity'))}</td>"
                f"<td>{_esc(scores.get('drift'))}</td>"
                f"<td>{_esc(scores.get('compression'))}</td>"
                f"<td>{_esc(scores.get('temporal_coherence'))}</td>"
                f"<td>{_esc(', '.join(map(str, preserved[:5])))}{('…' if len(preserved)>5 else '')}</td>"
                f"<td>{_esc(fmt)}</td>"
            )
            details = (
                "<details><summary>Show Contexts</summary>"
                f"<div><strong>Sent</strong><code>{_esc(sent)}</code></div>"
                f"<div><strong>Received</strong><code>{_esc(recv)}</code></div>"
                "</details>"
            )
            parts.append(f"<td>{details}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

    parts.append("</body></html>")

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10, help="How many recent pipelines to include")
    ap.add_argument("--output", type=str, default="reports/eval_report.html", help="Output HTML file path")
    args = ap.parse_args()

    pipelines = fetch_recent_pipelines(args.limit)
    render_report(pipelines, args.output)
    print(f"Wrote report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

