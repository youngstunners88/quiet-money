"""Operating safety: one kill switch and one daily spend ceiling, checked before anything that costs money or goes public.

The kill switch is a file, `state/PAUSE`; its first line is the reason. Creating it (or setting `[safety] paused = true`) stops
`daily` and `make`, and every paid provider refuses to run, so a bad day is one `echo "why" > state/PAUSE` away from being contained.
Deleting the file resumes. The ceiling (`[safety] daily_usd_ceiling`, default $3) is the sum of everything the ledger recorded today
across all providers; it sits above the per-provider caps as a second wall. Both raise ProviderUnavailable, which provider chains
already treat as "skip this one", so a halted provider never crashes a run that can still be finished free.
"""

from __future__ import annotations

from faceless import config, ledger
from faceless.config import Paths
from faceless.providers import ProviderUnavailable

DEFAULT_CEILING = 3.0


def pause_file():
    return Paths.state / "PAUSE"


def paused() -> str | None:
    """The reason the studio is paused, or None when it is running."""
    f = pause_file()
    if f.exists():
        try:
            first = f.read_text(encoding="utf-8").strip().splitlines()
        except OSError:
            first = []
        return (first[0] if first else "state/PAUSE exists")[:200]
    if config.load().get("safety", {}).get("paused"):
        return "[safety] paused = true"
    return None


def ceiling() -> float:
    return float(config.load().get("safety", {}).get("daily_usd_ceiling", DEFAULT_CEILING))


def headroom() -> float:
    return round(ceiling() - ledger.usd_total(), 6)


def guard(what: str, usd: float = 0.0) -> None:
    """Raise ProviderUnavailable when the studio is paused or `usd` more would pass today's ceiling. Call before a paid or public action."""
    why = paused()
    if why:
        raise ProviderUnavailable(f"{what}: studio is paused ({why})")
    if usd > 0 and usd > headroom():
        raise ProviderUnavailable(f"{what}: daily spend ceiling ${ceiling():.2f} reached (spent ${ledger.usd_total():.2f})")


def pause(reason: str) -> None:
    pause_file().parent.mkdir(parents=True, exist_ok=True)
    pause_file().write_text(reason.strip() + "\n", encoding="utf-8")


def resume() -> bool:
    f = pause_file()
    if f.exists():
        f.unlink()
        return True
    return False
