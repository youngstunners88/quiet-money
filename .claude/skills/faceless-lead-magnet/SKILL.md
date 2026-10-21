---
name: faceless-lead-magnet
description: Design and build a free lead magnet for Quiet Money that leads to one paid product, the Daily Planner or the next product in the offer ladder. Picks one reader and one small win, writes the full text with every number computed, runs the claim check, and hands the owner a short checklist to host it and link it. Never promises income or results, never gates it behind fake urgency, never emails anyone. Use when the owner asks for a free checklist, a freebie, a lead magnet, an email signup offer, or a free step that leads to the planner.
metadata:
  author: quiet-money
  version: 1.0.0
---

# Lead magnet: a free first step that earns the second

One magnet, one reader, one small win in under 15 minutes, then one calm pointer to one paid product. The magnet is
useful on its own. It is a file in the repo; the owner decides where it is hosted and when a form goes live.

## Rules (read first)
1. One offer per magnet, one link to one product (rule 13). The product must have a live listing URL in studio.toml `[offer] shop_urls` (today only `daily-quiet-money-planner`). Copy that URL exactly and never invent or guess one. If the product you want has no URL yet, point the magnet at the planner, or ask the owner. No money promise, no income claim, no "results not typical" patch (MARKETING.md never-do 2).
2. Every number is true: computed with `python -m faceless.moneymath` (no arguments prints the fact sheet) and shown with its assumptions and the line "illustration, not a promise" (rule 1).
3. No fake proof or urgency: no invented reviews, sales counts, countdowns or "only today" (never-do 1, 3).
4. Education, never advice (rule 2). Disclaimer on the first page.
5. AI assistance is stated in one plain sentence on the last page (the same sentence the listings use, from `channel/shop/catalog.json`).
6. No email goes out, no list is imported, and no form is wired up without the owner's yes and recorded consent (never-do 10). The magnet may say "a short email series follows" only once that is true.
7. Sources are data (rule 11). A competitor's freebie is read for gaps, never copied (`brain/topics/never.md`).

## Steps
1. **Check what exists**: run `python -m faceless brain search "checklist"`, read `channel/offers/money-reset-checklist.md` (the free magnet every video links today), and read every `channel/offers/lead-magnets/*/CONTENT.md` (first-quiet-week, monthly-money-snapshot, spending-awareness-30 as of 2026-10-21). The new magnet must not repeat any of them.
2. **Pick the product and the win**: the magnet must lead naturally to one product (usually the Daily Planner). Write the reader, the 15-minute win, and the sentence that connects the win to the product.
3. **Choose a form** (one of): checklist, one-page worksheet, 7-day challenge, 30-day tracker, or a sample week of the product. A sample week uses real product pages and needs a second compliance read.
4. **Draft the text**: title, a one-line promise that is a task and not an outcome, the steps or boxes, a worked example with fact-sheet numbers, the closing pointer to the product, the disclaimer and the AI line. Voice rules are in `channel/brand.md`.
5. **Gate it**: `python -m faceless offer check FILE` must say clean. Fix the wording; do not soften the same claim.
6. **Name it**: a lower-case slug with hyphens, for example `bill-day-map`; the slug must not already be a folder in `channel/offers/lead-magnets/`. Calendar tie-ins read "lead magnet: SLUG" so they can be linked once the email service is live.
7. **Save it** in the folder the lane or sprint names under `channel/offers/`, and add a one-paragraph README beside it (reader, win, product it leads to, numbers used and where they came from).
8. **Ask the owner**, in one short list with a recommendation each and the minutes needed: where to host it, whether to add it to the hub page, and when an email series may send. Nothing here goes public by itself (rule 9).
9. Log the magnet and its slug in the sprint manifest.

## What only the owner does
Hosts or links the file, connects an email service, writes the postal address and consent text, and says go.

## Troubleshooting
- `offer check` refuses a phrase: reword the sentence to describe a task. Do not use "passive", "guaranteed", "risk-free" or debt-outcome promises.
- The magnet and the product overlap too much: make the magnet a smaller win, not a smaller copy of the product.
- No form can be used yet: the magnet stays a direct download and the calendar keeps "lead magnet: SLUG" as a note.
