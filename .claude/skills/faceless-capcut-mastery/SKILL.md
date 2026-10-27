---
name: faceless-capcut-mastery
description: Professional editing and finishing rules (retention pacing, beat-synced cuts, sound design, cinematic grade, text motion, QA and export) adapted from the owner's CapCut masterclass notes to what Quiet Money can do with ffmpeg, numpy and the phone's CapCut. Use when editing, polishing or QA-ing any video, when a cut feels flat, soft or slow, or when asked to "edit like a pro", fine-tune, grade, add sound design or make a hero video.
metadata:
  author: quiet-money
  version: 1.0.0
  source: owner's Drive doc "New CapCut Editing" (a creator masterclass transcript) and the Qwen knowledge base distilled from it, 2026-10-27
---

# Editing mastery (CapCut masterclass, adapted)

This skill sits on top of `faceless-film-editing`, `faceless-cineedit`, `faceless-reel`, `faceless-rhythm` and `faceless-craft`. Those decide what to cut; this one decides how to finish it. Where a technique needs a desktop NLE or a matting model we do not have, it says so instead of pretending.

## The rules that matter most
1. **Story over effects.** An effect that does not serve the line or the hit gets removed. Every clip needs a reason to be on screen.
2. **Cut the boring parts.** No dead air, no settling frames at the start of a clip, no 8 s static stretch. A visual change every 3 to 5 s on average, never more than 6 s still (our 10-27 Shorts had 8.5 s and 11.3 s holds: that is the gap Flow clips and punch-ins fill).
3. **Hide cuts with motion.** Jump cut plus a 6 to 12 percent punch-in on the next shot ("fake zoom"), or B-roll over the cut. Alternate zoomed and wide framings so repeated cuts do not feel identical.
4. **Think like the viewer.** Is the value obvious in the first 1.5 s? Is there a reason to stay to the last frame? Ending on a high point, held, then faded (L3, L4 in `faceless-craft`).

## Sound (this is where "slacking" is heard first)
- **Dialogue** peaks between -6 and -12 dBFS before the master. Our measured voice track peaks at about -8.8 dBFS: fine. Final master is -14 LUFS integrated, true peak under -1.5 dBTP (`render.py`, `reel.py`).
- **Noise:** clean the voice (`arnndn` or `anlmdn` if a take is noisy) before mixing. Never raise a noisy take to compensate.
- **Foley and ambience:** put the viewer in the scene. A wind bed under an exterior, room tone under an interior, a coin ping when a coin lands. Silence is only allowed as a deliberate drop before the biggest hit.
- **Risers and hits:** a riser into a cut, a hit or shutter exactly on it. Without a sound on the cut, the cut reads as a glitch.
- **Beat sync:** find the music's onsets and put cuts and impacts on them (`faceless/pipeline/beats.py` if present, else the numpy onset detector in this skill's recipe below). A cut a few frames off the beat feels wrong even when nobody can say why.
- **Duck, do not fight:** raise the bed before raising the voice; sidechain the bed under speech.
- **Music tweaks that sell a scene:** low-pass the bed (about 900 Hz) when something goes dull or underwater, then automate it back up on the surface.

## Picture
- **One global grade, applied last.** Grade clips to match, then one adjustment pass over the whole piece (what an adjustment layer is). Never grade clip by clip and leave it.
- **Teal and orange is the cinematic default:** lift shadows toward teal, push highlights warm, saturation about 1.1 to 1.2, contrast curve with crushed (not clipped) blacks. The named CapCut filters (Kendall, Journey, Cyan Red) cannot be copied; this curve is the equivalent.
- **Exaggerate or isolate with HSL:** boost one hue (gold is ours) or desaturate everything but the subject.
- **Texture:** grain and a light vignette so AI smoothness does not read as plastic (`cineedit.GRAIN`, `VIGNETTE`).
- **Letterbox bars** only for 16:9 hero pieces. On 9:16 they waste the screen, so do not add them to Shorts.
- **Never upscale soft AI stills.** Crop or reframe; do not blow them up.

## Text and motion
- **Short punch text, not subtitles of the speech.** The owner's rule (2026-10-25) bans word-for-word speech captions on edits: use 1 to 3 words on the hit, max two layers, never two competing.
- **Brand type:** Anton or Montserrat Black in gold `#FFD23F` on dark, Apple-style minimal when the piece is calm: one word per line, slide up on an ease curve with a short blur-in.
- **Supersample text.** Render text layers at 2x the output size and scale down (the "8K timeline trick" in ffmpeg terms) so edges stay crisp when the text moves or scales.
- **Count-ups** for money figures: drawtext with an expression for the number, motion blur by `tmix`. Keep the figure true to the script (`faceless-offer` rules: no income promises).
- **Text fly-through** (scale hard toward the lens on a cubic-in curve) is the one big transition we allow per piece, at the turn.
- **Kinetic shadows:** every text gets a soft drop shadow so it holds on busy footage.

## Techniques we cannot automate here
- **Key-subject masking and character glow, video-inside-text, liquid text, morph shapes:** need background matting or a desktop NLE. Do them in the phone's CapCut by hand only when a piece truly needs them, and say so.
- **CapCut's Smart HDR, filters, auto beat, auto captions:** owner-side tools. Keep Smart HDR OFF; never use AI ultra HD (owner, 2026-10-25).

## QA pass before anything ships (do all of it)
1. Loudness: `ebur128`: integrated -14 LUFS (+-1), true peak under -1.5 dBTP, first 15 s and last 15 s within 1 LU.
2. Flash frames and jump glitches: scene-detect segments shorter than 5 frames are bugs unless intentional.
3. Dead stretches: any hold longer than 6 s without a visual change is fixed (punch-in, cut, B-roll).
4. Contact sheet read by eye, then listen to the first 3 s and the ending.
5. Text typos and the "AI-assisted" ban: the words are never written into content; the platform AI toggle is the label.
6. Export: H.264 MP4, 1080x1920, high bitrate (10 to 15 Mbps minimum; 100 Mbps from CapCut finals), 30 fps for Shorts, Smart HDR off, no CapCut ending.

## Recipes
**Onset detector (numpy, no librosa):** decode the bed to mono 22.05 kHz PCM with ffmpeg, take a spectral-flux envelope over 1024-sample hops, keep peaks above mean + 1.2 std at least 0.25 s apart; use the nearest onset within 0.12 s of each planned cut. See `tools/hero_edit.py` for a working version.

**Punch-in:** `crop=iw/Z:ih/Z:(iw-iw/Z)/2:(ih-ih/Z)/2,scale=W:H` with Z between 1.06 and 1.12, easing in with `zoompan` when it should move.

**Speed ramp:** slow to 0.65x into the hit (optical-flow interpolated), snap to 2x through it, ease out (`faceless-cineedit`).

**Phone CapCut finishing** (`faceless-capcut-phone`): only for what ffmpeg cannot do. CapCut's gallery tab shows only files the phone has indexed: push to `/sdcard/Download/QuietMoney/`, `touch` the file, broadcast the media scan, then restart CapCut before opening New video. Dismiss promo pop-ups with their X, never the offer button.
