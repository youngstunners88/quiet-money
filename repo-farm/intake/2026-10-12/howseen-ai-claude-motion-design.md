# Intake: howseen-ai/claude-motion-design

- **Source:** https://github.com/howseen-ai/claude-motion-design
- **Looked at:** 2026-10-12 15:09 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
python fetch_assets.py              # downloads the free music, SFX, logos and font (not redistributed here)
python -m http.server 8000 &        # serve the film
python render.py probe 1 8 15 20    # quick stills -> probe/sheet.png
python render.py full               # 24 s, 60 fps, subframe motion blur -> out/video.mp4
python audio.py                     # music + SFX by peak, -14 LUFS -> out/audio.wav
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# claude-motion-design

A Claude Code skill to make motion design videos **in pure code**: HTML + Playwright + ffmpeg. No After Effects, no Remotion license, no editing app.

Every frame is computed from time, rendered frame by frame, blended for motion blur, and cut to the beat of the music. Every sound effect lands on its measured peak.

<p align="center"><img src="examples/howseen-launch/preview.gif" width="320" alt="Howseen launch video, made with this skill"></p>

The example above is the launch video of [Howseen](https://howseen.ai) (AI visibility tracking: see if ChatGPT, Gemini and Perplexity recommend your brand). It was made with Claude Opus 5.5 and this skill, in 5 iterations. Its full source is in [`examples/howseen-launch`](examples/howseen-launch).

## Why code instead of an editor

- **Deterministic**: the whole film is one `seek(t)` function. Same input, same frames, every time. Fix one scene without touching the rest.
- **Free**: Chromium, ffmpeg, Python. No license, no subscription.
- **Beat-synced by construction**: scenes are placed on a beat map, the music drop is aligned to the key visual moment, SFX are placed by peak.
- **Iterable by an AI**: "make the transitions faster", "change the music", "add a 3D cube on the drop" are just code changes.

## Install

1. Copy the skill into Claude Code:
   '''bash
   mkdir -p ~/.claude/skills && cp -r skill/motion-de
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-12)

**PARK**, pipeline stage: render.

MIT. It makes motion design in pure code: HTML, Playwright and ffmpeg, with no editing app and no Remotion licence. Its strongest ideas are design choices, not dependencies: every frame is a function of time (seek(t)), so the same input gives the same frames, one scene can change without touching the others, and audio is aligned to measured peaks and loudness-normalised to -14 LUFS. We already have all three pieces (HyperFrames for frames, Playwright in the image, ffmpeg in the render) and do not need its pipeline. It also downloads music, SFX and fonts with a script, which the studio does not allow in an unattended run.

**Worth taking:** Deterministic seek(t) frames and -14 LUFS loudness normalisation for the final audio mix (rule: one measured loudness per video, not whatever the voice happens to be). Both can be added as steps in the existing render, with a test.

**Only the owner can:** Only if a sample shows our audio varies too much in loudness across videos: then add the normalisation step. No install needed for that.
