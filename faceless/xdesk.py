"""The X desk: every finished Short becomes a ready-to-post X draft (native video + a short thread). The owner posts by hand.

Most clients come from X (owner, 2026-11-15), so each passed video also gets an X post: the video file to attach, a lead post
(title + hook, under 280 characters), the thread replies from the script (repurpose.thread, no model calls) and the disclosure.
Nothing here posts, follows, likes or replies (CLAUDE.md rule 9: posting anywhere new is the owner's act).

    python -m faceless x                 draft every finished video of the last DAYS days that has no draft yet
    python -m faceless x status          drafted / posted counts and what waits for the owner
    python -m faceless x log <job> posted --url https://x.com/...    after posting; a logged video is never offered again
    python -m faceless x log <job> skipped                            the owner chose not to post it

Files: outbound/x/<day>/<job_id>.md (the draft), state/x.jsonl (one line per draft or outcome; no handles, no personal data).
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

from faceless import config, events
from faceless.config import STUDIO, Paths
from faceless.fsutil import read_jsonl, write_atomic

DIR = STUDIO / "outbound" / "x"
LOG = STUDIO / "state" / "x.jsonl"
DAYS = 3
STATUSES = ("drafted", "posted", "skipped")
AI_LINE = "AI-generated visuals and voice. Educational content, not financial advice."
MAX_LEAD = 280


def _days(today: str) -> set[str]:
    d = config.today_utc().fromisoformat(today)
    return {(d - timedelta(days=i)).isoformat() for i in range(DAYS)}


def latest() -> dict[str, dict]:
    """job id -> its newest log row."""
    out: dict[str, dict] = {}
    for r in read_jsonl(LOG) if LOG.exists() else []:
        if r.get("job"):
            out[r["job"]] = r
    return out


def candidates(today: str | None = None) -> list[dict]:
    """Finished videos of the last DAYS days with a render on disk and a final script, newest first."""
    from faceless.state import all_jobs
    today = today or config.today_utc().isoformat()
    days = _days(today)
    out = []
    for j in all_jobs():
        if j.status not in ("packaged", "published") or j.day not in days:
            continue
        video = Paths.output / j.day / j.id / "final.mp4"
        script = Paths.final / f"{j.id}.json"
        if video.exists() and script.exists():
            out.append({"job": j.id, "day": j.day, "video": video, "script": script})
    out.sort(key=lambda c: c["job"], reverse=True)
    return out


def lead_post(script: dict, prefix: str = "") -> str:
    """The post the video rides on: the thread number, the title and the hook, under 280 characters, and the AI line."""
    from faceless.repurpose import _clip
    title = _clip(" ".join(str(script.get("title") or "").split()), 110)
    hook = _clip(" ".join(str(script.get("hook_text") or "").split()).capitalize(), 110)
    text = f"{prefix}{title}\n\n{hook}\n\n{AI_LINE}" if hook and hook.lower() != title.lower() else f"{prefix}{title}\n\n{AI_LINE}"
    return text if len(text) <= MAX_LEAD else f"{prefix}{_clip(title, MAX_LEAD - len(AI_LINE) - len(prefix) - 2)}\n\n{AI_LINE}"


def draft_text(job_id: str, script: dict, video: Path) -> str:
    from faceless.repurpose import thread
    replies = thread(script, job_id, "checklist").split("\n\n---\n\n")[1:]      # tweet 1 of the kit's thread is replaced by the video post
    rel = video.relative_to(STUDIO) if video.is_relative_to(STUDIO) else video
    body = [f"# X post: {script.get('title', job_id)}", "",
            f"Job: `{job_id}`", f"Attach: `{rel}`", "",
            "## Post (with the video attached)", "", lead_post(script, f"1/{len(replies) + 1} "), "",
            "## Replies (post each as a reply to the one before)", ""]
    for r in replies:
        body += [r.strip(), ""]
    body += ["## After posting", "", f"`python -m faceless x log {job_id} posted --url <the post's link>`", "",
             "Do not post the same video twice; the desk lists only videos with no log line."]
    return "\n".join(body) + "\n"


def _append(row: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def draft(today: str | None = None) -> dict:
    """Write a draft for every candidate that has none. Never rewrites a drafted, posted or skipped video."""
    from faceless import safety
    if why := safety.paused():
        return {"drafted": [], "refused": f"the studio is paused ({why})"}
    seen = latest()
    made = []
    for c in candidates(today):
        if c["job"] in seen:
            continue
        try:
            script = json.loads(c["script"].read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        path = DIR / c["day"] / f"{c['job']}.md"
        write_atomic(path, draft_text(c["job"], script, c["video"]))
        _append({"t": events.now_iso(), "job": c["job"], "status": "drafted", "file": str(path.relative_to(STUDIO))})
        made.append(c["job"])
    if made:
        events.emit("X_DRAFTS", count=len(made))
    return {"drafted": made}


def log(job_id: str, status: str, url: str = "") -> dict:
    if status not in ("posted", "skipped"):
        raise ValueError("status must be posted or skipped")
    if job_id not in latest():
        raise ValueError(f"no X draft for {job_id}; run `python -m faceless x` first")
    if url and not url.startswith(("https://x.com/", "https://twitter.com/")):
        raise ValueError("url must be the post's https://x.com/... link")
    row = {"t": events.now_iso(), "job": job_id, "status": status}
    if url:
        row["url"] = url[:200]
    _append(row)
    return row


def status(today: str | None = None) -> dict:
    """What the board shows: drafts waiting for the owner, posted today and all-time, and videos with no draft yet."""
    today = today or config.today_utc().isoformat()
    rows = latest()
    waiting = sorted(j for j, r in rows.items() if r["status"] == "drafted")
    seen = set(rows)
    undrafted = [c["job"] for c in candidates(today) if c["job"] not in seen]
    posted_today = sum(1 for r in (read_jsonl(LOG) if LOG.exists() else []) if r.get("status") == "posted" and str(r.get("t", ""))[:10] == today)
    return {"waiting": len(waiting), "waitingTop": waiting[-5:][::-1], "undrafted": len(undrafted),
            "postedToday": posted_today, "postedAllTime": sum(1 for r in rows.values() if r["status"] == "posted"),
            "source": "outbound/x/, state/x.jsonl, state/jobs, production/output"}


def main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="python -m faceless x")
    p.add_argument("action", nargs="?", default="draft", choices=["draft", "status", "log"])
    p.add_argument("job", nargs="?")
    p.add_argument("status", nargs="?")
    p.add_argument("--url", default="")
    a = p.parse_args(argv)
    if a.action == "status":
        print(json.dumps(status(), indent=1))
        return 0
    if a.action == "log":
        try:
            print(json.dumps(log(a.job or "", a.status or "", a.url)))
        except ValueError as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        return 0
    r = draft()
    if r.get("refused"):
        print(f"refused: {r['refused']}")
        return 1
    print(f"{len(r['drafted'])} X draft(s) written to outbound/x/. Nothing was posted; you post by hand.")
    return 0
