# Production: the edit bay

Turns a final script into a 1080x1920, 30 fps, -14 LUFS MP4. All code lives in `faceless/pipeline/`.

## Pipeline
1. **Voice** (`voice.py`): one TTS pass for natural prosody → word timings. If the read lands outside
   61-72 s, it re-synthesizes at an adjusted rate (aiming just inside the nearest edge). Punctuation is
   re-attached to timed words so captions break at sentences. Beats are aligned to words by character progress.
2. **Visuals** (`visuals.py`): one still per beat = `beat.visual + pillar.style + composition suffix`.
   Hook image uses the hero model. Deterministic seeds + prompt-hash cache: re-renders cost nothing.
3. **Captions** (`captions.py`): ASS subtitles via libass: 1-3 word chunks, active word gold at 108%,
   gold hook box for the first beat, Anton callouts that pop in, brand wordmark.
4. **Render** (`render.py`): beats → shots (beats > 3.2 s split into a wide shot + a punch-in on a new
   focal point). Each shot is a sub-pixel Ken Burns move (OpenCV warp, cubic) graded per pillar
   (color balance, vignette, film grain), encoded in parallel. Then one pass adds the progress bar and
   captions and mixes voice + ducked procedural music + whoosh SFX, loudness-normalized to -14 LUFS.
5. **Music** (`music.py`): original ambient pad + soft pulse in the pillar's key: never a copyright claim.

## Look per pillar
| Grade | Pillar | Feel |
|---|---|---|
| warm | story | amber/teal vintage film |
| gold | math | black + gold, high contrast |
| cool | psychology | desaturated noir |
| contrast | myth | punchy, crimson/charcoal |
| clean | playbook | bright, light vignette |

## Providers (fallback chains in `studio.toml`)
- Images: Cloudflare FLUX.2 klein 4B (free tier, ~156 neurons/image, ~60 images/day free) → OpenRouter
  Gemini image (~$0.04) → Pollinations (free, low-res, logo cropped) → procedural art.
- Voice: Edge neural TTS (free, word timings) → ElevenLabs (premium, timings) → Gemini TTS (free, estimated timings).

## Performance (4 vCPU)
~2-3 minutes per video end to end (images ~1 min, render ~1.5 min). 5 videos ≈ 12-15 minutes.

## Upgrading to motion (phase 2)
- Swap stills for short clips per beat (Veo 3.1 lite/fast via Gemini API, or HeyGen/Remotion scenes)
  by adding a `video` provider and letting `render.py` use clips where present: the caption, audio,
  and grading passes stay the same.
- Remotion (React) is the path for animated charts/number counters in the math pillar.
