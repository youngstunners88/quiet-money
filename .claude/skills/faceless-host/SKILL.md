---
name: faceless-host
description: Create and keep consistent the Quiet Money host, the recurring human front man who appears once a week to welcome and update the community. Designs a brand-new voice with Muapi (a custom voice profile nobody has heard), keeps his face and voice identical across videos, writes and checks his lines, prices and generates ten-second Seedance 2 clips from the owner's Google Flow reference image, and schedules one a week. Use when asked for the host, the front man, the channel introduction, a weekly announcement, a new voice, or to put the same character in a new scene.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/host.py
---

# The host

Code `faceless/host.py`, CLI `python -m faceless host ...`, state and bible in `channel/host/`. Read `channel/host/BIBLE.md` first: it holds the locks.

## The four locks that keep him the same man
1. **Face:** the owner's reference image `channel/host/reference.png` (Quinton was made in Google Flow: AI-generated, not a real person, so rule 3 does not apply to him), passed as `@image1` to every image-to-video model. Image-to-video keeps identity far better than
   text-to-video; never regenerate his face from a description. Put him in other rooms by changing the room sentence only.
2. **Voice:** `python -m faceless host voice` makes a custom profile with `gemini-omni-audio` (a base voice reshaped by a written description; free; the id goes in
   `host.json`). Honest limit: it starts from one of Google's 30 base voices, so it is a new voice built on a base, not a recording of a person.
   Then **the anchor**: after the first intro, `python -m faceless host anchor <intro.mp4>` keeps 12 s of its audio; later clips use the reference-audio model
   (`seedance-2-omni-reference-no-video-fast`) with that file so the timbre carries over.
3. **Look:** one wardrobe (black blazer, charcoal roll-neck, the gold Q pin on the left lapel, wedding ring). The sentence `LOOK` in `host.py` is pasted into every prompt.
4. **Seed:** pass a fixed seed to models that take one.
Alternative with a built-in lock: Gemini Omni (`gemini-omni-character` from the photo, with the voice profile attached, then `gemini-omni-flash-1-1-image-to-video` with
`character_ids` and `audio_ids`): about $1.00 for ten seconds against $1.50 for Seedance 2. The owner asked for Seedance 2 for the intro, so that is the default.

## Workflow
```bash
python -m faceless host status                 # what exists: photo, voice profile, character, anchor, videos
python -m faceless host voice                  # once: the custom voice profile (free)
python -m faceless host character              # once the photo is in place: a reusable Gemini Omni character (free)
python -m faceless host line                   # the decision layer picks the best welcome from the candidates (Jev when TYPESAFE_API_KEY is set)
python -m faceless host clip "<line>"          # prices it; add --apply to generate (about $1.50 for ten seconds at 720p)
python -m faceless host anchor <video.mp4>     # after the first intro: keep the voice for later clips
```
Rules: lines are 20 to 26 words, complete sentences, no advice or promises (`check_line` refuses anything else). Generating spends: the desk's limits apply
(`[muapi]` $2/day, studio ceiling $3/day); a single clip needs `--max-usd` above $0.50 (the CLI default is $2.50). **Look at the clip before anything else happens
with it:** face, pin, voice, lip-sync, ending. A clip is not posted until the owner approves it.

## Voice and captions (non-negotiable)
Every spoken line of Quinton comes from a Seedance/talking-head clip that uses `voice-anchor.wav`; never narrate over him with another
TTS voice (Gemini Orus was rejected by the owner on 2026-10-22: "not the same voice"). A product video must open and feel like the
approved first clip. Captions come from `faceless.align` timings and must pass `python -m faceless caption-check` (see faceless-gauntlet).
Do not spend on a new clip until the script is read aloud against the first clip's voice and the owner has seen the plan.

## Weekly
`[host] enabled` stays false until the owner approves the intro. Then `host.due()` is true on the host's weekday once a week; `host.weekly_line()` writes the message
(checked like any line), `make_clip` renders it, `register` packages it as a job that the normal publisher and `post-backlog` can post.

## Disclosure
He is AI-generated. Descriptions say so; the upload carries the synthetic-media flag. Never present him as a real person or give him credentials.
