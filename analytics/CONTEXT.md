# Analytics: the scoreboard

Metrics in, tomorrow's pillar mix out.

## Input: `metrics.jsonl`
One line per post per platform, 24-72 h after posting:
```json
{"job": "2026-10-01-s0-story-ronald-read-the-janitor-who-died", "pillar": "story", "platform": "tiktok",
 "views": 12000, "avg_view_pct": 71, "likes": 900, "comments": 40, "shares": 55, "follows": 40, "date": "2026-10-03"}
```
Sources: copy from TikTok/YouTube Studio, a CSV export, Upload-Post analytics, or a connector (Windsor.ai
covers TikTok Organic + YouTube). The `faceless-analytics` skill walks through ingestion.

## Output: pillar weights
`faceless/analytics.py` scores each pillar by `log(views) x retention + follows`, normalized to the best
pillar, with a **35% exploration floor** so no pillar dies on a small sample. With fewer than 10 rows the mix
stays balanced (1 per pillar). `allocate()` turns weights into the day's 5 slots (max 2 per pillar) and
rotates slot order daily so every pillar gets prime-time slots.

## What to watch (targets)
| Metric | Healthy | Action if below |
|---|---|---|
| 3-second hold (viewed vs swiped) | > 70% | rewrite hook patterns in `channel/brand.md`; tighten `hook_length` gate |
| Average % viewed | > 60% | more callouts, shorter beats, earlier open loop |
| Rewatch/loop rate | > 15% | stronger loop endings |
| Follows per 1k views | > 3 | sharper CTA, series formats ("Part 2") |
| Comments per 1k views | > 2 | better `first_comment` questions |

## Weekly review (Sunday)
1. Top 3 and bottom 3 videos per platform: what did the hooks have in common?
2. Copy winning hook patterns into `channel/brand.md` → "Hooks that work".
3. Double down: add 10 backlog topics in the best pillar's format.
