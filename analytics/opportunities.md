# Opportunities, 2026-10-05

Last 7 days: 39 videos, 10 held (26%), images {'cloudflare': 140, 'openrouter': 155, 'pollinations': 149, 'procedural': 53}, paid $6.22, metrics rows 0, publish mode `local`.

No revenue data exists yet: ranking is impact on output/reach divided by effort, not profit.

| # | Opportunity | Type | Impact | Effort | Who | Why |
|---|---|---|---|---|---|---|
| 1 | Remove the daily image cap: Cloudflare Workers Paid (~$5/month) or top up OpenRouter | ops | 4 | 1 | owner | 41% of images this week came from the low-resolution fallback; providers were out of quota on 2 day(s). Paid images look sharper and let all 5 daily videos use real FLUX art. |
| 2 | Switch paid images from OpenRouter (~$0.04/image) to Cloudflare Workers Paid ($5/month + $0.011 per 1,000 neurons over the free 10k/day) | ops | 4 | 1 | owner | At our metered ~417 neurons per 864x1536 FLUX-2-klein-4b image, the ~45 images/day above the free tier cost ~19k neurons = ~$0.21/day (~$11/month incl. the $5 base) vs ~$1.50/day (~$45/month) on OpenRouter this week. Steps: Cloudflare dashboard > Workers & Pages > Plans > Workers Paid; then an operator raises cloudflare_daily_neurons in studio.toml. Source: https://developers.cloudflare.com/workers-ai/platform/pricing/ (2026-10-05). |
| 3 | Create the YouTube/TikTok/Instagram accounts and turn on auto-posting (Upload-Post) | growth | 5 | 2 | owner | Publish mode is local: videos are made but nobody sees them. Nothing else compounds until posts go out. |
| 4 | Start recording post metrics (views, retention, follows) so pillar weights and this scanner can use real data | growth | 4 | 2 | owner | Only 0 metric rows exist; the router stays balanced and profit ranking is impossible until ~10+. |
| 5 | Cut the hold rate (26%): fix the most common failing gate | ops | 4 | 2 | operator | 10 of 39 videos held this week. Top failing gates: word_count x6, loop_ending x6, no_placeholder_art x5. |
| 6 | TikTok Creator Rewards: 10k followers, 100k views/30 days, >1 min, and 'minimal original input' content excluded | monetization | 4 | 2 | owner | Our 61-72 s length qualifies, but fully synthetic videos risk the 'minimal original input' exclusion and unlabeled AI content escalates to removal from the program. Owner should keep the AI label on every post and plan some human input (e.g. own voice or on-screen commentary on a share of posts). Sources: https://storrito.com/resources/what-tiktoks-ai-monetization-restrictions-signal-for-creator-income/ , https://www.shortfast.com/blog/tiktok-creator-rewards-program-requirements (2026-10-05). |
| 7 | Reduce 'inauthentic / mass-produced' risk before posting: vary templates and add visible human editorial input | risk | 5 | 3 | operator | YouTube renamed 'repetitious content' to 'inauthentic content' (mass-produced, templated, little variation) and in Jan 2026 terminated AI channels with billions of views; AI use itself is allowed with disclosure and genuine human value. Our six pillars already vary looks; next: rotate caption/hook layouts, add an owner-reviewed angle per video. Sources: https://lenspov.com/articles/youtube-ai-content-demonetization-2026 , https://ytgrowth.io/blog/youtube-ai-policy (2026-10-05). |
| 8 | Add a 'finance stat that shocks' hook pattern (one national statistic + its yearly cost) to the math and myth pillars | content | 3 | 2 | operator | Listed among high-performing personal-finance Shorts formats in 2026; fits our fact-sheet math if each stat is sourced. Finance Shorts CPM cited around $4.50. Source: https://fluxnote.io/guides/youtube-shorts-trending-formats-2026 , https://outlierkit.com/blog/youtube-rpm-finance-niche (2026-10-05). |
| 9 | Prioritize backlog topics with the strongest search demand (car loan vs used car 30, cash envelope 29, compound interest 27) | content | 2 | 2 | operator | keywords --backlog shows demand from 3 to 30 among queued topics; ideate picks in file order, so low-demand topics ship first. Source: python -m faceless keywords --backlog 12 (2026-10-05). |

## Who can act
- **auto**: scout can do this itself (--act)
- **operator**: an operator session may do this (code/tests/review); no money or accounts involved
- **owner**: needs the owner: money, accounts, or credentials
