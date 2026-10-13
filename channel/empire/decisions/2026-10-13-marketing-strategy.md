# Decision: marketing strategy choices, 2026-10-13

**Strategy:** `channel/empire/MARKETING.md` (built by a 36-agent research, verification, draft, judge and critic run; 9 research lenses, every finding checked by two independent verifiers).
**Panel:** Jev 1.13 (`typesafe/jev-1.13-20260917`), Microsoft-Decision-1 (`-20261009`), Solar Decide Flash (`-20261008`), GPT-6 Luna Decisions (`-20261006`) as decision models, plus Claude Haiku 5.5 as a chat model (2 runs each). Raw answers: `state/panels/2026-10-13-marketing-strategy.json`; the questions: `2026-10-13-marketing-strategy.request.json`. Total cost about $0.012.
**Approved by:** Claude Code as marketing director, under the owner's task. The approval covers the **direction of the plan only**. Every price, listing, discount, account, message to a person and post outside the YouTube mode stays the owner's yes (CLAUDE.md rule 9).

## What the models said
| Decision | Jev | MS-Decision-1 | Solar | Luna | Haiku 5.5 | Outcome |
|---|---|---|---|---|---|---|
| D1 price for the first 30 days | hold $17 (0.96) | hold (0.90) | hold (0.92) | hold (0.98) | hold | **Hold $17** (unanimous; the only owner-approved price) |
| D2 first ask for cold viewers | free checklist (1.00) | checklist (0.94) | Free Sample Week (0.73) | checklist (0.72) | checklist | **Free checklist first, planner 1 in 3** (the engine default) |
| D3 lead product | planner alone (0.56) | alone (0.77) | alone (0.46) | alone (0.87) | alone | **Daily Planner alone**; Debt planner stays a prepared asset (X11 reopens it) |
| D4 first stranger channel after the warm launch | Etsy (0.93) | Etsy (0.52) | Etsy (0.62) | creators (0.50) | Etsy | **Etsy edition first** (needs the owner's Etsy approval and the Etsy app) |
| D6 warm-launch mechanic | FIRST14 (0.99) | FIRST14 (0.98) | FIRST14 (1.00) | FIRST14 (0.97) | **no discount** | **No discount** by default (see below) |
| D7 Escape the Rat Race series | checklist only (0.96) | checklist only (0.97) | checklist only (0.91) | pause (0.61) | checklist only | **Free checklist only, one slot a day, under the written rule** |
| D10 Gumroad global affiliate opt-out | opt out 90 days (0.98) | opt out (0.98) | opt out (0.87) | opt out (0.99) | **decide at Day 30** | **Decide at Day 30**; record the setting before listing (see below) |

Not put to the panel: D5 (the email service: the facts are unverified, so the agent reads Brevo's and Kit's rules first), D8 (long-form needs the owner's yes), D9 (a recorded exemption for automated email), D11 (a legal-judgment cover question). Those are for the owner.

## Adjudication
1. **D1, D3 are unanimous and agree with the facts** (one approved price, no sales data, a debt spreadsheet that has no owner approval). Nothing to adjudicate.
2. **D2, D4, D7:** the dissent is one model each (Solar for a free sample week that needs a build and a second compliance read; Luna for creators with unmeasured acceptance at 40% commission, about $8.41 net a sale; Luna for pausing a series the written rule already constrains). Haiku's reasons use the facts that matter (the checklist exists, Gumroad email is locked until the first payout, Etsy is the only channel where strangers already search to buy, TikTok cannot carry a profile link under 1,000 followers).
3. **D6 is the one real split, four decision models against Haiku.** The decision models give probabilities and no reasons. Haiku's reasons check against the facts: a code is a price change (owner-gated, rule 9), it nets $11.39 instead of $14.01, it moves the $100 balance gate from the 8th sale to the 9th, and nothing shows a discount converts better for warm contacts. A discount can be added later; one given cannot be taken back. Rule 4 of the panel skill (a close call goes to the reversible, cheaper option) sets **no discount** as the default. FIRST14 remains an option the owner can choose.
4. **D10, the same pattern:** the affiliate program only matters once the product is Discover-listed (a $100 balance, about three weeks of review and one sale), so nothing is at stake before roughly Day 30. Opting out is reversible. Haiku's "check the setting before listing and record it, decide with data at Day 30" costs nothing; it is the default.

## Actions this sets
- Strategy file and experiment register are in the repo; the weekly brief reads them.
- Price stays $17; the planner leads alone; the free checklist is the first ask; the Rat Race series stays free-checklist-only; no discount unless the owner picks FIRST14; the affiliate decision waits for Day 30.
- Etsy is the first stranger channel when the owner approves it and creates the Etsy app (`ETSY_API_KEY`, then `python -m faceless etsy auth`).

## What would change it
Real data: X1 (cold page conversion), X2 (warm-message conversion), X11 (printable versus spreadsheet), the first Etsy visits. The monthly review replaces vendor priors with measured rates.
