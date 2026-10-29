# Performance review, 2026-10-29

Sources: YouTube app analytics (channel, all time and last 7 days), a scrape of every public Short (`analytics/snapshots/youtube-2026-10-29.json`, 68 Shorts, `tools/perf-snapshot.py`),
`analytics/metrics.jsonl` (32 rows, pillar-tagged), the TikTok profile grid and notices on the phone, `faceless ypp`. Not available: retention (average view duration, % viewed),
traffic sources, hub-link clicks (no PostHog key), TikTok analytics API for @quiet.money28 (the Windsor connector is wired to the owner's other TikTok account and was not used).
Everything below with a small sample is marked as a signal, not a fact.

## Scoreboard
| | Now | Needed for money from the platforms |
|---|---|---|
| YouTube subscribers | 7 | 500 (expanded YPP) or 1,000 (ad sharing) |
| YouTube views, all time / last 7 days | 1,683 (1.7K) / 850 | Shorts: 3M views in 90 days (expanded) or 10M (ad sharing) |
| Likes / comments / shares, all time | 33 / 1 / 6 | |
| Shorts live | 68, mean 24.8 views, median 15.5, best 229, **16 with 5 views or fewer** | |
| TikTok @quiet.money28 | 1 follower, 12 likes, 0 to 223 views per video, 1 video removed (warning) | |
| Revenue | $0 | |

The last-7-days curve is flat (about 30 a day) until 10-27, then about 250 a day: the jump follows the move to five Shorts a day plus the hero Short, not a change in per-video reach. Per-video reach did not move (newest 25 Shorts: median 10; older 43: median 16).
At this rate the platform-payout route is out of reach for months (0.0% of the Shorts-views threshold). The first dollar has to come from the products and services (Fiverr gigs, Web3 outreach, the checklist funnel), which the platforms only feed.

## What the numbers say (signals, n = 68)
1. **Concrete beats abstract.** Titles with a digit average 38.5 views against 18.2 without (22 vs 46 videos). Titles built from vague nouns (Hidden, Silent, Brain, Direction) have a median of **1.5 views** against 16 for the rest (8 vs 60). Every zero-view Short is abstract: "The Price Tag Hidden Behind Your Monthly Life", "The Hidden Direction of Your Cash Flow", "Why Tired Brains Buy Stuff at Night", "The Silent Checking Account Trap".
2. **A named person or object with a dollar outcome is the best format we have.** Top five: George Foreman $138M (229), The Billionaire Who Drove a 1993 Volvo (176), The Mortgage Payoff Trap (104), How to Kill Hidden PayPal Billing Authorizations (64), Dollar-Cost Averaging Costs You Money (62). Pillar averages in `metrics.jsonl`: story 46.7, escape 25.4, myth 24.5, math 17.3, psychology 16.6, playbook 7.5.
3. **Nobody reacts.** 1 comment and 6 shares on 1.7K views, 7 subscribers. The hooks earn a glance, the endings and CTAs earn nothing. The first-comment question is not doing its job.
4. **Long audio is not a reach tool yet.** The three songs got 1 to 4 views each; the full-length Breathe film is the only long piece the owner called "EPIC" and it is not live (see the note to the owner).
5. **Volume is not the lever.** Five a day produced the same per-video views as fewer. More of the same title style is more zeros.
6. **Compliance risk is now a cost.** One TikTok removal and a first warning (2026-10-27 hero); the next violation can restrict the account. Skill `faceless-tiktok-policy` and the `ttpolicy` lint now guard captions.

## Adjustments
Done now: the title rule, the TikTok lint, the performance skill and snapshot tool. Owner decisions are marked (not changed).
Quality
- Title rule (added to `channel/brand.md`): every title carries a **number or a named thing** (person, brand, product) and a consequence. Abstract nouns are banned from titles. Existing zero-view topics are rewritten, not re-posted as they were.
- Editing: apply `faceless-capcut-mastery` to the daily Shorts, not only the hero: no hold over 6 s, a sound on every cut, one global grade. Audio is checked against -14 LUFS before posting (the owner flagged audio twice).
- Hook proof: the first 1.5 s must show the number or the name. The gauntlet gets this as a check when retention data arrives.

Reach
- Allocation: story and escape get the prime slots until a pillar beats them on at least 10 posts; psychology and math keep the 35% exploration floor but only with concrete titles.
- (Owner decision, not changed) Cut to **three** stronger Shorts a day plus one hero-style piece a week; the 10-27 hero got 10 views on YouTube, so a hero must also carry a concrete hook (it was beautiful but abstract). The freed capacity goes to rewriting the zero-view topics.
- Engagement: end every Short on a forced-choice question ("$10,000 now or 20% of the product?"), pin the question, and answer every comment quickly.
- Series: "Part 2" and recurring named formats so a viewer has a reason to follow (seven subscribers means nothing pulls people back).
- TikTok: Content disclosure toggle on for promo captions; no more "free money" or graphic wording; five complete hashtags.

Measurement (so the next review is sharper)
- Export YouTube Studio's per-video CSV (views, average view duration, % viewed, impressions CTR) weekly into `analytics/metrics.jsonl`; without retention the hook cannot be tuned.
- Give the site a PostHog key (or any click counter) to see hub-page visits per platform; right now the funnel is blind after the view.
- Re-run `tools/perf-snapshot.py` every Sunday and compare against this file (skill `faceless-performance-review`).

## Review checkpoints
| Date | Check | Pass |
|---|---|---|
| 2026-11-05 | median views of Shorts posted after 10-30 vs 15.5 | 25 or more |
| 2026-11-05 | zero-view Shorts (5 or fewer) among the new ones | under 10% (now 24%) |
| 2026-11-12 | comments per 1k views | 2 or more (now 0.6) |
| 2026-11-12 | subscribers | 25 or more (now 7) |
