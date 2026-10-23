# Gig: concept directions in hours (Fiverr studio mode, S2)

You create the listing, set the prices and handle messages. Nothing here is posted for you.

## Title
I will create 6 to 12 distinct logo, mascot or illustration concept directions for your brand

## What the buyer gets (be exact; promise only this)
| tier | price to test | includes |
|---|---|---|
| Explore | $20 | concept sheet with 6 directions (picture, name, one-line idea, 3-colour palette each), PDF + PNG |
| Refine | $50 | Explore with 9 directions, plus your pick refined by hand into a clean final (PNG, transparent background), 1 revision |
| Studio | $110 | Explore with 12 directions, plus 2 picks refined, the final as vector (SVG) where the design allows, 2 revisions |

These prices are guesses to test. Raise them as soon as orders arrive faster than you can fill them. The speed is the edge: the sheet takes minutes, so "first concepts within 24 hours" is safe to promise.

## Description (paste)
Not sure what your logo, mascot or cover art should look like? Send a short brief (what it is for, who it is for, the feeling you
want) and get a sheet of distinct directions, each taking a different angle: metaphor, shape language, era, mood and colour. Every
direction has a name, a one-line idea and a three-colour palette, so you can compare them in one glance. Pick one (or two to combine)
and it is refined into the final.

AI disclosure: the concept pictures are generated with AI image tools, and the chosen direction is refined by hand. AI-generated
images may not be registrable as trademarks; if you need a registrable mark, the refined vector is redrawn by hand and you should
check with a trademark professional. Concepts are original: no copying of artists, studios or existing brands.

## What not to promise
- No trademark registration or legal clearance.
- No "in the style of" a living artist, and no lookalike of an existing brand. The engine refuses those briefs.
- No unlimited revisions.
- No sales or growth results.

## Fulfilment (agent and owner, per order)
1. `python -m faceless concepts "<the buyer's brief>" --kind logo|character|art --n 6|9|12 --client "<first name>"` (add `--hq` for Refine and Studio: Muapi pictures first, about $0.05 a sheet). This takes about 2-5 minutes. Pictures are made free first (Pollinations), then by Muapi under its daily cap. It never uses the Cloudflare budget that the daily videos need.
2. Look at `sheet.png`. If a direction is weak, run it again; the brief and the seed are the same, so change `--n` or reword the brief.
3. Send `sheet.pdf` with the text of `DELIVERY.md`. Orders are written under `channel/services/studio/orders/` and are gitignored, so a client brief never reaches the public repo.
4. Refining the pick is your hand work, and it is what the higher tiers pay for.

## Gallery
Use `samples/*/sheet.png` (made-up brands: Fern & Fold, Orbit Kid) and label them "sample". Check Fiverr's current rules on
AI-assisted work and disclosure before publishing the gig.
