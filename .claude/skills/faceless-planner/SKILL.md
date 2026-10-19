---
name: faceless-planner
description: Build, check and ship the Quiet Money Daily Planner, the 427-page printable (US Letter and A4, undated) with one picture, one lesson and one action per day, weekly check-ins, wellness break pages, a cover, and its Etsy and Gumroad listing pack. Use when asked to build or rebuild the planner, change a lesson, a page, the cover or the art, check it before it is sold, make its listing, or add the owner's pictures to it.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/product_planner.py
---

# The Daily Planner

A product, not a video. Everything is built from files in this repo, free and offline. Read `channel/products/daily-quiet-money-planner/CONTEXT.md` first (style guide and content rules).

## Rules (read first)
1. **Every number is true.** Lessons live in `channel/products/daily-quiet-money-planner/content/q1.txt` to `q4.txt`. Never type a computed figure: write a placeholder such as `{fv:200,8,30}`; `faceless/planner_content.py` fills it from `faceless/moneymath.py`. See `references/lessons-format.md`.
2. **Education, never advice.** No "buy this", no promised returns; hypothetical rates are called hypothetical. `planner check` fails on advice phrases.
3. **Facts about real people only from `channel/research/` briefs.** The lessons name concepts and books, not people.
4. **Nothing public without the owner's yes:** price, copy, files, accounts. Building and checking are not public.
5. **Health pages carry the not-medical-advice note** and the posters with quantified or clinical claims are listed for the owner (`planner_wellness.REVIEW`). Never edit a poster's words.
6. A page that would clip is refused at build time (`Overflow`). Never shrink fonts to hide it: shorten the text.

## Steps
1. `python -m faceless planner build` (about 90 s; `--size Letter` or `--days 14` for a quick test). It draws any day without an owner picture, builds both PDFs and writes `build.json`.
2. `python -m faceless planner check`: content, computed numbers, no advice, text fit, wellness manifest, page counts (`references/page-map.md`), Etsy's 20 MB per file, listing copy gates. Every hard gate must pass; the soft ones (owner pictures, claims for review) are for the owner.
3. `python -m faceless listing build daily-quiet-money-planner`: nine Etsy pictures, a silent video, Gumroad cover and thumbnail, copy, checklist, report. The pictures are rebuilt output (git-ignored); send them to the owner with SendUserFile.
4. Look at pages as a buyer would: render a few with `pdftoppm -r 60 -f N -l N -png -singlefile file.pdf out` and read the images. A passing gate is not a good page.
5. `python -m faceless ci` before every push of code (rule 12 of CLAUDE.md).

## Where things live
- Pictures: owner's the repo folder assets/planner/source/day-NNN.* (cleaned copy in `clean/`) beat drawn ones (`faceless/planner_art.py`, 14 motifs, same day gives the same picture). See skill `faceless-poster-crop` for the owner's wellness posters.
- Cover: `faceless/planner_cover.py`; the print cover is page 1 of each PDF; `python -m faceless planner cover` writes `cover.png`.
- Page layouts: `faceless/product_planner.py`. Fonts: Anton, Montserrat, Carlito (OFL) in the repo folder assets/fonts.
- Listing copy: `channel/shop/catalog.json` (product `daily-quiet-money-planner`), human summary `channel/products/daily-quiet-money-planner/LISTING.md`.

## When the page count changes
It is stated in `catalog.json` (two descriptions and the notes), `LISTING.md`, `README.md`, `CONTEXT.md`, and computed in `planner check`. Change all of them in one commit and rebuild.

## Troubleshooting
- **PDF over 20 MB:** lower the picture quality in `Pen.image` (default 70; wellness pages use 58 at 820 px) or the drawn-art size in `planner_art.W/H`. Do not drop pages.
- **A lesson placeholder fails:** it is a closed set of functions in `planner_content.FUNCS`; add a function there with a test, never `eval`.
- **Title longer than one line:** shorten it (Anton 27 pt, one line).
