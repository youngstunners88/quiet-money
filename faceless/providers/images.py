"""Text-to-image providers.

Chain (studio.toml [images].chain): cloudflare (free FLUX.2 klein, neuron-capped) ->
openrouter (paid, cents) -> pollinations (free, low-res, watermark cropped) ->
procedural (always works, abstract gradient art). Results are cached by prompt hash.
"""

from __future__ import annotations

import base64
import hashlib
import io
import math
import random
import threading
import time
import urllib.parse

from PIL import Image, ImageDraw, ImageFilter

from faceless import config, ledger
from faceless.config import Paths
from faceless.providers import ProviderError, ProviderUnavailable, http, run_chain


def _save(img_bytes: bytes, out) -> None:
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    if min(im.size) < 256:
        raise ProviderError(f"image too small {im.size}")
    im.save(out, "JPEG", quality=95)


def neurons(model: str, w: int, h: int) -> float:
    """Cloudflare Workers AI neuron cost (published pricing, Oct 2026)."""
    if model.endswith("flux-2-klein-9b"):
        mp = w * h / (1024 * 1024)
        return 1363.64 + max(0.0, mp - 1) * 181.82
    if model.endswith("flux-2-klein-4b"):
        # published rate is 26.05/tile, but the account's free 10k ran out after 24 images at 864x1536
        # (2026-10-02), i.e. ~417 neurons each; budget on what Cloudflare actually meters
        return math.ceil(w / 512) * math.ceil(h / 512) * 69.5
    if model.endswith("flux-1-schnell"):
        return 4 * 4.8 + 8 * 9.6
    return 1500.0


def cloudflare(prompt: str, w: int, h: int, seed: int, out, hero: bool = False) -> None:
    key = config.env("CLOUDFLARE_API_KEY", "CLOUDFLARE_API_TOKEN")
    acct = config.env("CLOUDFLARE_ACCOUNT_ID")
    if not key or not acct:
        raise ProviderUnavailable("CLOUDFLARE_API_KEY / CLOUDFLARE_ACCOUNT_ID not set")
    cfg = config.load()["images"]
    model = cfg["cloudflare_hero_model"] if hero else cfg["cloudflare_model"]
    cost = neurons(model, w, h)
    if ledger.used("cloudflare", "blocked") or not ledger.allow("cloudflare", "neurons", cost, cfg["cloudflare_daily_neurons"]):
        if hero:  # fall back to the cheap model before leaving Cloudflare
            return cloudflare(prompt, w, h, seed, out, hero=False)
        raise ProviderUnavailable("daily free neuron budget used")
    for attempt in range(2):
        files = {"prompt": (None, prompt), "width": (None, str(w)), "height": (None, str(h)),
                 "seed": (None, str(seed + attempt * 7919))}
        r = http().post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{model}",
                        headers={"Authorization": f"Bearer {key}"}, files=files, timeout=180)
        if r.status_code == 200:
            break
        if "flagged" in r.text and attempt == 0:   # safety filter false positive: a new seed usually passes
            ledger.spend("cloudflare", "neurons", cost)
            continue
        if r.status_code == 429 and "daily free allocation" in r.text:
            # Cloudflare's meter is the truth: block it for the rest of the day so later images skip straight on
            ledger.spend("cloudflare", "blocked", 1)
            raise ProviderUnavailable("cloudflare daily free allocation used")
        raise ProviderError(f"cloudflare {r.status_code}: {r.text[:200]}")
    ctype = r.headers.get("content-type", "")
    if "json" in ctype:
        d = r.json()
        if not d.get("success", True):
            raise ProviderError(f"cloudflare: {d.get('errors')}")
        res = d.get("result", {})
        data = base64.b64decode(res["image"] if isinstance(res, dict) else res)
    else:
        data = r.content
    _save(data, out)
    ledger.spend("cloudflare", "neurons", cost, usd=0.0)


def openrouter(prompt: str, w: int, h: int, seed: int, out, hero: bool = False) -> None:
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    cfg = config.load()["images"]
    if ledger.used("openrouter", "blocked") or not ledger.allow("openrouter", "images", 1, cfg.get("openrouter_daily_images", 60)):
        raise ProviderUnavailable("daily paid image cap reached")
    model = cfg["openrouter_model"]
    body = {"model": model, "modalities": ["image", "text"],
            "messages": [{"role": "user", "content": f"Generate one vertical 9:16 image. {prompt}"}],
            "image_config": {"aspect_ratio": "9:16"}}
    r = http().post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=240,
                    headers={"Authorization": f"Bearer {key}"})
    if r.status_code == 402:   # out of credit: skip this provider for the rest of the day
        ledger.spend("openrouter", "blocked", 1)
        raise ProviderUnavailable("openrouter credit exhausted")
    if r.status_code != 200:
        raise ProviderError(f"openrouter-image {r.status_code}: {r.text[:200]}")
    msg = r.json()["choices"][0]["message"]
    imgs = msg.get("images") or []
    if not imgs:
        raise ProviderError("openrouter-image returned no image")
    url = imgs[0]["image_url"]["url"]
    data = base64.b64decode(url.split(",", 1)[1]) if url.startswith("data:") else http().get(url, timeout=120).content
    _save(data, out)
    ledger.spend("openrouter", "images", 1, usd=0.04)


_POLL_LOCK = threading.Lock()   # the anonymous tier allows one request at a time per IP


def pollinations(prompt: str, w: int, h: int, seed: int, out, hero: bool = False) -> None:
    q = urllib.parse.quote(prompt[:900])
    with _POLL_LOCK:
        for attempt in range(4):   # sporadic 402/429 when requests come too fast; a short wait clears it
            r = http().get(f"https://image.pollinations.ai/prompt/{q}",
                           params={"width": w, "height": h, "nologo": "true", "seed": seed, "model": "flux"}, timeout=180)
            if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
                break
            if r.status_code not in (402, 429, 500, 502, 503) or attempt == 3:
                raise ProviderError(f"pollinations {r.status_code}")
            time.sleep(2 + 2 * attempt)
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    iw, ih = im.size
    im = im.crop((0, 0, iw, int(ih * 0.93)))  # anonymous tier stamps a logo bottom-right
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=95)
    _save(buf.getvalue(), out)
    ledger.spend("pollinations", "images", 1)


def procedural(prompt: str, w: int, h: int, seed: int, out, hero: bool = False) -> None:
    """Last resort: moody abstract gradient with soft light orbs. Never fails, never repeats exactly."""
    rnd = random.Random(seed ^ int(hashlib.sha1(prompt.encode()).hexdigest()[:8], 16))
    base = Image.new("RGB", (w, h))
    top = (rnd.randint(5, 40), rnd.randint(10, 45), rnd.randint(20, 60))
    bot = (rnd.randint(0, 25), rnd.randint(0, 20), rnd.randint(5, 35))
    d = ImageDraw.Draw(base)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3)))
    glow = Image.new("RGB", (w, h))
    gd = ImageDraw.Draw(glow)
    for _ in range(7):
        r = rnd.randint(w // 8, w // 2)
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        col = rnd.choice([(255, 210, 63), (46, 229, 157), (90, 140, 255), (255, 120, 80)])
        gd.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(c * 0.55) for c in col))
    glow = glow.filter(ImageFilter.GaussianBlur(w // 6))
    Image.blend(base, glow, 0.55).save(out, "JPEG", quality=92)


PROVIDERS = {"cloudflare": cloudflare, "openrouter": openrouter, "pollinations": pollinations,
             "procedural": procedural}


def generate(prompt: str, *, seed: int, hero: bool = False, job: str | None = None) -> tuple[str, str]:
    """Return (provider, cached_path). Identical prompt+seed never costs twice."""
    cfg = config.load()["images"]
    w, h = cfg["width"], cfg["height"]
    cache = Paths.cache / "images"
    cache.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(f"{prompt}|{w}x{h}|{seed}|{hero}".encode()).hexdigest()[:16]
    for existing in cache.glob(f"{digest}.*.jpg"):
        return existing.name.split(".")[1], str(existing)

    def make(name):
        def call():
            out = cache / f"{digest}.{name}.jpg"
            PROVIDERS[name](prompt, w, h, seed, out, hero=hero)
            return str(out)
        return call

    return run_chain("image", [(n, make(n)) for n in cfg["chain"] if n in PROVIDERS], job=job)
