"""Publishing providers.

local       -> writes a ready-to-post pack (video + caption + title + schedule) into distribution/queue
youtube     -> schedules the video on the studio's YouTube channel (Composio authorises, we send the bytes), public at its slot time.
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
from faceless.fsutil import write_atomic


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


def render_post(k: int, when_text: str, meta: dict) -> str:
    """POST.md for slot k (0-based): what to paste where, and what to tick. Pure, so a pack can be rewritten from its meta.json."""
    post = [
        f"# Slot {k + 1}: {meta['title']}",
        f"Post at: {when_text}",
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
        f"- [ ] Pin this comment: {pinned}" if (pinned := (meta.get("offer") or {}).get("pinned_comment")) else "- [ ] Pin a comment with the link-in-bio CTA",
        "- [ ] Profile link on every platform is the hub page (see OFFER.md); links in captions and comments are not tappable",
    ]
    return "\n".join(post)


def local_pack(job, meta: dict) -> dict:
    when = slot_time(job.day, job.slot)
    post_day, k = nominal_slot(job.day, job.slot)
    folder = Paths.queue / post_day / f"slot{k + 1}-{job.pillar}"
    folder.mkdir(parents=True, exist_ok=True)
    video = Path(job.artifacts["video"])
    shutil.copy2(video, folder / "video.mp4")
    if job.artifacts.get("cover"):
        shutil.copy2(job.artifacts["cover"], folder / "cover.jpg")
    (folder / "POST.md").write_text(render_post(k, when.strftime('%Y-%m-%d %H:%M %Z'), meta), encoding="utf-8")
    write_atomic(folder / "meta.json", json.dumps({**meta, "post_at": when.isoformat()}, indent=2))
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


def _youtube_cfg() -> dict:
    return config.load()["publish"].get("youtube", {})


def _post_day(job) -> str:
    y = job.artifacts.get("youtube") or {}
    if y.get("post_at"):
        return datetime.fromisoformat(y["post_at"]).astimezone(ZoneInfo(config.load()["publish"]["timezone"])).date().isoformat()
    return nominal_slot(job.day, job.slot)[0]


def youtube(job, meta: dict) -> dict:
    """Schedule the video on the studio's YouTube channel for its slot. Idempotent per job; refuses any channel but the configured one."""
    from faceless.providers import composio_tools as ct
    from faceless.state import all_jobs
    cfg = _youtube_cfg()
    if not cfg.get("channel_id"):
        raise ProviderUnavailable("[publish.youtube] channel_id is not set")
    done = job.artifacts.get("youtube") or {}
    if done.get("video_id"):
        return {"mode": "youtube", "skipped": "already uploaded", "video_id": done["video_id"]}
    planned = (job.artifacts.get("youtube_plan") or {}).get("post_at")      # set by `post-backlog`: a made video given a slot of its own
    when = datetime.fromisoformat(planned) if planned else slot_time(job.day, job.slot)
    post_day = when.astimezone(ZoneInfo(config.load()["publish"]["timezone"])).date().isoformat() if planned else nominal_slot(job.day, job.slot)[0]
    taken = sum(1 for j in all_jobs() if (j.artifacts.get("youtube") or {}).get("video_id") and _post_day(j) == post_day)
    if taken >= int(cfg.get("max_per_day", 5)):
        raise ProviderUnavailable(f"YouTube daily cap reached ({taken} scheduled for {post_day}); the local pack is ready")
    out = ct.youtube_upload(job.artifacts["video"], meta["title"], meta["description"], [t.lstrip("#") for t in meta.get("hashtags", [])],
                            expected_channel_id=cfg["channel_id"], publish_at=when.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            job=job.id)
    job.artifacts["youtube"] = {**out, "post_at": when.isoformat(), "comment_posted": False}
    try:   # the series playlist is how viewers (and YouTube) find the next video of the same kind; a failure here never costs the upload
        from faceless import ytchannel
        job.artifacts["youtube"]["series"] = ytchannel.add_to_series(out["video_id"], job.pillar)
    except (ProviderError, ProviderUnavailable) as e:
        job.notes.append(f"series playlist: {str(e)[:120]}")
    events.emit("PUBLISH_SCHEDULED", job=job.id, provider="youtube", when=when.isoformat(), video_id=out["video_id"])
    return {"mode": "youtube", "post_at": when.isoformat(), **out}


def post_due_comments(now: datetime | None = None) -> list[str]:
    """First comment on every scheduled YouTube video that has gone public (YouTube takes none while it is still scheduled).
    Tries each video three times, then leaves it for the owner. Returns the job ids commented on. API cannot pin: pin in Studio."""
    from faceless.providers import composio_tools as ct
    from faceless.state import all_jobs
    cfg = _youtube_cfg()
    if not cfg.get("channel_id"):
        return []
    now = now or datetime.now(ZoneInfo("UTC"))
    done = []
    for j in all_jobs():
        y = j.artifacts.get("youtube") or {}
        if not y.get("video_id") or y.get("comment_posted") or y.get("comment_tries", 0) >= 3:
            continue
        if datetime.fromisoformat(y["post_at"]) + timedelta(minutes=10) > now:
            continue
        try:
            text = json.loads((j.dir / "meta.json").read_text(encoding="utf-8")).get("first_comment")
        except (OSError, ValueError):
            text = None
        if text:
            try:
                ct.execute("YOUTUBE_POST_COMMENT", {"videoId": y["video_id"], "channelId": cfg["channel_id"], "textOriginal": text}, job=j.id)
            except (ProviderError, ProviderUnavailable) as e:
                y["comment_tries"] = y.get("comment_tries", 0) + 1
                j.notes.append(f"first comment failed: {str(e)[:120]}")
                j.save()
                continue
        y["comment_posted"] = True
        j.save()
        done.append(j.id)
    return done


PUBLISHERS = {"local": local_pack, "upload_post": upload_post, "youtube": youtube}


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
