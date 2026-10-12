"""Song post: the YouTube copy for a finished song video, and (only with --apply) the upload.

The copy is written to be found and to be quoted. Search: the title leads with the song and its subject, the first 150 characters of the description say what
the song is and who made it. Answer engines (AEO) and generative engines (GEO): a plain "What is this song about / Who is it for / Who is Quiet Money"
block of short, self-contained sentences that name the channel every time, and the full original lyrics for long-tail lyric searches. The call to action
is an invitation: share it with one friend who wants to exit the rat race. One link (the free checklist, tracked), no money promise, an AI disclosure.
Nothing here posts unless `apply` is set; the upload goes through the studio's YouTube connection, which refuses any channel but the configured one.
Skill: .claude/skills/faceless-songs. Posting a song is the owner's yes, given for 2026-10-12's songs and renewed per batch.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from faceless import config, events, offer, safety
from faceless.config import Paths
from faceless.fsutil import read_jsonl, write_atomic

LEDGER = Paths.state / "songposts.jsonl"
TITLE_MAX = 100
DESC_MAX = 4900
CATEGORY_MUSIC = "10"
TAG_CHARS = 450


def _sentence(text: str) -> str:
    t = text.strip().rstrip(".")
    return t[:1].upper() + t[1:] if t else t


def _topic(theme: str) -> str:
    return re.sub(r"\s+", " ", theme.strip().rstrip("."))


def title_for(pack: dict) -> str:
    """Song first, then the subject a person would type into search, then the channel; the longest form that fits 100 characters."""
    song, topic = pack["title"].strip(), pack.get("seo_topic") or "Money and Emotions"
    topic = topic.title()
    for form in (f"{song} | A Song About {topic} | Quiet Money", f"{song} | A Song About {topic}", f"{song} (Original Song) | Quiet Money", song):
        if len(form) <= TITLE_MAX:
            return form
    return song[:TITLE_MAX]


def hashtags() -> str:
    return "#QuietMoney #MoneyPsychology #OriginalSong"          # three: YouTube ignores all hashtags when a description has more than fifteen


def tags_for(pack: dict) -> list[str]:
    words = ["quiet money", "money psychology", "original song", "ai music", "song about money", "money mindset", "rat race", "exit the rat race",
             "financial wellness", "personal finance", pack["title"].lower(), _topic(pack["theme"]).lower()]
    out, used = [], 0
    for w in words:
        if w and w not in out and used + len(w) + 1 <= TAG_CHARS:
            out.append(w)
            used += len(w) + 1
    return out


def link_for(pack: dict) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", pack["title"].lower()).strip("-")
    return offer.tracked(offer.checklist_url(), "youtube", "song", slug)


def description_for(pack: dict) -> str:
    song, topic, hook = pack["title"].strip(), _topic(pack["theme"]), pack["hook_line"].strip().rstrip(".")
    url = link_for(pack)
    about = pack["description"].strip()
    lines = [
        f"“{song}” is an original song by Quiet Money about {topic[:1].lower() + topic[1:]}.",
        "If it sounded like your life, send it to one friend who wants to exit the rat race.",
        "",
        f"The line people keep: “{hook}.”",
        "",
        "ABOUT THIS SONG",
        about,
        "",
        "QUICK ANSWERS",
        f"What is “{song}” about? It is about {topic[:1].lower() + topic[1:]}, told as a song rather than a lecture.",
        "Who is it for? People between 18 and 40 who earn a paycheck, feel behind with money, and want to feel understood before they are told what to do.",
        "Who is Quiet Money? Quiet Money is a channel about money psychology and personal finance education, built around one idea: the money rules nobody taught you.",
        "Not financial advice: it is a song and a story about feelings and habits, shared for education and reflection only.",
        "",
    ]
    if url:
        lines += [f"Free 7-day Money Reset checklist from Quiet Money: {url}", ""]
    lines += [
        "LYRICS",
        pack["lyrics"].strip(),
        "",
        "AI disclosure: the lyrics were written with AI assistance and the audio was made with an AI music tool. Not financial advice.",
        "",
        hashtags(),
    ]
    text = "\n".join(lines)
    if len(text) > DESC_MAX:                                   # YouTube allows 5000 characters; the lyrics are what gives way
        keep = DESC_MAX - len(text) + len(pack["lyrics"].strip()) - 40
        text = text.replace(pack["lyrics"].strip(), pack["lyrics"].strip()[:max(0, keep)].rsplit("\n", 1)[0] + "\n...")
    return text


def first_comment(pack: dict) -> str:
    return (f"Which line of “{pack['title']}” hit you hardest? Tell us below, and send it to one friend who wants to exit the rat race. "
            f"We read every comment.")


def build(pack: dict) -> dict:
    copy = {"title": title_for(pack), "description": description_for(pack), "tags": tags_for(pack), "first_comment": first_comment(pack),
            "category_id": CATEGORY_MUSIC, "synthetic": True, "language": "en"}
    copy["problems"] = problems(copy)
    return copy


def problems(copy: dict) -> list[str]:
    """The checks a post must pass before it can go out. An empty list means clean."""
    out = []
    if len(copy["title"]) > TITLE_MAX:
        out.append(f"title is {len(copy['title'])} characters")
    if len(copy["description"]) > 5000:
        out.append("description over 5000 characters")
    links = re.findall(r"https?://\S+", copy["description"])
    if len(links) > 1:
        out.append(f"{len(links)} links in the description (one allowed)")
    if len(re.findall(r"#\w+", copy["description"])) > 3:
        out.append("more than three hashtags")
    prose = copy["description"].split("LYRICS")[0] + copy["first_comment"]
    out += [f"claim check: {v}" for v in offer.violations(prose)]
    return out


def pack_dir_posts(day: str) -> list[Path]:
    return sorted((Paths.root / "music" / "packs" / day).glob("song*/pack.json"))


def write_pack(pack_json: Path) -> dict:
    """Write POST.md and post.json beside a song's pack. Returns the copy."""
    pack = json.loads(pack_json.read_text(encoding="utf-8"))
    copy = build(pack)
    folder = pack_json.parent
    write_atomic(folder / "post.json", json.dumps(copy, indent=2, ensure_ascii=False))
    write_atomic(folder / "POST.md", "\n".join([
        f"# YouTube post: {pack['title']}", "", "## Title", copy["title"], "", "## Description", "```", copy["description"], "```", "",
        "## Tags", ", ".join(copy["tags"]), "", "## First comment (pin it)", copy["first_comment"], "",
        "## Settings", "- Visibility: Public (or Schedule)", "- Category: Music", "- Altered or synthetic content: **Yes**", "- Made for kids: No",
        "- Thumbnail: the cover image", ""] + (["## Problems", *copy["problems"]] if copy["problems"] else [])))
    return copy


def posted(slug: str) -> dict | None:
    return next((r for r in read_jsonl(LEDGER) if r.get("slug") == slug), None)


def publish(pack_json: Path, video: Path, *, apply: bool = False, publish_at: str | None = None) -> dict:
    """Dry run unless `apply`. Refuses a clean-copy failure, a pause, a missing file, and a song already posted."""
    from faceless.providers import composio_tools
    pack = json.loads(pack_json.read_text(encoding="utf-8"))
    slug = re.sub(r"[^a-z0-9]+", "-", pack["title"].lower()).strip("-")
    copy = write_pack(pack_json)
    result = {"slug": slug, "title": copy["title"], "applied": False, "problems": copy["problems"]}
    if copy["problems"]:
        return result
    if prev := posted(slug):
        result["already"] = prev.get("video_id")
        return result
    if not apply:
        return result
    video = Path(video)
    if not video.is_file():
        raise FileNotFoundError(video)
    if why := safety.paused():
        raise RuntimeError(f"paused: {why}")
    channel = config.load()["publish"]["youtube"]["channel_id"]
    out = composio_tools.youtube_upload(str(video), copy["title"], copy["description"], copy["tags"], expected_channel_id=channel,
                                        category_id=CATEGORY_MUSIC, synthetic=True, publish_at=publish_at, job=f"song-{slug}")
    row = {"slug": slug, "video_id": out["video_id"], "privacy": out["privacy"], "publish_at": publish_at}
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    events.emit("SONG_POSTED", job=f"song-{slug}", video_id=out["video_id"])
    result.update(applied=True, **row)
    return result
