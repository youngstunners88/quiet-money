---
name: faceless-cash
description: Run Quiet Money's money desk. Read every revenue rail's real state (the Web3 video service, Gumroad products, the two Fiverr gigs, collaborations), do every part the agent may do, and hand the owner a short ranked list of paste-ready steps that bring the first dollars soonest. Use when the owner says money, cash, revenue, sales, "we need money now", first sale, monetize, or asks what to do today to make money; also at the end of any daily routine that touches sales.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/cash.py
---

# The money desk

`python -m faceless cash` reads the engine's own state and writes `channel/empire/CASH.md`. It shows every rail, what the agent
already did, and the owner's next 30 minutes. HQ shows the same top three steps. It reads only.

## The order money comes in (judgment until a rail has sold once)
1. **Web3 video and KOL service.** Highest ticket. The 07:47 UTC hunt queues three gated drafts a day (`service-outbound`). The
   owner sends them; a reply is a project. Prices are set (2026-10-23): $65 for a 30-second video, $120 for a 75-second one; replies quote them from `templates/quote.md`.
2. **Gumroad products.** Built and verified; only the price yes is missing. One owner line ("list X at $N") is enough. Then follow
   `faceless-ship`: write `[shop.approved."<id>"]` quoting the owner's message, `shop publish`, add the live URL to `[offer] shop_urls`.
   From that moment the offer layer points the matching series at it (`faceless-offer`).
3. **Fiverr gigs** (brand kit, concept sheets). Marketplaces already have buyers. The owner pastes `GIG.md` and the samples.
4. **Collaborations** feed the audience every rail sells to; they are not a sale.

## What the agent does without asking (rule 16)
- Rebuild and verify products and listing packs (`python -m faceless products`, `listing build all`, `listing check`) so a yes ships in minutes.
- Create **unpublished** Gumroad drafts (`shop draft`); drafts are free and reversible.
- Keep the outbound hunt, the collaboration notes and the offer layer running, and relay the drafts in its reply (they are gitignored).
- Fulfil an order the owner forwards: `concepts` for a concept-sheet gig, `brandkit` for a brand-kit gig.

## What only the owner does (rule 9)
Setting or changing any price, going live, sending any message to a person, creating marketplace accounts, payouts. Never write a
`[shop.approved]` entry without the owner's own message naming the price; quote it in the commit.

## Reporting
Lead with the money line (sales, net), then the next 30 minutes exactly as `cash` prints them. If nothing sold and nothing changed,
say so in one line; do not pad. A rail that is "blocked" names the one step that unblocks it.
