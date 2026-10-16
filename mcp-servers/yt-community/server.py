"""Quiet Money YouTube Posts MCP server (stdio). Run on the owner's own machine: `python server.py`.

Tools: community_status, community_login, community_post, community_post_day.
Publishing needs QM_COMMUNITY_APPROVED=1 in the server's environment; without it every post is a dry run that ends with a screenshot.
"""

from __future__ import annotations

import random
import time

from mcp.server.fastmcp import FastMCP

import browser
import core

mcp = FastMCP("quiet-money-youtube-posts")


def _find(day: str, index: int) -> dict:
    items = core.comics(day)
    if not 1 <= index <= len(items):
        raise ValueError(f"{day} has {len(items)} comics; index must be 1..{len(items)}")
    return items[index - 1]


@mcp.tool()
def community_status(day: str = "") -> dict:
    """Which comics are ready for the Posts tab on a day (default today, UTC), which went out, and whether publishing is switched on."""
    day = day or core.today_utc()
    rows = [{"index": i + 1, "slug": c["slug"], "title": c["title"], "posted": bool(core.posted(c["slug"])), "problems": core.problems(c)}
            for i, c in enumerate(core.comics(day))]
    return {"day": day, "channel": core.channel_id(), "posted_today": core.posted_today(), "daily_max": core.MAX_PER_DAY,
            "publishing_enabled": core.os.environ.get("QM_COMMUNITY_APPROVED") == "1", "comics": rows}


@mcp.tool()
def community_login() -> str:
    """Open a visible browser on this machine so the channel owner can sign in to YouTube by hand. The sign-in stays in the local profile folder."""
    return browser.login(core.channel_id())


@mcp.tool()
def community_post(day: str, index: int, publish: bool = False) -> dict:
    """Post comic number `index` (1-based) of `day` to the Posts tab. publish=false fills the composer and returns a screenshot without pressing Post."""
    item = _find(day, index)
    if why := core.gate(item, publish=publish, day=day):
        return {"posted": False, "refused": why, "slug": item["slug"]}
    res = browser.post_image(core.channel_id(), item["picture"], item["text"], publish=publish)
    core.record(item["slug"], published=bool(res.get("published")), note="dry run" if not publish else "")
    return {"posted": bool(res.get("published")), "slug": item["slug"], **res}


@mcp.tool()
def community_post_day(day: str = "", publish: bool = False) -> list[dict]:
    """Post every ready comic of a day one after another, with a pause between posts. Stops at the daily maximum or the first refusal."""
    day = day or core.today_utc()
    out = []
    for i, item in enumerate(core.comics(day), start=1):
        if core.posted(item["slug"]):
            continue
        res = community_post(day, i, publish=publish)
        out.append(res)
        if res.get("refused"):
            break
        if publish:
            time.sleep(random.uniform(45, 120))          # posts a person would make, not a burst
    return out


if __name__ == "__main__":
    mcp.run()
