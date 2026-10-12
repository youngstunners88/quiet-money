# The Quiet Money Daily Planner

Printable PDF, 375 pages, US Letter and A4. Built entirely from files in this repository, free and offline. Nothing is published by any command here.

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
