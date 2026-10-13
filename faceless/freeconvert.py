"""FreeConvert (freeconvert.com API v1): an optional normaliser for picture formats Pillow cannot open (HEIC, TIFF, PSD, AVIF) into PNG.

Why it is here and what it is not: FreeConvert converts, compresses and resizes files. It cannot remove a watermark, so the handle cleaner stays local
(planner_clean.py). Pictures the owner exports from a phone are often HEIC, and those cannot enter the planner until they are PNG or JPG.

Rules it keeps (CLAUDE.md rules 7, 10, 11, 14; intake verdict TRIAL in repo-farm/intake/2026-10-12):
  * OFF until FREECONVERT_API_KEY is in the environment (a free account's API token; intake never signs anyone up). The key is never printed or stored.
  * The picture is uploaded to FreeConvert (they delete it a few hours later): only the owner's own artwork, never anything private.
  * Capped: `[freeconvert] daily_minutes` (default 15 of the free 20) and `per_file_mb`, counted in the ledger; `state/PAUSE` stops it.
  * The upload goes only to a freeconvert.com host, the result is fetched only through providers.fetch_bytes (https, size-limited), and every call has a timeout.
Flow (from the public docs): POST /process/import/upload, POST the file to the returned form, POST /process/jobs {convert, export/url}, poll the job, fetch the URL.
It could not be tried against the live service here (no token); the tests replay the documented replies.
"""

from __future__ import annotations

import os
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from faceless import config, ledger, safety
from faceless.config import STUDIO
from faceless.providers import ProviderError, ProviderUnavailable, fetch_bytes, http

BASE = "https://api.freeconvert.com/v1"
EXOTIC = {".heic", ".heif", ".tif", ".tiff", ".psd", ".avif", ".bmp", ".gif"}
INCOMING = STUDIO / "assets" / "planner" / "incoming"


def cfg() -> dict:
    return {"daily_minutes": 15, "per_file_mb": 10, "timeout": 180, "poll_seconds": 3.0, **config.load().get("freeconvert", {})}


def key() -> str | None:
    return config.env("FREECONVERT_API_KEY")


def available() -> bool:
    return bool(key())


def _api(method: str, path: str, **kw) -> dict:
    k = key()
    if not k:
        raise ProviderUnavailable("FREECONVERT_API_KEY not set")
    r = http().request(method, BASE + path, headers={"Authorization": f"Bearer {k}", "Accept": "application/json"}, timeout=cfg()["timeout"], **kw)
    if r.status_code in (401, 403):
        raise ProviderUnavailable("FreeConvert refused the token (check FREECONVERT_API_KEY)")
    if r.status_code == 429:
        raise ProviderUnavailable("FreeConvert rate limit")
    if r.status_code >= 400:
        raise ProviderError(f"freeconvert {r.status_code} on {path}")
    return r.json()


def _safe_host(url: str) -> bool:
    u = urlparse(url)
    return u.scheme == "https" and bool(u.hostname) and (u.hostname == "freeconvert.com" or u.hostname.endswith(".freeconvert.com"))


def normalize(src: Path, dest_dir: Path | None = None, fmt: str = "png") -> Path:
    """Convert one picture to PNG through FreeConvert and return the new file's path. Raises ProviderUnavailable when it is off, capped or paused."""
    src = Path(src)
    c = cfg()
    if src.suffix.lower() not in EXOTIC:
        raise ValueError(f"{src.name}: only {', '.join(sorted(EXOTIC))} go through FreeConvert; Pillow opens the rest itself")
    if src.stat().st_size > c["per_file_mb"] * 2**20:
        raise ValueError(f"{src.name} is over the {c['per_file_mb']} MB limit")
    if not available():
        raise ProviderUnavailable("FREECONVERT_API_KEY not set")
    safety.guard("freeconvert")
    if not ledger.allow("freeconvert", "minutes", 1, c["daily_minutes"]):
        raise ProviderUnavailable(f"FreeConvert's daily cap of {c['daily_minutes']} conversion minutes is used")
    up = _api("POST", "/process/import/upload", json={})
    form = ((up.get("result") or {}).get("form")) or {}
    if not up.get("id") or not _safe_host(form.get("url", "")):
        raise ProviderError("FreeConvert gave no usable upload address")
    r = http().post(form["url"], data=form.get("parameters") or {}, files={"file": (src.name, src.read_bytes())}, timeout=c["timeout"])
    if r.status_code >= 400:
        raise ProviderError(f"freeconvert upload {r.status_code}")
    job = _api("POST", "/process/jobs", json={"tasks": {
        "convert": {"operation": "convert", "input": up["id"], "input_format": src.suffix.lower().lstrip("."), "output_format": fmt},
        "export": {"operation": "export/url", "input": "convert", "filename": f"{src.stem}.{fmt}"}}})
    deadline = time.time() + c["timeout"]
    while job.get("status") not in ("completed", "failed"):
        if time.time() > deadline:
            raise ProviderError("FreeConvert job timed out")
        time.sleep(c["poll_seconds"])
        job = _api("GET", f"/process/jobs/{job['id']}")
    if job["status"] == "failed":
        bad = [(t.get("result") or {}).get("errorCode") for t in job.get("tasks", []) if t.get("status") == "failed"]
        raise ProviderError(f"FreeConvert could not convert {src.name}: {[b for b in bad if b] or 'failed'}")
    task = next((t for t in job.get("tasks", []) if t.get("name") == "export"), None)
    url = ((task or {}).get("result") or {}).get("url", "")
    if not url:
        raise ProviderError("FreeConvert finished without a download address")
    body, _type = fetch_bytes(url, limit=40 * 2**20)
    im = Image.open(BytesIO(body))
    im.verify()                                                      # a download that is not a picture is refused, not saved
    dest = (dest_dir or INCOMING) / f"{src.stem}.{fmt}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
    try:
        tmp.write_bytes(body)
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    ledger.spend("freeconvert", "minutes", 1, usd=0.0)
    return dest
