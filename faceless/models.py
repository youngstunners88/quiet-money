"""Every model this machine can reach, in one place: each agent's configured default, local Ollama models, and the OpenCode catalog.

Reads only. `build()` is the small summary embedded in the page; `catalog()` is the full provider/model list served separately so the
page stays light. Neither starts a model, pulls one, or reads an API key. Provider/model names are public identifiers; no key, token or
endpoint credential is included.
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from faceless import agents

CATALOG = Path.home() / ".cache" / "opencode" / "models.json"
SOURCE = "~/.cache/opencode/models.json, claude/codex/hermes config, ollama list"
_CACHE: dict[str, tuple[float, object]] = {}
_TTL = 60.0


def _run(args: list[str], timeout: float = 10.0) -> str | None:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    text = ((r.stdout or "") + (r.stderr or "")).strip()
    return text or None


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ollama() -> dict:
    """Local models only. An empty list is a real answer (Ollama installed, nothing pulled)."""
    text = _run(["ollama", "list"])
    if text is None:
        return {"installed": False, "models": [], "source": "ollama list"}
    models = []
    for line in text.splitlines()[1:]:
        parts = line.split()
        if not parts or parts[0].upper() == "NAME":
            continue
        models.append({"name": parts[0], "id": parts[1] if len(parts) > 1 else None,
                       "size": " ".join(parts[2:4]) if len(parts) > 3 else None})
    return {"installed": True, "models": models, "source": "ollama list"}


def _read_catalog() -> dict | None:
    try:
        raw = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def catalog(limit_per_provider: int | None = None) -> dict | None:
    """The full provider/model list, compact and read-only. Cached for a minute; the file is 5-6 MB."""
    hit = _CACHE.get("catalog")
    if hit and time.monotonic() - hit[0] < _TTL:
        return hit[1]  # type: ignore[return-value]
    raw = _read_catalog()
    if raw is None:
        return None
    providers = []
    total = 0
    for pid, p in raw.items():
        if not isinstance(p, dict):
            continue
        ms = []
        for mid, m in (p.get("models") or {}).items():
            if not isinstance(m, dict):
                continue
            ms.append({"id": mid, "name": m.get("name") or mid})
        total += len(ms)
        if limit_per_provider:
            ms = ms[:limit_per_provider]
        providers.append({"id": pid, "name": p.get("name") or pid, "count": len((p.get("models") or {})), "models": ms})
    providers.sort(key=lambda x: (-x["count"], x["name"].lower()))
    doc = {"generatedAt": _now(), "providers": providers, "totalProviders": len(providers), "totalModels": total, "source": str(CATALOG)}
    _CACHE["catalog"] = (time.monotonic(), doc)
    return doc


def build() -> dict:
    defaults = agents.default_models()
    cat = _read_catalog()
    summary = None
    if cat is not None:
        counts = sorted(((pid, len((p.get("models") or {}))) for pid, p in cat.items() if isinstance(p, dict)), key=lambda x: -x[1])
        summary = {"providers": len(counts), "models": sum(n for _, n in counts),
                   "top": [{"id": pid, "count": n, "name": (cat.get(pid) or {}).get("name") or pid} for pid, n in counts[:10]],
                   "source": "~/.cache/opencode/models.json"}
    return {
        "defaults": [{"agent": k, **(v or {})} for k, v in defaults.items()],
        "ollama": ollama(),
        "catalog": summary,
        "source": SOURCE,
    }


def summary(doc: dict | None) -> str:
    if not doc:
        return "Models: source missing"
    c = doc.get("catalog") or {}
    o = doc.get("ollama") or {}
    return f"Models: {c.get('models', 0)} in catalog across {c.get('providers', 0)} providers; {len(o.get('models') or [])} local Ollama model(s)"
