# The Quiet Money Daily Planner

Printable PDF, 427 pages, US Letter and A4. Built entirely from files in this repository, free and offline. Nothing is published by any command here.

| File | What it is |
|---|---|
| `Quiet-Money-Daily-Planner-Letter.pdf`, `...-A4.pdf` | the product (about 17 MB each, Etsy allows 20 MB per file) |
| `LISTING.md` | the price, copy and checklist summary for Gumroad and Etsy (full packs in `channel/shop/daily-quiet-money-planner/`) |
| `CONTEXT.md` | style guide and the content rules |
| `content/q1.txt` to `q4.txt` | the 365 lessons as editable data |
| `cover.png` | the print cover as a picture (`python -m faceless planner cover`) |
| `build.json` | when and how it was last built |

## Commands (run from the repo root)
```bash
python -m faceless planner build              # draw the missing pictures, build both PDFs (about 90 s; add --size Letter or --days 14 for a quick test)
python -m faceless planner check              # the gauntlet: content, computed numbers, no advice, fit, page counts, file size, listing copy
python -m faceless listing build daily-quiet-money-planner   # Etsy images, Gumroad cover and thumbnail, copy files, report
python -m faceless planner ingest <folder>    # number the owner's pictures into assets/planner/source/day-NNN.* (natural file order; --start N)
python -m faceless planner clean              # remove the @handle from them (originals untouched; cleaned copies in assets/planner/clean/)
python -m faceless planner inventory          # which days use the owner's picture and which are drawn
python -m pytest -q tests/test_planner.py
```

## How the pictures are handled
- **Owner pictures first.** Any `day-NNN.jpg|png|webp` in `assets/planner/source/` (or the cleaned copy in `assets/planner/clean/`) is used for that day. Any shape works: close to 2.2:1 is cropped, anything else is placed whole over a dark blurred copy of itself.
- **Missing days are drawn in code** in the same black-and-gold language (see `CONTEXT.md`), 14 motifs, a seed per day. Same day, same picture, every run.
- **Handle removal** (`planner clean`): thin text is found with top-hat and black-hat filters in the six places a handle usually sits, grouped into a line, and only those pixels are repainted with OpenCV inpainting. Pixels outside the mask are byte-identical to the original (a test proves it). Tested on drawn marks over dark artwork; **check `assets/planner/clean-before-after.jpg` by eye**, and pass `--box x0,y0,x1,y1` (fractions of the picture) when a handle sits somewhere unusual or the artwork has real text nearby. For heavily textured or bright backgrounds a manual pass in Photopea may still look better.
- Build artifacts: the drawn pictures go to `assets/planner/generated/` (git-ignored, rebuilt on demand).

## Changing things
- **A lesson:** edit the line in `content/qN.txt`, run `planner build`, then `planner check`. Computed numbers use `{name:args}` placeholders (`faceless/planner_content.py` lists them).
- **A page design:** `faceless/product_planner.py`. **The cover:** `faceless/planner_cover.py`. **A picture motif:** `faceless/planner_art.py`.
- A page that would clip is refused at build time, never shipped.

## The quiet-planner MCP server (for agents)
`.mcp.json` registers `python -m faceless.planner_mcp`, a dependency-free stdio MCP server, so an agent can do the whole picture job with tools instead of shell commands:
`planner_status`, `planner_normalize`, `planner_ingest`, `planner_clean`, `planner_review`, `planner_build`, `planner_check`, `planner_cover`. None of them publishes, lists, posts or prices anything.

| Layer | What it does | Cost | Needs |
|---|---|---|---|
| Local (always) | OpenCV handle finder and inpainting; local before/after checks (nothing changed outside the handle's area, under 2% of the picture repainted, no text still found) | free | nothing |
| Vision look (optional) | a small model through OpenRouter (`[planner] review_model`) sees one before \| after crop and answers three yes/no questions; its answer can only hold a picture back | about $0.0002 a picture, cap `[planner] daily_usd = 0.10` | `OPENROUTER_API_KEY` |
| Decision gate (optional) | `decide.ask` (Jev when `TYPESAFE_API_KEY` is set, Laya if `LAYA_URL` is) may escalate to "a person looks", never release a held picture; stays in `dry_run` until the owner flips it | per `[decide]` | `TYPESAFE_API_KEY` |
| FreeConvert (optional) | `planner_normalize` turns HEIC, TIFF, PSD, AVIF pictures into PNG (it cannot remove a watermark; that is the local layer's job) | free tier 20 conversion minutes a day, cap `[freeconvert] daily_minutes = 15` | `FREECONVERT_API_KEY` (a free FreeConvert account token the owner creates) |

Jev is TypeSafe's decision API, not a model served by OpenRouter: the two are separate keys and separate jobs (Jev answers short typed questions, OpenRouter's vision model looks at pictures). Each layer is
skipped quietly when its key is missing, and the report says which layers actually looked. `planner_clean` ends with a picture list: `needs_a_person` names the days the owner should open in the contact sheet first.

Typical run for an agent: `planner_status` -> `planner_normalize` (if phone pictures) -> `planner_ingest` -> `planner_clean` -> owner looks at `assets/planner/clean-before-after.jpg` -> `planner_build` -> `planner_check`.

## The wellness posters (supporting pages) and the Photopea crop
The owner's 44 "DID YOU KNOW" posters are the planner's supporting pages: wellness that goes hand in hand with money (a calm, rested, moving body makes steadier money
decisions), framed that way on the page. Forty are the owner's artwork; twelve more (weeks 41 to 52) are typeset by `python -m faceless planner posters-make` in the same style. They live in `assets/planner/wellness/`:
`original/` (as made, never changed), `cropped/` (handle removed), `report.json` (what was done to each, by which engine). The owner's logo and wordmark are in `assets/planner/brand/`.
- `planner_crop` (MCP) or `planner_posters.process()` finds the @handle (pixels first, then a vision model through OpenRouter as the second opinion), **crops it off in Photopea**
  (photopea.com driven headlessly through its official messaging API, the same crop the owner makes by hand), and checks the result against a plain Pillow crop (Pillow is the fallback).
- Two handles sit on the poster itself, over plain white: those are repainted (OpenCV), nothing else touched. Cut lines for handles right against the poster are given by hand (`manual_cuts`).
- Pictures where the pixels and the model disagree are never changed: they come back as `needs_human`.
- Measured on the 44 posters (15 had a handle, checked by eye): Claude Haiku 5.5 as the second opinion found 15 of 15, none wrong, $0.007 for all 44; the chat router `typesafe/jev-router` found 9 of 15 and flagged 10 posters that have no handle ($0.029),
  so Haiku does the locating and Jev (the real decision model, `typesafe/jev-1.13`, through OpenRouter's Decisions API, only `OPENROUTER_API_KEY` needed) is the review gate (`[planner] gate_backend`, `[decide] decisions_*`).

## Covers (skill `faceless-cover`)
`python -m faceless planner cover` writes `cover.png` (default: Quinton seated with steepled hands, rim-lit, glowing Q pin, title typeset in code) plus the alternates `cover-desk.png` (Quinton looking at the open planner) and
`cover-coin.png` (the brand coin, no person) for A/B. Scenes are made with Muapi from his reference photo (about $0.03 each, $0.02 to upscale) and live in `assets/planner/cover/`. A deep dive by Claude Haiku
(`.claude/skills/faceless-cover/references/haiku-cover-research.md`) found no evidence that a man, steepled hands or a silhouette raises sales; the one cue with some support is a visible face looking at the product. So the face stays readable
(rim light, not shadow) and the covers should be rotated and measured, not assumed. The cover character is disclosed as a virtual AI-generated host on the About page and in both listings.
