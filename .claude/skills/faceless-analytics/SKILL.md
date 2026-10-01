---
name: faceless-analytics
description: Ingest Quiet Money post metrics (views, retention, follows) from TikTok, YouTube, and Instagram, update analytics/metrics.jsonl, and run the weekly review that re-weights pillars and upgrades hook patterns. Use when asked how videos performed, for weekly reviews, or to tune what the engine makes.
---

# Analytics

## Ingest
For each posted job (`state/jobs/*.json` with status `published`), 24-72 h after posting,
append one line per platform to `analytics/metrics.jsonl`:
`{"job": "<job_id>", "pillar": "<pillar>", "platform": "tiktok", "views": 0, "avg_view_pct": 0, "likes": 0, "comments": 0, "shares": 0, "follows": 0, "date": "YYYY-MM-DD"}`

Sources, best first: a connected analytics tool (Windsor.ai has TikTok Organic + YouTube connectors),
Upload-Post analytics, a CSV export from TikTok Studio / YouTube Studio, or numbers the owner pastes in.

## Weekly review
1. `python -c "from faceless.analytics import pillar_weights; print(pillar_weights())"`: tomorrow's mix.
2. Rank videos by views x avg_view_pct. For the top 3 and bottom 3, read the scripts in `script-lab/final/`.
3. Write the winning hook patterns into `channel/brand.md` → "Hooks that work".
4. Add 10 backlog topics shaped like the winners (`faceless-trends` skill).
5. If a pillar sits at the 35% floor for 3 weeks, propose replacing its format (ask the owner).
6. Summarize: best video, worst video, what changes tomorrow.
