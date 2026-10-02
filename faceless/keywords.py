"""Search demand from YouTube's own autocomplete: what people actually type (free, no key).

The free stand-in for TubeBuddy / vidIQ keyword checks. A topic check for the operator and the trends
skill: `python -m faceless keywords "how much money to retire"` or `keywords --backlog 20`. Not used to
auto-tag posts: raw autocomplete is too noisy to ship unreviewed.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache

from faceless.providers import http

URL = "https://suggestqueries.google.com/complete/search"
STOP = {"a", "an", "the", "to", "of", "in", "on", "for", "and", "or", "your", "you", "is", "are", "it", "its",
        "this", "that", "why", "how", "what", "who", "with", "from", "at", "by", "be", "do", "does", "can",
        "will", "my", "me", "we", "our", "they", "their", "than", "then", "into", "just", "only", "most", "more"}


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9$%']+", text.lower()) if w not in STOP and len(w) > 1]


@lru_cache(maxsize=512)
def suggest(seed: str) -> tuple[str, ...]:
    """YouTube autocomplete for a seed phrase; empty on any failure (never blocks a batch)."""
    seed = " ".join(seed.lower().split())[:100]
    if not seed:
        return ()
    try:
        r = http().get(URL, params={"client": "firefox", "ds": "yt", "q": seed}, timeout=8)
        data = json.loads(r.content.decode("utf-8", "replace")) if r.status_code == 200 else []
    except Exception:  # noqa: BLE001 - keyword data is a bonus, not a dependency
        return ()
    return tuple(s for s in (data[1] if len(data) > 1 else []) if isinstance(s, str))


def seeds(text: str, limit: int = 4) -> list[str]:
    """Two-word seeds from the content words, in order (autocomplete matches on prefixes)."""
    cw = words(text)
    out = [" ".join(cw[i:i + 2]) for i in range(len(cw) - 1)] or cw[:1]
    return out[:limit]


def demand(text: str) -> dict:
    """Autocomplete phrases sharing 2+ content words with the text. score = how many: 0 means no signal."""
    cw = set(words(text))
    found: list[str] = []
    for s in seeds(text):
        for sug in suggest(s):
            if len(cw & set(words(sug))) >= 2 and sug not in found:
                found.append(sug)
    return {"text": text, "score": len(found), "phrases": found[:12]}
