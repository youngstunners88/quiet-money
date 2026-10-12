"""Song desk: three original songs a day, written by Claude Haiku 5.5, ready for the owner to paste into Suno.

For each song the desk writes: a Suno style prompt, structured lyrics with section tags, a cover-image prompt, a title and a description with the AI
label. Two candidates are written per slot; the decision layer (`decide.ask`: Jev / Laya / Clef, heuristic fallback) picks the one that moves people.
Code gates refuse real-artist names, copied-looking or repeated lyrics, money promises and links. The desk never calls Suno, never uploads, never posts.
The owner makes the audio in Suno, then the studio edits the video. Playbook and sources: .claude/skills/faceless-songs/references/suno-playbook.md
"""

from __future__ import annotations

import json
import re
import time

from faceless import config, events, ledger, safety
from faceless.config import Paths
from faceless.fsutil import read_jsonl, write_atomic
from faceless.providers import ProviderError, ProviderUnavailable

MODEL = "anthropic/claude-haiku-5.5"
ROOT = Paths.root / "music"
PACKS = ROOT / "packs"
LEDGER = Paths.state / "songs.jsonl"

STYLE_MAX = 250          # community guidance says the first words of the style field weigh most; short is better (limits are not documented officially)
LYRICS_MAX = 2800        # kept under the 3000-character box people report
LINES_MIN, LINES_MAX = 24, 64

# Three lanes a day, rotating: different sound, voice and feeling so the feed is never one song three times.
LANES = [
    ("hush", "intimate acoustic folk-pop, fingerpicked guitar, soft piano, warm breathy vocal, 78 bpm, tender and reflective"),
    ("rise", "anthemic indie pop-rock, driving drums, big sing-along chorus, bright electric guitar, 118 bpm, hopeful and determined"),
    ("midnight", "dark minimal R&B, sub bass, soft finger snaps, smooth falsetto, 70 bpm, late-night honest and vulnerable"),
    ("porch", "americana soul, warm Rhodes, brushed drums, gritty heartfelt male vocal, 84 bpm, storytelling"),
    ("neon", "melodic hip-hop with a sung hook, lo-fi drums, airy pads, confessional rap verses, 88 bpm, introspective"),
    ("gospel", "gospel-tinged pop ballad, choir swell in the last chorus, piano, powerful female lead, 72 bpm, uplifting and raw"),
]
THEMES = [
    "the voice in your head that says you are behind, and who first put it there",
    "what your parents' silence about money taught you",
    "being the first in your family to break a pattern",
    "buying comfort when you were hurting, and forgiving yourself",
    "enough: the day you stopped comparing your life to a screen",
    "time is the only currency you cannot earn back",
    "the quiet rebuild: small, boring steps that nobody claps for",
    "love, rent and the conversations couples avoid",
    "the version of you five years from now thanking you",
    "scarcity as a childhood language you can learn to unlearn",
    "working hard for a life you are too tired to enjoy",
    "starting over after a number on a statement scared you",
]

BAD_STYLE = re.compile(r"\b(in the style of|sounds? like|à la|imitat|cover of|feat\.?|ft\.?)\b", re.I)
MONEY_PROMISE = re.compile(r"\b(get rich|guaranteed|risk[- ]free|passive income|financial freedom in|\d+%\s*(return|a year|per year)|buy\s+(bitcoin|stocks?|crypto)|invest in)\b", re.I)
URLISH = re.compile(r"(https?://|www\.|\.com\b|@\w{3,})", re.I)
TAG = re.compile(r"^\[[^\]\n]{2,40}\]$")

SYSTEM = f"""You are the songwriter and Suno prompt engineer for Quiet Money, a channel about money psychology for 18-40 year olds who feel behind with money.
Write ONE original song that makes listeners feel seen and then think. It is a song about people, not a lecture and not financial advice.

Rules for the lyrics
- Concrete images over abstractions (a cracked phone, a lunch box, the sound of a bill slipped under the door). One idea, one voice, one turning point.
- Structure: [Intro] [Verse 1] [Pre-Chorus] [Chorus] [Verse 2] [Pre-Chorus] [Chorus] [Bridge] [Final Chorus] [Outro]. Put the title or its key phrase in the chorus.
- The chorus is 4 lines, plain words, singable, repeated in full each time (write it out; never write "repeat chorus").
- Lines of 6-9 syllables, natural rhyme (never forced), no filler "oh oh" walls. Section tags on their own line, 1-3 words, in square brackets.
- The bridge is the thought the listener keeps: a question or a reframe. End on resolution, not on a sales line.
- Never mention real artists, brands, apps, products, URLs, handles. No advice to buy or invest, no promised returns or income, no shaming of people.
- Total lyrics under {LYRICS_MAX} characters, between {LINES_MIN} and {LINES_MAX} lines.

Rules for the Suno style prompt (the style field)
- Under {STYLE_MAX} characters. Order: genre and subgenre, mood and energy, vocal character, two or three key instruments, tempo in bpm. Most important words first, no synonym stacking.
- Never name a real artist, band or song, and never write "in the style of". Describe the sound instead.
- Also give a short "exclude" list (things to keep out, e.g. "autotune, spoken intro").

Rules for the cover image prompt
- Epic, powerful, poster-scale: ONE mythic scene that turns the song's idea into a giant visual metaphor (a table adrift in a storm sea, a shattered chain across a burning dawn, a lantern in a desert of black glass). Vast scale, dramatic sky, volumetric god rays, anamorphic lens, 8K blockbuster composition, 2-3 named colours.
- Never a quiet small still life. No text, letters or logos in the image. No visible faces: silhouettes from behind, hands, objects, places. End the prompt with "No text, no letters, no logos, no visible faces."

Return ONLY a JSON object with keys:
title (2-6 words), theme, hook_line (the single line people will remember), style, exclude, lyrics (string with newlines), image_prompt, video_notes (2-3 sentences: pacing and visuals for the owner's video), description (2 sentences for the post, no links, no money promise)."""


class SongError(Exception):
    def __init__(self, message: str, reasons: list[str] | None = None):
        super().__init__(message)
        self.reasons = reasons or []


def settings() -> dict:
    cfg = dict(config.load().get("songs", {}))
    cfg.setdefault("per_day", 3)
    cfg.setdefault("candidates", 2)
    cfg.setdefault("daily_usd", 0.10)
    cfg.setdefault("per_call_usd", 0.01)
    cfg.setdefault("model", MODEL)
    cfg.setdefault("effort", "low")
    return cfg


def lanes_for(day: str, n: int) -> list[tuple[str, str]]:
    ordinal = int(day.replace("-", "")) if day else 0
    start = ordinal % len(LANES)
    return [LANES[(start + i * 2) % len(LANES)] for i in range(n)]       # step 2: neighbours in the list sound alike


def theme_for(day: str, slot: int) -> str:
    return THEMES[(int(day.replace("-", "")) * 3 + slot) % len(THEMES)]


def _lines(lyrics: str) -> list[str]:
    return [ln.strip() for ln in lyrics.splitlines() if ln.strip() and not TAG.match(ln.strip())]


def _shingles(text: str) -> set[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return {" ".join(words[i:i + 4]) for i in range(max(0, len(words) - 3))}


def previous_lyrics() -> list[tuple[str, set[str]]]:
    return [(r.get("title", ""), _shingles(r.get("lyrics", ""))) for r in read_jsonl(LEDGER)]


def violations(song: dict, *, prior: list[tuple[str, set[str]]] | None = None) -> list[str]:
    """Hard gates. An empty list means the song may be offered to the owner."""
    bad = []
    for key in ("title", "style", "lyrics", "image_prompt", "description", "hook_line"):
        if not isinstance(song.get(key), str) or not song[key].strip():
            bad.append(f"missing {key}")
    if bad:
        return bad
    style, lyrics = song["style"], song["lyrics"]
    if len(style) > STYLE_MAX:
        bad.append(f"style is {len(style)} characters (max {STYLE_MAX})")
    if len(lyrics) > LYRICS_MAX:
        bad.append(f"lyrics are {len(lyrics)} characters (max {LYRICS_MAX})")
    body = _lines(lyrics)
    if not LINES_MIN <= len(body) <= LINES_MAX:
        bad.append(f"{len(body)} lyric lines (need {LINES_MIN}-{LINES_MAX})")
    tags = [ln.strip().lower() for ln in lyrics.splitlines() if TAG.match(ln.strip())]
    if sum(t.startswith("[chorus") or t.startswith("[final chorus") for t in tags) < 2:
        bad.append("needs a chorus at least twice, written out")
    if not any(t.startswith("[verse") for t in tags):
        bad.append("needs a [Verse]")
    if BAD_STYLE.search(style) or BAD_STYLE.search(song.get("exclude", "") or ""):
        bad.append("style names or imitates an artist")
    blob = " ".join(str(song.get(k, "")) for k in ("title", "style", "lyrics", "image_prompt", "description", "hook_line"))
    if MONEY_PROMISE.search(blob):
        bad.append("money promise or buy/invest call")
    if URLISH.search(blob):
        bad.append("link or handle in the text")
    if re.search(r"\b(text|words|letters|caption|logo)\b", song["image_prompt"], re.I) and not re.search(r"no (text|words|letters)", song["image_prompt"], re.I):
        bad.append("image prompt asks for text in the picture")
    if re.search(r"\b(face|portrait|man|woman|girl|boy)\b", song["image_prompt"], re.I) and not re.search(r"no (visible )?(face|faces)|silhouette|from behind|hands", song["image_prompt"], re.I):
        bad.append("image prompt may show a face")
    counts: dict[str, int] = {}
    for ln in body:
        counts[ln.lower()] = counts.get(ln.lower(), 0) + 1
    if len(set(counts)) < len(body) * 0.45:
        bad.append("too repetitive")
    mine = _shingles(lyrics)
    for title, other in (prior if prior is not None else previous_lyrics()):
        if mine and other and len(mine & other) / len(mine | other) > 0.25:
            bad.append(f"too close to an earlier song ({title})")
            break
    return bad


def heuristic_score(song: dict) -> float:
    """Code's own pick between candidates: concrete words, a short hook, a bridge that asks a question."""
    lyrics = song.get("lyrics", "")
    score = 0.0
    score += min(len(set(re.findall(r"[a-z']+", lyrics.lower()))) / 160, 1.0)
    score += 0.5 if "?" in lyrics else 0
    score += 0.5 if 3 <= len(song.get("hook_line", "").split()) <= 9 else 0
    score += 0.3 if any(t in lyrics.lower() for t in ("[bridge]", "[bridge")) else 0
    return round(score, 3)


def _call(msgs: list[dict], cfg: dict, job: str) -> tuple[str, float]:
    from faceless.providers.llm import _extract_json  # noqa: F401  (imported by the caller too)
    from faceless.pipeline.sketch import _cost, _post
    safety.guard("song", cfg["per_call_usd"])
    if not ledger.allow("songs", "usd", cfg["per_call_usd"], cfg["daily_usd"]):
        raise ProviderUnavailable(f"songs daily cap ${cfg['daily_usd']:.2f} reached")
    body = {"model": cfg["model"], "messages": msgs, "response_format": {"type": "json_object"}, "max_tokens": 4000,
            "temperature": 0.9, "usage": {"include": True}, "reasoning": {"effort": cfg["effort"]}}
    data = _post(body)
    spent = _cost(data.get("usage", {}))
    ledger.spend("songs", "usd", spent, usd=spent, job=job)
    return data["choices"][0]["message"]["content"] or "", spent


def write_song(day: str, slot: int, lane: tuple[str, str], theme: str, *, avoid: list[str], job: str, cfg: dict | None = None) -> dict:
    """One song that passed the hard gates. Asks, and once more with the refusal reasons. Raises SongError if neither answer passes."""
    from faceless.providers.llm import _extract_json
    cfg = cfg or settings()
    user = (f"Theme: {theme}\nSound lane '{lane[0]}': {lane[1]}\n"
            f"Avoid repeating these earlier titles and their images: {', '.join(avoid[-12:]) or 'none yet'}\n"
            "Write the song now as the JSON object.")
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    prior = previous_lyrics()
    reasons: list[str] = []
    text = ""
    for attempt in (1, 2):
        try:
            text, _ = _call(msgs, cfg, job)
            song = _extract_json(text)
            if isinstance(song, list) and song:
                song = song[0]
            if not isinstance(song, dict):
                raise ProviderError("not an object")
            if isinstance(song.get("lyrics"), list):
                song["lyrics"] = "\n".join(map(str, song["lyrics"]))
            why = violations(song, prior=prior)
        except (ProviderError, KeyError, IndexError, OSError) as e:
            why = [f"unusable answer: {type(e).__name__}"]
            song = {}
        if not why:
            song["lane"], song["slot"], song["day"] = lane[0], slot, day
            return song
        reasons += why
        msgs = msgs + [{"role": "assistant", "content": text[:6000]},
                       {"role": "user", "content": "Refused for: " + "; ".join(why) + ". Fix every point and return the complete JSON object again."}]
        time.sleep(1)
    raise SongError("; ".join(reasons[-4:]) or "no valid song", reasons)


def choose(cands: list[dict], job: str) -> tuple[dict, str]:
    """Pick the song that moves people most. Fallback is code's score; the decision layer answers in dry-run too (logged, acted on only when switched on)."""
    if len(cands) == 1:
        return cands[0], "only-candidate"
    from faceless import decide
    best = max(range(len(cands)), key=lambda i: heuristic_score(cands[i]))
    opts = {str(i): f"'{c['title']}': hook \"{c['hook_line']}\"" for i, c in enumerate(cands)}
    state = {"candidates": {str(i): {"title": c["title"], "hook": c["hook_line"], "chorus_and_bridge": c["lyrics"][:1400]} for i, c in enumerate(cands)}}
    d = decide.ask({"pick": decide.Q("choice", "Which song would make a 25 year old who feels behind with money feel seen, then think? Prefer concrete images, a chorus "
                                              "they could sing after one listen, and a bridge that reframes. Reject preaching.", str(best), options=opts)}, state, job)["pick"]
    idx = int(d.value) if str(d.value).isdigit() and int(d.value) < len(cands) else best
    return cands[idx], d.backend


def suno_md(song: dict) -> str:
    return (f"# {song['title']}\n\n_{song['theme']}_ · lane `{song['lane']}` · slot {song['slot']} · {song['day']}\n\n"
            f"## 1. Suno: Style of Music (paste in the style box)\n```\n{song['style']}\n```\n\n"
            f"## 2. Suno: Exclude styles (if your plan shows the field)\n```\n{song.get('exclude', '')}\n```\n\n"
            f"## 3. Suno: Lyrics (paste in the lyrics box, tags included)\n```\n{song['lyrics'].strip()}\n```\n\n"
            f"## 4. Cover image prompt (9:16 and 1:1)\n```\n{song['image_prompt'].strip()}\n```\n\n"
            f"## 5. Post\n**Title:** {song['title']} (Original song)\n\n{song['description'].strip()}\n\n"
            f"{DISCLOSURE}\n\n## 6. Video notes for the edit\n{song.get('video_notes', '').strip()}\n\n"
            f"## Owner checklist\n- Make it on a paid Suno plan (free-tier songs are non-commercial); listen to 2-3 takes, keep the one that lands.\n"
            f"- Fix any mispronounced word by respelling it in the lyrics box, not in the pack.\n"
            f"- Drop the audio and the finished video in the folder and tell the studio; it edits next.\n"
            f"- Turn the platform's AI label ON when posting.\n")


DISCLOSURE = "AI disclosure: this song was written with AI assistance and its audio is AI-generated. Original lyrics. Not financial advice."


def build_day(day: str | None = None, *, force: bool = False) -> dict:
    """Make the day's packs. Idempotent: a slot that already has a pack is kept unless force."""
    day = day or config.today_utc().isoformat()
    cfg = settings()
    out, problems = [], []
    lanes = lanes_for(day, cfg["per_day"])
    for slot, lane in enumerate(lanes, 1):
        folder = PACKS / day / f"song{slot}-{lane[0]}"
        if (folder / "pack.json").exists() and not force:
            out.append(json.loads((folder / "pack.json").read_text(encoding="utf-8")))
            continue
        job = f"{day}-song{slot}"
        theme = theme_for(day, slot)
        avoid = [t for t, _ in previous_lyrics()]
        cands = []
        for _ in range(cfg["candidates"]):
            try:
                cands.append(write_song(day, slot, lane, theme, avoid=avoid, job=job, cfg=cfg))
            except SongError as e:
                events.emit("SONG_REFUSED", job=job, reasons=e.reasons[-4:])
                problems.append(f"slot {slot}: {e}")
            except ProviderUnavailable as e:
                problems.append(f"slot {slot}: {e}")
                break
        if not cands:
            continue
        song, backend = choose(cands, job)
        song["chosen_by"] = backend
        song["disclosure"] = DISCLOSURE
        write_atomic(folder / "pack.json", json.dumps(song, indent=2, ensure_ascii=False))
        write_atomic(folder / "SUNO.md", suno_md(song))
        write_atomic(folder / "style.txt", song["style"] + "\n")
        write_atomic(folder / "lyrics.txt", song["lyrics"].strip() + "\n")
        write_atomic(folder / "image-prompt.txt", song["image_prompt"].strip() + "\n")
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps({"day": day, "slot": slot, "title": song["title"], "lane": lane[0], "theme": song["theme"], "lyrics": song["lyrics"]},
                               ensure_ascii=False) + "\n")
        events.emit("SONG_MADE", job=job, title=song["title"], lane=lane[0], chosen_by=backend)
        out.append(song)
    if out:
        rows = "\n".join(f"{i}. **{s['title']}** ({s['lane']}): {s['hook_line']}" for i, s in enumerate(out, 1))
        write_atomic(PACKS / day / "README.md", f"# Songs for {day}\n\n{rows}\n\nEach folder has SUNO.md: paste blocks 1-3 into Suno, block 4 into your image tool.\n")
    return {"day": day, "made": len(out), "wanted": cfg["per_day"], "songs": out, "problems": problems}


def status(day: str | None = None) -> dict:
    day = day or config.today_utc().isoformat()
    folders = sorted((PACKS / day).glob("song*/pack.json")) if (PACKS / day).exists() else []
    return {"day": day, "packs": len(folders), "wanted": settings()["per_day"], "titles": [json.loads(p.read_text(encoding="utf-8"))["title"] for p in folders]}
