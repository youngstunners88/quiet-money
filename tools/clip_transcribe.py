#!/usr/bin/env python3
"""Transcribe the speech of a Flow clip with the Gemini API (audio only) to check the spoken line. usage: clip_transcribe.py CLIP.mp4
The key comes from .env (GEMINI_API_KEY); never printed."""
import base64, json, os, re, subprocess, sys, tempfile, urllib.request
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key = os.environ.get("GEMINI_API_KEY") or re.search(r"^GEMINI_API_KEY=(.+)$", open(f"{root}/.env").read(), re.M).group(1).strip().strip('"\'')
mp3 = tempfile.mktemp(suffix=".mp3")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", sys.argv[1], "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k", mp3], check=True, timeout=60)
body = {"contents": [{"parts": [{"text": "Transcribe exactly what is spoken in this audio, word for word, with approximate start time in seconds for the first word. Say 'no speech' if there is none. Reply as: START=<seconds> TEXT=<words>"},
        {"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(open(mp3, "rb").read()).decode()}}]}]}
for model in ("gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-transcribe", "gemini-3.1-flash-lite"):
    req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}", json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=90)); print(model, "->", r["candidates"][0]["content"]["parts"][0]["text"].strip()); break
    except Exception as e: print(model, "failed:", str(e)[:120])
os.remove(mp3)
