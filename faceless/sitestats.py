"""O15: what the website did, read back from PostHog. Visits, calculator use and clicks to the shop, by week.

The pages send cookieless events (faceless/site.py `analytics_snippet`); this reads them with the personal API key from the environment
(`POSTHOG_PERSONAL_API_KEY`, `POSTHOG_PROJECT_ID`) through PostHog's query API, and appends one row to `analytics/site.jsonl`.
`python -m faceless site-stats [--days 7]`. HQ shows the latest row. The funnel the owner cares about is video -> site -> shop click.
"""

from __future__ import annotations

import json
import re

from faceless import config
from faceless.config import Paths
from faceless.fsutil import read_jsonl

LOG = Paths.analytics / "site.jsonl"
API = "https://us.posthog.com/api/projects/{pid}/query/"
EVENTS = {"$pageview": "pageviews", "calculator_used": "calculator_uses", "shop_click": "shop_clicks"}


def query(hogql: str) -> list[list]:
    from faceless.providers import ProviderUnavailable, http
    key, pid = config.env("POSTHOG_PERSONAL_API_KEY"), config.env("POSTHOG_PROJECT_ID")
    if not key or not pid or not str(pid).isdigit():
        raise ProviderUnavailable("POSTHOG_PERSONAL_API_KEY and POSTHOG_PROJECT_ID are needed")
    r = http().post(API.format(pid=pid), json={"query": {"kind": "HogQLQuery", "query": hogql}},
                    headers={"Authorization": f"Bearer {key}"}, timeout=60)
    if r.status_code != 200:
        raise ProviderUnavailable(f"PostHog query refused (HTTP {r.status_code})")
    return r.json().get("results") or []


def pull(days: int = 7, rows=None) -> dict:
    """Counts for the last `days`: events by kind, distinct visitors (cookieless, so a visitor is per page load day), top pages."""
    days = max(1, min(90, int(days)))
    names = ", ".join(f"'{n}'" for n in EVENTS)
    base = re.sub(r"[^A-Za-z0-9:/._-]", "", str(config.load()["site"]["base_url"]))      # the real site only, never a local test page
    where = f"timestamp > now() - interval {days} day and properties.$current_url like '{base}%'"
    got = rows if rows is not None else {
        "events": query(f"select event, count() from events where {where} and event in ({names}) group by event"),
        "pages": query(f"select properties.$pathname, count() from events where {where} "
                       "and event = '$pageview' group by properties.$pathname order by count() desc limit 5"),
    }
    counts = {v: 0 for v in EVENTS.values()}
    for name, n in got["events"]:
        if name in EVENTS:
            counts[EVENTS[name]] = int(n)
    views = counts["pageviews"]
    row = {"day": config.today_utc().isoformat(), "days": days, **counts,
           "shop_click_rate": round(counts["shop_clicks"] / views, 4) if views else None,
           "top_pages": [{"path": str(p), "views": int(n)} for p, n in got["pages"]]}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def latest() -> dict | None:
    rows = read_jsonl(LOG)
    return rows[-1] if rows else None
