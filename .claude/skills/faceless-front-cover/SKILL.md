---
name: faceless-front-cover
description: Build, check and ship the striking front covers for the shop's printables, Money Reset Kit, Debt Payoff Planner (free gift) and Rat Race Escape Planner, drawn in code at 1600x2560 with automated squint and grid checks, then used in the Gumroad cover, thumbnail and Etsy first image. Use when a product has no front cover, a cover looks weak at thumbnail size, a new product needs one, or covers must be refreshed on Gumroad.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/frontcover.py
---

# Front covers

`faceless/frontcover.py` draws each product's cover from a spec: ground gradient, one symbol, title lines, tagline, tier pips (or a FREE GIFT pill). The design rules come from `faceless-cover-science`; the Daily Planner keeps its Quinton cover (`faceless-cover`).

## Commands

```bash
python -m faceless frontcover build [product]   # writes channel/shop/<id>/front/cover.jpg + thumb.jpg, then the series sheet
python -m faceless frontcover check [product]   # the checks as numbers; all must pass
python -m faceless frontcover sheet             # channel/shop/front-covers-sheet.png: look at it, at small size too
python -m faceless listing build <id>           # the listing pack now uses the cover: Etsy first image, Gumroad 16:9 cover and square thumbnail
python -m faceless shop refresh <id> --yes      # put the new name, copy, covers and thumbnail on the existing Gumroad product (never publishes)
```

## The look of the series

| product | tier | ground | symbol | title |
|---|---|---|---|---|
| Money Reset Printables | Starter | emerald | reset arrow around the brand coin | MONEY RESET / PRINTABLES |
| Money Reset Kit | Complete | navy | three rising steps 1-2-3 with the coin on top | MONEY RESET / KIT |
| Debt Payoff Planner | Free Gift | black and crimson | a chain link snapped, the broken end flying off | DEBT / PAYOFF PLANNER |
| Rat Race Escape Planner | (draft) | yellow | a doorway of light, a small silhouette from behind | RAT RACE / ESCAPE / PLANNER |

Quiet Money's coin and the line "THE MONEY RULES NOBODY TAUGHT YOU." appear on every cover so the series reads as one shelf.

## Changing or adding a cover

1. Add or edit the product's entry in `SPECS` (colours, title lines as `(text, font, size, colour)`, tagline). Taglines state what the buyer sees, never an income or result promise.
2. New symbol: write `_sym_<name>(size)` returning an RGBA image; keep it one shape and one accent colour. The engine measures the title first and fits the symbol under it; do not hard-code positions that can collide.
3. `frontcover build <id>` then `frontcover check <id>`. Look at the image at full and thumbnail size. A failed check is a failed cover: fix the design, never the threshold.
4. Dark covers sit on warm paper in the product shots (Etsy ranks dark main images lower; the `etsy_main_image_not_dark` gate enforces it).
5. `listing build <id>`, `listing check`, then `shop refresh <id> --yes`. Refresh builds first and checks every picture exists before it removes any Gumroad cover; if it refuses, nothing was changed.

## Free gift

A product with `price 0`, `free: true` and `price_test [0]` in `channel/shop/catalog.json` is a free gift (tier "Free Gift"). It still needs an entry `[shop.approved."<id>"] price = 0.0` in studio.toml (the owner said "issue out the debt payoff planner free", 2026-10-24). The offer layer lists it as kind `gift` (hub badge "Free"); it is never a paid offer in a video, and the free checklist stays the video call to action.

## Never

No photographs of real people, no price or sale text on a cover, no generated pictures (AI disclosure would apply), no change to a live product's price without the owner's approval entry.
