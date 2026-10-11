# Intake: howseen-ai/claude-motion-design

- **Source:** https://github.com/howseen-ai/claude-motion-design
- **Looked at:** 2026-10-11 12:38 UTC (public metadata and text only; nothing was cloned, installed or run)
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
- [x] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-11)

**TRIAL**, pipeline stage: render.

MIT. A Claude Code skill for motion videos in pure code with HTML, Playwright and ffmpeg: the same method the studio already runs (HyperFrames is HTML plus headless Chrome plus ffmpeg), and the same loop the JavaScript Claude video teaches (storyboard first, contact sheet, fix, re-render). Read from its README only.

**Worth taking:** Its storyboard-before-code step and contact-sheet check, as a gate for new drawn scenes.

**Only the owner can:** Read it once before building the next ledger scene kinds; do not install it.
