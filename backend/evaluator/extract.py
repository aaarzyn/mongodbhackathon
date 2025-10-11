"""Deterministic key info extraction for evaluation.

Extracts salient units from structured JSON and freeform text to support
key-info preservation checks without relying on LLMs.
"""

from __future__ import annotations

import json
import re
from typing import Iterable, List, Set

_QUOTE_RE = re.compile(r'"([^"]{3,})"|\'([^\']{3,})\'')
_CAP_SEQ_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,4})\b")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]{3,}")

_STOPWORDS: Set[str] = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "you",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "into",
    "about",
    "based",
    "similar",
}


def _flatten_json_keys(data: object, prefix: str = "") -> List[str]:
    items: List[str] = []
    if isinstance(data, dict):
        for k, v in data.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            items.append(key)
            items.extend(_flatten_json_keys(v, key))
    elif isinstance(data, list):
        for i, v in enumerate(data[:20]):  # limit breadth
            items.extend(_flatten_json_keys(v, f"{prefix}[{i}]") )
    return items


def _try_parse_json(text: str) -> List[str]:
    try:
        obj = json.loads(text)
        return _flatten_json_keys(obj)
    except Exception:
        return []


def _quoted_phrases(text: str) -> List[str]:
    phrases: List[str] = []
    for m in _QUOTE_RE.finditer(text or ""):
        group = next((g for g in m.groups() if g), None)
        if group:
            phrases.append(group.strip())
    return phrases


def _capitalized_sequences(text: str) -> List[str]:
    return [m.group(1).strip() for m in _CAP_SEQ_RE.finditer(text or "")]


def _top_terms(text: str, k: int = 10) -> List[str]:
    tokens = [t.lower() for t in _TOKEN_RE.findall(text or "")]
    tokens = [t for t in tokens if t not in _STOPWORDS]
    # simple frequency without Counter to keep lightweight
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    return [t for t, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:k]]


def extract_key_units(text: str) -> List[str]:
    """Extract salient units from text or JSON.

    Heuristics:
    - JSON keys (if parsable)
    - Quoted phrases
    - Capitalized sequences
    - Top frequent terms (filtered)
    """
    keys = _try_parse_json(text)
    phrases = _quoted_phrases(text)
    caps = _capitalized_sequences(text)
    terms = _top_terms(text)

    # Deduplicate while preserving order
    seen: Set[str] = set()
    result: List[str] = []
    for item in [*keys, *phrases, *caps, *terms]:
        norm = item.strip()
        if not norm:
            continue
        low = norm.lower()
        if low in seen:
            continue
        seen.add(low)
        result.append(norm)
    return result


def compute_key_info_preserved(sent: str, received: str, limit: int = 20) -> List[str]:
    """Return list of key units preserved from `sent` that appear in `received`.

    Matching is case-insensitive substring containment for simplicity.
    """
    sent_units = extract_key_units(sent)[:limit]
    rec_low = (received or "").lower()
    preserved: List[str] = []
    for u in sent_units:
        if u.lower() in rec_low:
            preserved.append(u)
    return preserved

