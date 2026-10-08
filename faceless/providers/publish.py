"""Publishing providers.

local       -> writes a ready-to-post pack (video + caption + title + schedule) into distribution/queue
upload_post -> pushes through Upload-Post (one API for TikTok, YouTube, Instagram), scheduled per slot.
               Their accounts are already API-approved, which sidesteps YouTube's "locked private"
               rule for unaudited API projects and TikTok's direct-post audit.
"""

from __future__ import annotations

import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from faceless import config, events, safety
from faceless.config import Paths
from faceless.providers import ProviderError, ProviderUnavailable, http


def nominal_slot(day: str, slot: int) -> tuple[str, int]:
    """(post date, slot of that day) a job was planned for. Slots past the day's count roll into later
    days, so videos made ahead (`daily --extra`) bank into tomorrow's schedule instead of colliding."""
    per_day = len(config.load()["publish"]["slots"])
    return (date.fromisoformat(day) + timedelta(days=slot // per_day)).isoformat(), slot % per_day


LEAD = timedelta(minutes=20)   # a post needs at least this long to upload and schedule


def nominal_time(post_day: str, k: int) -> datetime:
    """The planned posting time of slot k on post_day, in the audience's time zone."""
    cfg = config.load()["publish"]
    hh, mm = map(int, cfg["slots"][k].split(":"))
    return datetime.fromisoformat(post_day).replace(hour=hh, minute=mm, tzinfo=ZoneInfo(cfg["timezone"]))


def slot_time(day: str, slot: int) -> datetime:
    when = nominal_time(*nominal_slot(day, slot))
    now = datetime.now(when.tzinfo)
    while when <= now + LEAD:  # never schedule into the past (only hand-made `make --slot` jobs land here)
        when += timedelta(days=1)
    return when


def local_pack(job, meta: dict) -> dict:
    when = slot_time(job.day, job.slot)
    post_day, k = nominal_slot(job.day, job.slot)
    folder = Paths.queue / post_day / f"slot{k + 1}-{job.pillar}"
    folder.mkdir(parents=True, exist_ok=True)
    video = Path(job.artifacts["video"])
    shutil.copy2(video, folder / "video.mp4")
    if job.artifacts.get("cover"):
        shutil.copy2(job.artifacts["cover"], folder / "cover.jpg")
    post = [
        f"# Slot {k + 1}: {meta['title']}",
        f"Post at: {when.strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        "## YouTube Shorts",
        f"Title: {meta['title']}",
        "",
        meta["description"],

        "",
        "## TikTok / Instagram caption",
        meta["caption"],
        "",
        "## Checklist",
        "- [ ] Toggle the platform's AI-generated content label ON",
        "- [ ] TikTok: add a trending sound at 5-10% volume under the voice",
        "- [ ] Pin a comment with the link-in-bio CTA",
    ]
    (folder / "POST.md").write_text("\n".join(post), encoding="utf-8")
    (folder / "meta.json").write_text(json.dumps({**meta, "post_at": when.isoformat()}, indent=2), encoding="utf-8")
    return {"mode": "local", "folder": str(folder), "post_at": when.isoformat()}


def upload_post(job, meta: dict) -> dict:
    key = config.env("UPLOAD_POST_API_KEY")
    user = config.env("UPLOAD_POST_USER")
    if not key or not user:
        raise ProviderUnavailable("UPLOAD_POST_API_KEY / UPLOAD_POST_USER not set")
    cfg = config.load()["publish"]
    when = slot_time(job.day, job.slot)
    data = [("user", user), ("title", meta["title"]),
            ("youtube_title", meta["title"]), ("youtube_description", meta["description"]),
            ("tiktok_title", meta["caption"]), ("instagram_title", meta["caption"]),
            ("scheduled_date", when.strftime("%Y-%m-%dT%H:%M:%S")), ("timezone", cfg["timezone"]),
            ("external_id", job.id), ("async_upload", "true"),
            # platform AI disclosure labels (TikTok + YouTube "altered or synthetic content")
            ("tiktok_is_ai_generated", "true"), ("containsSyntheticMedia", "true")]
    data += [("platform[]", p) for p in cfg["platforms"]]
    data += [("tags[]", t.lstrip("#")) for t in meta.get("hashtags", [])]
    if meta.get("first_comment"):
        data.append(("first_comment", meta["first_comment"]))
    with open(job.artifacts["video"], "rb") as f:
        r = http().post("https://api.upload-post.com/api/upload", data=data, files={"video": ("video.mp4", f, "video/mp4")},
                        headers={"Authorization": f"Apikey {key}", "Idempotency-Key": job.id}, timeout=600)
    if r.status_code not in (200, 201, 202):
        raise ProviderError(f"upload-post {r.status_code}: {r.text[:300]}")
    res = r.json()
    events.emit("PUBLISH_SCHEDULED", job=job.id, provider="upload_post", when=when.isoformat(), response=res)
    return {"mode": "upload_post", "post_at": when.isoformat(), "response": res}


PUBLISHERS = {"local": local_pack, "upload_post": upload_post}


def publish(job, meta: dict) -> dict:
    mode = config.load()["publish"]["mode"]
    out = {"local": local_pack(job, meta)}  # always keep a local pack as the record of truth
    if mode != "local":
        try:
            safety.guard(f"publish via {mode}")           # the kill switch stops posting; the local pack above is still written
            out[mode] = PUBLISHERS[mode](job, meta)
        except ProviderUnavailable as e:
            out[mode] = {"skipped": str(e)}
    return out
