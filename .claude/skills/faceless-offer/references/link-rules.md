# Where a link can be tapped (checked 2026-10-08)

Sources are third-party guides and the 2023 trade press, not the platforms' own help pages (those could not be read from here), so treat the
TikTok line in particular as "verify on the Edit profile screen". Re-check with `python -m faceless policy` when it learns these pages.

| Surface | Tappable link? | Evidence |
|---|---|---|
| TikTok caption or comment | No, plain text | Colorado State social media guide; Outfy help |
| TikTok profile "Website" field | Yes when the account qualifies | Sources disagree: Stan Store (April 2026) and Rocketlink say 1,000 followers or a business account; UniLink (May 2026) says the follower minimum was dropped in mid-2024; Linkboo (June 2026) says about 1,000 and varies by region |
| Instagram caption or comment | No | same guides |
| Instagram profile link | Yes | same guides |
| YouTube Shorts description or comment | No, plain text since 31 August 2023 | TechCrunch and Tubefilter (10 August 2023); a 2026 third-party guide says it still holds |
| YouTube channel page links (up to 14) | Yes | same coverage |
| YouTube long video description and comments | Yes | same coverage |
| X post, LinkedIn post, Pinterest pin, newsletter | Yes | standard behaviour |

Consequences built into `faceless/offer.py`:
- the bio link is one hub page per platform, tagged `utm_source=<platform>&utm_medium=bio`; that is the attribution for short video
- the caption says "link in bio"; the YouTube description carries one tracked URL (it helps when the video is opened as a long video or the text is copied)
- thread, LinkedIn, pin and newsletter assets in the repurposing kit carry `utm_source=x|linkedin|pinterest|newsletter` and `utm_content=<video id>`
- DM automations that reply to a comment keyword are a separate decision (check the platform's rules first); nothing here sends a message
