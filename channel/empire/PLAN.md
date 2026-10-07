# The printing press: plan

*Quiet Money, a purely digital operation run by one agent and one owner. Numbers marked (measured) come from our own
files; numbers marked (assumed) are placeholders until real posts produce data. Re-run `python -m faceless forecast` and
`python -m faceless empire` for today's figures.*

## Thesis
Attention is rented; an audience you can contact and assets you own compound. A video costs cents to make and its views
are close to worthless on their own (Shorts ads pay roughly $0.02-0.10 per 1,000 views, assumed). The money is made *after
the view*: the list, the products, the services. So every video is built to be reused on other surfaces, and every
surface points at one free entry point (the 7-day Money Reset) that leads to a list, then to products.

## The machine
```
 research + verified math (moneymath, channel/research)
        |
   script  -> gauntlet (score >= 80, no hard fails)
        |
   Short (5/day) -----------> TikTok / YouTube / Instagram          [needs: accounts live]
        |
   repurposing kit (automatic, per video)
        |-- thread, LinkedIn post ........ text platforms
        |-- 7-slide carousel, pin ........ Instagram / LinkedIn / Pinterest
        |-- audio clip ................... podcast edition
        |-- newsletter item .............. weekly issue (auto-compiled)
        '-- website page + calculators ... search and AI answer engines
        |
   free Money Reset (7 days) -> autoresponder -> list               [needs: email service, domain, address]
        |
   products: Rat Race Escape Planner (built) -> planners -> bundle  [needs: Gumroad shop]
   services: brand kit for faceless creators -> studio mode          [needs: Fiverr gig]
```
Owner-made Flow clips replace the hook still of a video (3 clips a day, about 10 minutes): real motion in the opening
seconds and one fewer generated image. Motion cards (count-up numbers, comparisons, numbered steps) replace stills on
numeric beats. Variety comes from format, not from more spend.

## Unit economics
| item | figure | source |
|---|---|---|
| generated images per video | 11.5 | measured, 12 videos |
| free Cloudflare images per day | about 24 (about 2 videos) | measured: 417 neurons per image |
| next batch of 5, free tier used up | about $2.21 | measured price x images |
| next batch of 5 on Cloudflare Workers Paid | about $0.25 | Cloudflare's published rate |
| 5 videos a day for a month, Workers Paid | about $10 all in | forecast |
| 5 videos a day for a month, OpenRouter fallback | about $42 | forecast |
| revenue per month, low / base / high | $33 / $229 / $1,828 | **assumed**: 300 / 2,000 / 15,000 views per video, 1% reach the link, 25% join the list, 3% of the list buys a $19 product |
Reading: cost is small and known; revenue depends almost entirely on views and the list. That is why distribution (accounts
live) is the first unlock and the list the second.

## Sequence
**Phase 0, now (no owner needed): done or in the repo.** Daily factory, website, repurposing kit, Flow lane, motion-card
variety, two spreadsheet products (Rat Race Escape Planner and Debt Payoff & Compound Interest Planner, each recalculated in a
real spreadsheet engine and matched to independent math), the 7-day Money Reset autoresponder (every number computed), the
newsletter compiler, the Fiverr brand-kit engine with gallery samples, the empire gauntlet and the forecast.
**Phase 1, week 1 (owner, about 30 minutes):** create the channels and connect posting; pay $5 for Cloudflare Workers.
Result: 5 videos a day actually post, with enough image supply for every one.
**Phase 2, weeks 2-4:** open a Gumroad shop, list the planner (price test $12 / $19 / $29); pick an email service, a
domain and a postal address, start the 7-day autoresponder and the weekly issue. The agent builds the next unblocked item
each week (next: printable pack, audio edition, weekly long-form, studio mode).
**Phase 3, month 2+:** Fiverr gig for the brand kit, weekly long-form compilation, podcast edition, Etsy for printables.
**Phase 4, by evidence:** every item moves up only when its metric beats its kill rule for 4 weeks; otherwise it is killed
and the reason is written in `RANKING.md`.

## Metrics and kill rules
| rail | metric | kill rule |
|---|---|---|
| Shorts | views per video, hold rate of our own gauntlet | hold rate above 40% for 2 weeks |
| variety layer | retention vs baseline | no lift after 30 videos |
| list | joins per 1,000 views | under 1 per 1,000 after 60 days |
| products | sales per 100 page views | zero sales after 200 views, or a refund rate above 10% |
| services | quotes to orders | fewer than 1 order in 30 days of an active gig |
| marketplaces | acceptance and download rate | rejected twice for the same reason |
Scores in the ranking are judgment until these numbers exist; the weekly run re-scores with whatever evidence arrived.

## Risks
- **Platform policy on AI content / "inauthentic" content** can limit reach or monetization. Mitigation: AI disclosure on, original scripts and research, varied formats, no reused third-party media; the weekly scan re-checks the rules.
- **Account loss.** The agent never touches platform logins; the owner holds every account on one domain mailbox so recovery is possible.
- **Image supply.** Single biggest operational bottleneck; fixed by the $5 plan, with motion cards and Flow clips reducing the need.
- **No data yet.** All revenue figures are assumptions; the plan front-loads getting posts live to replace guesses with numbers.
- **Legal.** Education only, no advice; newsletter needs a postal address and unsubscribe before the first send; no income claims.

## What the owner unlocks, in order of value
1. Open the shop (Gumroad first): unlocks the planner and everything that follows it.
2. Channels live with auto-posting: unlocks distribution, the metrics loop, long-form and rewards.
3. Cloudflare Workers Paid ($5/month): unlocks full 5-a-day image supply.
4. Email service + domain + postal address: unlocks the list, autoresponder and weekly issue.
5. Ten minutes a day in Flow: unlocks moving hooks.
6. Fiverr gig, podcast host, Etsy + Printify, Adobe Stock, affiliates: later, in that order.

## Not doing (killed by the attack round)
Cloning other sellers' best-sellers; scripting a personal Google login to automate Flow; agent-created accounts and mailbox
signups; prompt packs on Etsy. Each risks the owner's accounts or breaks a platform's rules for a small gain.
