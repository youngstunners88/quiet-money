---
name: faceless-cineedit
description: Cinematic impact editing for the owner's Google Flow clips: speed ramps into the hit, adaptive colour grade, grain, a 2-frame gold flash on the peak, the Quiet Money brand mark and the end card. Use when asked to edit, cut, grade, brand or punch up a Flow clip, or when clips land in channel/flow/inbox.
---

# Faceless cinematic edit

## Why
Raw AI video is soft, floaty and evenly paced. The job is never to "clean it up": it is to rebuild its energy so the clip lands like a trailer moment. `faceless/cineedit.py` does this with ffmpeg and the repo's own brand kit, so an edit costs nothing but CPU.

## Run it
`python -m faceless cineedit <clip.mp4> --impact 8.9` writes `<clip>-edit.mp4` and prints what it did (grade chosen, mean luma, where the hit landed, the ramp segments). `--out` sets the path, `--card` the end-card line.

**`--impact` is the one judgement call.** It is the second, in the SOURCE clip, where the peak lands: the explosion, the clash, the moment of contact. Find it by eye before running: `ffmpeg -i clip.mp4 -vf "fps=1,scale=240:-1,tile=10x1" -frames:v 1 sheet.png`, then read the sheet. A wrong impact time ruins the edit, so never guess it from the prompt — the generator rarely puts the peak where the prompt asked.

## What the edit does
1. **Pacing.** Establish (1.4s, tightened to 1.25x), build (compressed toward `BUILD_SECONDS` = 3s, up to 2x), one second of slow motion at 0.5x into the hit, the strike at 2x, then the aftermath at 0.6x. Speeds stay inside atempo's 0.5-2.0 range so Flow's own audio ramps with the picture and the roar stays on the hit.
2. **Peak framing.** A 2-frame gold flash on the hit, and a slow push-in across the clip that peaks there.
3. **Grade, by brightness.** `mean_luma` measures the clip, then `grade_for` picks day, dusk or night. Crushing a night scene the way you crush a daylight one turns it to mud, so the night grade lifts the shadows and pushes saturation for neon instead. The flash opacity drops with the grade for the same reason.
4. **Texture.** Film grain and a vignette, so the frame has grit rather than AI smoothness.
5. **Brand.** The gold Q watermark bottom-right throughout, then a 1-second end card: the coin, the wordmark in Anton, and the handle.

## Rules
- **Check the output before it ships.** Read a contact sheet of the edit, not just the exit code. The two failures that have happened: the flash blew out a dark clip, and the grade crushed a night scene to black. Both were only visible in frames.
- **Watch for faces.** The Flow lane is faceless, and the generator sometimes puts a visible face in anyway. Flag it to the owner rather than shipping it quietly.
- **Never stretch a clip to fill time.** A short, hard edit beats a long, floaty one.
- The clips are AI output: the post's disclosure covers them.
