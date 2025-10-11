"""LLM-based judge using Fireworks for handoff evaluation.

Produces JSON-structured judgments for fidelity, drift, and preserved key info.
Falls back gracefully if parsing fails.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.config import get_settings
from backend.providers.fireworks import FireworksJudge, FireworksProviderError

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        match = _JSON_BLOCK_RE.search(text or "")
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None
        return None


def judge_handoff_via_fireworks(
    *,
    context_sent: str,
    context_received: str,
    temperature: float = 0.0,
    max_tokens: int = 384,
) -> Optional[Dict[str, Any]]:
    """Call Fireworks to judge fidelity, drift, and preserved key info.

    Returns:
        Dict with keys: fidelity, drift, preserved (list[str]), or None on failure.
    """
    settings = get_settings()
    judge = FireworksJudge(settings)
    if not judge.available():
        logger.warning("Fireworks judge not available (no API key)")
        return None

    system = (
        "You are a strict evaluator of context transfer between agents. "
        "You must output a single JSON object with numeric scores in [0,1]."
    )
    user = (
        "Evaluate how well the RECEIVER preserved the SENDER's key information.\n\n"
        "SENDER:\n" + context_sent + "\n\n"
        "RECEIVER:\n" + context_received + "\n\n"
        "Return ONLY this JSON schema (no prose):\n"
        "{\n  \"fidelity\": <float 0..1>,\n  \"drift\": <float 0..1>,\n  \"preserved\": [<up to 10 short strings>]\n}"
    )
    try:
        out = judge.judge_text(system_prompt=system, user_prompt=user, temperature=temperature, max_tokens=max_tokens)
    except FireworksProviderError as e:
        logger.error("Fireworks provider error: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error from Fireworks: %s", e)
        return None

    if not out:
        return None
    data = _extract_json(out)
    if not isinstance(data, dict):
        return None
    # Basic normalization
    fidelity = data.get("fidelity")
    drift = data.get("drift")
    preserved = data.get("preserved") or []
    try:
        if fidelity is not None:
            fidelity = max(0.0, min(1.0, float(fidelity)))
        if drift is not None:
            drift = max(0.0, min(1.0, float(drift)))
    except Exception:
        fidelity = None
        drift = None
    if not isinstance(preserved, list):
        preserved = []
    preserved = [str(x)[:200] for x in preserved[:10]]
    return {"fidelity": fidelity, "drift": drift, "preserved": preserved}

