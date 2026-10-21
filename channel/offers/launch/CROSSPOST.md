# Cross-posting routine for TikTok and Instagram Reels (owner, about 10 min a day, Wed 10-21 to Tue 10-27)

**Reality check:** across 32 Shorts the 48-hour median is 16 views. Cross-posting gives the videos more chances to be seen, but it probably won't produce sales on its own this week. The 60 one-to-one warm messages (owner queue U03) are the plan's first-sales engine. If you only have time for one of the two, do U03 first; MARKETING.md cuts TikTok/Reels second when owner hours run short. This lane spends none of the $10. I edited no repository files.

## Day 0, done once (about 25 min)
- [ ] **TikTok `@quietmoneyrule`**: keep it a Personal account, not Business. A Business account loses the general music library and Creator Rewards, and verifying one needs business documents.
- [ ] **Make the TikTok profile tappable:** Edit profile → Links → Add → link Instagram and YouTube. These icons work before 1,000 followers. TikTok says this "isn't currently available everywhere".
- [ ] **TikTok bio** (74 of 80 characters): `Money rules nobody taught you. Free checklist + Daily Planner: tap IG icon`
- [ ] **Instagram `@quietmoneyrule`**: Edit profile → Links → Add external link. This works only in the phone app, not on a computer. Use `https://youngstunners88.github.io/quiet-money/links/?utm_source=instagram&utm_medium=bio&utm_campaign=profile&o=daily-quiet-money-planner`. The `&o=` part moves the planner card to the top of the hub. I checked this in `faceless/site.py` and on the live page. The bio text stays as in `channel/profiles.md`.
- [ ] **Download the 14 MP4s below** on a computer: YouTube Studio → Content → pick the video → menu (⋮) → Download. Put them in a phone album called "QM cross-post".
  - The files are 720p or 360p, and each video can be downloaded 5 times a day.
  - Upload this clean file to Instagram. Never upload the copy TikTok saves, because Mosseri says Instagram tries "not [to] recommend Reels with logos from other apps".
- [ ] **Ask the agent for two checks before Day 1:**
  - The music beds are Lyria RealTime AI instrumentals (`assets/music/manifest.json`). Their terms for promotional use are still unverified (MARKETING C8), and TikTok asks for a Music Usage Confirmation when commercial disclosure is on.
  - A Kamprad research brief, so the IKEA video can be cleared (see Hold).

## Every day (10 min)
- [ ] **TikTok, 3 min:** + → Upload → today's video A → Next.
  - Paste the caption (formula below). For the cover, use the first frame, which shows the hook text.
  - More options: turn **AI-generated content ON**. Then turn **Disclose commercial content ON → Your brand**. The caption promotes our own planner, and TikTok's ads help says you "must turn on" disclosure for that. Third-party guides quoting TikTok say disclosure doesn't affect distribution.
  - Keep the original sound. Do **not** add a trending sound, even though the POST.md checklist says to. With disclosure on, TikTok steers you to the Commercial Music Library.
  - Leave it visible to Everyone with comments, Duet and Stitch on. Post, then post the pinned comment and pin it.
- [ ] **Instagram, 3 min:** + → Reel → the same MP4 → paste the caption → turn **Add AI label ON**. Meta lists "a reel narrated by a realistic AI voice" as needing the label. Share, then pin the comment.
- [ ] **Video B, 2 min:** do the same for both platforms. Use Schedule for 18:30 ET if your app offers it; otherwise post it in the evening.
- [ ] **Replies, 2 min:** answer every comment on yesterday's posts.
- [ ] **Log, 30 s:** write down each post's 48-hour views and saves on TikTok and on Instagram. This is the X5 trial (14 posts). Its pass bar is a 500 median view count and a 2% save rate.

## What goes in each field
| Field | TikTok | Instagram |
|---|---|---|
| Caption line 1 | the pack title | same |
| Line 2 | first sentence of the pack caption (POST.md "TikTok / Instagram caption", or `caption` in the script JSON for videos without a pack) | same |
| Line 3: CTA if the pillar is story, psychology or myth | `The Quiet Money Daily Planner (paid): tap the Instagram icon on my profile.` | `The Quiet Money Daily Planner: link in bio (paid).` |
| Line 3: CTA if the pillar is escape or math | `Free money reset checklist: tap the Instagram icon on my profile.` | `Free money reset checklist: link in bio.` |
| Line 4 (rule 2, every post) | `Educational, not financial advice. Narration and visuals are AI-assisted.` | same |
| Hashtags | 4-5 from the pack. Drop `#passiveincome` and `#financialfreedom`, which are claim-gate terms in MARKETING C1 | same |
| Pinned comment | line 3 + ` Educational only, not financial advice.` (at most 134 of 150 characters) | the pack's OFFER.md pinned line |
| Labels | AI-generated content ON, Disclose commercial content → Your brand | Add AI label ON. Leave Paid partnership off; that label is for third-party brands |

## The 14 picks, ranked by 48-hour YouTube views
Story, myth and escape lead the snapshot data. 9 of the 14 are planner pillars. Pack folders are under `distribution/queue/`.

| Day | Video A | Video B |
|---|---|---|
| Wed 10-21 | 1932 Envelope Trick (55 views, story → planner, `3MFMt8QYqLk`, `2026-10-09/slot4-story`) | Why Your Paycheck Carries the Highest Tax (53, escape → checklist, `8tW9TqejAwM`, `2026-10-17/slot5-escape`) |
| Thu 10-22 | College Degree ROI Trap (37, myth → planner, `cfF5bJzOpLM`, `2026-10-14/slot1-myth`) | Brutal Cost of Impressing Strangers (34, psychology → planner, `d2XkFvt82t8`, `2026-10-10/slot5-psychology`) |
| Fri 10-23 | The 4 Paths to Wealth (35, escape → checklist, `m76oHf3xh18`, no pack: `script-lab/final/2026-10-02-s8-escape-the-four-ways-to-earn-money-and.json`) | Why You Keep Paying for Things You Don't Use (28, psychology → planner, `C93Ji89b1qk`, `2026-10-14/slot5-psychology`) |
| Sat 10-24 | Real HYSA Yield After Taxes (33, math → checklist, `t82nM8o95wQ`, `2026-10-15/slot3-math`) | Why Wealth Isn't an Income Problem (23, myth → planner, `A4hZ3AX6tGQ`, `2026-10-13/slot2-myth`) |
| Sun 10-25 | Value Equation Math (25, escape → checklist, `Ldjc0VXFJFQ`, `2026-10-13/slot4-escape`) | The House Myth (22, myth → planner, `om0qWihW1Kw`, no pack: `script-lab/final/2026-10-06-s7-myth-myth-your-house-is-your-best-inv.json`) |
| Mon 10-26 | 10-Year Delay That Costs $400,130 (23, math → checklist, `AvG_HOwq1EQ`, no pack: `script-lab/final/2026-10-02-s0-math-starting-to-invest-at-25-vs-35-t.json`) | Why Avoiding Credit Cards Costs You More (16, myth → planner, `PkXY3sgepWo`, `2026-10-17/slot3-myth`) |
| Tue 10-27 | Math to Replace Your Paycheck (20, escape → checklist, `VdMYSYRX98Y`, `2026-10-14/slot3-escape`) | Why Your Brain Hates Your Future Self (14, psychology → planner, `23eTM0G1z2s`, no pack: `script-lab/final/2026-10-06-s6-psychology-present-bias-why-your-brain-pref.json`) |

**Hold**
- **IKEA story** (176 views, the best performer, `iPGcarrFBvo`): there's no research brief on Kamprad in `channel/research/` (rule 8), and its "$50 BILLION" callout has no source in the script's facts. If the agent's brief confirms it, post it first, in place of Mon 10-26 B.
- **Grace Groner, Latte Factor and Hetty Green stories:** none of these people has a research brief either.
- **Today's 5 videos:** they never reached YouTube because of the quota, so they can't be downloaded from Studio yet.

## Link-in-bio rules, exact text
- **TikTok:** "You can add a link to a website on your TikTok profile if you have at least 1,000 followers, or if you have a Verified Business Account."
  - TikTok's own page is script-rendered and wouldn't load from here. This sentence is quoted the same way by three 2026 sources, as recorded in `.claude/skills/faceless-offer/references/link-rules.md` (settled 2026-10-09).
  - Until you reach 1,000 followers, use the linked Instagram and YouTube icons. Captions and comments are never tappable.
- **Instagram** (official Help Center, read today): "You can add up to 5 websites to your Instagram profile. Note: anyone, on or off Instagram, can see your websites." It works for any account type with no follower minimum. Captions and comments are not tappable.

## 3 free communities where a money-planner post is allowed
1. **r/budget** (173k members, the best audience fit). Rule 3 (quoted by ThreadFox, read 2026-10-05): "No Advertising Affiliated Products or Services without Disclosure. Any post or comment that advertises a product or service associated with the user must have a disclosure stating if they are affiliated with or stand to benefit from the product." Rule 5 sends budgeting platforms and software to the megathread, so present the planner as a printable, not an app.
2. **r/financialindependence**, Weekly Self-Promotion Thread, every Wednesday (next one: Wed 10-21). The thread text (copy dated 2026-10-14) says: "Self-promotion (ie posting about projects/businesses that you operate and can profit from) is typically a practice that is discouraged in /r/financialindependence, and these posts are removed through moderation. This is a thread where those rules do not apply. However, please do not post referral links in this thread. Use this thread to talk about your blog, talk about your business, ask for feedback, etc. ... Link-only posts will be removed. Put some effort into it."
3. **r/TimeManagement**, Weekly Introduction Thread, every Friday (next one: Fri 10-23). Mod post of 2026-07-18: "Every Friday, we drop our Weekly Introduction Thread. This is your green light to pitch! You're welcome to introduce yourself, your app, your coaching, or your content, and include your links." The same post names "planners" among what members build.

**How to post in all three:**
- Post from your own established Reddit account, once per community this week.
- Lead with value: a real tip, such as a 50/30/20 split with stated assumptions. Don't invent a personal story or results.
- Add a disclosure line: "I made this and earn from it; AI-assisted design."
- State the facts: $17, two PDFs (Letter and A4, 427 pages each, 365 daily pages), undated, 30-day refund.
- Use the plain Gumroad URL `https://chrisclassroom4.gumroad.com/l/utwsfs`, with no referral or shortened links and no income claims.
- Stay an hour to reply.

Note that `channel/empire/DISTRIBUTION.md` parked Reddit because promotional accounts get removed. These three are places where the rules explicitly allow it, and posting there is your call under rule 9.

## What I couldn't verify
- Reddit's rule pages blocked this machine (403 errors and login walls). The quotes above come from dated mirrors and quoting services, so open each live rules page before posting.
- TikTok's 1,000-follower sentence and the name of the commercial-disclosure label come from secondary sources.
- The Instagram Schedule menu path is unconfirmed.

Sources:
- [TikTok AI-generated content](https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content) and [its in-app page](https://www.tiktok.com/tns-inapp/pages/ai-generated-content)
- [TikTok commercial disclosure](https://ads.tiktok.com/help/article/how-to-turn-on-the-commercial-content-disclosure-setting-in-tiktok)
- [TikTok profile links](https://support.tiktok.com/en/getting-started/setting-up-your-profile/linking-another-social-media-account)
- [SirenCY on the TikTok link rule](https://www.sirency.com/blog/how-to-add-link-in-bio-on-tiktok)
- [Instagram websites on your profile](https://help.instagram.com/362497417173378/?cms_platform=iphone-app)
- [Instagram AI label steps, quoted from Meta](https://www.zolyp.com/blog/how-to-label-ai-content-on-instagram)
- [Mosseri on logos from other apps](https://www.socialmediatoday.com/news/instagram-clarifies-including-your-own-logo-on-a-reel-is-ok/730852/)
- [YouTube: download your own videos](https://support.google.com/youtube/answer/56100)
- [r/budget rules (ThreadFox)](https://threadfox.vip/rules/budget)
- [r/financialindependence thread, 2026-10-14](https://r.datuan.dev/r/financialindependence/comments/1x5mr5x/weekly_selfpromotion_thread_wednesday_october_14/)
- [r/TimeManagement mod post](https://redlib.vanillax.me/r/TimeManagement/comments/1v084zz/how_do_i_promote_myself_my_business_here/)

Repo files used: `/home/user/quiet-money/analytics/snapshots.jsonl`, `/home/user/quiet-money/distribution/queue/`, `/home/user/quiet-money/channel/empire/MARKETING.md` (C8, X5), `/home/user/quiet-money/channel/profiles.md`, `/home/user/quiet-money/.claude/skills/faceless-offer/references/link-rules.md`, `/home/user/quiet-money/assets/music/manifest.json`.