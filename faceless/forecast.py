"""The math: what the next batch costs, what the free tiers can carry, and what a funnel could earn.

Measured numbers come from our own files (ledger, jobs, scripts). Revenue numbers are ASSUMPTIONS from
[forecast] in studio.toml, printed as ranges and labeled as such: no channel data exists until posts go out.
`python -m faceless forecast` re-runs it; the weekly scan quotes it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from faceless import analytics, config, ledger
from faceless.config import Paths
from faceless.pipeline import cards
from faceless.providers import images as image_providers
from faceless.state import all_jobs

OPENROUTER_PER_IMAGE = 0.04
MUAPI_PER_IMAGE = 0.0057           # klein 4B turbo $0.0052 for most beats, $0.0104 for the hook still (Muapi catalog, 2026-10-08)
CF_PAID_PER_1K_NEURONS = 0.011     # Workers Paid, beyond the free 10k/day (Cloudflare pricing page, 2026-10-05)
CF_PAID_BASE_MONTH = 5.0
RENDER_MINUTES = 4.5               # measured wall-clock per video on this machine
DEFAULTS = {"views_per_video": [300, 2000, 15000], "rpm_per_1000_views": [0.02, 0.05, 0.10], "link_visit_rate": 0.01,
            "email_capture_rate": 0.25, "list_buys_per_month": 0.03, "product_price": 19.0, "videos_per_day": 5}


def measured() -> dict:
    """Averages over finished videos: generated images per video and numeric-callout beats per pillar."""
    gen, numeric = [], {}
    for j in all_jobs():
        if j.status not in ("packaged", "published"):
            continue
        try:
            imgs = json.loads((Paths.output / j.day / j.id / "images.json").read_text(encoding="utf-8"))
            gen.append(sum(1 for r in imgs if r.get("provider") not in ("card", "clip")))
        except (OSError, json.JSONDecodeError):
            pass
        try:
            s = json.loads((Paths.final / f"{j.id}.json").read_text(encoding="utf-8"))
            numeric.setdefault(j.pillar, []).append(sum(1 for b in s["beats"][1:] if cards.parse_number(b.get("callout", ""))))
        except (OSError, json.JSONDecodeError, KeyError):
            pass
    ccfg = config.load()["production"].get("cards", {})
    on = ccfg.get("mode") == "numbers"
    card_beats = {p: (round(sum(v) / len(v), 1) if on and p in ccfg.get("pillars", []) else 0.0) for p, v in numeric.items()}
    return {"images_per_video": round(sum(gen) / len(gen), 1) if gen else 12.0, "videos_measured": len(gen),
            "card_beats": card_beats}


def neurons_per_image() -> float:
    cfg = config.load()["images"]
    return image_providers.neurons(cfg["cloudflare_model"], cfg["width"], cfg["height"])


def next_batch(n: int = 5) -> dict:
    """Slots the next batch would fill, the series for each, and image/neuron/dollar needs under each provider setup."""
    from faceless import orchestrator
    per_day = len(config.load()["publish"]["slots"])
    m = measured()
    weights = analytics.pillar_weights()
    slots = orchestrator.open_slots(per_day, extra=n)
    rows, images = [], 0.0
    for d, k in slots:
        pillar = analytics.allocate(per_day, weights, datetime.fromisoformat(d).toordinal())[k]
        gen = max(0.0, m["images_per_video"] - m["card_beats"].get(pillar, 0.0))
        rows.append({"day": d, "slot": k + 1, "pillar": pillar, "images": round(gen, 1)})
        images += gen
    npi = neurons_per_image()
    free_left = max(0.0, config.load()["images"]["cloudflare_daily_neurons"] - ledger.used("cloudflare", "neurons"))
    free_images = free_left / npi
    over = max(0.0, images - free_images)
    return {"slots": rows, "images": round(images, 1), "neurons_per_image": round(npi),
            "free_images_left_today": round(free_images, 1), "render_minutes": round(len(rows) * RENDER_MINUTES),
            "cost": {"now (free Cloudflare, then Muapi)": round(over * MUAPI_PER_IMAGE, 2),
                     "Cloudflare Workers Paid (plus its $5 a month)": round(over * npi / 1000 * CF_PAID_PER_1K_NEURONS, 2),
                     "OpenRouter instead of Muapi (the old fallback)": round(over * OPENROUTER_PER_IMAGE, 2)}}


def monthly_cost(videos_per_day: int | None = None) -> dict:
    cfg = {**DEFAULTS, **config.load().get("forecast", {})}
    vpd = videos_per_day or cfg["videos_per_day"]
    m = measured()
    imgs = vpd * m["images_per_video"] * 30
    npi = neurons_per_image()
    free = config.load()["images"]["cloudflare_daily_neurons"] / npi * 30
    over = max(0.0, imgs - free)
    return {"images_per_month": round(imgs), "free_images_per_month": round(free),
            "muapi": round(over * MUAPI_PER_IMAGE, 2), "openrouter": round(over * OPENROUTER_PER_IMAGE, 2),
            "cloudflare_paid": round(CF_PAID_BASE_MONTH + over * npi / 1000 * CF_PAID_PER_1K_NEURONS, 2)}


def ladder() -> list[dict]:
    """Low/base/high monthly picture. ASSUMPTIONS, not predictions: edit [forecast] in studio.toml."""
    cfg = {**DEFAULTS, **config.load().get("forecast", {})}
    cost = monthly_cost()["muapi"]
    out = []
    for name, v, rpm in zip(("low", "base", "high"), cfg["views_per_video"], cfg["rpm_per_1000_views"]):
        views = cfg["videos_per_day"] * 30 * v
        ads = views / 1000 * rpm
        visitors = views * cfg["link_visit_rate"]
        list_add = visitors * cfg["email_capture_rate"]
        # a list that grows all month sells to its average size; one product at one price
        product = list_add / 2 * cfg["list_buys_per_month"] * cfg["product_price"]
        out.append({"case": name, "views": round(views), "ads": round(ads, 2), "email_adds": round(list_add),
                    "product": round(product, 2), "total": round(ads + product, 2), "cost": cost, "net": round(ads + product - cost, 2)})
    return out


def report() -> str:
    b, mc, lad, m = next_batch(), monthly_cost(), ladder(), measured()
    cfg = {**DEFAULTS, **config.load().get("forecast", {})}
    L = [f"# The math ({datetime.now(timezone.utc):%Y-%m-%d})", "",
         f"Measured on {m['videos_measured']} finished videos: {m['images_per_video']} generated images per video; one Cloudflare "
         f"image costs {b['neurons_per_image']} neurons, so the free 10k/day carries {round(10000 / b['neurons_per_image'])} images "
         f"(about {round(10000 / b['neurons_per_image'] / m['images_per_video'], 1)} videos).", "",
         "## Next batch", "| day | slot | series | images to generate |", "|---|---|---|---|"]
    L += [f"| {r['day']} | {r['slot']} | {r['pillar']} | {r['images']} |" for r in b["slots"]]
    L += ["", f"Total {b['images']} images; free Cloudflare left today carries {b['free_images_left_today']}. "
              f"Render time about {b['render_minutes']} minutes.", "", "Cost of the batch by image setup:"]
    L += [f"- {k}: ${v}" for k, v in b["cost"].items()]
    from faceless.providers import images as image_providers
    bal = image_providers.muapi_balance()
    if bal is not None:
        per_day = mc["muapi"] / 30
        L += ["", f"Muapi wallet: ${bal:.2f}" + (f", about {bal / per_day:.0f} days of images at this rate." if per_day else ".")]
    L += ["", f"## A month at {cfg['videos_per_day']} videos/day", f"{mc['images_per_month']} images; free tier covers {mc['free_images_per_month']}.",
          f"- Muapi for the rest: ${mc['muapi']}/month (the plan)", f"- OpenRouter for the rest instead: ${mc['openrouter']}/month",
          f"- Cloudflare Workers Paid: ${mc['cloudflare_paid']}/month (all-in, including the $5 base: dearer than Muapi at this volume)",
          "", "## What it could earn (ASSUMPTIONS, not data: no posts are live, so no real views exist yet)",
          f"Assumed: {cfg['link_visit_rate']:.0%} of views reach the link, {cfg['email_capture_rate']:.0%} of those join the list, "
          f"{cfg['list_buys_per_month']:.0%} of the list buys one ${cfg['product_price']:.0f} product a month, Shorts ads pay "
          f"${cfg['rpm_per_1000_views'][0]}-{cfg['rpm_per_1000_views'][2]} per 1,000 views.", "",
          "| case | views/mo | ad revenue | list adds | product revenue | total | cost | net |", "|---|---|---|---|---|---|---|---|"]
    L += [f"| {r['case']} | {r['views']:,} | ${r['ads']:,} | {r['email_adds']:,} | ${r['product']:,} | ${r['total']:,} | ${r['cost']} | ${r['net']:,} |" for r in lad]
    L += ["", "Read it as: costs are small and known; revenue is dominated by what happens after the view (list, products, services),",
          "and ads on Shorts alone are close to rounding error until views reach the millions."]
    return "\n".join(L)
