# Muapi recipes

Verified live on 2026-10-08 unless a recipe says "not run". A command spends only with `--yes`; the prices are what `estimate` returned.
Every recipe ends with the check that must follow it, because a model that answered is not a model that was right.

## 1. Find a model and read its fields
```bash
python -m faceless muapi find "text to speech" --category "Text to Audio"
python -m faceless muapi inspect ideogram-v3-t2i          # fields, types, allowed values, defaults
python -m faceless muapi estimate ideogram-v3-t2i --set prompt="x" --set aspect_ratio=9:16
```
Names move: `inspect` reads the live schema, so trust it over this file. A model's submit path is its `endpoint_url` slug, which can differ
from its name (`ai-image-upscaler` posts to `ai-image-upscale`); the desk handles it.

## 2. Voice samples (verified: the same 279 characters, three voices)
The studio's voice is free Edge TTS. To let the owner choose by ear, make the same narration in the premium voices:
```bash
python -m faceless muapi run elevenlabs-tts-turbo-2-5 --set prompt=@narration.txt --set voice_id=nPczCjzI2devNBz1zQrb --set speed=1.1 --out voices --yes
```
```python
from faceless import muapi
muapi.run("gemini-3-1-flash-tts", {"speakers": [{"speaker_id": "Speaker 1", "voice_name": "Charon", "accent": "American (Gen)", "style": "Newscaster", "pace": "Natural"}],
          "dialogue_turns": [{"speaker_id": "Speaker 1", "text": narration}], "sample_context": "Calm, confident explainer narration."}, "voices")
```
Measured: ElevenLabs Turbo 2.5 $0.014 for 279 characters (about $0.05 for a 1,000-character video script), 15.9 s; Gemini 3.1 Flash TTS $0.0098, 18.7 s; Edge $0 and 15.5 s.
Check: normalise all samples to the same loudness (`loudnorm=I=-16`) before anyone compares them, then let the owner listen. Choosing a Muapi voice for the
videos needs word timings for the captions: Muapi's TTS returns none, so use `openai-whisper` (`response_format` verbose_json) or the engine's `estimate_timings`.

## 3. How many people search for it (verified)
```bash
python -m faceless muapi run seo-keywords-search-volume --set keywords='["debt payoff planner","fire calculator"]' --yes
```
$0.0148 for 12 keywords, $0.0164 for 16. Returns monthly Google volume, CPC and competition per keyword; the answer is saved as JSON next to the media.
The 2026-10-08 run is in `channel/research/keyword-demand-2026-10-08.md`. Check: Google volume is a proxy for Etsy and Gumroad demand, never the same number.

## 4. Words inside a picture: draw them in code
`ideogram-v3-t2i` ($0.02 to $0.05) renders legible type, but still misspells now and then. Anything that carries our name, a price, a number or a
claim is drawn with Pillow from our own strings (`faceless/mockup.py`), so it is spelled right by construction. If a generated picture must contain text,
read it back with OCR (recipe 6) and compare it with what you asked for.

## 5. Never run an AI edit over a product screenshot (verified, and it went wrong)
`nano-banana-2-1-edit` ($0.06 at 2k) did what was asked, a light-gray backdrop, and silently changed the product's own contents: "Your age" became
"Your aga", "$900" became "$800", "3.88%" became "3.80%", "Rat-Race-Escape-Planner.xlsx" became ".alsx". An edit model regenerates every pixel.
Use edit models only for scenes with no text or numbers that matter (a desk, a texture, a background), and composite the real screenshot in code.
A listing picture that shows a number the product does not produce is a false claim.
```bash
python -m faceless muapi run nano-banana-2-1-edit --set prompt="empty wooden desk, soft window light, no text" --set images_list='["room.jpg"]' --out scenes --yes
```

## 6. Read the text in a picture (OCR, verified)
```bash
python -m faceless muapi run ocr-recognize-text --set image_url=hero.jpg --yes      # $0.02; a local path is uploaded for you
```
Returns a list of `{text, bbox: [x, y, w, h] as fractions, confidence}`. Check: every string you drew must appear, and a still that should have no text must return an empty list.
(The engine's per-still check is cheaper: Cloudflare Clef, 28 free neurons. Use OCR for listing pictures and for a second opinion.)

## 7. Animate a still (verified for hook clips)
```bash
python -m faceless muapi run seedance-pro-i2v-fast --set prompt="slow push-in, no new objects, no text" --set image_url=still.jpg --set duration=5 --set resolution=720p --out clips --yes
```
About $0.15 for 5 s at 720p. The engine's own hook clip path (`hookclip.py`, OFF by default) adds the frame-by-frame check. Check: look at the first, middle and last frames for warped objects, new text or faces.

## 8. A quick language-model answer (verified)
```bash
python -m faceless muapi run gemini-3-8-flash --set prompt="Summarise in one line: ..." --set system_prompt="Answer in one line." --yes     # $0.0002
```
`image_url` makes it read one picture. The answer comes back in `text` and is saved as JSON. Models from every vendor are listed under category "Text to Text".

## 9. Search and competitor data (cheap; run once to see the shape)
`seo-google-serp` $0.001, `seo-rank-track` $0.001 (is our page ranking for a phrase), `seo-youtube-organic` $0.0033, `seo-youtube-video-info` $0.01 (views, tags, channel),
`seo-youtube-video-subtitles` $0.01, `social-search-posts` $0.02 (platform tiktok, instagram, youtube, x, reddit or linkedin; query; limit), `news-search` $0.02,
`research-web-answer` $0.05. Check: these report what is public today; never copy another creator's script or caption, only learn what topics and hooks get attention.

## 10. Publishing (not run: needs the owner's one-time connection)
`tiktok-publish` (`account_id`, `media_url`, `title`, `is_ai_generated` must be true), `youtube-publish` (no synthetic-media field), `instagram-publish`,
`pinterest-publish`, `linkedin-publish`, `threads-publish`, `x-publish`, `facebook-publish`: $0.01 to $0.02 each. The owner connects accounts at muapi.ai (Integrations).
Show the owner the exact caption, account and time first. The engine's publish mode stays `local` until they say go.
