---
name: faceless-poster-crop
description: Bring the owner's artwork into the planner and take their @youngstunnersss handle off it. Finds the handle (pixels first, a vision model second), crops it off in Photopea the way the owner does by hand, repaints the few that sit on the poster itself, keeps originals untouched, and lists anything uncertain for a person. Use when the owner shares pictures or a Drive doc of posters, asks to remove or crop a handle or watermark, or asks which pictures are done.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/planner_posters.py
---

# Poster handle crop

The owner's 44 "DID YOU KNOW" wellness posters carry `@youngstunnersss` on the floor strip below the poster (15 of them), or on the poster itself (two). The owner's own fix is a crop in Photopea. This skill does the same, repeatably.

## Rules
1. **Originals are never changed.** the repo folder assets/planner/wellness/original/ is as received; results go to `cropped/`; `report.json` records what was done to each and why.
2. **The pixels say where, the model must agree.** A disagreement is `needs_human`; it is never cropped on a guess. Position must agree within 5% of the height.
3. **Never use AI to edit a picture whose words matter** (muapi skill rule 8). Cropping and repainting a few dark text pixels on plain white are the only edits.
4. **Look at the result.** A gate passing is not a clean picture: make a contact sheet of the bottoms and read it (`references/ground-truth-method.md`).
5. Pictures with health claims keep the owner's words; the page adds the disclaimer (skill `faceless-planner`).

## Steps
1. Get the files: skill `faceless-drive-intake` (a Drive doc's images are inside its zip export).
2. `planner_crop` (MCP, skill `faceless-planner-mcp`) or in Python: `planner_posters.ingest(folder, skip=(positions that are logos or banners,))`, then `planner_posters.process(manual_cuts=..., paint=...)`.
3. For each `needs_human`: view the bottom of the picture with scale marks (fractions of the height), choose a cut row 6 to 10 px above the first letter, and pass it as `manual_cuts={"wellness-021": 1197/1248}`. If the handle is on plain white inside the poster, pass `paint={"wellness-036": [x0, y0, x1, y1]}` (fractions) instead.
4. Check: no handle left, no poster edge cut, nothing else changed. Re-run only changes; the pipeline is deterministic.

## What was measured (44 posters, hand-checked)
15 handles. Pixels alone: 12 found, none wrong. Claude Haiku 5.5 as second opinion: 15 of 15, none wrong, $0.007 for all. `typesafe/jev-router`: 9 of 15 and 10 false alarms, $0.029. So `[planner] locate_model` is Haiku. Photopea crop = Pillow crop of the same box (mean pixel difference under 4), which is the check on every crop.

## Troubleshooting
- **No Chromium or Photopea slow/blocked:** the pipeline falls back to Pillow and says `engine: pillow` in the report. See skill `faceless-photopea`.
- **Handle against the poster edge:** the pixel finder cannot find clear floor; it comes back `needs_human`. Use a manual cut.
- **A different handle or a logo:** change `PROMPT` in `faceless/planner_locate.py` and re-measure before trusting it (skill `faceless-bench`).
