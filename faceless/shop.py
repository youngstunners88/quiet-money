"""Storefront connections: what is connected, what the owner's next step is, and (with their token) draft products on Gumroad.

Gumroad has two rails, both owner-authorised and neither able to take anything live:
  read   Composio's managed OAuth: the owner clicks one Connect Link (`composio connect gumroad`) and the engine can read the account,
         products and sales (the metrics loop). Seven read tools; no product writes exist there.
  draft  the official `gumroad` CLI (github.com/antiwork/gumroad-cli) with GUMROAD_ACCESS_TOKEN in the environment: `products create --draft`
         builds an unpublished product with its files, cover, thumbnail and gallery. Publishing is one click in the dashboard and stays the
         owner's: this module has no publish command on purpose.
Etsy has its own rail (faceless/etsy.py): the Open API v3 with the owner's developer app and a one-time OAuth login; it creates DRAFT listings too.
Going live is gated by `approval()`: studio.toml [shop.approved."<product>"] must name the product's current catalog price and the rail. `publish()` then
asks the rail to set the draft live; without that entry it refuses, so a "ship it" without a settled price cannot publish anything.

Everything here is a dry run until `--yes`, refuses while the studio is paused, and skips a product whose name already exists.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess

from faceless import config, events, listing, safety
from faceless.config import STUDIO, Paths
from faceless.fsutil import read_jsonl
from faceless.providers import ProviderError, ProviderUnavailable

SALES = Paths.analytics / "sales.jsonl"


def gumroad_cli() -> str | None:
    """The gumroad CLI on PATH, or where `go install` puts it (a routine's shell does not add ~/go/bin)."""
    found = shutil.which("gumroad")
    if found:
        return found
    home = os.path.join(os.path.expanduser("~"), "go", "bin", "gumroad")
    return home if os.access(home, os.X_OK) else None


TOKEN_NAMES = ("GUMROAD_ACCESS_TOKEN", "GUMROAD_TOKEN", "GUMROAD")


def token() -> str | None:
    """The owner's environment names the Gumroad token GUMROAD; the CLI wants GUMROAD_ACCESS_TOKEN."""
    return config.env(*TOKEN_NAMES)


def token_present() -> bool:
    return bool(token())


def status() -> list[dict]:
    """One row per rail: state is 'ready', 'needs owner' or 'manual'; `next` says exactly what to do."""
    rows = []
    try:
        from faceless.providers import composio_tools as ct
        conn = ct.connected_toolkits()
        read_ok, read_detail = "gumroad" in conn, "Composio works; Gumroad is not connected yet"
    except ProviderUnavailable as e:
        read_ok, read_detail = False, str(e)
    except Exception as e:  # noqa: BLE001 - a status page must never crash on a vendor error
        read_ok, read_detail = False, f"{type(e).__name__}: {str(e)[:80]}"
    rows.append({"rail": "gumroad read (sales, products)", "state": "ready" if read_ok else "needs owner",
                 "detail": read_detail if not read_ok else "connected through Composio",
                 "next": "" if read_ok else "run `python -m faceless composio connect gumroad` and open the link while signed in to Gumroad"})
    ready = token_present() and bool(gumroad_cli())
    rows.append({"rail": "gumroad draft products", "state": "ready" if ready else "needs owner",
                 "detail": f"token {'set' if token_present() else 'missing'}, CLI {'found' if gumroad_cli() else 'not installed'}",
                 "next": "" if ready else "Gumroad > Settings > Advanced > Applications > create an access token, add it to the environment as GUMROAD_ACCESS_TOKEN; "
                                         "the agent then installs the CLI (`go install github.com/antiwork/gumroad-cli/cmd/gumroad@<release tag>`)"})
    from faceless import etsy
    e = etsy.status()
    rows.append({"rail": "etsy draft + publish", "state": e["state"], "detail": f"app key {'set' if e['api_key'] else 'missing'}, login {'saved' if e['tokens'] else 'not done'}",
                 "next": e["next"] or "ready"})
    return rows


def md_to_html(md: str) -> str:
    """The little Markdown our descriptions use (paragraphs, bullet lists, bold, italics) as the HTML Gumroad's description field takes."""
    out = []
    for block in re.split(r"\n\s*\n", md.strip()):
        lines = block.splitlines()
        if all(ln.strip().startswith("- ") for ln in lines):
            out.append("<ul>" + "".join(f"<li>{_inline(ln.strip()[2:])}</li>" for ln in lines) + "</ul>")
        elif any(ln.strip().startswith("- ") for ln in lines):
            head = [ln for ln in lines if not ln.strip().startswith("- ")]
            items = [ln.strip()[2:] for ln in lines if ln.strip().startswith("- ")]
            out.append(f"<p>{_inline(' '.join(h.strip() for h in head))}</p><ul>" + "".join(f"<li>{_inline(i)}</li>" for i in items) + "</ul>")
        else:
            out.append(f"<p>{_inline(' '.join(ln.strip() for ln in lines))}</p>")
    return "".join(out)


def _inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", s)


def create_args(p: dict) -> list[str]:
    """The `gumroad products create` arguments for one product: always a draft, files and pictures from the built pack."""
    folder = listing.OUT / p["id"]
    imgs = sorted((folder / "etsy" / "images").glob("*.jpg"))
    cover, thumb, video = folder / "gumroad" / "cover.jpg", folder / "gumroad" / "thumbnail.jpg", folder / "etsy" / "video.mp4"
    if not (imgs and cover.exists() and thumb.exists()):
        raise ProviderError(f"{p['id']}: build the pack first (`python -m faceless listing build {p['id']}`)")
    g = p["gumroad"]
    argv = ["products", "create", "--name", g["name"], "--price", f"{p['price']:.2f}", "--draft",
            "--description", md_to_html(g["description"]), "--custom-summary", g["summary"]]
    for t in g["tags"]:
        argv += ["--tag", t]
    for f in [p["file"], *p.get("extra_files", [])]:
        argv += ["--file", str(STUDIO / f)]
    argv += ["--cover-image", str(cover), "--thumbnail", str(thumb)]
    for im in imgs[1:6]:
        argv += ["--preview-image", str(im)]
    if video.exists():
        argv += ["--preview-video", str(video)]
    return argv + ["--json", "--no-input"]


def _run(argv: list[str], timeout: int = 600) -> dict:
    cli = gumroad_cli()
    if not cli:
        raise ProviderUnavailable("the gumroad CLI is not installed")
    env = os.environ.copy()
    if token():
        env["GUMROAD_ACCESS_TOKEN"] = token()
    r = subprocess.run([cli, *argv], capture_output=True, text=True, timeout=timeout, env=env, check=False)
    try:
        data = json.loads(r.stdout or "{}")
    except ValueError:
        data = {}
    if r.returncode != 0 or data.get("success") is False:
        raise ProviderError(f"gumroad {' '.join(argv[:2])}: {str(data.get('error') or r.stderr or r.stdout)[:300]}")
    return data


def plan(only: str | None = None) -> list[tuple[str, list[str]]]:
    """[(product id, argv)] for every product whose pack is built. Nothing runs."""
    out = []
    for p in listing.products(only):
        out.append((p["id"], create_args(p)))
    return out


def push(only: str | None = None, run: bool = False) -> list[dict]:
    """Create DRAFT products on Gumroad. A dry run lists what would be created; `run=True` needs the token, the CLI and an unpaused studio."""
    steps = plan(only)
    if not run:
        return [{"product": pid, "action": "would create a draft", "name": listing.products(pid)[0]["gumroad"]["name"], "args": len(argv)} for pid, argv in steps]
    safety.guard("shop push")
    if not token_present():
        raise ProviderUnavailable("GUMROAD_ACCESS_TOKEN is not set in the environment")
    existing = {x.get("name") for x in _run(["products", "list", "--all", "--json", "--no-input"]).get("products", [])}
    results = []
    for pid, argv in steps:
        name = listing.products(pid)[0]["gumroad"]["name"]
        if name in existing:
            results.append({"product": pid, "action": "skipped: a product with this name already exists", "name": name})
            continue
        data = _run(argv, timeout=1800)
        prod = data.get("product", {})
        events.emit("SHOP_DRAFT_CREATED", product=pid, gumroad_id=str(prod.get("id", ""))[:24], published=bool(prod.get("published")))
        results.append({"product": pid, "action": "draft created" if not prod.get("published") else "CREATED PUBLISHED: unpublish it", "name": name, "id": prod.get("id")})
    return results


def _sale_row(s: dict) -> dict | None:
    """One sale as stored: ids, time, product, dollars, refunded and the source tag the buyer arrived with. No buyer details: the repo is public."""
    sid = s.get("id") or s.get("sale_id")
    if not sid:
        return None
    cents = s.get("price")
    usd = float(cents) / 100 if isinstance(cents, (int, float)) else float(str(s.get("formatted_total_price") or "0").replace("$", "").replace(",", "") or 0)
    params = s.get("url_params") if isinstance(s.get("url_params"), dict) else {}
    return {"id": sid, "at": s.get("created_at") or s.get("timestamp"), "product": s.get("product_name") or s.get("product_id"), "usd": usd,
            "refunded": bool(s.get("refunded")), "src": params.get("src") or params.get("utm_source") or "", "discover": bool(s.get("discover_fee_charged"))}


def _record_sales(rows: list) -> list[dict]:
    seen = {r.get("id") for r in read_jsonl(SALES)} if SALES.exists() else set()
    fresh = []
    for s in rows if isinstance(rows, list) else []:
        row = _sale_row(s) if isinstance(s, dict) else None
        if row and row["id"] not in seen:
            fresh.append(row)
            seen.add(row["id"])
    if fresh:
        SALES.parent.mkdir(parents=True, exist_ok=True)
        with open(SALES, "a", encoding="utf-8") as f:
            f.writelines(json.dumps(r) + "\n" for r in fresh)
    return fresh


def sales(days: int = 30) -> list[dict]:
    """Recent Gumroad sales appended once each to analytics/sales.jsonl: through the gumroad CLI when the token and CLI exist, else through Composio (needs the owner's Connect Link)."""
    from datetime import datetime, timedelta, timezone
    if token_present() and gumroad_cli():
        after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        return _record_sales(_run(["sales", "list", "--all", "--after", after, "--json", "--no-input"]).get("sales", []))
    from faceless.providers import composio_tools as ct
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res = ct.execute("GUMROAD_GET_SALES", {"after": after})
    data = res.get("data", res)
    rows = (data.get("data", data) if isinstance(data, dict) else data) or {}
    rows = rows.get("sales", rows) if isinstance(rows, dict) else rows
    return _record_sales(rows)


# ---------------------------------------------------------------- going live (the owner's yes)

def approval(pid: str, rail: str) -> tuple[bool, str]:
    """(allowed, why not). The owner's entry in studio.toml must carry the product's CURRENT price, so a price change cancels an old yes."""
    p = listing.products(pid)[0]
    entry = ((config.load().get("shop") or {}).get("approved") or {}).get(pid) or {}
    if not entry:
        return False, f'no approval: add [shop.approved."{pid}"] with price = {p["price"]} and {rail} = true to studio.toml once the owner has settled the price'
    if abs(float(entry.get("price", -1)) - float(p["price"])) > 1e-9:
        return False, f"the approval is for ${entry.get('price')} but the catalog price is ${p['price']}: the owner confirms the current price first"
    if entry.get(rail) is not True:
        return False, f"the owner has not approved the {rail} rail for {pid}"
    bad = [g.name for g in listing.check(pid).get(pid, []) if g.hard and not g.ok]
    if bad:
        return False, f"the listing gauntlet fails: {bad}"
    return True, ""


def draft_all(pid: str, rails: tuple[str, ...] = ("gumroad", "etsy")) -> list[dict]:
    """Create DRAFTS on each rail that is ready; a rail that is not ready is reported with the owner's next step, never skipped silently."""
    out = []
    for rail in rails:
        try:
            if rail == "gumroad":
                out += push(pid, run=True)
            elif rail == "etsy":
                from faceless import etsy
                out.append({"rail": "etsy", **etsy.create_draft(pid)})
        except ProviderUnavailable as e:
            out.append({"rail": rail, "product": pid, "action": "not ready", "why": str(e)[:200]})
        except ProviderError as e:
            out.append({"rail": rail, "product": pid, "action": "failed", "why": str(e)[:300]})
    return out


def publish(pid: str, rail: str, listing_id: str | None = None) -> dict:
    """Set a DRAFT live on one rail, only with the owner's approval of this price. Returns what happened; raises ProviderError when refused."""
    safety.guard(f"publish {rail}")
    ok, why = approval(pid, rail)
    if not ok:
        raise ProviderError(f"refused: {why}")
    if rail == "etsy":
        from faceless import etsy
        lid = listing_id or (etsy.existing(listing.products(pid)[0]["etsy"]["title"]) or {}).get("listing_id")
        if not lid:
            raise ProviderError("no Etsy draft found for this product: run draft first")
        res = etsy.publish_listing(lid)
        events.emit("SHOP_PUBLISHED", product=pid, rail="etsy", listing_id=str(lid))
        return {"rail": "etsy", "listing_id": lid, "state": res.get("state"), "url": res.get("url", "")}
    if rail == "gumroad":
        name = listing.products(pid)[0]["gumroad"]["name"]
        prods = _run(["products", "list", "--all", "--json", "--no-input"]).get("products", [])
        found = next((x for x in prods if x.get("name") == name), None)
        if not found:
            raise ProviderError("no Gumroad draft found for this product: run draft first")
        res = _run(["products", "publish", str(found["id"]), "--json", "--no-input"])
        events.emit("SHOP_PUBLISHED", product=pid, rail="gumroad", gumroad_id=str(found["id"])[:24])
        prod = res.get("product", found)
        return {"rail": "gumroad", "id": found["id"], "published": bool(prod.get("published", True)), "url": prod.get("short_url") or prod.get("url", "")}
    raise ProviderError(f"unknown rail {rail!r}")
