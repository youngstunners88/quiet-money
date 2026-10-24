---
name: faceless-cover-science
description: The evidence behind a cover that sells, from the owner's cover-research document (corrected edition): genre signalling and low complexity, colour in context, the Rule of One, title-as-cover, the curiosity gap, thumbnail-first design, marketplace specs, what the research does not support, and how to test variants. Use before designing or judging any product cover, thumbnail or hero image, when the owner asks why a cover works, or when two covers need a verdict.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/frontcover.py
---

# Cover science

Source: the owner's cover-research Google Doc (read in full, rule 17), corrected edition. Where the doc and a claim in circulation disagree, the correction wins. Nothing here is a promise of sales; a cover is a hypothesis and the shop's numbers judge it.

## What to do (each rule becomes a check in `faceless/frontcover.py`)

1. **Look like the genre, then be simple.** Buyers decide from a small image in a grid. A cover that reads as a money planner at a glance (prototypicality) and carries little visual complexity is judged faster and liked more. Check: `thumbnail_title_visible` (title still legible at 120 px).
2. **Colour is learned, not universal.** Colour works through genre associations: nonfiction yellow/white, business navy, financial literacy and wellness emerald, prestige black and gold, alarm black and crimson. Pick the colour for the job: printables emerald (reset, calm), kit navy and gold (the complete tier), debt black and crimson (the alarm, then the way out), rat race yellow and black (escape, "nonfiction" yellow).
3. **Rule of One.** One focal point, one primary colour, one accent. Checks: `palette_discipline` (at least 93% of chromatic pixels in two hue families) and `one_focal_zone` (the symbol zone holds 30-75% of the detail).
4. **The title is the cover.** Title type takes roughly 70-80% of the visual weight; the symbol supports it. Check: `title_contrast` at least 4.5:1 against the ground.
5. **Curiosity gap, moderate.** Loewenstein's information gap (not the Zeigarnik effect): one tagline that states what the buyer will see ("your payoff date and the interest it costs") without giving the answer. A gap that is too wide reads as clickbait; too narrow gives no reason to open.
6. **Design at thumbnail size first.** Squint test (blur the cover, the title and the symbol still read) and grid test (six covers in a row, none confusable: `series_gates`, hue or lightness at least 40 apart).
7. **Specs.** Ebook ratio 1.6:1 (1600 x 2560 here; KDP asks 2560 x 1600 shape rotated), RGB JPEG, a thin grey border on light covers so they do not melt into a white page, no price, sale or review claims on the cover.
8. **Test with traffic, not belief.** Run variants as separate listings or ads and compare click-through; one variable at a time; decide on numbers after enough views.

## Corrections table (do not repeat these)

| circulating claim | status |
|---|---|
| "Judged in 50 ms" (Lindgaard) | That study is about web pages, not book covers; use it only as "first impressions are fast" |
| "Humans process images 60,000 times faster than text" | Unsupported; never cite it |
| "A better cover lifts sales 30-50%" | Not established; treat any lift as to be measured |
| Curiosity gap = Zeigarnik effect | Wrong; it is Loewenstein's information-gap theory |
| One colour is best for all books | No; colour works in a genre context |

## Rules that stay ours

Education, not advice (rule 2), AI disclosure where the cover uses generated art (rule 4: the front covers here are drawn in code, no generated pictures), no real person's face (rule 3), no income promise in cover or tagline (rule 13; `offer.violations` runs over the tagline).

Use `faceless-front-cover` to build, check and upload them; use `faceless-cover` for the Daily Planner's Quinton cover.
