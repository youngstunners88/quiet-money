---
name: faceless-studio-gig
description: Fulfil Quiet Money's Fiverr studio-mode gig. Turn a client brief into a labelled sheet of 6 to 12 distinct logo, mascot or illustration concept directions with a delivery note, refuse briefs that copy an artist or a brand, and rebuild the gig gallery. Use when the owner forwards a Fiverr order, a client brief, or says concept sheet, logo concepts, mascot concepts, studio mode, or gig samples.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/concepts.py
---

# Studio mode (S2)

The gig copy, tiers and what not to promise are in `channel/services/studio/GIG.md`. The owner lists the gig and talks to clients;
the studio never messages anyone.

## Fulfil an order
```bash
python -m faceless concepts "<the buyer's brief, as written>" --kind logo|character|art --n 6|9|12 --client "<first name>" [--hq]
```
- `--n` follows the tier: Explore 6, Refine 9, Studio 12. `--hq` for Refine and Studio puts Muapi pictures first (about half a cent
  each, under its daily cap); otherwise Pollinations draws free. Cloudflare is never used: its free budget belongs to the daily videos.
- Output in `channel/services/studio/orders/<date>-<client>/` (gitignored: a client brief never reaches the public repo): `sheet.png`,
  `sheet.pdf`, the pictures, `directions.json`, `DELIVERY.md` (the message to paste with the PDF).
- Look at `sheet.png` before it goes out. A weak direction: run again with a reworded brief. Send the owner the PDF and the note.

## Refusals (by design)
Briefs with "in the style of", "like the logo of", copies, knock-offs or dupes are refused, and any direction that names an artist or
a brand is dropped. Say why to the owner; offer an original direction instead. AI-generated images may not be registrable as
trademarks: the sheet says so, and the refined final is the owner's hand work.

## Gallery
`python -m faceless concepts --samples` rebuilds the two made-up samples (Fern & Fold, Orbit Kid). Only the sheets, directions and
notes are committed.
