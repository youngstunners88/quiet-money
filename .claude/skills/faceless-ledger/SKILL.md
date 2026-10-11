---
name: faceless-ledger
description: The second visual style of the Quiet Money series, the "ledger" look (warm ledger paper, ink type, gold marker, every beat after the hook drawn in code, no generated stills), on the same brand kit as the cinematic look. Use to turn it on or off, compare it with the cinematic look on retention, render a sample, add a new ledger scene, or decide whether another animation library belongs in the stack.
---

# Ledger style (the second look)

One brand, two looks. The **cinematic** look (AI stills, slow camera moves, dark cards) is the house style. The **ledger** look is a
bookkeeper's page: cream paper, ink type in Anton and Montserrat Black, the brand gold as a marker under the key number, the series
name as the kicker. Same fonts, same gold, same captions, same voice and music; only the picture layer changes. It fits the
number-led series (math, escape, playbook). Stories, psychology and myths keep the cinematic look, they need faces and places.

Sample frames: `channel/empire/ledger-sample.png` (one frame per scene; the first is a count-up with its chart, then a rule card, years,
a two-bar comparison, two numbered steps, two phrase cards).

## How it works
- `faceless/pipeline/cards.py`: `THEMES` (CSS variables), `LEDGER_PAPER`, `style_for(job_id, pillar)`, `pick(..., style)`. In ledger style every beat after
  the hook becomes a drawn scene: comparison, numbered step, counting number, or the beat's key phrase. The hook keeps its still (cover and hook box sit on it).
- `faceless/pipeline/visuals.py` picks the look once per video and records it in `job.artifacts["style"]`; `render_reel` reads it for the theme.
- `[production.ledger]` in `studio.toml`: `mode` (off | on), `pillars`, `share` (fraction of those series drawn in ledger, fixed per video by a hash of its id), `accent`.
- Cost: a ledger video makes about one image instead of ten, so no image quota, no Muapi fallback and no still that image QA can flag. Measured spend so
  far is mostly OpenRouter text calls, not images, so expect a small saving, not a large one. The value is the variation and the A/B.

## Turn it on (owner decision)
It ships **off**. The owner looks at a sample and says go (same rule as sketch scenes). To make a sample:
`PYTHONPATH=. python .claude/skills/faceless-ledger/scripts/sample.py ledger` (from `faceless-studio` root; builds a nine-beat
escape script and renders `state/tmp/ledger/ledger/cards/reel.mp4` in about a minute; pass `cinematic` for the house look on the same beats), then look at frames (`ffmpeg -ss T -i reel.mp4 -frames:v 1`), never trust the render without looking.
On "go": set `mode = "on"` and keep `share = 0.5`.

## Judge it
Every video records its look. After about 20 posts per look, compare average view duration and viewed-vs-swiped-away per look in `analytics/`
before changing `share`. Do not conclude from fewer: the series, slot and topic differ video to video.

## Add a ledger scene
Same rules as `faceless-hyperframes`: seek-safe tweens only, text out of the caption band (y 1070 to 1280), escape every model-written string,
look at frames. Ideas not built: a ruled column that totals itself, a stamp ("PAID") that lands, a pencil underline that draws, an equation in KaTeX.

## The stack (what each tool does here)
| Layer | Tool | Status |
|---|---|---|
| Clock and easing | GSAP 3.14.2, hash-checked | in use |
| Renderer | HyperFrames 0.8.136 (HTML to MP4) | in use |
| Scene design | Haiku 5.5 designs a JSON scene, code validates it (`sketch.py`) | built, off until the owner approves a sample |
| Page camera | Playwright (screen recordings of our own calculators, frame QA) | verdict USE, lane not built yet |
| Stickers | lottie-web with Lottie we make ourselves | verdict TRIAL |
| Math look | Manim Community | PARK; its graphs are redone in GSAP and SVG |
Verdicts and reasons: `repo-farm/intake/2026-10-11/decisions.md`.
