"""Phone lane: the owner's own Android phone does the jobs that have no API, or whose API is rationed, driven by Claude Code on the
owner's computer through OpenDeviceMCP (tools/open-device-mcp: free, local, adb over USB or Wi-Fi).

Why a queue and not a live connection: the engine runs in the cloud and the phone sits on the owner's desk, so the two meet in git.

  cloud    `phone queue`   writes one JSON job per action into state/phone/jobs/<day>/ and checks it (text, caps, duplicates)
           `phone stage`   puts the media the jobs need (comic pictures, Short videos) on the `phone-media` branch under out/<day>/<id>/
  computer `phone next`    the next job whose gate is open, with its recipe (skill faceless-phone) and its files fetched to the
                           OpenDeviceMCP drop folder; the agent pushes them to the phone, drives the app, and screenshots the result
           `phone done`    records what happened (receipt), so nothing is posted twice and the caps hold across both machines
           `phone inbound` (Flow images) commits what the phone made to the same branch under in/<day>/<id>/
  cloud    `phone collect` copies inbound images to where the engine looks first (a vibe video's shot cache), so Muapi is not paid

Job kinds: yt_community (a comic on the Posts tab), yt_short (a Short the API could not upload), tiktok (a Short on TikTok),
flow_image (a picture made in Google Flow on the owner's account), fiverr_inbox (read new Fiverr messages, draft replies, send nothing),
fiverr_reply (send one drafted reply, only after `phone approve <id>`: a message to a real person is the owner's call, rule 16).
Posting through the phone was approved by the owner on 2026-10-25 for YouTube, the Posts tab and TikTok (`[phone]` in studio.toml).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from faceless import config, safety
from faceless.config import Paths
from faceless.fsutil import read_jsonl, write_atomic

KINDS = ("yt_community", "yt_short", "tiktok", "flow_image", "fiverr_inbox", "fiverr_reply")
POSTS = ("yt_community", "yt_short", "tiktok")
RECIPES = {   # section of .claude/skills/faceless-phone/references/recipes.md the agent follows for each kind
    "yt_community": "YouTube Posts tab (picture post)", "yt_short": "YouTube Short upload", "tiktok": "TikTok upload",
    "flow_image": "Google Flow image", "fiverr_inbox": "Fiverr inbox (read and draft)", "fiverr_reply": "Fiverr reply (approved only)",
}
DEVICE_DIR = "/sdcard/Download/QuietMoney"           # where the agent pushes media; the gallery pickers of every app list it
COMMUNITY_DISCLOSURE = "Illustrated with AI."
VIDEO_DISCLOSURE = "AI-assisted"
TIKTOK_DISCLOSURE = "Education, not financial advice."
BANNED = re.compile(r"\s*Narration and visuals are AI-assisted\.?|\s*AI-assisted\.?", re.I)    # owner, 2026-10-25: those words are never written into content; the platform AI toggle is the label
TEXT_MAX = {"yt_community": 1500, "yt_short": 5000, "tiktok": 2200}
COLLECT_ROOTS = ("production/cache", "channel/flow/inbox", "assets/flowbank")   # where an inbound picture may land


def cfg() -> dict:
    c = config.load().get("phone", {})
    return {"enabled": c.get("enabled", False), "post_community": c.get("post_community", False), "post_youtube": c.get("post_youtube", False),
            "post_tiktok": c.get("post_tiktok", False), "branch": c.get("media_branch", "phone-media"),
            "caps": {"yt_community": 5, "yt_short": 5, "tiktok": 5, "flow_image": 30, "fiverr_inbox": 3, "fiverr_reply": 10, **c.get("max_per_day", {})}}


def home() -> Path:
    return Paths.state / "phone"


def drop() -> Path:
    """Local folder for fetched media: inside OpenDeviceMCP's default pathAllowlist, so push_file accepts it."""
    return Path.home() / "open-device-mcp" / "quiet-money"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def job_id(kind: str, day: str, key: str) -> str:
    return f"{day}-{kind}-{re.sub(r'[^a-z0-9]+', '-', key.lower()).strip('-')[:48]}"


# ------------------------------------------------------------------ jobs and receipts

def job_path(jid: str) -> Path:
    return home() / "jobs" / jid[:10] / f"{jid}.json"


def load(jid: str) -> dict:
    return json.loads(job_path(jid).read_text(encoding="utf-8"))


def save(job: dict) -> None:
    write_atomic(job_path(job["id"]), json.dumps(job, indent=1, ensure_ascii=False))


def jobs(day: str | None = None) -> list[dict]:
    root = home() / "jobs"
    out = []
    for p in sorted((root / day).glob("*.json") if day else root.glob("*/*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue                                       # one damaged job never hides the others
    return out


def receipts() -> list[dict]:
    return read_jsonl(home() / "receipts.jsonl")


def done_today(kind: str, day: str | None = None) -> int:
    day = day or config.today_utc().isoformat()
    return sum(1 for r in receipts() if r.get("kind") == kind and r.get("result") == "posted" and str(r.get("at", "")).startswith(day))


def already(key: str, kind: str) -> bool:
    return any(r.get("key") == key and r.get("kind") == kind and r.get("result") == "posted" for r in receipts())


def add(kind: str, day: str, key: str, payload: dict, media: list[Path] | None = None) -> dict | None:
    """Queue one job (idempotent: an existing job or a posted key is left alone). Returns the job, or None when skipped."""
    if kind not in KINDS:
        raise ValueError(f"unknown phone job kind {kind!r}")
    jid = job_id(kind, day, key)
    if job_path(jid).exists() or already(key, kind):
        return None
    files = [str(m.relative_to(Paths.root)) if m.is_relative_to(Paths.root) else str(m) for m in (media or [])]
    job = {"id": jid, "kind": kind, "day": day, "key": key, "status": "queued", "created": now(), "recipe": RECIPES[kind],
           "media": [{"source": f, "name": Path(f).name} for f in files], "staged": False, **payload}
    save(job)
    return job


# ------------------------------------------------------------------ what may go out

def problems(job: dict) -> list[str]:
    """What is wrong with the job itself; checked when it is queued and again before it runs."""
    out, kind, text = [], job["kind"], str(job.get("text", ""))
    if kind in POSTS:
        if not text.strip():
            out.append("no post text")
        if len(text) > TEXT_MAX[kind]:
            out.append(f"text is {len(text)} characters (limit {TEXT_MAX[kind]})")
        if not job.get("media"):
            out.append("no media file")
    if kind == "yt_community":
        if re.search(r"https?://", text):
            out.append("a link in the text (picture posts carry none)")
        if COMMUNITY_DISCLOSURE.lower() not in text.lower():
            out.append("the AI disclosure line is missing")
    # owner, 2026-10-25: the words "AI-assisted" are never written into content; the platform's own AI toggle is the label.
    if kind == "yt_short" and not str(job.get("title", "")).strip():
        out.append("no title")
    if kind == "tiktok":
        if re.search(r"https?://", text):
            out.append("a link in the caption (not tappable on TikTok; the bio carries it)")
    if kind == "flow_image" and not str(job.get("prompt", "")).strip():
        out.append("no prompt")
    if kind == "flow_image" and not _collect_ok(str(job.get("dest", ""))):
        out.append(f"destination must be under {', '.join(COLLECT_ROOTS)}")
    if kind == "fiverr_reply" and not str(job.get("draft", "")).strip():
        out.append("no drafted reply")
    return out


def gate(job: dict) -> str | None:
    """Why this job must not run now, or None."""
    c = cfg()
    if why := safety.paused():
        return f"paused: {why}"
    if not c["enabled"]:
        return "the phone lane is off ([phone] enabled = false)"
    if why := problems(job):
        return "; ".join(why)
    switch = {"yt_community": "post_community", "yt_short": "post_youtube", "tiktok": "post_tiktok"}.get(job["kind"])
    if switch and not c[switch]:
        return f"[phone] {switch} is off"
    if job["kind"] == "fiverr_reply" and not (home() / "approved" / job["id"]).exists():
        return f"waiting for the owner: python -m faceless phone approve {job['id']}"
    if job.get("status") != "queued":
        return f"job is {job.get('status')}"
    if already(job["key"], job["kind"]):
        return "already done"
    cap = int(c["caps"].get(job["kind"], 0))
    if done_today(job["kind"]) >= cap:
        return f"today's cap of {cap} {job['kind']} reached"
    return None


# ------------------------------------------------------------------ the cloud side: what to queue

def _section(md: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)", md, re.S | re.M)
    return m.group(1).strip() if m else ""


def short_texts(post_md: str) -> dict:
    """Title, YouTube description and TikTok caption from a posting pack's POST.md."""
    yt = _section(post_md, "YouTube Shorts")
    title = re.search(r"^Title:\s*(.+)$", yt, re.M)
    desc = re.sub(r"^Title:.*\n?", "", yt, count=1, flags=re.M).strip()
    tk = _section(post_md, "TikTok / Instagram caption")
    if tk and TIKTOK_DISCLOSURE.lower() not in tk.lower():
        tk = f"{tk}\n\n{TIKTOK_DISCLOSURE}"
    return {"title": title.group(1).strip() if title else "", "description": BANNED.sub("", desc).strip(), "tiktok": BANNED.sub("", tk).strip()}


def queue_comics(day: str) -> list[dict]:
    out = []
    for meta in sorted((Paths.root / "distribution" / "comics" / day).glob("*/comic.json")):
        pic = meta.parent / "picture.png"
        data = json.loads(meta.read_text(encoding="utf-8"))
        slug = f"{day}/{meta.parent.name}"
        posted = {r.get("slug") for r in read_jsonl(Paths.state / "community_posts.jsonl") if r.get("published")}
        if not pic.is_file() or slug in posted:
            continue
        if job := add("yt_community", day, slug, {"text": str(data.get("post", "")), "alt": str(data.get("alt", "")), "title": str(data.get("title", ""))}, [pic]):
            out.append(job)
    return out


def queue_shorts(day: str, youtube: bool = True, tiktok: bool = True) -> list[dict]:
    """A day's passed Shorts: TikTok for every one, YouTube only for those the API never uploaded."""
    from faceless.state import all_jobs
    out = []
    for j in all_jobs():
        video = Path(j.artifacts.get("video") or "/nonexistent")
        if j.day != day or not j.scores.get("passed") or not video.is_file():
            continue
        pack = Path((j.artifacts.get("publish") or {}).get("local", {}).get("folder", "/nonexistent")) / "POST.md"
        if not pack.is_file():
            continue
        t = short_texts(pack.read_text(encoding="utf-8"))
        if youtube and not (j.artifacts.get("youtube") or {}).get("video_id"):
            if job := add("yt_short", day, j.id, {"title": t["title"], "text": t["description"], "ai_label": "altered or synthetic content: Yes"}, [video]):
                out.append(job)
        if tiktok and t["tiktok"]:
            if job := add("tiktok", day, j.id, {"text": t["tiktok"], "ai_label": "AI-generated content: on"}, [video]):
                out.append(job)
    return out


def queue_flow(day: str, prompts_file: Path) -> list[dict]:
    """flow_image jobs from a JSON list of {"name", "prompt", "dest", "aspect"} (dest: the file the engine will look for)."""
    out = []
    for row in json.loads(prompts_file.read_text(encoding="utf-8")):
        payload = {"prompt": str(row["prompt"]), "dest": str(row["dest"]), "aspect": str(row.get("aspect", "16:9"))}
        if job := add("flow_image", day, str(row.get("name") or row["dest"]), payload):
            out.append(job)
    return out


def flow_from_vibe(slug: str) -> Path:
    """A prompts file for every still of a planned vibe video that is not made yet, so Flow paints them instead of Muapi."""
    work = Paths.cache / "vibe" / slug
    shots = json.loads((work / "plan.json").read_text(encoding="utf-8"))      # vibe.plan: one {prompt, motion, clip_prompt} per shot
    rows = [{"name": f"{slug}-shot{i + 1:02d}", "prompt": s["prompt"], "aspect": "16:9", "dest": f"production/cache/vibe/{slug}/shot{i + 1:02d}.png"}
            for i, s in enumerate(shots) if not (work / f"shot{i + 1:02d}.png").is_file()]
    path = home() / "prompts" / f"{slug}.json"
    write_atomic(path, json.dumps(rows, indent=1))
    return path


def queue_day(day: str, flow: Path | None = None, fiverr: bool = True) -> dict:
    c = cfg()
    made = {"yt_community": queue_comics(day) if c["post_community"] else [],
            "shorts": queue_shorts(day, youtube=c["post_youtube"], tiktok=c["post_tiktok"]),
            "flow_image": queue_flow(day, flow) if flow else [],
            "fiverr_inbox": [j for j in [add("fiverr_inbox", day, f"inbox-{day}", {"draft_dir": f"state/phone/fiverr/{day}"}) if fiverr else None] if j]}
    return {k: [j["id"] for j in v] for k, v in made.items()}


# ------------------------------------------------------------------ media through git (the phone-media branch)

def _git(*args: str, cwd: Path | None = None, timeout: int = 180) -> str:
    r = subprocess.run(["git", *args], cwd=cwd or Paths.root, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])} failed: {r.stderr.strip()[:300]}")
    return r.stdout


def worktree() -> Path:
    """A checkout of the media branch under state/tmp (gitignored), created as an orphan branch the first time."""
    branch, wt = cfg()["branch"], Paths.state / "tmp" / "phone-media"
    if (wt / ".git").exists():
        try:
            _git("pull", "--rebase", "origin", branch, cwd=wt)
        except RuntimeError:
            pass                                           # the branch is not on the remote yet
        return wt
    wt.parent.mkdir(parents=True, exist_ok=True)
    try:
        _git("fetch", "origin", f"{branch}:refs/remotes/origin/{branch}", "--depth", "1")
        _git("worktree", "add", "-B", branch, str(wt), f"origin/{branch}")
    except RuntimeError:
        _git("worktree", "add", "--orphan", "-b", branch, str(wt))
    return wt


def _publish(wt: Path, message: str) -> bool:
    _git("add", "-A", cwd=wt)
    if not _git("status", "--porcelain", cwd=wt).strip():
        return False
    _git("-c", "user.name=Quiet Money", "-c", "user.email=noreply@quietmoney.local", "commit", "-q", "-m", message, cwd=wt)
    _git("push", "-u", "origin", cfg()["branch"], cwd=wt, timeout=600)
    return True


def stage(day: str, push: bool = True, keep_days: int = 3) -> dict:
    """Copy every unstaged job's media to out/<day>/<id>/ on the media branch; days older than keep_days are dropped from it."""
    wt = worktree()
    staged, missing = [], []
    for job in jobs(day):
        if job.get("staged") or not job.get("media"):
            continue
        dest = wt / "out" / day / job["id"]
        dest.mkdir(parents=True, exist_ok=True)
        ok = True
        for m in job["media"]:
            src = Paths.root / m["source"] if not Path(m["source"]).is_absolute() else Path(m["source"])
            if not src.is_file():
                ok = False
                missing.append(m["source"])
                continue
            shutil.copy2(src, dest / m["name"])
        if ok:
            job["staged"] = True
            save(job)
            staged.append(job["id"])
    days = sorted(p.name for p in (wt / "out").glob("*") if p.is_dir())
    for old in days[:-keep_days] if keep_days else []:
        shutil.rmtree(wt / "out" / old)
    pushed = _publish(wt, f"phone media for {day}") if push else False
    return {"staged": staged, "missing": missing, "pushed": pushed}


def fetch(job: dict) -> list[Path]:
    """On the owner's computer: the job's files from the media branch, into the OpenDeviceMCP drop folder."""
    if not job.get("media"):
        return []
    branch = cfg()["branch"]
    _git("fetch", "origin", f"{branch}:refs/remotes/origin/{branch}", "--depth", "1", timeout=600)
    out = []
    for m in job["media"]:
        dest = drop() / job["id"] / m["name"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        blob = subprocess.run(["git", "show", f"origin/{branch}:out/{job['day']}/{job['id']}/{m['name']}"], cwd=Paths.root, capture_output=True, timeout=600)
        if blob.returncode != 0:
            raise RuntimeError(f"{m['name']} is not on {branch} yet: run `python -m faceless phone stage` where the video was made")
        dest.write_bytes(blob.stdout)
        out.append(dest)
    return out


def _collect_ok(dest: str) -> bool:
    return bool(dest) and ".." not in Path(dest).parts and not Path(dest).is_absolute() and any(dest.startswith(r + "/") for r in COLLECT_ROOTS)


def inbound(jid: str, files: list[Path], push: bool = True) -> dict:
    """On the owner's computer: what the phone made (Flow pictures) goes to in/<day>/<id>/ on the media branch."""
    job = load(jid)
    wt = worktree()
    dest = wt / "in" / job["day"] / jid
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    for i, f in enumerate(files):
        name = f"{i + 1:02d}{f.suffix.lower()}"
        shutil.copy2(f, dest / name)
        names.append(name)
    pushed = _publish(wt, f"phone inbound {jid}") if push else False
    return {"files": names, "pushed": pushed}


def collect(day: str | None = None) -> list[str]:
    """In the cloud: inbound Flow pictures copied to their destination (the first file of each job), so the engine uses them."""
    from PIL import Image
    wt = worktree()
    got = []
    for job in jobs(day):
        if job["kind"] != "flow_image" or not _collect_ok(job.get("dest", "")):
            continue
        dest = Paths.root / job["dest"]
        files = sorted((wt / "in" / job["day"] / job["id"]).glob("*"))
        if dest.is_file() or not files:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        Image.open(files[0]).convert("RGB").save(dest)
        got.append(job["dest"])
    return got


# ------------------------------------------------------------------ adb on the owner's computer (media in and out; the MCP does the tapping)

IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp")


def adb(*args: str, timeout: int = 120, binary: bool = False):
    r = subprocess.run(["adb", *args], capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"adb {' '.join(args[:2])} failed: {r.stderr.decode(errors='replace').strip()[:300]}")
    return r.stdout if binary else r.stdout.decode(errors="replace")


def push(job: dict, files: list[Path]) -> list[str]:
    """Copy the job's files to DEVICE_DIR and ask the media scanner to index them, so every app's gallery picker lists them.
    Done here rather than through the MCP's push_file, which (rightly) asks a person each time; this path is behind gate()."""
    if why := gate(job):
        raise RuntimeError(f"not pushing: {why}")
    adb("shell", "mkdir", "-p", DEVICE_DIR)
    out = []
    for f in files:
        remote = f"{DEVICE_DIR}/{f.name}"
        adb("push", str(f), remote, timeout=600)
        try:
            adb("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{remote}")
        except RuntimeError:
            pass                                           # newer Android scans /sdcard/Download on its own
        out.append(remote)
    return out


def downloads() -> list[str]:
    return [n.strip() for n in adb("shell", "ls", "/sdcard/Download").splitlines() if n.strip().lower().endswith(IMAGE_EXT)]


def snapshot(job: dict) -> None:
    """Before a Flow job: remember what is already in the phone's Download folder, so `pull` takes only the new pictures."""
    job["before"] = downloads()
    save(job)


def pull(jid: str, push_branch: bool = True) -> dict:
    """After a Flow job: the new pictures in the phone's Download folder come to the computer and go to the media branch."""
    job = load(jid)
    new = [n for n in downloads() if n not in set(job.get("before", []))]
    if not new:
        raise RuntimeError("no new picture in /sdcard/Download: save the Flow image first (Download in Flow's menu)")
    got = []
    for n in new:
        dest = drop() / jid / n
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(adb("exec-out", "cat", f"/sdcard/Download/{n}", binary=True, timeout=300))
        got.append(dest)
    return {"pulled": [str(g) for g in got], **inbound(jid, got, push=push_branch)}


# ------------------------------------------------------------------ the home host's heartbeat (skill faceless-phone-host)

HOST_STALE_HOURS = 6
HOST_COMMIT_HOURS = 3


def heartbeat(device: str, reachable: bool, note: str = "") -> dict:
    """The home host says it ran: when, whether the phone answered, and what it did. state/phone/host.json (committed) is rewritten
    only when something changed or every HOST_COMMIT_HOURS, so the host does not add a commit every half hour; `commit` says which."""
    row = {"at": now(), "device": device[:64], "reachable": reachable, "note": note[:200]}
    path = home() / "host.json"
    try:
        prev = json.loads(path.read_text(encoding="utf-8"))
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(prev["at"])).total_seconds() / 3600
        changed = (prev.get("reachable"), prev.get("note")) != (reachable, row["note"]) or age >= HOST_COMMIT_HOURS
    except (OSError, ValueError, KeyError):
        changed = True
    write_atomic(path if changed else Paths.state / "tmp" / "host-last.json", json.dumps(row, indent=1))
    return {**row, "commit": changed}


def host() -> dict:
    """The last heartbeat with its age; `stale` means the host has not run for HOST_STALE_HOURS (off, offline, or its schedule broke)."""
    try:
        row = json.loads((home() / "host.json").read_text(encoding="utf-8"))
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(row["at"])).total_seconds() / 3600
    except (OSError, ValueError, KeyError):
        return {"seen": False, "stale": True}
    return {"seen": True, **row, "age_hours": round(age, 1), "stale": age > HOST_STALE_HOURS or not row.get("reachable")}


# ------------------------------------------------------------------ the computer side: run and record

def next_job(day: str | None = None) -> dict | None:
    """The first queued job whose gate is open, oldest day first, posts before pictures before Fiverr."""
    order = {k: i for i, k in enumerate(("yt_short", "yt_community", "tiktok", "flow_image", "fiverr_inbox", "fiverr_reply"))}
    for job in sorted((j for j in jobs(day) if j.get("status") == "queued"), key=lambda j: (j["day"], order[j["kind"]], j["id"])):
        if gate(job) is None:
            return job
    return None


def record(jid: str, result: str, *, url: str = "", note: str = "", ai_label: bool | None = None) -> dict:
    """What happened on the phone. result: posted | made | drafted | held | failed. A post's AI label must be stated."""
    if result not in ("posted", "made", "drafted", "held", "failed"):
        raise ValueError("result is posted, made, drafted, held or failed")
    job = load(jid)
    if result == "posted" and job["kind"] in POSTS and ai_label is None:
        raise ValueError("say whether the AI label was switched on (--ai-label yes|no)")
    row = {"id": jid, "kind": job["kind"], "key": job["key"], "result": result, "at": now(), "url": url[:300], "note": note[:300], "ai_label": ai_label}
    path = home() / "receipts.jsonl"
    write_atomic(path, "".join(json.dumps(r) + "\n" for r in receipts() + [row]))
    job["status"] = {"posted": "done", "made": "done", "drafted": "done", "held": "held", "failed": "queued"}[result]
    job.setdefault("history", []).append({"at": row["at"], "result": result, "note": note[:200]})
    if result == "failed" and sum(1 for h in job["history"] if h["result"] == "failed") >= 2:
        job["status"] = "held"                             # two failures: a person looks before a third try
    save(job)
    if job["kind"] == "yt_community" and result == "posted":     # the browser route (mcp-servers/yt-community) reads the same ledger
        led = Paths.state / "community_posts.jsonl"
        write_atomic(led, "".join(json.dumps(r) + "\n" for r in read_jsonl(led) + [{"slug": job["key"], "published": True, "at": row["at"], "note": "phone"}]))
    return row


def approve(jid: str) -> Path:
    job = load(jid)
    if job["kind"] != "fiverr_reply":
        raise ValueError("only fiverr_reply jobs need an approval")
    p = home() / "approved" / jid
    write_atomic(p, now() + "\n")
    return p


def status(day: str | None = None) -> dict:
    rows = jobs(day)
    by: dict = {}
    for j in rows:
        k = by.setdefault(j["kind"], {"queued": 0, "done": 0, "held": 0})
        k[j.get("status", "queued")] = k.get(j.get("status", "queued"), 0) + 1
    nxt = next_job(day)
    return {"enabled": cfg()["enabled"], "paused": safety.paused(), "host": host(), "jobs": by, "next": nxt["id"] if nxt else None,
            "blocked": [{"id": j["id"], "why": gate(j)} for j in rows if j.get("status") == "queued" and gate(j)][:10]}
