---
name: faceless-hyperframes
description: Motion cards for Quiet Money videos, drawn in code with HyperFrames (free, local, no API key). Animated count-up number cards, kinetic phrase cards and growth charts that replace AI stills, so videos need fewer generated images and never ship placeholder art. Use to turn cards on or off, add a new card design, debug a failed card render, or when image quota is the bottleneck.
---

# HyperFrames motion cards

[HyperFrames](https://github.com/heygen-com/hyperframes) turns an HTML + GSAP composition into an MP4 with headless
Chrome and ffmpeg. Apache-2.0, **no API key, no account, no per-render fee** for local rendering (HeyGen's cloud
and desktop app are separate and not used). Needs Node 22+ (present in the cloud environment) and ffmpeg.

## What it does here
`faceless/pipeline/cards.py` draws one **reel** per video (a single Chrome launch, ~35 s for five cards) and
`render.py` cuts each card beat out of it. Two card kinds, both on the pillar's own dark palette with the series name
as a kicker:
- **stat**: the callout number counts up to its exact value with a growing compounding-curve chart (e.g. `$698,202`).
  Years (1900-2100) are shown static; the font auto-fits the frame width.
- **phrase**: kinetic words reveal for a beat that has no number (used for placeholder replacement).

A card replaces an AI still, so a card beat costs **no image generation**: it saves quota and can never end up as the
procedural placeholder art that trips the `no_placeholder_art` gate.

## Config (`studio.toml [production.cards]`)
| mode | behaviour |
|---|---|
| `off` | never use cards |
| `auto` | only a beat whose image fell to procedural placeholder art becomes a card |
| `numbers` (current) | `auto`, plus numeric-callout beats of the listed `pillars` (math, escape) become count-up cards |

The hook beat (beat 0) always keeps its hero still: the hook box and cover sit on it. If Node/Chrome is missing or the
reel fails, the video falls back to stills (event `CARDS_FAILED`), so cards can never block a batch.

## Rules the renderer imposes (learned the hard way)
- Only `set/to/from/fromTo` timeline calls and the properties opacity, x, y, scale, rotation, width, height,
  visibility are seek-safe. **No `onUpdate` callbacks**: the count-up is stacked values toggled by `visibility`.
- GSAP loads from jsDelivr at render time (pinned 3.14.2). If the CDN is unreachable the render fails and the
  fallback applies.
- The CLI is pinned (`cards.CLI = hyperframes@0.8.136`) so the same input renders the same video. Upgrade on purpose:
  bump the pin, run `pytest`, render a sample, compare frames.
- Keep text out of the caption band (y ~1070-1280): captions sit at 61% height. Cards use the upper 40% for content and
  the chart below the captions.

## Add a card design
1. Add a branch in `cards._scene` (HTML + the `tl.` calls) and a kind name in `cards.pick`.
2. Cover it in `tests/test_engine.py` (escape all LLM text with `html.escape`: callouts and phrases are untrusted).
3. Render a real reel and **look at frames** (contact sheet) before shipping: e.g. run `cards.render_reel` on an existing
   script, then `ffmpeg -ss <t> -i reel.mp4 -frames:v 1`.
4. Ideas not built yet: two-value comparison bars (25 vs 35 years old), step list for playbook videos, animated
   caption styles, transitions between stills.

## Security and hygiene
- `npx hyperframes init` also installs third-party agent skills that "run with full agent permissions". **We never run
  `init` or install those skills**; the engine writes its own project and calls only `render`.
- Anonymous telemetry is switched off (`telemetry disable` in the session hook; `DO_NOT_TRACK=1` on every render).
- Compositions are generated from LLM text: everything is HTML-escaped, and numbers are parsed, never evaluated.

## Debug
`grep CARDS_ state/journal.jsonl | tail`; run the reel by hand with
`npx --yes hyperframes@0.8.136 render production/output/<day>/<job>/cards -o /tmp/reel.mp4`
(`hyperframes check <dir>` lints a composition). The generated `cards/index.html` is kept per job as the record.
