# Distribution: how a video reaches people

Written 2026-10-08 after the owner's note that distribution may be the biggest blind spot. Read with `python -m faceless distribute` (the live table of rails)
and `channel/empire/PLAN.md` (the whole business).

## The finding

Production is closed-loop and tested. Distribution was not, and that was the real gap. What the repository showed before this pass:

| Gap | Evidence |
|---|---|
| Nothing posts | `[publish] mode = "local"`; no posting rail has keys. Every video is a pack waiting in `distribution/queue/` |
| The same link on every video, tappable nowhere | the description carried one generic URL; short-video captions and comments are plain text on every platform (`faceless-offer/references/link-rules.md`) |
| No way to collect an email address | the 7-day sequence is written (`channel/offers/autoresponder/`), but the site had no signup form and no service was chosen |
| No attribution | analytics re-weights series by views; nothing joined a video to a click, a signup or a sale |
| Products not routed from videos | four products are ready; no video pointed at the matching one |
| Long-form deferred | the weekly compile (C3) is where links are tappable and watch hours accumulate; it is vetted, not built |
| No outreach | no collaborators, newsletters or podcasts were ever listed or drafted |

The owner's reference case (a Grok conversation about autonomous shops) makes the same point: "automation scales production, not demand". Its numbers
(17 listings in ten days and no sale; 54 dollars in 111 days) are claims in a transcript that we did not verify, so they are a warning, not evidence.

## What was built in this pass (all tested, CI green)

| Piece | Where | What it does |
|---|---|---|
| **Offer layer** | `faceless/offer.py`, `faceless-offer` skill | every video gets one offer: the free checklist leads, a paid product only when its live URL is in `[offer] shop_urls`; pinned-comment line, caption call to action, one tracked link, `OFFER.md` per pack, append-only ledger `state/offers.jsonl`; claim check refuses guarantees, income promises, returns, debt-relief promises, buy calls; no model calls |
| **Hub page** | `/links/` on the site (`site.hub_page`) | the one link in every profile; free checklist first, live products next, tools and library; `?o=<slug>` moves a card to the top; noindex, not in the sitemap |
| **Email signup, off until configured** | `site.signup_form`, `[newsletter] form_action` | the form appears on the hub and the checklist page only once the owner pastes an email service's public form address |
| **Visit counter slot** | `[site] head_snippet` | one file of the owner's own analytics tag, inserted on every page; no provider is baked in |
| **Tagged links where links work** | `repurpose.py` | thread, LinkedIn post, pin and newsletter item carry `utm_source=x|linkedin|pinterest|newsletter` and the video id |
| **Rails report** | `faceless/distribute.py`, `python -m faceless distribute` | every rail with its state and the owner's next step; `--live` checks the hub is published |
| **Safety nets** | preflight `offer:coverage`, watchdog "videos shipped without an offer", gauntlet soft gate `offer_cta` | a video is never held for its call to action, but a missing one is reported |
| **Intake fix** | `faceless/intake.py` | a second batch dated the same day no longer overwrites the first batch's rows in the registers |

### Where this pass corrected the Grok draft of `faceless-offer`
- A pinned comment with a URL does nothing on TikTok, Instagram or YouTube Shorts (plain text). The offer is "link in bio" and the bio link is the hub.
- Per-platform UTM variants of one link per video only help where a link is tappable. For short video the attribution is the platform on the profile link, the day,
  and the card the visitor asked for (`o=`); per-video attribution holds for the repurposed assets and the long video.
- The ledger is JSONL (`state/offers.jsonl`), not CSV: two sessions that append at once merge by union, which a CSV header would break.
- "Publish only ships a video whose offer row exists" became a soft gate plus the `offer --batch` net, because a call-to-action problem must never hold a good video.

## What the numbers can and cannot tell us
Bio-link traffic arrives from every video of a platform at once. We can see which platform converts, which day's mix of videos was followed by clicks, and which
offer card was asked for. We cannot see which single short sent a visitor unless a link was tappable. That is why the weekly long-form compile and the repurposed
assets matter for learning, not only for reach.

## Ranked next moves (distribution only)
1. **Go live (owner).** Accounts, then either posting by hand from `POST.md` or an auto-posting rail (Upload-Post is the one that sets the AI labels on TikTok and YouTube).
   Nothing below matters until posts exist. `python -m faceless distribute` lists the exact steps.
2. **Email list on.** Pick a service, paste its form address into `[newsletter] form_action`, add the postal address, import `channel/offers/autoresponder/sequence.json`.
3. **First product live.** List one product from its ready pack, add the URL to `[offer] shop_urls`; the offer rotation starts by itself.
4. **A visit counter** (cookieless), saved as the file named in `[site] head_snippet`.
5. **Weekly long-form compile** (portfolio C3): tappable links in the description, watch hours, finance RPM. Build after the first month of real posts.
6. **Outreach drafts** (see below): collaborators, newsletters and podcasts, drafted for the owner to send.
7. **Packaging formats** from the owner's transcript ("seven levels of...", "why it sucks to be...", "X warned us about Y"): a bank of title shapes that the topic picker can use, with
   our own subjects. Never copy a channel's titles, and never use a format that needs a claim about a real person.
8. **Answer-engine work** (AEO): Bing and Brave indexing (IndexNow is already in the site), comparison pages with computed numbers. Programmatic pages must each be useful on their own,
   or Google's scaled-content policy turns them into a liability.

## Considered and not done
| Idea | Why not |
|---|---|
| treg (tool gateway, lead signals) | B2B prospecting with contact look-ups; a third-party token and a prepaid balance; our research data already comes from TokConnect, Exa, TinyFish and the Muapi desk. Parked: `repo-farm/intake/2026-10-08b/` |
| rea (reverse-engineering MCP) | its use here would be rebuilding private platform APIs to drive the owner's Etsy or Flow account, which puts a real account at risk. Killed again |
| Adobe Stock and Fiverr gigs | Grok's review of this repository said to skip a standalone Adobe Stock skill and to hold Fiverr until the Gumroad pages have sales; a brand-kit gig competes with the studio for the same hour. Portfolio S1/S2/M1 stay as they are |
| Meme-token tie-in for a character | a securities-and-fraud magnet attached to a personal-finance brand; the transcript's own numbers are wallet receipts, not profit. Rejected |
| Swapping a character into other people's viral videos | borrows someone else's footage and likeness. Rejected |
| Comment-to-DM automation | possibly useful for per-video attribution, but each platform's automation rules must be read first and an account is at stake. Parked until the owner asks |
| Reddit | the SEO WORK document itself quotes a Promptwatch co-founder (unverified) that Reddit fell from 15% of ChatGPT citations to zero while documentation pages rose 32%; promotional accounts are also routinely removed. Unchanged |
| Buying followers, engagement pods | suppress reach and risk monetisation (`faceless-growth` Never list). Unchanged |

## Decisions only the owner can make
- Which accounts to create and when to go live; which posting rail (Upload-Post is the recommended one).
- Which email service, and the postal address for the footer.
- When to list the first product, and its price test (the catalog has a $12/$19/$29 band for the planner).
- Whether to add a visit counter, and which.
