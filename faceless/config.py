"""Configuration and filesystem layout.

Everything the engine touches is resolved from STUDIO (the repo root),
so the same code runs locally, in CI, and from a scheduled agent session.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

STUDIO = Path(os.environ.get("FACELESS_STUDIO", Path(__file__).resolve().parent.parent))


class Paths:
    root = STUDIO
    config = STUDIO / "studio.toml"
    fonts = STUDIO / "assets" / "fonts"
    ideas = STUDIO / "script-lab" / "ideas"
    drafts = STUDIO / "script-lab" / "drafts"
    final = STUDIO / "script-lab" / "final"
    output = STUDIO / "production" / "output"
    cache = STUDIO / "production" / "cache"
    queue = STUDIO / "distribution" / "queue"
    analytics = STUDIO / "analytics"
    reports = STUDIO / "gauntlet" / "reports"
    state = STUDIO / "state"
    jobs = STUDIO / "state" / "jobs"

    @classmethod
    def ensure(cls) -> None:
        for p in (cls.ideas, cls.drafts, cls.final, cls.output, cls.cache, cls.queue,
                  cls.analytics, cls.reports, cls.jobs):
            p.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Pillar:
    id: str
    name: str
    weight: float
    format: str
    style: str
    grade: str
    music_key: str


@lru_cache(maxsize=1)
def load() -> dict:
    with open(Paths.config, "rb") as f:
        cfg = tomllib.load(f)
    cfg["pillars"] = [Pillar(**p) for p in cfg.get("pillars", [])]
    return cfg


def pillar(pillar_id: str) -> Pillar:
    for p in load()["pillars"]:
        if p.id == pillar_id:
            return p
    raise KeyError(f"unknown pillar {pillar_id!r}")


def env(*names: str) -> str | None:
    """First non-empty environment variable among names (keys are named inconsistently across tools)."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v.strip()
    return None


def ca_bundle() -> str | None:
    """Corporate/agent proxies re-terminate TLS; honour their CA bundle when one is configured."""
    for n in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE"):
        v = os.environ.get(n)
        if v and Path(v).exists():
            return v
    p = Path("/root/.ccr/ca-bundle.crt")
    return str(p) if p.exists() else None
