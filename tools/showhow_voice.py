#!/usr/bin/env python3
"""Voice a Showhow reel with Quiet Money's free Edge voice instead of ElevenLabs.

usage: showhow_voice.py <slug> [--rate +10%]
Reads repo-farm/showhow/engine/reels/<slug>/script.txt and writes voice.mp3 plus voice.alignment.json in the
ElevenLabs character-timing format that Showhow's tighten.py and align.py read (word times spread over their letters).
"""
import asyncio, json, subprocess, sys
from pathlib import Path

import edge_tts

from faceless import config

REELS = Path(__file__).resolve().parent.parent / "repo-farm/showhow/engine/reels"


async def main(slug: str, rate: str) -> None:
    reel = REELS / slug
    text = (reel / "script.txt").read_text().strip()
    voice = config.load()["voice"]["edge_voice"]
    com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    audio, words = bytearray(), []
    async for ch in com.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            words.append((ch["text"], ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7))
    (reel / "voice.mp3").write_bytes(bytes(audio))
    chars, st, en, pos, last = [], [], [], 0, 0.0
    for w, s, e in words:
        i = text.find(w, pos)
        if i < 0:
            raise SystemExit(f"word {w!r} not found in the script after offset {pos}")
        for c in text[pos:i]:            # spaces and paragraph breaks sit at the end of the previous word
            chars.append(c); st.append(last); en.append(last)
        n = len(w)
        for k, c in enumerate(w):
            chars.append(c); st.append(s + (e - s) * k / n); en.append(s + (e - s) * (k + 1) / n)
        pos, last = i + n, e
    for c in text[pos:]:
        chars.append(c); st.append(last); en.append(last)
    doc = {"voice": {"model": "edge", "id": voice, "name": voice + " (Edge)"},
           "alignment": {"characters": chars, "character_start_times_seconds": st, "character_end_times_seconds": en}}
    (reel / "voice.alignment.json").write_text(json.dumps(doc))
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(reel / "voice.mp3")],
                               capture_output=True, text=True).stdout)
    print(f"{len(words)} words, {dur:.1f}s, voice {voice}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[sys.argv.index("--rate") + 1] if "--rate" in sys.argv else "+8%"))
