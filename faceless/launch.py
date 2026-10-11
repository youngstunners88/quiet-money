"""Launch order: which pillar goes in which slot while the channel has no metrics of its own.

With no analytics the planner can only rotate pillars. For the first `days` days of posting (counted from the first video scheduled on YouTube; before any exists, every plan counts) this puts the strongest lead (a config
list, the owner's Escape series first) into the slot we expect to perform best (`slot_value`, best first). Both lists are ASSUMPTIONS:
sources on Shorts timing disagree and none covers personal finance. After the window the planner goes back to rotating, so the
metrics can tell a slot's effect from a pillar's, and `analytics.pillar_weights` takes over once there are enough posts.
"""

from __future__ import annotations

from datetime import date

from faceless import config


def settings() -> dict:
    return config.load()["publish"].get("launch", {})


def first_post_day() -> str | None:
    """Post day of the earliest video scheduled on YouTube, or None before the first one."""
    from faceless.providers.publish import nominal_slot
    from faceless.state import all_jobs
    days = [nominal_slot(j.day, j.slot)[0] for j in all_jobs() if (j.artifacts.get("youtube") or {}).get("video_id")]
    return min(days) if days else None


def in_window(post_day: str, cfg: dict | None = None, first: str | None = "-") -> bool:
    cfg = settings() if cfg is None else cfg
    if not cfg:
        return False
    first = first_post_day() if first == "-" else first
    if first is None:
        return True
    return 0 <= (date.fromisoformat(post_day) - date.fromisoformat(first)).days < int(cfg.get("days", 3))


def strategic_plan(pillars: list[str], post_day: str, cfg: dict | None = None, first: str | None = "-") -> list[str]:
    """`pillars` is the day's plan (index = slot). Inside the launch window, return it reordered: lead pillars take the best slots."""
    cfg = settings() if cfg is None else cfg
    if not in_window(post_day, cfg, first) or not pillars:
        return pillars
    priority = cfg.get("pillars", [])
    ranked = sorted(pillars, key=lambda p: priority.index(p) if p in priority else len(priority))   # stable: ties keep the planner's order
    slots = [s for s in cfg.get("slot_value", range(len(pillars))) if s < len(pillars)]
    slots += [s for s in range(len(pillars)) if s not in slots]
    out = [""] * len(pillars)
    for slot, pillar in zip(slots, ranked):
        out[slot] = pillar
    return out
