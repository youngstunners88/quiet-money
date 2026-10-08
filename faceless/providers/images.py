"""Text-to-image providers.

Chain (studio.toml [images].chain): cloudflare (free FLUX.2 klein, neuron-capped) ->
muapi (paid, about half a cent: the same FLUX.2 klein family) -> openrouter (paid, 4 cents) ->
pollinations (free, low-res, watermark cropped) -> procedural (always works, abstract gradient art).
Results are cached by prompt hash.
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

from faceless import config, ledger, safety
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
    gen_cap = cfg["cloudflare_daily_neurons"] - cfg.get("cloudflare_qa_reserve", 2500)   # the rest of the free pool is kept for semantic QA (qa.py, clef.py)
    if ledger.used("cloudflare", "blocked") or not ledger.allow("cloudflare", "neurons", cost, gen_cap):
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


_OR_LOCK = threading.Lock()
_or_inflight = 0   # paid requests in flight: visuals runs 4 workers, so the cap check must count them too


def openrouter(prompt: str, w: int, h: int, seed: int, out, hero: bool = False) -> None:
    global _or_inflight
    key = config.env("OPENROUTER_API_KEY")
    if not key:
        raise ProviderUnavailable("OPENROUTER_API_KEY not set")
    cfg = config.load()["images"]
    safety.guard("openrouter image", 0.04)
    with _OR_LOCK:   # check and reserve atomically so concurrent workers can't overshoot the paid cap
        if ledger.used("openrouter", "blocked") or \
                ledger.used("openrouter", "images") + _or_inflight + 1 > cfg.get("openrouter_daily_images", 60):
            raise ProviderUnavailable("daily paid image cap reached")
        _or_inflight += 1
    try:
        body = {"model": cfg["openrouter_model"], "modalities": ["image", "text"],
                "messages": [{"role": "user", "content": f"Generate one vertical 9:16 image. {prompt}"}],
                "image_config": {"aspect_ratio": "9:16"}}
        r = http().post("https://openrouter.ai/api/v1/chat/completions", json=body, timeout=240,
                        headers={"Authorization": f"Bearer {key}"})
        if r.status_code == 402:   # out of credit: skip this provider for the rest of the day
            ledger.spend("openrouter", "blocked", 1)
            raise ProviderUnavailable("openrouter credit exhausted")
        if r.status_code != 200:
            raise ProviderError(f"openrouter-image {r.status_code}: {r.text[:200]}")
        ledger.spend("openrouter", "images", 1, usd=0.04)   # billed once the model answered, even if unusable
    finally:
        with _OR_LOCK:
            _or_inflight -= 1
    msg = r.json()["choices"][0]["message"]
    imgs = msg.get("images") or []
    if not imgs:
        raise ProviderError("openrouter-image returned no image")
    url = imgs[0]["image_url"]["url"]
    data = base64.b64decode(url.split(",", 1)[1]) if url.startswith("data:") else http().get(url, timeout=120).content
    _save(data, out)


MUAPI = "https://api.muapi.ai/api/v1"
_MU_LOCK = threading.Lock()
_mu_inflight = 0.0   # USD reserved by requests in flight (4 workers), so the daily cap cannot be overshot


def muapi_balance() -> float | None:
    """Wallet balance in USD, or None when there is no key or the call fails."""
    key = config.env("MUAPI_API_KEY")
    if not key:
        return None
    try:
        r = http().get(f"{MUAPI}/account/balance", headers={"x-api-key": key}, timeout=20)
        return float(r.json()["balance"]) if r.status_code == 200 else None
    except Exception:  # noqa: BLE001 - a status call must never break anything
        return None


def muapi(prompt: str, w: int, h: int, seed: int, out, hero: bool = False) -> None:
    """Muapi (submit, then poll): FLUX.2 klein 4B at 720x1280, $0.0052 (turbo) or $0.0104. Roughly 8x cheaper than OpenRouter's image model."""
    global _mu_inflight
    key = config.env("MUAPI_API_KEY")
    if not key:
        raise ProviderUnavailable("MUAPI_API_KEY not set")
    cfg = config.load()["images"]
    model = cfg.get("muapi_hero_model", "flux-2-klein-4b") if hero else cfg.get("muapi_model", "flux-2-klein-4b-turbo")
    price = {"flux-2-klein-4b-turbo": 0.0052, "flux-2-klein-4b": 0.0104, "flux-schnell-image": 0.003}.get(model, 0.03)
    cap = float(cfg.get("muapi_daily_usd", 1.5))
    safety.guard("muapi image", price)
    with _MU_LOCK:
        if ledger.used("muapi", "blocked") or ledger.used("muapi", "usd") + _mu_inflight + price > cap:
            raise ProviderUnavailable("muapi daily spend cap reached")
        _mu_inflight += price
    try:
        s = http()
        headers = {"x-api-key": key}
        body = {"prompt": prompt, "aspect_ratio": "9:16", "seed": seed}
        if "klein" not in model:      # other families take sizes (multiples of 64) instead of an aspect ratio
            body = {"prompt": prompt, "width": 832, "height": 1472}
        r = s.post(f"{MUAPI}/{model}", json=body, headers=headers, timeout=60)
        if r.status_code in (401, 402, 403) and any(t in r.text.lower() for t in ("credit", "balance", "insufficient", "payment")):
            ledger.spend("muapi", "blocked", 1)       # out of credit: skip the provider for the rest of the day
            raise ProviderUnavailable("muapi credit exhausted")
        if r.status_code == 429:
            raise ProviderUnavailable("muapi rate limited")
        if r.status_code != 200:
            raise ProviderError(f"muapi {r.status_code}: {r.text[:160]}")
        d = r.json()
        paid = float((d.get("cost") or {}).get("amount_usd") or price)
        ledger.spend("muapi", "usd", paid, usd=paid)            # billed on submit
        ledger.spend("muapi", "images", 1, usd=0.0)
        rid = d["request_id"]
        for _ in range(75):
            time.sleep(2)
            res = s.get(f"{MUAPI}/predictions/{rid}/result", headers=headers, timeout=30).json()
            if res.get("status") == "completed":
                break
            if res.get("status") in ("failed", "cancelled"):
                raise ProviderError(f"muapi job {res.get('status')}: {str(res.get('error'))[:120]}")
        else:
            raise ProviderError("muapi job timed out")
        if any(res.get("has_nsfw_contents") or []):
            raise ProviderError("muapi flagged the output")
        _save(s.get(res["outputs"][0], timeout=120).content, out)
    finally:
        with _MU_LOCK:
            _mu_inflight = max(0.0, _mu_inflight - price)


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


PROVIDERS = {"cloudflare": cloudflare, "muapi": muapi, "openrouter": openrouter, "pollinations": pollinations,
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
