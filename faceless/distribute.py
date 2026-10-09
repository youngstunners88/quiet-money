"""Distribution rails: how a finished video reaches people, what already works, and the one thing the owner does next.

Production is closed-loop; distribution is mostly the owner's accounts. This lists every rail with an honest state, from what the repository and
the environment can see (nothing is posted, nothing is paid for, no account is touched):

  ready        works now
  needs owner  built, waiting for an account, a key, a listing URL or a decision that is the owner's
  manual       works by hand from a ready pack
  planned      not built yet (the portfolio row says where it stands)

    python -m faceless distribute            # the table
    python -m faceless distribute --live     # also fetch the hub page once to confirm it is published
"""

from __future__ import annotations

import json

from faceless import config, offer
from faceless.config import Paths
from faceless.providers import ProviderUnavailable


def _row(rail: str, state: str, detail: str, nxt: str = "") -> dict:
    return {"rail": rail, "state": state, "detail": detail, "next": nxt}


def _connected() -> tuple[dict, str]:
    """Composio's connected apps, or the reason they cannot be read. A status page must never crash on a vendor error."""
    try:
        from faceless.providers import composio_tools as ct
        return ct.connected_toolkits(), ""
    except ProviderUnavailable as e:
        return {}, str(e)
    except Exception as e:  # noqa: BLE001
        return {}, f"{type(e).__name__}: {str(e)[:80]}"


def _hub_live(url: str) -> tuple[bool, str]:
    from faceless.providers import http
    try:
        r = http().get(url, timeout=20)
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}"
    return r.status_code == 200 and "Start" in r.text, f"HTTP {r.status_code}"


def metrics_rows() -> int:
    from faceless import analytics
    return len(analytics.load())


def status(live: bool = False, connected: dict | None = None) -> list[dict]:
    cfg = config.load()
    rows: list[dict] = []
    mode = cfg["publish"]["mode"]
    rows.append(_row("posting", "manual" if mode == "local" else "ready",
                     "every video becomes a pack in distribution/queue; the machine posts nothing" if mode == "local" else f"publish mode {mode}",
                     "post from POST.md, or pick an auto-posting rail below and say go (publish mode, plus the approval constant in tests/test_hygiene.py)" if mode == "local" else ""))
    up = bool(config.env("UPLOAD_POST_API_KEY")) and bool(config.env("UPLOAD_POST_USER"))
    rows.append(_row("auto-post: Upload-Post (TikTok, YouTube, Instagram, with the AI labels)", "ready" if up else "needs owner",
                     "keys present" if up else "UPLOAD_POST_API_KEY and UPLOAD_POST_USER are not set",
                     "" if up else "create an Upload-Post account, connect the three channel accounts, put both values in the Claude Code environment (never a file); daily TikTok posting needs a paid plan"))
    conn, why = (connected, "") if connected is not None else _connected()
    yt = "youtube" in conn
    rows.append(_row("auto-post: YouTube through Composio", "planned",
                     ("connected, used for metrics; " if yt else (why or "not connected; ") ) + "the engine has no upload code for it yet",
                     "" if yt else "`python -m faceless composio connect youtube`; an upload rail would also have to send the altered-or-synthetic label"))
    rows.append(_row("auto-post: Muapi publishers (tiktok-publish, youtube-publish)", "planned",
                     "listed in the Muapi catalog; tiktok-publish takes is_ai_generated, youtube-publish has no synthetic-content flag",
                     "the owner connects the accounts at muapi.ai first; YouTube would still need the label set by hand, so Upload-Post is the better rail"))
    st = offer.status()
    pinned = st["pinned"] > 0
    rows.append(_row("profile links (the hub page, tagged per platform)", "ready" if pinned else "needs owner",
                     st["hub"] or "[site] base_url is empty",
                     "" if pinned else "put the three URLs from `python -m faceless offer` in the Instagram and YouTube link fields now; TikTok shows its link field only at 1,000 followers or with a Verified Business Account (see faceless-offer references/link-rules.md)"))
    if live and st["hub"]:
        ok, detail = _hub_live(st["hub"])
        rows.append(_row("hub page published", "ready" if ok else "needs owner", f"{st['hub']} answered {detail}",
                         "" if ok else "the Website workflow publishes it on every push to main; check Settings > Pages"))
    cover = f"{st['videos']} video(s) logged; {st['draft']} waiting to be pinned, {st['pinned']} pinned"
    rows.append(_row("one offer per video", "ready" if st["link_missing"] == 0 else "needs owner", cover,
                     "" if st["link_missing"] == 0 else "set [site] base_url"))
    nl = cfg.get("newsletter", {})
    form = str(nl.get("form_action", "")).startswith("https://")
    addr = bool(nl.get("postal_address"))
    seq = (Paths.root / "channel" / "offers" / "autoresponder" / "sequence.json").exists()
    todo = [t for ok, t in ((form, "paste the email service's public form address into [newsletter] form_action"),
                            (addr, "add the postal address ([newsletter] postal_address; the law requires one on every issue)"),
                            (seq, "run `python -m faceless autoresponder`")) if not ok]
    rows.append(_row("email list (the asset you own)", "ready" if not todo else "needs owner",
                     f"signup form {'on' if form else 'off'}, postal address {'set' if addr else 'missing'}, 7-day sequence {'written' if seq else 'missing'}",
                     "; ".join(todo)))
    live_products = [d["slug"] for d in offer.destinations() if d["kind"] == "paid"]
    rows.append(_row("paid products", "ready" if live_products else "needs owner",
                     f"{len(live_products)} of {len(offer.catalog())} have a live listing URL in [offer] shop_urls",
                     "" if live_products else "list a product (channel/shop/<product>/CHECKLIST.md), then add its URL to [offer] shop_urls; `python -m faceless shop status` shows the storefront rails"))
    snippet = bool(cfg.get("site", {}).get("head_snippet"))
    n = metrics_rows()
    rows.append(_row("measurement", "ready" if snippet and n else "needs owner",
                     f"visit counter on the site: {'yes' if snippet else 'no'}; platform metrics rows: {n}",
                     "; ".join(t for ok, t in ((snippet, "save a (cookieless) counter's tag as the file named in [site] head_snippet"),
                                               (n > 0, "paste the weekly numbers or connect a source (faceless-analytics)")) if not ok)))
    rows.append(_row("weekly long-form compile (YouTube, tappable links, watch hours)", "planned", "portfolio C3: vetted, not built", ""))
    rows.append(_row("outreach drafts (collaborators, newsletters, podcasts)", "planned" if not (Paths.root / ".claude" / "skills" / "faceless-outreach").exists() else "ready",
                     "drafts only: the owner sends every message", ""))
    return rows


def render(rows: list[dict]) -> str:
    out = []
    for r in rows:
        out.append(f"{r['state']:12} {r['rail']}: {r['detail']}" + (f"\n{'':13}next: {r['next']}" if r["next"] else ""))
    return "\n".join(out)


def as_json(rows: list[dict]) -> str:
    return json.dumps(rows, indent=1)
