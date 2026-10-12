# Daily Quiet Money Planner: style guide and rules

A 415-page printable (US Letter and A4), undated: one picture, one short lesson and one small action for every day of the year. Complements the video
series and the spreadsheets in `channel/products/`. The owner approves price, copy, files and accounts before anything goes live (CLAUDE.md rule 9).

## What is in the book
Cover | Welcome | Net worth snapshot | Debt map | Year at a glance | 365 daily pages | Summary and goals | Money words | 2 notes pages | About this planner.
Each week runs Monday Learn, Tuesday By the numbers, Wednesday Do it, Thursday Mindset, Friday Action, Saturday weekly check-in, Sunday reflect and reset.
52 weekly themes in four quarters (foundations; debt, credit and compounding; investing and income; life, protection and freedom), plus a bonus Day 365.

## Content rules (they are the channel's rules)
1. **Every number is true.** Lesson text never contains a hand-typed computed figure. Write `{fv:200,8,30}`-style placeholders; `faceless/planner_content.py`
   fills them from `faceless/moneymath.py` (the math the videos quote). Placeholders accept numbers and `+ - * / ( )` only. Hand-typed numbers are allowed only when
   they are definitions or setups ("a $4,000 raise", "100 outreaches a day"), never results.
2. **Education, never advice.** No "buy this", no promised returns, hypothetical rates are called hypothetical. `planner check` fails on advice phrases.
3. **Facts about real people only from `channel/research/` briefs.** The lessons name concepts and book titles, not people. (Rat-race frameworks are taught in our own words, without names.)
4. Country-specific rules (credit scores, retirement accounts, tax) say they are country-specific and send the reader to an official source.
5. Voice: short sentences, second person, concrete over abstract, no guru words, no filler openers (`channel/brand.md`).
6. AI disclosure on the welcome page, the last page and in every listing: "Designed by Quiet Money with AI assistance."

Source text lives in `content/q1.txt` to `q4.txt` (week headers, then `L N D M A` day lines and `S R` prompts). Edit the text, run `planner build`.

## The picture style lock
Black-and-gold, quiet-luxury coin aesthetic that matches the logo (`channel/brand-kit/avatar.png`, `brand.coin()`):
- Ground near-black `#0E0E10` with one warm light from the upper left; vignette; no gradients to white.
- Gold `#FFD23F`, deep gold `#C9A227`, cream `#F5F1E6` for tiny highlights only. Soft gold bloom, never clipped flat.
- Coins are the hero object: gold face, deep-gold rim ring, a sheen top-left, a visible edge when stacked. The Q coin is the logo, used sparingly.
- 2.2:1 frame (1320 x 600 px), no text in the picture (the page adds the words), no real people, no faces.
- Motifs follow the lesson: stack, coin, curve, bars, ring, scale, rain, steps, gauge, tree, road, shield, grid (progress dots), pair. See `faceless/planner_art.py`.
- Quinton, the channel's virtual host, is not in the pictures. His character lock stays in `channel/host/BIBLE.md`.

### If the owner wants AI-made pictures for the missing days
The drawn pictures are free and identical on every run, so they are the default. To swap in AI-generated stills for specific days, generate them in this
locked language and drop them in as `assets/planner/source/day-NNN.jpg`; the build uses them automatically. Prompt (untested here, price it first with
`python -m faceless muapi estimate`; the studio's spend caps apply):
`quiet luxury still life, stacked antique gold coins and a single larger coin with a bold black letter Q, near-black background, one warm key light from the upper left, soft gold glow, shallow depth of field, cinematic, minimal, wide 2.2:1 frame, no text, no people`

## Where the pictures come from (priority order)
1. `assets/planner/clean/day-NNN.*` (the owner's picture with the handle removed)
2. `assets/planner/source/day-NNN.*` (the owner's picture as given)
3. drawn in code (`planner_art.render_motif`), seeded by the day number
