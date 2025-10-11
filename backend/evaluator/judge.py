"""LLM-based judge using Fireworks for handoff evaluation.

Produces JSON-structured judgments for fidelity, drift, and preserved key info.
Falls back gracefully if parsing fails.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from backend.config import get_settings
from backend.providers.fireworks import FireworksJudge, FireworksProviderError

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from text, handling various formats."""
    if not text:
        return None
        
    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass
    
    # Try to find JSON block
    match = _JSON_BLOCK_RE.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    
    # Try to extract from code blocks
    code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text)
    if code_block_match:
        try:
            return json.loads(code_block_match.group(1))
        except Exception:
            pass
    
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
        "You are a JSON-only API. Respond ONLY with valid JSON. "
        "No explanations, no reasoning, no markdown, no other text. "
        "Just the raw JSON object."
    )
    
    # Truncate contexts to avoid overwhelming the model
    sent_truncated = context_sent[:2000]
    recv_truncated = context_received[:2000]
    
    user = (
        "Evaluate how well RECEIVER preserved SENDER's information.\n\n"
        f"SENDER:\n{sent_truncated}\n\n"
        f"RECEIVER:\n{recv_truncated}\n\n"
        "Respond with ONLY this JSON (no other text):\n"
        '{"fidelity": <0.0-1.0>, "drift": <0.0-1.0>, "preserved": ["key1", "key2"]}\n\n'
        "JSON:"
    )
    
    try:
        out = judge.judge_text(
            system_prompt=system, 
            user_prompt=user, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        logger.debug(f"Raw Fireworks output: {out[:300] if out else 'None'}")
    except FireworksProviderError as e:
        logger.error("Fireworks provider error: %s", e)
        return None
    except Exception as e:
        logger.error("Unexpected error from Fireworks: %s", e)
        return None

    if not out:
        logger.warning("Fireworks returned empty/None response")
        return None
    
    data = _extract_json(out)
    logger.debug(f"Extracted JSON data: {data}")
    
    if not isinstance(data, dict):
        logger.warning(f"Failed to extract valid JSON dict from response")
        return None
    
    # Basic normalization
    fidelity = data.get("fidelity")
    drift = data.get("drift")
    preserved = data.get("preserved") or []
    
    try:
        if fidelity is not None:
            fidelity = max(0.0, min(1.0, float(fidelity)))
        else:
            logger.warning("No fidelity score in response")
            return None
            
        if drift is not None:
            drift = max(0.0, min(1.0, float(drift)))
        else:
            logger.warning("No drift score in response")
            return None
    except Exception as e:
        logger.error(f"Failed to parse scores: {e}")
        return None
    
    if not isinstance(preserved, list):
        preserved = []
    preserved = [str(x)[:200] for x in preserved[:10]]
    
    result = {"fidelity": fidelity, "drift": drift, "preserved": preserved}
    logger.debug(f"Final normalized result: {result}")
    
    return result