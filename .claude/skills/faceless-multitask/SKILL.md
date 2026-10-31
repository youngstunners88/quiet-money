---
name: faceless-multitask
description: Run Quiet Money lanes in parallel: PC renders in the background while the one phone does one task at a time, plus the twice-weekly Breathe film cadence. Use when the owner says "multitask", "continue on my phone", "while things render", or asks for the Breathe long-form to be posted or scheduled.
---

# Multitask: background PC work + one phone task

Owner rule (2026-10-31): never sit idle while a render runs. Start the PC job first, then use the phone.

## The pattern
1. **Start every PC job in the background first** (`(cmd > $SCRATCH/x.log 2>&1 &)` or `run_in_background`): `python -m faceless make --pillar P --script S.json --no-publish`, `node render.mjs <slug>` for Showhow, Blender renders, lead research. Two `make` runs at once are fine; the spend caps and ledger are shared.
2. **Then the phone, one task at a time** (it is a single device; adb automation cannot overlap): upload, Flow clip, Qwen/Gemini browser tab, TikTok/YouTube post. Check `adb devices` first.
3. **Poll with `until` loops or the completion notice**, never `sleep` chains. A background command that outlives 2 minutes is moved to the background automatically and notifies on exit.
4. Report each lane's result when it lands: what rendered, what the gauntlet said, what the phone did.

## Guard rails
- Never delete published posts (the owner does it by hand). Never auto-post a Showhow reel before the owner reviews it.
- Image model: 9B only, never klein 4B ([[feedback-never-flux-4b]]). The image cache is keyed by model.
- Put keys only in `.env` via a hidden `read -rsp` in a real terminal; test with a status code, never print.
- **Big videos to YouTube: share from the Drive app, not from adb.** Put the file in the owner's Drive (the owner or `Download` on the phone), search its name in the Drive app (search only, never browse folders), menu > Send a copy > YouTube: the Add details page then opens with Upload enabled. The adb-pushed share gives "Unable to preview video" and a dead Upload button. Drive-share also works for the 210 MB Breathe original.
- Phone quirks live in [[project-phone-posting-tools]]: push media then grant it by hand once, then `SKIP_PUSH=1`; ASCII-only titles and descriptions; keep descriptions near 600 characters.

## Breathe, twice a week
`music/videos/2026-10-18/vibe-breathe-original.mp4` is the owner's original (3:27, 1920x1080, untouched; "a masterpiece"). Post it as it is, never remake or recompress it. New ones come from `python -m faceless vibe` (skill `faceless-vibe`: premium 2K images, one coherent world, shots cut on the song's real energy, ElevenLabs voice welcome). Cadence: two long-form films a week, uploaded with `tools/yt-song-upload.py VIDEO TITLE_FILE DESC_FILE` (pack text in `music/packs/<day>/<slug>/`, title/desc ASCII, no "AI-assisted" wording, platform AI toggle on, hub link kept).


## Uploader notes (2026-10-31)
`tools/yt-song-upload.py` reports `FAIL: description does not match` after typing a ~600-character description on this laggy phone even when the text on screen is exact: check the screenshot, then finish by hand (Back x3, Attributes > AI use chevron (985,328) > Yes (102,1026), Back x2, Upload (540,2264)). Typing takes about 5 minutes; start it, then work elsewhere.
