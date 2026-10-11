# Platform profiles: Quiet Money

Handle everywhere: **@quietmoneyrule** (checked 2026-10-01: free on YouTube and TikTok; `@quietmoney`,
`@quietmoneytv`, `@quietmoneylab` are taken on YouTube). Display name: **Quiet Money**.
Assets: `brand-kit/avatar.png`, `brand-kit/banner-youtube.png`, `brand-kit/watermark.png`.

## YouTube
- **Name:** Quiet Money
- **Handle:** @quietmoneyrule
- **Description, keywords, language, banner, series playlists:** live in `studio.toml [youtube]` and are applied by `python -m faceless yt-channel --apply` (never paste by hand; `faceless-youtube-seo` explains the wording).
- **Links** (channel page, up to 14, tappable): the hub page tagged for YouTube (`utm_source=youtube&utm_medium=bio&utm_campaign=profile`; `python -m faceless offer` prints it), TikTok, Instagram. Links in Shorts descriptions and comments are plain text.
- **Branding:** profile picture `avatar.png`, banner `banner-youtube.png`, video watermark `watermark.png` (display: entire video)
- **Defaults:** category Education, language English, "altered or synthetic content" = Yes on every upload

## TikTok (bio max 80 chars)
- **Name:** Quiet Money
- **Username:** quietmoneyrule
- **Bio (69):** `Money rules nobody taught you. Real numbers, 60 sec a day. 👇 Free checklist`
- **Link:** the hub page tagged `utm_source=tiktok&utm_medium=bio&utm_campaign=profile` (`python -m faceless offer` prints it). TikTok shows the Links field only with 1,000 followers or a Verified Business Account (documents, up to 5 business days; a Business account also loses the general music library). Until then put the site address in the bio text (not tappable). Captions and comments are never tappable.
- Turn on: AI-generated content label for every post.

## Instagram (bio max 150 chars)
- **Name:** Quiet Money | Money Rules
- **Username:** quietmoneyrule
- **Bio (118):** `The money rules nobody taught you.\nReal stories. Real math. 60 seconds a day.\n📩 Free 7-day Money Reset ↓`
- **Link:** the hub page tagged `utm_source=instagram&utm_medium=bio&utm_campaign=profile` (`python -m faceless offer` prints it). Captions and comments are not tappable.

## Pinned comment (every video)
Each video's own line is in `distribution/queue/<day>/slot<N>-<pillar>/OFFER.md` (one offer per video, checked for money claims). The default is
`Free 60-second money reset checklist is in my bio. Educational only, not financial advice.` After pinning it: `python -m faceless offer mark <video id> pinned`.
