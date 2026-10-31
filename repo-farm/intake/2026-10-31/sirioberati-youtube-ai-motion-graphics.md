# Intake: sirioberati/YouTube-AI-Motion-Graphics

- **Source:** https://github.com/sirioberati/YouTube-AI-Motion-Graphics
- **Looked at:** 2026-10-31 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
git clone https://github.com/sirioberati/YouTube-AI-Motion-Graphics.git
python tools/export.py boards/D44Line.html --seconds 8 -o out/line.mp4
python tools/export.py timeline.json --audio my-voice.wav -o out/test.mp4 --first 60
python tools/export.py timeline.json --audio my-voice.wav -o out/video.mp4 --workers 6
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <a href="https://tein.ai"><img src="docs/branding/tein-ai-banner.svg" alt="TEIN AI: Join the waitlist for open-source AI workflows" width="960"></a>
</p>

<table>
<tr><td align="center" width="33%"><a href="boards/D50Venn.html"><img src="docs/gifs/D50Venn.gif" alt="Venn" width="100%"></a><br><sub><strong>Venn</strong></sub></td><td align="center" width="33%"><a href="boards/D49Timeline.html"><img src="docs/gifs/D49Timeline.gif" alt="Timeline" width="100%"></a><br><sub><strong>Timeline</strong></sub></td><td align="center" width="33%"><a href="boards/D51Matrix.html"><img src="docs/gifs/D51Matrix.gif" alt="2×2 matrix" width="100%"></a><br><sub><strong>2×2 matrix</strong></sub></td></tr>
<tr><td align="center" width="33%"><a href="boards/C111Slope.html"><img src="docs/gifs/C111Slope.gif" alt="Slope chart" width="100%"></a><br><sub><strong>Slope chart</strong></sub></td><td align="center" width="33%"><a href="boards/C116Heatmap.html"><img src="docs/gifs/C116Heatmap.gif" alt="Heatmap" width="100%"></a><br><sub><strong>Heatmap</strong></sub></td><td align="center" width="33%"><a href="boards/C241ChartFocus.html"><img src="docs/gifs/C241ChartFocus.gif" alt="Chart focus" width="100%"></a><br><sub><strong>Chart focus</strong></sub></td></tr>
<tr><td align="center" width="33%"><a href="boards/P227ScribbleFill.html"><img src="docs/gifs/P227ScribbleFill.gif" alt="Scrib
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-31)

**PARK**, pipeline stage: render.

MIT. A library of HTML motion boards (venn, timeline, 2x2 matrix, slope chart, heatmap, chart focus, scribble fill) exported to video by its own tools. Our HyperFrames cards cover the same job; the boards are a source of scene types, not a dependency. Its exporter runs a headless browser per frame, which our render already does.

**Worth taking:** Scene types we lack: slope chart (before and after), 2x2 matrix, timeline and venn. Re-draw them in our own card themes when a script needs one; credit the source in a comment.

**Only the owner can:** operator
