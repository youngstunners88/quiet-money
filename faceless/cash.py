"""The money desk: every rail that can bring in money, its real state, what the agent has already done, and the owner's one step,
ranked by how soon it can pay. Reads only.

The owner's attention is the scarcest input the business has, so this turns it into a short list of paste-ready steps instead of a
dashboard to interpret. States come from the engine itself (catalog, studio.toml, the service desk's outcomes, the gig folders, sales);
"how soon" is a labelled judgment, not a measurement, until a rail has made its first sale. Nothing here sets a price, lists a product,
sends a message or posts (rule 9): it prepares, the owner acts.

`python -m faceless cash [--json]` prints the desk and writes `channel/empire/CASH.md`. HQ shows the top steps.
"""

from __future__ import annotations

import json

from faceless import config
from faceless.config import Paths
from faceless.fsutil import read_jsonl, write_atomic

OUT = Paths.root / "channel" / "empire" / "CASH.md"
CATALOG = Paths.root / "channel" / "shop" / "catalog.json"


def _catalog() -> list[dict]:
    try:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    items = data if isinstance(data, list) else data.get("products", data)
    return list(items.values()) if isinstance(items, dict) else list(items)


def products() -> dict:
    """Gumroad: which built products are live, which wait on the owner's price."""
    cfg = config.load()
    live = (cfg.get("offer") or {}).get("shop_urls") or {}
    waiting = [p for p in _catalog() if p.get("id") not in live]
    drafted = {r.get("product") for r in read_jsonl(Paths.state / "journal.jsonl") if r.get("type") == "SHOP_DRAFT_CREATED" and not r.get("published")}
    ready = [p["id"] for p in waiting if p["id"] in drafted]
    return {
        "rail": "Gumroad products", "kind": "product", "soon": "days (judgment: needs traffic; the planner has been live since 2026-10-20)",
        "state": "live" if live else "blocked", "live": sorted(live), "waiting": [{"id": p["id"], "placeholder_price": p.get("price")} for p in waiting],
        "drafts_ready": ready,
        "agent_did": "built and verified every product, its listing pack and the listing gauntlet"
                     + (f"; {len(ready)} unpublished drafts already sit in the Gumroad dashboard" if ready else "")
                     + "; the offer layer points each series at its product once live",
        "owner_step": ("Settle the prices and say go: reply with one line, for example \"list " + ", ".join(f"{p['id']} at ${p.get('price')}" for p in waiting)
                       + "\". The listing then goes live through `shop publish` and every math and escape video starts offering it.") if waiting else None,
        "minutes": 2,
    }


def etsy() -> dict:
    """Etsy: buyers already search it for printables and planners; the rail needs the owner's app key and one login."""
    from faceless import etsy as e
    st = e.status()
    ready = st["state"] == "ready"
    return {
        "rail": "Etsy (printables and planners)", "kind": "product", "state": "ready" if ready else "blocked",
        "soon": "days to weeks (judgment: Etsy search brings buyers a new shop could not reach on its own)",
        "agent_did": "Etsy listing packs (pictures, video, copy, checklist) built and checked; the draft rail is written and waits on the login",
        "owner_step": None if ready else ("Open the Etsy rail (10 minutes, once): " + st["next"]),
        "minutes": 10,
    }


def service() -> dict:
    """The Web3 video and KOL desk: drafts queue daily; a reply is a project."""
    from faceless import outbound
    p, r = outbound.pipeline(), outbound.review()
    sent = r["sent"]
    replies = sum(v for k, v in r["counts"].items() if k.startswith("reply") or k in ("call-booked", "closed"))
    return {
        "rail": "Web3 video and KOL service", "kind": "service", "state": "live" if sent else "blocked",
        "soon": "1-3 weeks from the first sends (judgment: one positive reply per few dozen personal notes is the usual cold-outreach range)",
        "sent": sent, "replies": replies, "waiting_here": len(p["packages_waiting"]),
        "agent_did": "the 07:47 UTC hunt finds, researches, scores, drafts and gates three notes a day and puts them in its reply to you",
        "owner_step": ("Send today's three drafts from the outbound report (each names its channel and contact route), then record each: "
                       "`python -m faceless outbound outcome <slug> sent`. When one replies, quote from channel/services/web3-video/templates/quote.md: $65 for 30 s, $120 for 75 s (your prices, 2026-10-23)."),
        "minutes": 15,
    }


def gigs() -> list[dict]:
    """The two Fiverr gigs: ready to paste; listing them is the owner's account step."""
    out = []
    for gid, name, folder in (("S1", "Fiverr: faceless-channel brand kit", "brand-kit"), ("S2", "Fiverr: concept sheets (logo, mascot, art)", "studio")):
        root = Paths.root / "channel" / "services" / folder
        ready = (root / "GIG.md").exists()
        out.append({
            "rail": name, "kind": "gig", "state": "ready" if ready else "blocked", "id": gid,
            "soon": "1-3 weeks (judgment: a new seller's first order; marketplaces already have the buyers)",
            "agent_did": f"the engine, the gig copy with tiers and AI disclosure, and gallery samples in channel/services/{folder}/",
            "owner_step": f"Create the gig on Fiverr: paste title, tiers and description from channel/services/{folder}/GIG.md, upload the sample pictures, publish.",
            "minutes": 30,
        })
    return out


def growth() -> list[dict]:
    """Not money today, but what feeds every rail above."""
    from faceless import collab
    st = collab.status()
    return [{
        "rail": "Podcast collaborations", "kind": "growth", "state": "ready", "soon": "feeds the audience, not a sale",
        "agent_did": f"{st['looked_at']} shows looked at; notes drafted for small, active finance podcasts", "sent": st["outcomes"]["sent"],
        "owner_step": "Send the collaboration notes you were given (find each show's contact on its own page), then `collab outcome <slug> sent`.",
        "minutes": 10,
    }]


def desk() -> dict:
    from faceless import marketing
    rails = [service(), products(), etsy(), *gigs(), *growth()]
    order = {"service": 0, "product": 1, "gig": 2, "growth": 3}      # the biggest ticket first, then the two-minute price yes, then the gigs
    steps = sorted((r for r in rails if r.get("owner_step")), key=lambda r: (order.get(r["kind"], 2), r["minutes"]))
    return {"asOf": config.today_utc().isoformat(), "sales": marketing.sales_summary(), "rails": rails,
            "next30": [{"rail": r["rail"], "step": r["owner_step"], "minutes": r["minutes"]} for r in steps][:3]}


def markdown(d: dict) -> str:
    s = d["sales"]
    L = [f"# Money desk ({d['asOf']})", "", f"Sales so far: {s['sales']}, ${s['net_estimate']:.2f} net. Nothing here sets a price, lists, sends or posts: "
         "the agent prepares, you act.", "", "## Your next 30 minutes", ""]
    L += [f"{i}. **{x['rail']}** (about {x['minutes']} min): {x['step']}" for i, x in enumerate(d["next30"], 1)]
    L += ["", "## Every rail", "", "| rail | state | how soon (judgment) | what the agent already did |", "|---|---|---|---|"]
    L += [f"| {r['rail']} | {r['state']} | {r['soon']} | {r['agent_did']} |" for r in d["rails"]]
    return "\n".join(L) + "\n"


def write() -> dict:
    d = desk()
    write_atomic(OUT, markdown(d))
    return d

