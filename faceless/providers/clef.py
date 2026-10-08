"""Cloudflare Clef: typed decisions over text and images, hosted on Workers AI (Apache-2.0 open weights, Jev-API compatible).

A decision model does not write text. It reads a state (and up to four images) plus typed questions and returns a probability for
every allowed answer: `noul` (yes/no probability), `choice` (one option with per-option probabilities), `score` (probability-weighted
level). That is what quality gates want: fast (about 1 s), cheap (about $0.24 per million input tokens; one still is about 1,300
tokens, so about 28 neurons against 417 for generating it) and numeric, so a threshold can be set and tuned from data.
Usage counts against the same free neuron budget as image generation, so it is accounted in the ledger and skipped, never
blocking, when the budget is gone.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

from PIL import Image

from faceless import config, events, ledger
from faceless.providers import ProviderError, ProviderUnavailable, http

NEURONS_PER_TOKEN = (0.24 / 1e6) / (0.011 / 1000)     # $0.24 per M input tokens at $0.011 per 1,000 neurons
MODELS = {"clef": "@cf/cloudflare/clef", "clef-flash": "@cf/cloudflare/clef-flash"}
MAX_IMAGES, MAX_QUESTIONS = 4, 64


def available() -> bool:
    return bool(config.env("CLOUDFLARE_API_KEY", "CLOUDFLARE_API_TOKEN") and config.env("CLOUDFLARE_ACCOUNT_ID"))


def _data_uri(img) -> str:
    """A path or bytes becomes a JPEG data URI no larger than 1536 px on its long side (Clef accepts up to 4 MiB each)."""
    im = Image.open(io.BytesIO(img) if isinstance(img, (bytes, bytearray)) else Path(img)).convert("RGB")
    im.thumbnail((1536, 1536))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def run(state, questions: dict, images: list | None = None, model: str = "clef", job: str | None = None) -> dict:
    """Ask typed questions. Returns {name: answer dict}. Raises ProviderUnavailable when unconfigured or out of free budget."""
    key = config.env("CLOUDFLARE_API_KEY", "CLOUDFLARE_API_TOKEN")
    acct = config.env("CLOUDFLARE_ACCOUNT_ID")
    if not key or not acct:
        raise ProviderUnavailable("Cloudflare keys not set")
    if model not in MODELS:
        raise ValueError(f"model must be one of {sorted(MODELS)}")
    if not 1 <= len(questions) <= MAX_QUESTIONS or len(images or []) > MAX_IMAGES:
        raise ValueError("1-64 questions and at most 4 images")
    cap = config.load()["images"]["cloudflare_daily_neurons"]
    est = (300 + 1400 * len(images or [])) * NEURONS_PER_TOKEN
    if ledger.used("cloudflare", "blocked") or not ledger.allow("cloudflare", "neurons", est, cap):
        raise ProviderUnavailable("Cloudflare free neuron budget used for today")
    body = {"model": model, "state": state, "questions": questions}
    if images:
        body["images"] = [_data_uri(i) for i in images]
    r = http().post(f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{MODELS[model]}",
                    headers={"Authorization": f"Bearer {key}"}, json=body, timeout=90)
    if r.status_code == 429 and "daily free allocation" in r.text:
        ledger.spend("cloudflare", "blocked", 1)
        raise ProviderUnavailable("Cloudflare daily free allocation used")
    if r.status_code != 200:
        raise ProviderError(f"clef {r.status_code}: {r.text[:200]}")
    d = r.json()
    if not d.get("success", True):
        raise ProviderError(f"clef: {d.get('errors')}")
    res = d.get("result", d)
    tokens = (res.get("usage") or {}).get("input_tokens", 0)
    ledger.spend("cloudflare", "neurons", tokens * NEURONS_PER_TOKEN, job=job)
    events.emit("CLEF_CALL", job=job, model=model, questions=list(questions), images=len(images or []), input_tokens=tokens)
    return res.get("answers", {})


def probability(answer: dict) -> float:
    """The yes-probability of a noul answer."""
    return float(answer.get("noul", 0.0))
