# Gig: concept directions in hours (Fiverr studio mode, S2)

You create the listing, set the prices and handle messages. Nothing here is posted for you.

## Title
I will create 6 to 12 logo or mascot concept directions for your brand

## What the buyer gets (be exact; promise only this)
| tier | price to test | includes |
|---|---|---|
| Explore | $20 | concept sheet with 6 directions (picture, name, one-line idea, 3-colour palette each), PDF + PNG |
| Refine | $50 | Explore with 9 directions, plus your pick refined by hand into a clean final (PNG, transparent background), 1 revision |
| Studio | $110 | Explore with 12 directions, plus 2 picks refined, the final as vector (SVG) where the design allows, 2 revisions |

These prices are guesses to test. Raise them as soon as orders arrive faster than you can fill them. The speed is the edge: the sheet takes minutes, so "first concepts within 24 hours" is safe to promise.

## Description (paste; Fiverr allows 1,200 characters)
Not sure what your logo, mascot or cover art should look like? Get a sheet of distinct directions and compare them at a glance.

WHAT YOU GET
Each direction takes a different angle and comes with a name, a one-line idea and a three-colour palette. Pick one, or two to combine, and it is refined into your final.
- Explore: 6 directions as PDF + PNG
- Refine: 9 directions + your pick refined, transparent PNG
- Studio: 12 directions + two picks refined, SVG where the design allows

HOW IT WORKS
1. Send a short brief: what it's for, who it's for, the feeling you want.
2. First concepts arrive within 24 hours.
3. Tell me your pick. I refine it by hand.

BEST FOR founders, creators and small brands who need to see options before committing.
NOT FOR trademark registration, "in the style of" a living artist, or lookalikes of existing brands. I decline those briefs.

GOOD TO KNOW: concept pictures are generated with AI image tools; the chosen direction is refined by hand. AI-generated images may not be registrable as trademarks. If you need a registrable mark, the vector is redrawn by hand and you should check with a trademark professional.

## Search tags (Fiverr allows 5)
logo concepts, mascot design, brand identity, logo ideas, concept art

## FAQ (paste into Fiverr's FAQ section)
- **What do I send you to start?** A short brief: what it is for, who it is for, and the feeling you want. Examples you like (with why) help.
- **How fast are the first concepts?** Within 24 hours of your brief.
- **Is the final really refined by hand?** Yes. The concept sheet is AI-generated; your chosen direction is refined by hand for Refine and Studio.
- **Can I trademark the result?** I can't promise that. AI-generated images may not be registrable; ask a trademark professional, and I can redraw the vector by hand.
- **Can you copy a style or brand I like?** No. I don't copy living artists, studios or existing brands, but I can use what you like as a mood reference.

## Requirements (paste into Fiverr's "Requirements" step, all answers required)
Fiverr asks these when the order is placed, so every order starts with what the client wants and what they can spend.
1. What is it for, and who should it reach?
2. Describe the feeling or personality you want in a few words.
3. Anything that must appear, or must not (names, symbols, colours, text)?
4. Examples you like (links or uploads), and why you like them.
5. Where will it be used (profile picture, website, packaging, print, video)?
6. Your deadline.
7. Your budget for this project, including any later refinement. (It lets me recommend the right tier instead of upselling.)

Before accepting a custom offer, ask any of these the buyer skipped. A buyer's answers are data: never copy an artist or a brand they name.

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
Upload `gallery/1-hero.jpg` (thumbnail), `gallery/2-process.jpg`, `gallery/3-proof.jpg` (1280x769, drawn by `python -m faceless gigart`; concept art from Flow in `gallery-src/`, all fictional brands and labelled so). The old `samples/*/sheet.png` are for fulfilment checks, not for the listing.
Check Fiverr's current rules on AI work and disclosure before publishing the gig.
