"""Storefront connections: what is connected, what the owner's next step is, and (with their token) draft products on Gumroad.

Gumroad has two rails, both owner-authorised and neither able to take anything live:
  read   Composio's managed OAuth: the owner clicks one Connect Link (`composio connect gumroad`) and the engine can read the account,
         products and sales (the metrics loop). Seven read tools; no product writes exist there.
  draft  the official `gumroad` CLI (github.com/antiwork/gumroad-cli) with GUMROAD_ACCESS_TOKEN in the environment: `products create --draft`
         builds an unpublished product with its files, cover, thumbnail and gallery. Publishing is one click in the dashboard and stays the
         owner's: this module has no publish command on purpose.
Etsy has no agent rail yet: Composio has no Etsy toolkit, and the Open API needs the owner's own developer app and a one-time OAuth login.
The listing pack (faceless/listing.py) is the way, about 15 minutes per listing, until the owner decides to create that app.

Everything here is a dry run until `--yes`, refuses while the studio is paused, and skips a product whose name already exists.
"""

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from faceless import config, events, listing, safety
from faceless.config import STUDIO, Paths
from faceless.providers import ProviderError, ProviderUnavailable

SALES = Paths.analytics / "sales.jsonl"


def gumroad_cli() -> str | None:
    return shutil.which("gumroad")


def token_present() -> bool:
    return bool(config.env("GUMROAD_ACCESS_TOKEN"))


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
    rows.append({"rail": "etsy", "state": "manual", "detail": "no agent rail: the listing pack is complete and checked",
                 "next": "open channel/shop/<product>/CHECKLIST.md; optional later: create a free Etsy developer app for draft listings"})
    return rows


def md_to_html(md: str) -> str:
    """The little Markdown our descriptions use (paragraphs, bullet lists, bold, italics) as the HTML Gumroad's description field takes."""
    out, in_list = [], False
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
    r = subprocess.run([cli, *argv], capture_output=True, text=True, timeout=timeout, env=os.environ.copy(), check=False)
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


def sales(days: int = 30) -> list[dict]:
    """Recent Gumroad sales through Composio (needs the owner's Connect Link), appended once each to analytics/sales.jsonl."""
    from datetime import datetime, timedelta, timezone

    from faceless.providers import composio_tools as ct
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    res = ct.execute("GUMROAD_GET_SALES", {"after": after})
    data = res.get("data", res)
    rows = (data.get("data", data) if isinstance(data, dict) else data) or {}
    rows = rows.get("sales", rows) if isinstance(rows, dict) else rows
    seen = set()
    if SALES.exists():
        seen = {json.loads(ln).get("id") for ln in SALES.read_text(encoding="utf-8").splitlines() if ln.strip()}
    fresh = []
    for s in rows if isinstance(rows, list) else []:
        sid = s.get("id")
        if sid and sid not in seen:
            fresh.append({"id": sid, "at": s.get("created_at"), "product": s.get("product_name") or s.get("product_id"), "usd": (s.get("price") or 0) / 100,
                          "refunded": bool(s.get("refunded"))})
    if fresh:
        SALES.parent.mkdir(parents=True, exist_ok=True)
        with open(SALES, "a", encoding="utf-8") as f:
            f.writelines(json.dumps(r) + "\n" for r in fresh)          # no buyer details are stored: the repo is public
    return fresh
