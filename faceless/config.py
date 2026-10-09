"""Configuration and filesystem layout.

Everything the engine touches is resolved from STUDIO (the repo root),
so the same code runs locally, in CI, and from a scheduled agent session.
"""

from __future__ import annotations

import os
import re
import tomllib
from datetime import date, datetime, timezone
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
    research = STUDIO / "channel" / "research"

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


def load_dotenv(path: Path | None = None) -> int:
    """Read KEY=VALUE lines from the studio's .env (gitignored) for runs on your own machine, so keys stay
    on that machine. Real environment variables win. Returns how many keys were loaded."""
    path = path or STUDIO / ".env"
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.removeprefix("export ").split("=", 1)
        k, v = k.strip(), v.strip()
        if len(v) >= 2 and v[0] in "'\"" and v[0] in v[1:]:
            v = v[1:v.index(v[0], 1)]            # quoted: keep exactly what's inside the quotes
        else:
            v = v.split(" #", 1)[0].strip()      # unquoted: drop an inline comment
        if k and v and not os.environ.get(k):
            os.environ[k] = v
            n += 1
    return n


def today_utc() -> date:
    """Today's date in UTC. Job days, the spend ledger and the posting calendar are all UTC; `date.today()` follows the machine's clock zone and would
    name tomorrow (or yesterday) for a few hours a day on a laptop outside UTC."""
    return datetime.now(timezone.utc).date()


_SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|COMPOSIO_API")
_SECRET_QUERY = re.compile(r"(?i)([?&](?:key|api_key|apikey|token|access_token|auth)=)[^&\s\"'\\#)]+")   # stops at \ so JSON stays valid


# Credentials have recognisable shapes, so a key that is NOT in this process's environment (a vendor's error message echoing a rotated key, a header
# dumped by a library) is still scrubbed before it reaches the public journal. Same shapes as the committed-file scan in tests/test_hygiene.py.
_SECRET_SHAPES = re.compile(
    r"\bsk-[A-Za-z0-9_-]{20,}|\bAIza[0-9A-Za-z_-]{35}|\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}|\bxox[abprs]-[A-Za-z0-9-]{10,}"
    r"|\bAKIA[0-9A-Z]{16}\b|\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{8,}"
    r"|(?i:\b(?:bearer|apikey|api-key)\s+)[A-Za-z0-9._~+/=-]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[A-Za-z0-9+/=\\n\s]*(?:-----END [A-Z ]*PRIVATE KEY-----)?")


def redact(text: str) -> str:
    """Scrub credentials from text bound for committed files (journal, job notes, reports): query-string
    keys that HTTP libraries echo in error messages, the value of every secret-looking env var, and anything shaped like a known key."""
    text = _SECRET_QUERY.sub(r"\1[redacted]", text)
    text = _SECRET_SHAPES.sub("[redacted]", text)
    for name, val in os.environ.items():
        if val and len(val) >= 12 and _SECRET_NAME.search(name) and val in text:
            text = text.replace(val, "[redacted]")
    return text


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
