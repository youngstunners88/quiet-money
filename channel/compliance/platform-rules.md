# Platform rules we run on (verified 2026-10-08)

Read from the platforms' own pages on the date above (sources linked; `python -m faceless policy` re-reads the ones this machine can
fetch and the weekly session re-reads the rest). Where a row says *unverified*, nobody has read the primary page yet. Rules change:
check the live page before the owner lists, posts or sends.

## YouTube ([monetization policies](https://support.google.com/youtube/answer/1311392), [AI disclosure](https://support.google.com/youtube/answer/14328491))
- **Inauthentic content** (renamed from "repetitious content" on 2025-07-15): mass-produced, generic, repetitive or templated content is not monetizable.
  Not allowed: image slideshows or scrolling text with little narrative or educational value; AI content "made with generic or unoriginal templates giving the
  impression of mass production without adding the creator's original, authentic insights". Allowed: the same intro and outro, and series where each video has a
  distinct storyline, focus or concept.
- Reviewers look at the channel's main theme, most-viewed and newest videos, biggest watch-time share, metadata and the About section.
- **AI disclosure** is required for realistic AI scenes and for *AI-generated music*; production help (script, titles, captions, upscaling) is not. We keep the
  "AI use" label on for every upload.
- What it means here: every video must carry its own substance (computed numbers, a distinct story or steps); keep formats varied (cards, clips, steps, comparisons);
  watch the sameness score (`faceless variety`); never run a single template five times a day with swapped nouns.

## TikTok ([Creator Rewards](https://support.tiktok.com/en/business-and-creator/creator-rewards-program/creator-rewards-program), [AI content](https://support.tiktok.com/en/using-tiktok/creating-videos/ai-generated-content))
- Creator Rewards needs: personal account (not Business), 18+, 10,000 followers, 100,000 views in 30 days, videos at least one minute, original content "filmed,
  designed, and produced entirely by yourself", at least 1,000 qualified For You views per video. Sponsored content and Series videos do not qualify.
- Not original: duets/stitches, copied or slightly modified content, content from other creators without new ideas, looping or templated reuse.
- Label realistic AI-generated content; fake authoritative sources, crisis events and the likeness of private people or minors are prohibited.
- What it means here: our 61-72 second videos clear the length bar; the account must be a Personal account; follower and view thresholds come first.

## Marketplaces
- **Gumroad** ([not allowed](https://gumroad.com/help/article/155-things-you-cant-sell-on-gumroad)): no reselling other people's work (ebooks, templates, prompts, presets),
  no AI services fulfilled off-platform, **no credit-repair ebooks or "products that discuss credit improvement"**, no dropshipping, no products whose only delivery
  is "message me elsewhere". Second violation: two weeks' notice, payout, account deleted.
  Our planners are original files delivered on the platform. Keep listing copy away from credit-score or credit-repair promises.
- **Etsy** ([AI stance](https://www.etsy.com/seller-handbook/article/1275449912004), [Creativity Standards](https://www.etsy.com/legal/creativity)): seller-prompted AI creations allowed
  with a disclosure in the listing description; **AI prompt bundles are prohibited**; digital items must be made or designed by the seller.
- **Adobe Stock** ([generative AI guidelines](https://helpx.adobe.com/stock/contributor/submit-your-content/submit-generative-ai-content/generative-ai-content-guidelines.html), updated 2026-06-11): label
  every generative AI asset; never put artist names, real people, fictional characters, third-party IP or government agency names in prompts, titles or keywords; confirm the
  generating tool's terms allow licensing the output. FLUX.2 klein 4B is Apache-2.0 (Black Forest Labs' help center), but Cloudflare's hosted-partner terms were not
  read: *unverified*, check before the first upload.
- **Fiverr** ([Community Standards](https://help.fiverr.com/hc/en-us/articles/32242973123985-Our-Community-Standards)): one account per person, truthful profile and
  gig claims, no copying other sellers' gig text, no AI imagery to create or verify an account. AI tools are welcome; misrepresentation is not.

## Email ([FTC CAN-SPAM](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business))
Every commercial email needs: accurate From/To/Reply-To and subject; a clear ad identification; your valid postal address (street address, registered PO box or registered
private mailbox); a clear way to opt out; opt-outs honored within 10 business days and workable for 30 days; no selling the addresses of people who opted out. Up to $53,088
per violating email, and hiring a sender does not move the responsibility. Our weekly issue is marked NOT SENDABLE until `[newsletter] postal_address` is set.

## Our own supply chain
- **Cloudflare Clef** (decision model): Apache-2.0 open weights, hosted on Workers AI, $0.24 per million input tokens, counted in the same free neuron pool as images.
- **Google Lyria** (music): the paid Lyria 3 / 3.5 models have no free tier (HTTP 429 on our key, 2026-10-08); the experimental Lyria RealTime works on the free tier,
  is instrumental only and always SynthID-watermarked. AI-generated music needs the YouTube AI label (above).
- **Pixabay Content License** (the 19 bundled sound effects in the media-use skill): commercial use without attribution; redistributing the files on their own is not
  allowed, so they are never committed here.
- **Gemini API**: no free tier for Lyria 3.x; Lyria RealTime and embeddings work on the free tier today (see `gemini-pricing` in the watchlist).
- **Muapi** (image and video supply): pay-as-you-go wallet, prices from the public catalog (`muapi-pricing` in the watchlist). The terms for commercial use of output from
  its hosted models (FLUX.2 klein 4B is Apache-2.0 upstream; Seedance is ByteDance's model) were *not read*: check them before any stock-marketplace upload or before
  turning hook clips on. Generated clips and stills still carry the YouTube AI label and our own disclosure.
