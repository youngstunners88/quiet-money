---
name: faceless-measure
description: Measure what Quiet Money cannot see from Shorts views alone. The road to the YouTube Partner Program (subscribers, uploads, Shorts views in the 90-day window, estimated dates per tier) and the website funnel from cookieless PostHog analytics (pageviews, calculator use, clicks to the shop). Use when the owner asks about monetization eligibility, the Partner Program, YPP, how far from ad revenue, website traffic, whether the site sells, or when HQ's Partner Program or site numbers look stale.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/ypp.py, faceless/sitestats.py, faceless/site.py
---

# Measure the road to money

## Partner Program (R1)
`python -m faceless ypp --pull` reads the subscriber count live (one Data API call; the 07:02 UTC task runs it while the shared quota
is fresh), counts public uploads and Shorts views in the 90-day window from the engine's records, and appends `analytics/ypp.jsonl`.
`python -m faceless ypp` prints progress per tier with estimated dates from the last 14 days' pace.
- Thresholds were read from YouTube's help pages (answers 72851 and 13429240) on 2026-10-23. YouTube announced YPP updates from
  2027-02-01 without numbers: re-read those pages then and update `ypp.TIERS` and `CHECKED` in one commit.
- Shorts views are the latest count of each Short posted in the window, an approximation (YouTube counts only views inside the window).
  Long-form watch hours need the Analytics API and are reported as not measurable, never guessed (rule 1).
- A refused subscriber read is recorded as unknown.

## Website funnel (O15)
- Pages carry PostHog only when `POSTHOG_TOKEN` (the public `phc_` project token) is in the environment at build time; on GitHub it is
  the Actions variable `POSTHOG_TOKEN` (a variable, not a secret). Cookieless: memory persistence, no autocapture, recording, heatmaps
  or dead clicks. Events: pageviews, `calculator_used` (first input on a page), `shop_click` (Gumroad or Etsy links).
- `python -m faceless site-stats --days 7` reads them back with `POSTHOG_PERSONAL_API_KEY` and `POSTHOG_PROJECT_ID` (US cloud), real
  site only, into `analytics/site.jsonl`. HQ shows the last row. The metric that matters: shop clicks per pageview.
- Headless browsers are dropped by PostHog's bot filter, so a test in Playwright captures nothing unless the filter is lifted inside
  that test session only. Never ship `opt_out_useragent_filter` on the site.
- The privacy page states what is counted; change both together (and `LEGAL_UPDATED`).
