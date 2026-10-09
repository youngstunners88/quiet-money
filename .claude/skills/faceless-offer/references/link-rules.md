# Where a link can be tapped (checked 2026-10-08)

Sources are third-party guides and the 2023 trade press, not the platforms' own help pages (TikTok's and YouTube's are script-rendered and could not be read from here), so
check the Edit profile screen before relying on a line. The TikTok row was settled on 2026-10-09 from three independent 2026 sources (on.link read TikTok's page on 4 and 6 September 2026,
Shopify, SirenCY) that all quote the same help-page sentence; the guides that say a free switch to Business unlocks the field at once contradict that wording and look outdated.

| Surface | Tappable link? | Evidence |
|---|---|---|
| TikTok caption or comment | No, plain text | Colorado State social media guide; Outfy help |
| TikTok profile "Links" field | Yes with **1,000 followers on a General account, or a Verified Business Account** | TikTok's help page: "You can add a link to a website on your TikTok profile if you have at least 1,000 followers, or if you have a Verified Business Account." Verification needs documents (an EIN and legal name in the US), takes up to 5 business days and is offered only in listed countries. A Business account cannot use the general music library (Commercial Music Library only) and an unverified one may be converted back |
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
- on TikTok, until the field is available (1,000 followers), the only link that works is one a viewer can type: a short address in the bio text and, later, on screen. A short domain
  (portfolio O2) that serves this site would do it: GitHub Pages takes a custom domain, so `quietmoney.<tld>/reset` can replace the long project address everywhere
- DM automations that reply to a comment keyword are a separate decision (check the platform's rules first); nothing here sends a message
