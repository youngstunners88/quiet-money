# Monetization: income in order of speed

Short-form ad revenue is the *slowest* money. Shorts pay roughly $0.05-0.45 per 1,000 views, and both
programs gate entry. So the plan stacks income sources that start on day 1 and lets platform
payouts arrive on top.

## Phase 0 (day 1): link in bio, no thresholds needed
1. **The hub page** (`/links/` on our own site, built by `faceless/site.py`) is the one link in every profile. Short-video captions and comments are not
   tappable, so every post says "link in bio" and the hub carries the offer: the free checklist first, then any product with a live listing.
   `python -m faceless offer` prints the three profile URLs (same page, tagged by platform) and `faceless-offer` writes the pinned comment per video.
   No link-in-bio service is needed; Stan Store or Gumroad are only the checkout behind a product card.
2. **Lead magnet**: the free "60-Second Money Reset" checklist (one page: automate savings, kill 3 fees, 50/30/20 split, starter emergency fund).
   The list is the asset you own: pick an email service, paste its public form address into `[newsletter] form_action`, and the hub and the
   checklist page show the signup form. The 7-day sequence is already written (`python -m faceless autoresponder`).
3. **Affiliate links** that match the pillars (apply to the ones available in your country):
   - Budgeting apps (YNAB-style, Monarch-style), high-yield savings accounts, brokerages with sign-up bonuses
     (Webull/M1/eToro-style CPA $50-$250), credit monitoring (Credit Karma-style, ~$7/sign-up), cashback apps.
   - Networks that aggregate finance offers: Impact, FlexOffers, Awin/ShareASale, CJ.
   - Affiliate links go in the hub or a description with the disclosure on (`channel.has_affiliate_links`), never in the pinned comment.

## Phase 1 (weeks 1-4): your own digital product
- **$9-$19 "Quiet Money Playbook"**: the 30 money rules from the channel, the calculators, the scripts
  for calling your bank. Sell on Stan Store / Gumroad / Payhip (no upfront cost; they take a cut).
  Every video is a free sample of the product. Best margin, no approval needed.

## Phase 2 (thresholds): platform payouts
| Program | Entry | Notes |
|---|---|---|
| TikTok Creator Rewards | 10k followers, 100k views in 30 days, 18+, eligible country | Only videos **over 60 seconds** earn, which is why our videos run 61-72s. Finance RPM ~$0.60-1.20. |
| YouTube Partner Program | 1k subs + 10M Shorts views in 90 days (or 4k watch hours) | Shorts revenue pool; long-form compilations earn far more (finance $10-18 RPM). |
| Instagram / Facebook | Invite-based bonuses vary by country | Cross-post the same packs. |

## Phase 3 (scale): sponsorships + long-form
- At ~10k followers, finance apps pay for integrations. Keep a media kit in `/channel` once numbers exist.
- Weekly 8-10 minute YouTube compilations of the best 8-10 shorts (same assets, high-RPM long-form).

## Unit economics (current stack)
| Item | Cost per video | Cost per day (5) |
|---|---|---|
| Script (Gemini free tier) | $0 | $0 |
| Voice (Edge neural TTS) | $0 | $0 |
| Images (Cloudflare FLUX.2 klein, free 10k neurons/day) | $0 (13 images ≈ 2,000 neurons) | $0 for ~4-5 videos, then ~$0.02/video |
| Render (GitHub Actions minutes) | $0 on public repos / free minutes | $0 |
| Posting (Upload-Post) | free 10/month; paid plan ~$16-24/month for daily TikTok | ~$0.80 |
| **Total** | **~$0-0.15** | **under $1/day** |
