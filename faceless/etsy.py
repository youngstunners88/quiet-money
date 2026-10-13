"""Etsy Open API v3 rail: connect once, then draft and (only with the owner's approval) publish a digital listing from the built pack.

    python -m faceless etsy status                 what is connected and what the owner still has to do
    python -m faceless etsy auth                   print the one-time login link (PKCE); the owner opens it signed in to the shop
    python -m faceless etsy auth --code CODE       exchange the code that Etsy shows after the login; the tokens are saved outside the repository
    python -m faceless etsy plan <product>         the exact listing that would be created (no network)
    python -m faceless etsy draft <product> --yes  create an inactive DRAFT listing with its two PDFs, images and video (never live)

Credentials (never in a file in this repository, CLAUDE.md rule 11):
  ETSY_API_KEY        the "keystring" of the owner's app (etsy.com/developers/your-apps; personal access is enough for one's own shop)
  ETSY_SHARED_SECRET  optional; sent as keystring:secret when set
  tokens              saved by `etsy auth --code` under ~/.config/quiet-money/ (or ETSY_SECRETS_DIR), mode 600. Etsy rotates the refresh token on every refresh,
                      so the file is the source of truth; ETSY_REFRESH_TOKEN in the environment only seeds the first refresh.
  ETSY_SHOP_ID        optional; found from the token's user id when absent
  [etsy] in studio.toml: redirect_uri, taxonomy_id (the planner category; looked up by name when 0)

Going live is a separate, gated act (`publish`): see shop.approval. A draft costs nothing; publishing costs Etsy's $0.20 listing fee, so it is the owner's yes.
Written to Etsy's documentation; not yet exercised against the live API because no credentials were present when this was built.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

from faceless import config, listing, providers
from faceless.config import STUDIO
from faceless.fsutil import write_atomic
from faceless.providers import ProviderError, ProviderUnavailable

API = "https://openapi.etsy.com/v3/application"
TOKEN_URL = "https://api.etsy.com/v3/public/oauth/token"
CONNECT_URL = "https://www.etsy.com/oauth/connect"
SCOPES = "listings_w listings_r listings_d shops_r"
TITLE_MAX, TAG_MAX, TAGS = 140, 20, 13
FILE_MAX = 20 * 2**20                    # Etsy: 20 MB per file, 5 files per listing
_cache: dict = {}


def secrets_dir() -> Path:
    return Path(os.environ.get("ETSY_SECRETS_DIR") or Path.home() / ".config" / "quiet-money")


def _tokens_file() -> Path:
    return secrets_dir() / "etsy-token.json"


def _cfg() -> dict:
    return config.load().get("etsy", {})


def keystring() -> str | None:
    return config.env("ETSY_API_KEY")


def _api_key_header() -> str:
    key, sec = keystring(), config.env("ETSY_SHARED_SECRET")
    return f"{key}:{sec}" if sec else str(key)


def _save_tokens(data: dict) -> None:
    f = _tokens_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    keep = {"access_token": data["access_token"], "refresh_token": data["refresh_token"], "expires_at": int(time.time()) + int(data.get("expires_in", 3600)) - 60}
    write_atomic(f, json.dumps(keep))
    os.chmod(f, 0o600)
    _cache.clear()


def _load_tokens() -> dict:
    f = _tokens_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    seed = config.env("ETSY_REFRESH_TOKEN")
    return {"refresh_token": seed, "expires_at": 0} if seed else {}


# ---------------------------------------------------------------- the one-time login (OAuth 2 with PKCE)

def auth_url() -> str:
    if not keystring():
        raise ProviderUnavailable("ETSY_API_KEY is not set (the keystring of the owner's Etsy app)")
    verifier = secrets.token_urlsafe(64)[:100]
    state = secrets.token_urlsafe(16)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    f = secrets_dir() / "etsy-pkce.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(f, json.dumps({"verifier": verifier, "state": state}))
    os.chmod(f, 0o600)
    q = {"response_type": "code", "client_id": keystring(), "redirect_uri": _cfg().get("redirect_uri", "https://localhost/callback"), "scope": SCOPES,
         "state": state, "code_challenge": challenge, "code_challenge_method": "S256"}
    return f"{CONNECT_URL}?{urlencode(q)}"


def finish_auth(code: str, state: str | None = None) -> dict:
    f = secrets_dir() / "etsy-pkce.json"
    if not f.exists():
        raise ProviderError("no login in progress: run `etsy auth` first")
    saved = json.loads(f.read_text(encoding="utf-8"))
    if state and state != saved["state"]:
        raise ProviderError("the state from Etsy does not match: start again with `etsy auth`")
    r = providers.http().post(TOKEN_URL, data={"grant_type": "authorization_code", "client_id": keystring(), "redirect_uri": _cfg().get("redirect_uri", "https://localhost/callback"),
                                               "code": code, "code_verifier": saved["verifier"]}, timeout=30)
    if r.status_code != 200:
        raise ProviderError(f"Etsy refused the code (HTTP {r.status_code}): {config.redact(r.text)[:200]}")
    _save_tokens(r.json())
    f.unlink(missing_ok=True)
    return {"saved": str(_tokens_file()), "shop_id": shop_id()}


def access_token() -> str:
    t = _cache.get("token")
    if t and t["expires_at"] > time.time():
        return t["access_token"]
    cur = _load_tokens()
    if cur.get("access_token") and cur.get("expires_at", 0) > time.time():
        _cache["token"] = cur
        return cur["access_token"]
    if not cur.get("refresh_token"):
        raise ProviderUnavailable("Etsy is not connected: set ETSY_API_KEY, then run `python -m faceless etsy auth` and open the link signed in to the shop")
    r = providers.http().post(TOKEN_URL, data={"grant_type": "refresh_token", "client_id": keystring(), "refresh_token": cur["refresh_token"]}, timeout=30)
    if r.status_code != 200:
        raise ProviderError(f"Etsy refused the refresh token (HTTP {r.status_code}); the owner runs `etsy auth` again")
    data = r.json()
    _save_tokens(data)
    _cache["token"] = _load_tokens()
    return data["access_token"]


# ---------------------------------------------------------------- requests

def _call(method: str, path: str, *, data: dict | None = None, files: dict | None = None, params: dict | None = None) -> dict:
    if not keystring():
        raise ProviderUnavailable("ETSY_API_KEY is not set")
    h = {"x-api-key": _api_key_header(), "Authorization": f"Bearer {access_token()}"}
    r = providers.http().request(method, f"{API}{path}", headers=h, data=data, files=files, params=params, timeout=300 if files else 60)
    if r.status_code == 429:
        raise ProviderError("Etsy rate limit reached; try again later")
    if r.status_code >= 300:
        raise ProviderError(f"Etsy {method} {path.split('?')[0]}: HTTP {r.status_code}: {config.redact(r.text)[:300]}")
    return r.json() if r.content else {}


def shop_id() -> str:
    if config.env("ETSY_SHOP_ID"):
        return str(config.env("ETSY_SHOP_ID"))
    if "shop" in _cache:
        return _cache["shop"]
    uid = access_token().split(".")[0]
    res = _call("GET", f"/users/{uid}/shops")
    sid = res.get("shop_id") or (res.get("results") or [{}])[0].get("shop_id")
    if not sid:
        raise ProviderError("the token's user has no Etsy shop")
    _cache["shop"] = str(sid)
    return _cache["shop"]


def taxonomy_id() -> int:
    """The planner category. Etsy's list of categories is walked by name when studio.toml leaves it at 0."""
    want = int(_cfg().get("taxonomy_id", 0))
    if want:
        return want
    nodes = _call("GET", "/seller-taxonomy/nodes").get("results", [])
    hits: list[tuple[str, int]] = []

    def walk(ns, trail):
        for n in ns:
            path = trail + [n.get("name", "")]
            if n.get("name", "").lower() == "planners":
                hits.append((" > ".join(path), n["id"]))
            walk(n.get("children", []), path)
    walk(nodes, [])
    if len(hits) != 1:
        raise ProviderError(f"{len(hits)} Etsy categories are called Planners ({[h[0] for h in hits][:3]}); set [etsy] taxonomy_id in studio.toml")
    return int(hits[0][1])


# ---------------------------------------------------------------- the listing

def _pack(p: dict) -> Path:
    return listing.OUT / p["id"]


def payload(p: dict, taxonomy: int = 0) -> dict:
    """The create-listing form for one product, from the checked pack. Raises when anything breaks Etsy's limits."""
    e = p["etsy"]
    title = (_pack(p) / "etsy" / "title.txt").read_text(encoding="utf-8").strip() if (_pack(p) / "etsy" / "title.txt").exists() else e["title"]
    tags = [t.strip() for t in e["tags"]]
    desc = (_pack(p) / "etsy" / "description.txt").read_text(encoding="utf-8").strip() if (_pack(p) / "etsy" / "description.txt").exists() else e["description"]
    bad = []
    if len(title) > TITLE_MAX:
        bad.append(f"title is {len(title)} characters (max {TITLE_MAX})")
    if len(tags) != TAGS or any(len(t) > TAG_MAX for t in tags):
        bad.append(f"need {TAGS} tags of {TAG_MAX} characters or fewer")
    if bad:
        raise ProviderError(f"{p['id']}: " + "; ".join(bad))
    return {"quantity": 999, "title": title, "description": desc, "price": f"{float(p['price']):.2f}", "who_made": "i_did", "when_made": "2020_2026",
            "taxonomy_id": taxonomy, "type": "download", "is_supply": "false", "should_auto_renew": "true", "tags": ",".join(tags), "state": "draft"}


def uploads(p: dict) -> dict:
    """Files for the listing, with Etsy's limits checked: at most 5 files of 20 MB, 10 images, one video."""
    pdfs = [STUDIO / f for f in [p["file"], *p.get("extra_files", [])]]
    imgs = sorted((_pack(p) / "etsy" / "images").glob("*.jpg"))[:10]
    video = _pack(p) / "etsy" / "video.mp4"
    bad = [f"{f.name} is missing" for f in pdfs if not f.exists()]
    bad += [f"{f.name} is {f.stat().st_size / 2**20:.1f} MB (Etsy: 20 MB)" for f in pdfs if f.exists() and f.stat().st_size > FILE_MAX]
    if not imgs:
        bad.append("no listing images: run `python -m faceless listing build`")
    if bad or len(pdfs) > 5:
        raise ProviderError(f"{p['id']}: " + "; ".join(bad or ["more than 5 files"]))
    return {"files": pdfs, "images": imgs, "video": video if video.exists() else None}


def plan(pid: str) -> dict:
    p = listing.products(pid)[0]
    pl, up = payload(p, int(_cfg().get("taxonomy_id", 0))), uploads(p)
    return {"product": pid, "title": pl["title"], "price": pl["price"], "state": "draft", "files": [f.name for f in up["files"]], "images": len(up["images"]),
            "video": bool(up["video"]), "tags": pl["tags"].split(","), "taxonomy": "from [etsy] taxonomy_id or looked up by name (Planners)",
            "by_hand": ["Etsy's AI-disclosure / creativity question on the listing form, if it asks one", "the owner's yes to go live (shop.approval)"]}


def existing(title: str) -> dict | None:
    for state in ("draft", "active", "inactive"):
        res = _call("GET", f"/shops/{shop_id()}/listings", params={"state": state, "limit": 100})
        for x in res.get("results", []):
            if x.get("title") == title:
                return x
    return None


def create_draft(pid: str) -> dict:
    """An inactive draft with its files, images and video. Skipped when a listing with this title already exists."""
    from faceless import safety
    safety.guard("etsy draft")
    p = listing.products(pid)[0]
    pl, up = payload(p, taxonomy_id()), uploads(p)
    have = existing(pl["title"])
    if have:
        return {"product": pid, "action": "skipped: a listing with this title exists", "listing_id": have.get("listing_id"), "state": have.get("state")}
    made = _call("POST", f"/shops/{shop_id()}/listings", data=pl)
    lid = made["listing_id"]
    base = f"/shops/{shop_id()}/listings/{lid}"
    for f in up["files"]:
        with open(f, "rb") as fh:
            _call("POST", f"{base}/files", data={"name": f.name}, files={"file": (f.name, fh, "application/pdf")})
    for rank, im in enumerate(up["images"], 1):
        with open(im, "rb") as fh:
            _call("POST", f"{base}/images", data={"rank": rank}, files={"image": (im.name, fh, "image/jpeg")})
    if up["video"]:
        with open(up["video"], "rb") as fh:
            _call("POST", f"{base}/videos", data={"name": up["video"].name}, files={"video": (up["video"].name, fh, "video/mp4")})
    from faceless import events
    events.emit("SHOP_DRAFT_CREATED", product=pid, rail="etsy", listing_id=str(lid), published=False)
    return {"product": pid, "action": "draft created", "listing_id": lid, "state": "draft", "url": made.get("url", "")}


def publish_listing(listing_id: int | str) -> dict:
    """Set a draft live. Callers go through shop.publish, which checks the owner's approval first; the listing fee is charged by Etsy."""
    from faceless import safety
    safety.guard("etsy publish")
    return _call("PATCH", f"/shops/{shop_id()}/listings/{listing_id}", data={"state": "active"})


def status() -> dict:
    out = {"api_key": bool(keystring()), "tokens": _tokens_file().exists() or bool(config.env("ETSY_REFRESH_TOKEN"))}
    out["state"] = "ready" if out["api_key"] and out["tokens"] else "needs owner"
    out["next"] = ("" if out["state"] == "ready" else
                   "1) etsy.com/developers/your-apps: create an app (personal access), copy its keystring into the environment as ETSY_API_KEY, add the redirect "
                   "https://localhost/callback to the app; 2) run `python -m faceless etsy auth`, open the link signed in to the shop, approve, copy the `code` "
                   "from the address bar; 3) `python -m faceless etsy auth --code <code>`")
    return out
