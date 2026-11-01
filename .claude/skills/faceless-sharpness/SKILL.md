---
name: faceless-sharpness
description: Make Quiet Money videos sharp and prove it before posting. Use when the owner says a video looks blurry, soft, pixelated or low quality, or before posting any batch. Measures resolution, bitrate and edge energy, finds which link in the chain softens the picture, and covers the platform-side reasons a sharp file still looks soft.
---

# Sharpness: measure first, then fix the right link

Owner (2026-11-01): "why is everything still blurry". Never answer from a guess: run the checker on the actual files.

```
.venv/bin/python tools/sharpness_check.py distribution/queue/<day>/*/video.mp4        # Shorts
.venv/bin/python tools/sharpness_check.py --flat production/showhow/.../video.mp4     # flat drawn graphics: resolution only
```
PASS needs width >= 1080, bitrate >= 6 Mbps and median edge energy >= 6. Reference points: the soft 10-31 Shorts scored 2.2 to 2.7 at about 1.2 Mbps; the Flow-still remakes score 10 to 15 at 16 Mbps.

## The chain, and what softens each link
1. **Stills (the biggest one).** FLUX klein 4B at 864x1536 upscaled to 1080x1920 is soft by construction. Use Flow stills (skill `faceless-flow-stills`, Nano Banana 2.1, 768x1376, Lanczos + unsharp) or klein 9B. Never 4B ([[feedback-never-flux-4b]]). The image cache is keyed by model, so old soft stills are not reused.
2. **Encode.** `faceless/pipeline/render.py` final pass: `crf 16`, `maxrate 16M`, `preset medium`, `unsharp` + light grain on the picture only (captions stay clean). The old `crf 21 / 6M` cap squeezed zooming stills to about 1 Mbps.
3. **Motion.** Slow zooms on soft stills smear; sharp stills hold.
4. **Showhow reels.** Remotion output is crisp but flat, so the bitrate looks low (1.4 Mbps) by design; gate it with `--flat`.
5. **Do not recompress for upload.** Push the render as is (the phone posters already do).

## Why a sharp file can still look soft (check these before blaming the render)
- **The old versions are still live.** A re-render does not replace a post. List what is actually posted (YouTube Shorts tab, TikTok profile) and have the owner delete the old soft ones by hand (the agent never deletes published posts).
- **A failed TikTok post leaves only the old video there.** After any post run, confirm each result (the log's last line must say posted), not just that YouTube worked.
- **YouTube serves fresh uploads in low resolution first** ("Processing up to HD, N min left"); HD and 1080p appear after processing. Judge sharpness on the file, or on the video again after processing, never in the first minutes.
- **TikTok recompresses hard.** Upload the 1080x1920 original (the 16 Mbps render), not a screen recording or a CapCut export of it.

## Before posting a batch
Run the checker on every pack, fix or re-render anything that FAILs, then post. Record the numbers in the report.
