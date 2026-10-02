"""Research briefs: verified notes about real people and their frameworks (channel/research/<id>.md).

The script writer and the fact-check judge both see the brief, so automated scripts about Hormozi,
Kiyosaki, Pena (or anyone added later) only state facts a human or research run already checked.
Backlog items point at a brief with "brief": "<id>"; the `faceless-research` skill writes new ones.
"""

from __future__ import annotations

from faceless.config import Paths


def brief(brief_id: str | None) -> str:
    """The brief's text without its source list (sources are for humans; the prompt stays lean)."""
    if not brief_id:
        return ""
    p = Paths.research / f"{brief_id}.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8").split("\n## Sources")[0].strip()


def available() -> list[str]:
    return sorted(p.stem for p in Paths.research.glob("*.md")) if Paths.research.exists() else []
