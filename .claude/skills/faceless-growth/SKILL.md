---
name: faceless-growth
description: Grow Quiet Money's reach on TikTok, YouTube Shorts, and Instagram Reels. Daily posting operations, hook iteration from retention data, comment engagement, cross-posting, series, collaborations, and the weekly growth review. Use when asked to "go viral", grow followers, or improve views, retention, or engagement.
---

# Growth playbook

Honest baseline: nobody can guarantee virality. What compounds is volume x quality x iteration: 5 strong
videos a day, measured, with the best patterns doubled. Expect weeks 1-2 to train each platform's
recommender on who the audience is; breakouts usually come from a hook pattern found in the data.

## Daily operations (automated by `faceless-daily` + CI)
- 5 videos, one per series, posted in the `[publish].slots` times (audience-local).
- Each post: AI label on, pinned first comment (a question), caption with 4-5 hashtags, and the library link in bio.
- First hour: reply to every comment (comment velocity is a ranking signal). Use the reply-with-video feature on
  TikTok for the best question (free extra post).

## What to measure (from `analytics/metrics.jsonl`)
| Signal | Target | If below |
|---|---|---|
| 3-second hold | > 70% | rewrite hook patterns (`channel/brand.md` → Hooks that work) |
| Average % viewed | > 60% | shorter beats, more callouts, earlier open loop |
| Loop/rewatch | > 15% | stronger loop endings |
| Follows / 1k views | > 3 | series framing ("Part 2 tomorrow"), sharper CTA |
| Shares / 1k views | > 5 | more "send this to someone who..." topics (relationships, family money) |

## Weekly review (Sunday)
1. Pull metrics (`faceless-analytics`; YouTube via `faceless-composio`).
2. Top 3 videos: copy their hook pattern into `brand.md`; add 10 backlog topics in that shape.
3. Bottom 3: diagnose the first 3 seconds; never repeat that hook pattern.
4. Re-weight pillars (automatic) and check the AEO probe (`faceless-aeo`).

## Multipliers
- **Series**: recurring formats ("Quiet Millionaires #3") create binge sessions and follows.
- **Duets/stitches**: stitch viral money claims and correct them with math (Money Myths pillar).
- **Cross-posting**: same pack to TikTok, Shorts, Reels; Pinterest and LinkedIn for the math cards.
- **Collabs**: tiny finance creators (< 10k) swap shoutouts more readily; offer a free custom calculator page.
- **Trending sounds**: add in-app at 5-10% volume under the voice on TikTok; never in the master file.

## Never
Buy followers or views, use engagement pods, mass-follow, or post near-duplicates: they suppress reach and can
cost monetization (YouTube inauthentic-content policy).
