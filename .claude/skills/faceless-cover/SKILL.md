---
name: faceless-cover
description: Design, generate and test product front covers and listing thumbnails for Quiet Money (the Daily Planner's Quinton cover, the coin cover, alternates for A/B). Covers the character locks, Muapi scene generation from the reference photo, upscaling, typesetting the title in code, the Q pin glow, AI disclosure, size limits and the evidence behind the design. Use when asked for a cover, a thumbnail, a hero image, to put Quinton on a product, or to compare covers.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/planner_cover.py
---

# Covers

The Daily Planner has three covers in `faceless/planner_cover.py`: **steeple** (default, Quinton seated with steepled hands, rim-lit, glowing Q pin), **desk** (Quinton looking down at an open planner), and the **coin** cover (the brand coin, no person, product-first). `cover(w, h, style=...)` renders any of them at any size; `python -m faceless planner cover` writes `cover.png` for the default.

## Rules
1. **No AI-made text on a cover.** Scenes are generated without words; the title, chips and tagline are typeset in code with the brand fonts (Anton, Montserrat). An AI picture regenerates letters wrongly (muapi skill rule 8).
2. **Quinton's locks do not change** (`channel/host/BIBLE.md`): face from `channel/host/reference.png`, short dark swept-up hair, light stubble, black blazer over a charcoal roll-neck, small round gold Q pin on the LEFT lapel. He is a virtual AI-generated host: the listing copy and the About page say so (CLAUDE.md rule 4; Etsy asks for AI disclosure).
3. **The face stays readable.** The research found no support for a pure silhouette, a male presenter or steepled hands raising sales; the one cue with some support is a visible face looking at the product. Keep "slight silhouette" as rim light, not shadow over the face.
4. **Etsy first photo 2000 px or more, Gumroad cover 1920x1080, thumbnail square.** The listing builder makes them; `python -m faceless listing build <id>` gates the sizes.
5. **Evidence is thin; test.** Read `references/haiku-cover-research.md` (what is verified, what is not). Rotate the covers (Gumroad takes up to 8) and compare click-through and favourites per impression for 3 to 4 weeks before calling a winner. Price is likely a bigger lever than the face.
6. **Spend:** each scene about $0.03, each upscale $0.02, through the Muapi desk (skill `muapi`): price first, caps apply, never route around a refusal.

## Making a scene
1. `python -m faceless muapi run nano-banana-2-lite-edit --set prompt="..." --set 'images_list=["channel/host/reference.png"]' --set aspect_ratio=2:3 --out <folder> --yes`. **`images_list` must be a JSON list** (a bare path gives a 422). Prompt: the locks above, the pose, "no text, letters, numbers or logos", a near-black `#0E0E10` ground with empty space in the top third for the title, palette near-black, cream `#F5F1E6`, gold `#FFD23F`.
2. Make two or three and choose by eye: hands correct (no extra fingers), face like the reference, pin on the left lapel.
3. Upscale: `seedvr2-image-upscale` (`--set image_url=<file>`), $0.02, returns about 3355x5001.
4. Resize to 1600 px wide, save as `assets/planner/cover/<name>.jpg`, add it to `SCENES` in `planner_cover.py`.
5. Look at it: render at 680 px and at thumbnail size. Check the title clears his head, nothing sits over the white pages, the pin glow is visible (`_pin` finds the pin by colour and adds the glow in code).
6. Rebuild: `python -m faceless planner build`, then `listing build`; the PDF must stay under 20 MB per file (a gate fails otherwise).

## Troubleshooting
- **No glow:** the pin was not found (needs gold pixels on the right chest); pass a scene where it is lit, or add a fixed position.
- **Title touches his head:** raise the style's offset in `cover_quinton` (`top = h * 0.125` for steeple, `0.17` for desk).
- **Hands wrong:** regenerate; do not edit the picture with AI (it changes everything).
