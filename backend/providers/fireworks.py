"""Fireworks judge model adapter (OpenAI-compatible HTTP interface).

This adapter is used for evaluation-only tasks (judge/extractor). It is
implemented to be resilient in restricted environments: if the API key is
missing or network access is unavailable, methods can be no-ops or return
fallbacks, allowing the rest of the evaluation pipeline to run.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import urllib.request
import urllib.error

from backend.config import Settings

logger = logging.getLogger(__name__)


class FireworksProviderError(Exception):
    """Raised when Fireworks provider operations fail."""

    pass


class FireworksJudge:
    """Minimal Fireworks client for judge prompts.

    Uses the OpenAI-compatible completions endpoint. Network failure is
    handled gracefully and reported via specific exceptions/logging.
    """

    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.fireworks_base_url.rstrip("/")
        self.model = settings.fireworks_model
        self.api_key = settings.fireworks_api_key

    def available(self) -> bool:
        """Return True if provider is configured with an API key."""
        return bool(self.api_key)

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.available():
            raise FireworksProviderError("Fireworks API key not configured")
        url = f"{self.base_url}/{path.lstrip('/')}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="ignore") if e.fp else str(e)
            logger.error(f"Fireworks HTTP error: {e.code} {text}")
            raise FireworksProviderError(f"HTTP {e.code}: {text}") from e
        except urllib.error.URLError as e:
            logger.error(f"Fireworks URL error: {e}")
            raise FireworksProviderError(str(e)) from e
        except Exception as e:
            logger.error(f"Unexpected error calling Fireworks: {e}")
            raise

    def judge_text(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> Optional[str]:
        """Obtain a judgment string from the model.

        Returns the model text or None if unavailable. Any exceptions are
        propagated to the caller for explicit handling if desired.
        """
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 512),
        }
        resp = self._post("chat/completions", payload)
        choices = resp.get("choices", [])
        if not choices:
            return None
        msg = choices[0].get("message", {})
        return msg.get("content")

