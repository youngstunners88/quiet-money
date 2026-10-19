# Decision: one product or a bundle, Daily Planner and Debt Payoff Planner

**Date:** 2026-10-12. **Decision: A. Two separate products. No new Daily + Debt bundle yet.** The Money Reset Kit stays the only bundle.
**Approved by:** Claude Code, under the owner's advance permission given in the same task ("get to a conclusion and then approve the best result"). The approval covers the
**product structure only**. It does not set a price, publish, list or post anything: the owner still approves prices, copy and accounts (CLAUDE.md rule 9).

## Method (re-run on the right models, 2026-10-12)
The first pass used `microsoft/phi-4`, a chat model: **that was the wrong tool.** The owner meant **`microsoft/microsoft-decision-1`**, one of 19 *decision models* on OpenRouter's Decisions API
(`POST /api/alpha/decisions`): it reads the state and returns a calibrated probability for each answer option instead of generating text. The same request
(`2026-10-12-daily-debt-bundle.request.json`: the facts as `state`, one `choice` question and three `noul` yes/no questions) was put to four decision models; raw answers in
`state/panels/2026-10-12-daily-debt-bundle-decisions.json`. Cost under $0.0004. (The first pass, Phi-4 and Claude Haiku 5.5 as chat models, is kept at `state/panels/2026-10-12-daily-debt-bundle.json`: Phi-4 voted C three times with generic reasons; Haiku voted A, C and failed once, and was the only one to notice the overlap in words.)

## What the decision models said
| Model | Pick (probability) | Overlap with the Kit | Has data | Third listing justified |
|---|---|---|---|---|
| Microsoft-Decision-1 | C (0.86), A 0.13 | 1.00 | 0.00 | **0.07** |
| Jev 1.13 (typesafe) | **A (0.61)**, C 0.36 | 0.95 | 0.04 | 0.23 |
| Solar Decide Flash (upstage) | C (0.97) | 0.95 | 0.04 | **0.13** |
| GPT-6 Luna Decisions (openai) | **A (0.91)**, C 0.08 | 1.00 | 0.00 | 0.22 |

## Adjudication
1. **The sub-questions are unanimous and match the facts:** every model says a new bundle would overlap the Kit (0.95 to 1.00), the shop has no data (at most 0.04), and a third listing is not justified (0.07 to 0.23).
2. **The headline pick splits two and two, and the two that chose C contradict themselves:** option C *is* a third listing, yet Microsoft-Decision-1 rates "third listing justified" at 0.07 and Solar at 0.13. Coherence gating (a pick must agree with the model's own answers about its consequences) leaves A (Jev 0.61, GPT-6 Luna 0.91).
3. A close call goes to the reversible, cheaper option: A can become C later with one new listing; C cannot undo its Etsy fees or the cannibalisation of the Kit.

## Actions this decision sets
- List the Daily Planner and the Debt Payoff Planner as separate products, Gumroad first. The Kit stays as it is.
- Cross-sell in the after-purchase message of the Daily Planner (done in `channel/shop/catalog.json`: weeks 14 to 16 point at the matching spreadsheet, no URL until the owner has a live one, rule 13). Add the live link to the message after the Debt planner is public.
- Measure first: view-to-sale at $17 and one lower step (about $14), at least 20 views each, before touching structure.
- Change to C (a "Daily + Debt" bundle priced below the sum, both parts already listed) only if buyers of one repeatedly buy or ask for the other, or if a price test shows a bundle price converts clearly better. Re-run the panel with the new facts then.
