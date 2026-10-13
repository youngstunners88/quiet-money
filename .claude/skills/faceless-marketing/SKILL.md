---
name: faceless-marketing
description: Run Quiet Money's marketing as a director: read the funnel, measure what each video earned, check the guard rails, advance or kill the pre-registered experiments, draft the next week's work with Claude Haiku 5.5 and Jev, and give the owner at most three decisions a week. Use for "marketing", "go to market", "how are sales", "weekly brief", "what should we test", "grow sales", the weekly marketing routine, or when a sale, a platform notice or a refund changes the picture.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/marketing.py, faceless/metrics.py
---

# Marketing director

The plan is `channel/empire/MARKETING.md` (built 2026-10-13 from nine research lenses, each finding checked by two verifiers; decisions in `channel/empire/decisions/2026-10-13-marketing-strategy.md`). It is honest about its numbers: the base case is about 8 genuine Gumroad sales by Day 30, and traffic, not conversion, is the limit. Read section 8 (Autonomy design) before acting alone.

## The weekly run (Monday, after the 11:07 UTC scout)
1. `git pull --rebase origin main`; if `state/PAUSE` exists, stop and report. Never resume a pause.
2. `python -m faceless metrics --pull` (read-only): 48-hour and 7-day snapshots into `analytics/snapshots.jsonl`, scorer rows into `analytics/metrics.jsonl`.
3. If the Gumroad connection exists: `python -m faceless shop sales` (reads sales into `analytics/sales.jsonl`).
4. `python -m faceless marketing`: guards (G1 floor, G3 spend, G8 keys), funnel, measurement coverage, experiment register, owner queue. It writes `analytics/brief-<day>.md`.
5. Work the brief:
   - **G1 warn:** fix it (`post-backlog --apply`, skill `faceless-unblock`); rule 15 is the standing order.
   - **A runnable experiment:** `python -m faceless marketing start X1`, run it exactly as registered, and at its pre-registered sample or 28 days `marketing result X1 won|killed "numbers"`. A winner counts only after it replicates in a different week. Never promote on a small sample.
   - **Drafts** (hooks, listing openings, email text, creator notes, the weekly summary): Haiku 5.5 writes (`anthropic/claude-haiku-5.5` through OpenRouter, a few thousandths of a cent a call). A different model or the phrase gate (`offer.violations`) reviews; the writer is never the judge. Jev (`typesafe/jev-1.13`) answers typed questions only and stays in shadow until a question has 50 labelled rows.
   - **A choice between options:** `faceless-panel` (decision models plus Haiku). Record it in `channel/empire/decisions/`. A close call goes to the reversible, cheaper option.
   - **Data:** `faceless-monid` (priced first, $1 a day) and TokConnect; free tools first.
6. Show the owner at most three open items from the queue (`python -m faceless marketing done U01` closes one). Seven days of silence is the status quo, never approval.
7. Commit `analytics/` and `channel/empire/experiments.json`, `owner_queue.json`, push to main (state and reports only, rule 12).

## What the agent may and may not do
- **Alone:** produce and schedule the 5 Shorts, read back, measure, report, draft internally, run the phrase gate, read policy pages, call Haiku/Jev/Monid under their caps.
- **Never without the owner's yes (rule 9):** a price, a discount code, a listing, a new account, a post outside the engine's YouTube mode, a message to any person (creator pitches, DMs, support replies, buyer emails), a long-form video, an affiliate term, a cap raise, an AI-generated person on an ad, a paid ad. The one recorded exemption would be the opted-in email sequence, only after the owner decides D9.
- **Never:** income or return claims, invented reviews or testimonials, urgency that is not real, buying followers, comment-to-DM automation, a number without a source or an "assumed" tag.

## Metric order (so the system does not chase the wrong number)
Engaged views, then hub clicks, then confirmed opt-ins, then sales. Refunds, unsubscribes, disputes and platform notices are guard rails. The existing pillar score optimises attention only; it is not a sales signal.

## Troubleshooting
- **Every experiment says blocked:** correct on Day 0. The planner needs a payout method before it can be published; then its live URL goes in `[offer] shop_urls`.
- **`metrics --pull` finds no public videos:** scheduled videos are private until their slot; snapshots start at 48 hours after the post time.
- **A guard says degraded (G8):** a key is missing in this environment. Say so in the brief; write no error rows; do not paste a key anywhere.
