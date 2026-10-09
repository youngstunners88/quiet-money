"""Hook clips: the opening shot as real motion, made automatically from the hook still with Muapi image-to-video.

The owner-made Flow clips (faceless/flow.py) cost ten minutes a day and are claimed first. When none is waiting, this module can animate
the hook still instead: upload it to Muapi, ask a cheap image-to-video model for a slow camera move, download the mp4, and check three of
its frames with the decision model (text, faces, logos) before using it. Any failure or a flagged frame means the still is used, so a clip
can never cost a video its slot. Spend is metered in the ledger and capped per day, and the feature ships OFF: it adds about $0.10 to $0.15
a clip (seedance-pro-i2v-fast, 5 s, 480p/720p; catalog price 2026-10-08), so turning it on is the owner's call (`[production.hookclip]`).
"""

from __future__ import annotations

import math
import shutil
import subprocess
import time
from pathlib import Path

from faceless import config, flow, ledger, safety
from faceless.providers import ProviderError, ProviderUnavailable, fetch_bytes, http

API = "https://api.muapi.ai/api/v1"
MOTION = ("Slow cinematic camera push-in with subtle natural motion, soft light shifting, shallow depth of field. Keep every object and the "
          "composition exactly as in the image. No new objects, no people, no text, no logos, no cuts.")


def cfg() -> dict:
    return {"enabled": False, "model": "seedance-pro-i2v-fast", "resolution": "720p", "max_per_day": 2, "daily_usd": 0.5,
            **config.load()["production"].get("hookclip", {})}


def enabled() -> bool:
    return bool(cfg()["enabled"]) and bool(config.env("MUAPI_API_KEY"))


def estimate(model: str, resolution: str, seconds: int) -> float | None:
    """Exact price for this request from Muapi's public estimate endpoint (no key, no inference)."""
    try:
        r = http().post(f"{API}/models/{model}/estimate-cost", json={"prompt": "x", "image_url": "https://example.com/a.jpg",
                                                                    "resolution": resolution, "duration": seconds}, timeout=20)
        return float(r.json()["cost"]) if r.status_code == 200 else None
    except Exception:  # noqa: BLE001 - an estimate is advice; the cap still protects the wallet
        return None


def _frames(clip: Path, out_dir: Path, secs: float) -> list[Path]:
    paths = []
    for k, at in enumerate((0.4, secs * 0.5, max(0.5, secs - 0.4))):
        p = out_dir / f"hook-clip-f{k}.jpg"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{at:.2f}", "-i", str(clip), "-frames:v", "1", "-q:v", "3", str(p)],
                       capture_output=True, timeout=60, check=False)
        if p.exists():
            paths.append(p)
    return paths


def make(job, still: str, need: float, narration: str = "") -> dict | None:
    """An mp4 at least `need` seconds long animating `still`, or None (disabled, over budget, failed, or a frame was flagged)."""
    if not enabled() or not shutil.which("ffmpeg"):
        return None
    c = cfg()
    if ledger.used("muapi", "blocked") or ledger.used("muapi", "clips") >= int(c["max_per_day"]):
        return None
    seconds = max(5, math.ceil(need + 0.5))
    price = estimate(c["model"], c["resolution"], seconds) or 0.25
    if ledger.used("muapi", "clip_usd") + price > float(c["daily_usd"]):
        return None
    try:
        safety.guard("hook clip", price)
    except ProviderUnavailable:
        return None
    key = config.env("MUAPI_API_KEY")
    headers = {"x-api-key": key}
    try:
        s = http()
        up = s.post(f"{API}/upload_file", headers=headers, files={"file": (Path(still).name, open(still, "rb"), "image/jpeg")}, timeout=90)
        if up.status_code != 200:
            raise ProviderError(f"upload {up.status_code}")
        r = s.post(f"{API}/{c['model']}", headers=headers, timeout=60,
                   json={"prompt": MOTION, "image_url": up.json()["url"], "resolution": c["resolution"], "duration": seconds})
        if r.status_code in (401, 402, 403) and any(t in r.text.lower() for t in ("credit", "balance", "insufficient")):
            ledger.spend("muapi", "blocked", 1)
            raise ProviderUnavailable("muapi credit exhausted")
        if r.status_code != 200:
            raise ProviderError(f"submit {r.status_code}")
        d = r.json()
        paid = float((d.get("cost") or {}).get("amount_usd") or price)
        ledger.spend("muapi", "clip_usd", paid, usd=paid, job=job.id)
        ledger.spend("muapi", "clips", 1, job=job.id)
        res = {}
        for _ in range(120):                      # clips take 30-90 s
            time.sleep(3)
            res = s.get(f"{API}/predictions/{d['request_id']}/result", headers=headers, timeout=30).json()
            if res.get("status") in ("completed", "failed", "cancelled"):
                break
        if res.get("status") != "completed" or not res.get("outputs"):
            raise ProviderError(f"clip job {res.get('status')}")
        job.dir.mkdir(parents=True, exist_ok=True)
        dest = job.dir / "hook-clip.mp4"
        dest.write_bytes(fetch_bytes(res["outputs"][0], session=s, timeout=180)[0])
    except (ProviderError, ProviderUnavailable, OSError, KeyError, ValueError):
        return None
    info = flow.probe(dest)
    if not info or info["duration"] < need + 0.2 or info["width"] < 480:
        dest.unlink(missing_ok=True)
        return None
    frames = _frames(dest, job.dir, info["duration"])
    if len(frames) < 3:
        dest.unlink(missing_ok=True)
        return None
    from faceless import qa
    bad = qa.check_frames([str(p) for p in frames])
    if bad is None or bad:                        # a flagged frame, or no opinion: do not ship unchecked motion
        dest.unlink(missing_ok=True)
        return None
    return {"clip": str(dest), "frame": str(frames[0]), "source": f"muapi:{c['model']}", "usd": paid, **info}
