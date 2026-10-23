---
name: faceless-client-desk
description: Draft the owner's reply to a client, on Fiverr (concept-sheet and brand-kit gigs) or for the Web3 video service. Works out what the client wants and their budget before any quote, asks only the discovery questions still open, quotes only the owner's prices, never promises results, and never takes a Fiverr client off Fiverr. Use when the owner pastes a client message, a Fiverr inquiry, a buyer question, a revision request, or asks how to answer a client.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/clientdesk.py
---

# The client desk

The studio cannot log in to Fiverr: Fiverr has no seller API, and its Community Standards forbid bots and unauthorised access. So the
owner pastes the client's message (or the whole thread) and gets back a reply to paste where the client wrote.

```bash
python -m faceless client reply --channel fiverr --gig studio "<the client's message>"
python -m faceless client reply --channel fiverr --gig brand-kit --file thread.txt
python -m faceless client reply --channel web3 "<a lead's reply>"
```

## What every draft does
1. **Discovery first.** It works out which points the client has not answered: what it is for, who it is for, the feeling, the
   must-haves, examples, where it will be used, the deadline, **the budget**. It asks only those, numbered. The budget is always asked
   when it is unknown.
2. **Prices only from the owner.** For a Fiverr gig these are the tier table in its `GIG.md`. For the service they come from
   `[outbound.prices]` ($65 for 30 s, $120 for 75 s). Code holds any other dollar figure, so there are no invented discounts, bundles or
   rush fees.
3. **No promises.** No views, sales, followers, rankings or trademark registration.
4. **On Fiverr, stays on Fiverr.** No email, phone, outside link, outside app or outside payment; a custom offer goes through Fiverr.
5. **Original work only.** A request to copy an artist or a brand is declined kindly, and an original direction is offered instead.

A held draft is rewritten once with the reason. If it is still held, the command prints why and exits 1. Fix it by hand before sending.

## After the client answers
- With the scope and budget clear, quote the matching tier, then fulfil the order. A concept sheet uses `faceless-studio-gig`
  (`concepts`), and a brand kit uses `brandkit`.
- Web3 service outcomes are recorded through `service-pipeline` (`outbound outcome <slug> <event>`).
- The owner sends every message. The studio never contacts a client.
