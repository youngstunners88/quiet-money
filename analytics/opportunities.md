# Opportunities, 2026-10-12

Last 7 days: 48 videos, 5 held (10%), images {'cloudflare': 153, 'openrouter': 125, 'muapi': 173, 'pollinations': 1}, paid $8.1, metrics rows 0, publish mode `youtube`.

No revenue data exists yet: ranking is impact on output/reach divided by effort, not profit.

| # | Opportunity | Type | Impact | Effort | Who | Why |
|---|---|---|---|---|---|---|
| 1 | Test a higher [publish.youtube].max_per_day: the 5-a-day cap may come from an outdated quota figure | ops | 4 | 1 | operator | Older guides say videos.insert costs 1,600 of 10,000 daily units (about 6 uploads). Newer ones report Google revised it to about 100 units on 2026-12-04 and gave videos.insert its own bucket on 2026-06-01 (default 100 calls a day). Sources conflict and are third-party, and the quota belongs to Composio's Google project, so verify empirically: raise the cap one step at a time and read the refusal. 59 made, passed videos are waiting to post and a higher cap drains them sooner. Sources: https://www.postzen.dev/blog/youtube-data-api-upload , https://adaptlypost.com/blog/youtube-api-quota-extension (2026-10-12). |
| 2 | Top up the 'ledger' topic backlog (6 left) | content | 3 | 1 | auto | Low backlog means the writer falls back to unconstrained ideation; seeded, demand-checked topics are better. |
| 3 | Top up the 'escape' topic backlog (6 left) | content | 3 | 1 | auto | Low backlog means the writer falls back to unconstrained ideation; seeded, demand-checked topics are better. |
| 4 | Paid spend $8.1 this week: raise free-tier use or lower the paid image cap | ops | 3 | 1 | operator | Paid fallbacks should be rare; check which provider is spending. |
| 5 | Top up the paid image and text suppliers: Muapi $11.81 (was $20.19 on 2026-10-09) and OpenRouter $3.28 | ops | 3 | 1 | owner | python -m faceless keys on 2026-10-12. Muapi fell about $8 in three days (host clips and extra batches), so its runway is shorter than the 54 days quoted on Oct 9; OpenRouter is under the $5 line and is the text and image fallback when the free tiers run out. Owner action: add credit in each dashboard; the spend caps stay as set. |
| 6 | 8 rule pages need a session fetch (Exa) and `faceless policy --record` | compliance | 3 | 1 | operator | tiktok-creator-rewards, tiktok-aigc, gumroad-prohibited, etsy-ai-stance, etsy-creativity, adobe-genai, fiverr-standards, ftc-canspam |
| 7 | Use the owner's existing TikTok account @youngstunnersss (2.59M followers on its public page) to send audience to the Quiet Money YouTube channel and hub page | growth | 5 | 2 | owner | The studio's own accounts start at zero; this one already has distribution and a bio about 'exiting the rat race'. Steps for the owner: post the Escape-series Shorts there with the AI label on (test 10-14 videos against the account's usual views), and put the hub link (python -m faceless offer) in its bio link field. Check median views of the last 10 posts first: a large follower count can still have little reach left. Source: https://www.tiktok.com/@youngstunnersss (read 2026-10-07). |
| 8 | Start recording post metrics (views, retention, follows) so pillar weights and this scanner can use real data | growth | 4 | 2 | owner | Only 0 metric rows exist; the router stays balanced and profit ranking is impossible until ~10+. |
| 9 | Qualify for the YouTube Partner Program under the current bar before 1 Feb 2027: 1,000 subs + 10M Shorts views in 90 days, or 4,000 watch hours | monetization | 5 | 3 | owner | From 1 Feb 2027 new applicants need 8,000 watch hours (365 days) or 20M Shorts views (90 days); current members are grandfathered, and Shorts ads then also need 10M Shorts views per 90 days. Fan Funding is unchanged (500 subs, 3 uploads in 90 days, 3,000 long-form hours or 3M Shorts views). About 16 weeks remain, so subscriber growth and a weekly long-form compile (watch hours) matter more than views alone. Source: https://www.tubefilter.com/2026/08/10/youtube-partner-program-ad-eligibility-requirements-shorts/ (2026-08-10, read 2026-10-12). |

## Portfolio (full ranking in channel/empire/RANKING.md)
- Agent builds next: C4 Audio edition: daily 60 s + weekly podcast episode (40.5); C3 Weekly long-form: 'Money Rules Weekly' (8-10 min, 16:9, chapters) (36.0); P6 Fillable PDF versions of the printable pack (36.0)
- Built, waiting for the owner: O18 Offer layer: one tracked offer per video, the link-in-bio hub page, the distribution rails report (200.0); P4 Money Reset Kit bundle (P1+P2+P3) (135.0); O10 LongCat as a third script provider (free daily allowance) (112.5)
- Owner unlocks the most: Create the YouTube, TikTok and Instagram accounts (@quietmoneyrule), connect them, and turn on auto-posting (446.7 pts); Pick an email service, a domain and a postal address, and connect them (375.5 pts); Open a Gumroad shop (and Etsy for printables); approve prices and listings (346.5 pts)

## Who can act
- **auto**: scout can do this itself (--act)
- **operator**: an operator session may do this (code/tests/review); no money or accounts involved
- **owner**: needs the owner: money, accounts, or credentials
