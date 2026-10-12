# Decision: one product or a bundle, Daily Planner and Debt Payoff Planner

**Date:** 2026-10-12. **Decision: A. Two separate products. No new Daily + Debt bundle yet.** The Money Reset Kit stays the only bundle.
**Approved by:** Claude Code, under the owner's advance permission given in the same task ("get to a conclusion and then approve the best result"). The approval covers the
**product structure only**. It does not set a price, publish, list or post anything: the owner still approves prices, copy and accounts (CLAUDE.md rule 9).

## Method
One brief (`2026-10-12-daily-debt-bundle.brief.txt`, facts from the studio's own files plus a Haiku market brief) put to two models through OpenRouter, three runs each, temperature 0.4:
`python -m faceless panel <brief> --models microsoft/phi-4,anthropic/claude-haiku-5.5 --runs 3`. Raw answers: `state/panels/2026-10-12-daily-debt-bundle.json`. Cost under $0.003.
(`microsoft/phi-4` is the only current Microsoft model on OpenRouter besides the older WizardLM-2.)

## What the models said
| Model | Votes | Confidence | Noticed |
|---|---|---|---|
| Microsoft Phi-4 | C, C, C | 0.80 to 0.85 | generic: flexibility, targeted marketing, Etsy fees, cannibalisation in the abstract |
| Claude Haiku 5.5 | A, C, (one run out of tokens) | 0.55 to 0.60 | **the Debt Payoff Planner is already inside the Money Reset Kit**, so a Daily + Debt bundle overlaps it; a shop with no sales or reviews has nothing to learn from a third listing; the discount rule means both parts must be listed apart first; Etsy listing fees |

## Adjudication
1. Agreement is not correctness. Phi-4 was consistent but did not use the fact that matters most (the overlap with the Kit); Haiku did, and its disagreement with itself (A vs C at about 0.55) says the call is close.
2. When a call is close and one option is reversible and cheaper, take that one: A can become C later with one new listing; C cannot undo its Etsy fees or the cannibalisation of the Kit.
3. The facts agree with A: new shop, no data, a price 5 to 17 times the cheap Etsy bundles (so price is the bigger test than structure), and the discount can only be advertised once the parts are live.

## Actions this decision sets
- List the Daily Planner and the Debt Payoff Planner as separate products, Gumroad first. The Kit stays as it is.
- Cross-sell in the after-purchase message of the Daily Planner (done in `channel/shop/catalog.json`: weeks 14 to 16 point at the matching spreadsheet, no URL until the owner has a live one, rule 13). Add the live link to the message after the Debt planner is public.
- Measure first: view-to-sale at $17 and one lower step (about $14), at least 20 views each, before touching structure.
- Change to C (a "Daily + Debt" bundle priced below the sum, both parts already listed) only if buyers of one repeatedly buy or ask for the other, or if a price test shows a bundle price converts clearly better. Re-run the panel with the new facts then.
