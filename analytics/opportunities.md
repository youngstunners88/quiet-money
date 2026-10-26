# Opportunities, 2026-10-26

Last 7 days: 49 videos, 16 held (33%), images {'cloudflare': 129, 'muapi': 203, 'pollinations': 12}, paid $6.13, metrics rows 32, publish mode `youtube`.

No revenue data exists yet: ranking is impact on output/reach divided by effort, not profit.

| # | Opportunity | Type | Impact | Effort | Who | Why |
|---|---|---|---|---|---|---|
| 1 | YPP entry changes 2027-02-01 for new applicants: 1,000 subs and 8,000 watch hours (365 d) or 20M Shorts views (90 d); existing members keep the current terms | monetization | 4 | 1 | operator | newscaststudio (2026-08-10) and air.io summary of the 2026 rules: current path is 1,000 subs plus 4,000 watch hours or 10M Shorts views in 90 days. Track progress with python -m faceless ypp. Sources: https://air.io/en/monetization/youtube-partner-program-requirements-2026-the-complete-guide and https://www.newscaststudio.com/2026/08/10/youtube-partner-program-monetization-changes-2027/ |
| 2 | Cloudflare Workers AI pricing page changed (model list edited); confirm the models the engine uses are still priced as expected | cost | 3 | 1 | operator | scout policy watch shows 2 added and 1 removed rule sentences on developers.cloudflare.com/workers-ai/platform/pricing/ (2026-10-26). The engine uses flux-2-klein models for stills; check the flux entries before the next daily run. |
| 3 | 8 rule pages need a session fetch (Exa) and `faceless policy --record` | compliance | 3 | 1 | operator | tiktok-creator-rewards, tiktok-aigc, gumroad-prohibited, etsy-ai-stance, etsy-creativity, adobe-genai, fiverr-standards, ftc-canspam |
| 4 | YouTube July 2026 clarification: AI personas discussing finance may be 'inauthentic' and unmonetized (verify on the YouTube help page) | compliance | 5 | 2 | owner | TechCrunch (2026-07-20) and HackerNoon (2026-07-16) report YouTube now lists generic or template content, off-putting content, and AI personas discussing sensitive topics such as health and finance as non-monetizable 'inauthentic content'. Secondary reporting only; the full 2026 text was not retrievable. Source: https://techcrunch.com/2026/07/20/youtube-clarifies-policies-around-ai-slop-and-upsetting-videos/ |
| 5 | Cut the hold rate (33%): fix the most common failing gate | ops | 4 | 2 | operator | 16 of 49 videos held this week. Top failing gates: loop_plan x12, originality x4, word_count x4. |
| 6 | Hold rate 33% this week; loop_plan gate is the most common failure (x12) ahead of originality (x4) | ops | 4 | 2 | operator | python -m faceless scout --act table: 16 of 49 videos held in 7 days; loop_plan x12, originality x4, word_count x4. Fixing the loop_plan writer rule is an engine change that needs CI. |
| 7 | Gemini Veo 3.1 preview models retire 2026-10-22: the engine does not call Veo, no change needed | tools | 2 | 1 | operator | A third-party tracker lists veo-3.1 preview models retiring 2026-10-22 with gemini-omni-1.1-flash as replacement; not confirmed on ai.google.dev. grep of faceless/ finds no Veo call. Source: https://tech-insider.org/veo-3-1-api-setup-sora-2-migration-2026/ |

## Portfolio (full ranking in channel/empire/RANKING.md)
- Built, waiting for the owner: O18 Offer layer: one tracked offer per video, the link-in-bio hub page, the distribution rails report (200.0); P4 Money Reset Kit bundle (P1+P2+P3) (135.0); O10 LongCat as a third script provider (free daily allowance) (112.5)
- Owner unlocks the most: Create the TikTok and Instagram accounts (@quietmoneyrule) and connect them for auto-posting (YouTube is live and posting) (401.0 pts); Pick an email service, a domain and a postal address, and connect them (375.5 pts); Approve the prices and listings of the built products (the Gumroad shop is open; Etsy for printables) (346.5 pts)

## Who can act
- **auto**: scout can do this itself (--act)
- **operator**: an operator session may do this (code/tests/review); no money or accounts involved
- **owner**: needs the owner: money, accounts, or credentials
