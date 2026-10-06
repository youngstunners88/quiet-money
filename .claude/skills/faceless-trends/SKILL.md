---
name: faceless-trends
description: Research trending and evergreen money topics for the Quiet Money channel and add vetted ideas to the script backlog. Use when the backlog runs low, before a weekly planning session, or when asked to find viral money topics.
---

# Trend research → backlog

## Sources (use what is connected)
- Web search / Exa / Firecrawl / TinyFish: "most viewed personal finance shorts this week", money news,
  Reddit r/personalfinance and r/povertyfinance top posts, Google Trends (money, budget, debt, salary).
- `agent-reach` (see `skills/agent-reach/SKILL.md`) for platform-native searches (YouTube, Reddit, X).
- Our own winners: top rows in `analytics/metrics.jsonl`.

## Filter (a topic must pass all)
1. Fits a pillar format (`channel/brand.md`).
2. Has one hard number or a documented story; facts verifiable in 2+ sources.
3. Evergreen or explainable without today's news (news pegs are fine if the lesson is evergreen).
4. Not a duplicate: `python -c "from faceless.pipeline.ideate import *; print(max(similarity('<topic>', h) for h in history_texts()+[r['topic'] for r in load_backlog()]))"` < 0.55.
5. Not advice to buy a specific asset.
6. Not already covered in the body of a past script, even under a different title:
   `python -m faceless memory "<topic words>"` (add `--pillar x`, `--status held`; `--rebuild` to re-index). The same search
   answers "why were videos held for X?" (`memory --status held word_count`) and "how did our best scripts open?".

## Add
Append lines to `script-lab/ideas/backlog.jsonl`:
`{"pillar": "math", "topic": "...", "angle": "...", "hook": "..."}`
Keep at least 10 unused topics per pillar.
