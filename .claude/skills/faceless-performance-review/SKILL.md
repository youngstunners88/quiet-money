---
name: faceless-performance-review
description: Weekly and after-batch performance review for Quiet Money: snapshot the public numbers from the phone, compare against the last review, find what to change in titles, hooks, pillars, volume and editing, and write the adjustments down. Use when asked how the channel is doing, for an analysis, a performance review, "what should we change", reach, retention, or before planning the next batch.
metadata:
  author: quiet-money
  version: 1.0.0
  source: first review 2026-10-29 (analytics/performance-2026-10-29.md)
---

# Performance review

## Inputs (collect in this order)
1. `python tools/perf-snapshot.py` (phone connected): every public Short with its views into `analytics/snapshots/youtube-<date>.json`.
2. YouTube app -> You -> Analytics (all time, last 7 days, subscribers, likes, comments, shares). The numbers sit in a screenshot; the UI tree does not expose them.
3. TikTok profile grid views and the Inbox -> System notifications (removals, warnings): screenshot, then type the numbers into the review file.
4. `analytics/metrics.jsonl` (pillar-tagged rows), `python -m faceless ypp`, `python -m faceless cash` (spend and revenue).
5. Retention (average view duration, % viewed, CTR) from YouTube Studio's per-video CSV when the owner exports it. Without it, say so: titles and hooks can be judged, retention cannot.
Do not use the Windsor TikTok connector for this channel: it is wired to the owner's other TikTok account (@youngstunnersss), not @quiet.money28.

## Method
- Report mean AND median (a single 229-view Short moves the mean). Compare the newest 25 Shorts with the older ones.
- Split by title features: has a digit, has a $ or % figure, abstract words (Hidden, Silent, Brain, Direction), named person or brand, pillar. Report n for every group and call anything under n = 30 a signal.
- Read the shape of the last-7-days chart before crediting a change: a jump that follows a volume change is volume, not quality.
- Check the funnel end to end: views -> comments/shares -> subscribers -> hub visits -> checklist signups -> sales. Say where the data stops.
- Check compliance first: any TikTok removal or warning outranks a reach problem (`faceless-tiktok-policy`).

## Output
- `analytics/performance-<date>.md` with the scoreboard, the signals, the adjustments (marked done or owner decision) and dated checkpoints with pass thresholds.
- Apply what is safe at once: `channel/brand.md` (title and hook rules), topic backlog rewrites, skill and lint updates. Anything that changes cadence, spend or the studio's rules is the owner's decision: list it, do not change it.
- Update the pillar allocation only through `faceless/analytics.py` (it keeps the 35% exploration floor).

## Review rhythm
After every batch of five: snapshot and compare the median. Sunday: full review and a new file. If the median has not improved over two weeks, change the format, not the volume.

## Targets (from `analytics/CONTEXT.md`)
3-second hold above 70%, average % viewed above 60%, rewatch above 15%, follows per 1k views above 3, comments per 1k views above 2. Current: comments 0.6 per 1k, subscribers 7.
