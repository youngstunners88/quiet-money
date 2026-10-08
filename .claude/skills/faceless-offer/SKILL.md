---
name: faceless-offer
description: Give every Quiet Money short exactly one offer (free checklist or a live product), a pinned-comment line, a caption call to action and a tracked link, then log it so analytics can see money instead of views. Never posts, never creates a product, never makes income claims. Use at the end of the daily run, when the user says "offer this", "pin the CTA", "utm this", "link in bio", or asks why videos get views but no list signups or sales.
---

# Faceless offer

One video, one offer, one line to pin. Production without a call to action is a dead post.

## What the platforms allow (why the offer is "link in bio")
Short-video captions and comments are not tappable. TikTok and Instagram make only the profile link tappable; YouTube turned links in Shorts
descriptions and comments into plain text in 2023. So the offer is the words "link in bio", and the bio link of every platform is ONE page on our
own site, `/links/` (the hub). Details and sources: `references/link-rules.md`. Per-video links still matter where a link IS tappable
(thread, LinkedIn post, pin, newsletter, a long video's description), and every one of those carries the video id.

## What the code does (`faceless/offer.py`, no model calls)
- `package.run` picks the offer while it packages: the caption gets its call to action before the hashtags, the description gets one tracked link,
  `meta.json` records the offer, and the gauntlet has a soft `offer_cta` gate. After publishing, `OFFER.md` lands beside `POST.md` and one row is
  appended to `state/offers.jsonl` (status `draft`).
- Which offer: the free 7-day Money Reset checklist builds the list and leads. A paid product is chosen only after two free ones, only when its live
  listing URL is in `studio.toml [offer] shop_urls`, only for a series that has a matching product (`[offer.match]`), and never the same product twice
  running. "Do This Today" is always the free checklist. With no live listing, every video gets the free checklist.
- The claim check refuses guarantees, income promises, specific returns, "risk-free", debt-relief promises, buy calls and "financial advice" that is
  not "not financial advice". An owner edit in `[offer.copy]` that fails it falls back to the built-in line and says so in the notes.

## Steps in a routine run
1. After `python -m faceless daily`, run `python -m faceless offer --batch today`. It is a net under the packaging step: idempotent, it repairs a pack made
   before the offer layer existed (caption, description, POST.md) and writes any missing `OFFER.md` and ledger row. Exit 1 means a video has no usable offer:
   read the problems it prints and fix the cause (usually `[site] base_url` empty, which prints `LINK_MISSING`).
2. `python -m faceless offer` shows coverage, the mix, which paid products are live, and the three profile links.
3. Put the counts in the report: videos with an offer, free versus paid, and how many still wait for the owner to pin.
4. Commit `state/offers.jsonl` and the `OFFER.md` / `POST.md` / `meta.json` text files with the rest of `state/` and `distribution/queue/`.

## What only the owner does
- Pins the comment from `OFFER.md` on each platform, then says so: `python -m faceless offer mark VIDEO pinned`.
- Puts the profile link (from `python -m faceless offer`) in each platform's link field once. TikTok's field may need a business account or follower count;
  check the Edit profile screen (the sources disagree: `references/link-rules.md`).
- Lists a product, then adds its URL to `[offer] shop_urls` in a commit that says so. Until then no paid offer exists.
- Picks an email service and pastes its public form address into `[newsletter] form_action`; the hub and the checklist page then show the signup form.
- Chooses a visit counter and saves its tag as the file named in `[site] head_snippet` (a cookieless one needs no banner).

## Hard rules
- One offer per video; the description carries exactly one link. A second URL is a failed run.
- Never post, schedule or call a publishing provider from here. Never create a Gumroad or Etsy product, never change a price.
- Never invent a URL: no `[site] base_url` means `LINK_MISSING` and no offer is written.
- Never put an income figure, a result or a guarantee in a call to action. Numbers that appear in a passed script may be quoted as "example" only.
- Affiliate links stay out of the pinned comment and the hub unless the affiliate disclosure is on (`channel.has_affiliate_links`).

## Troubleshooting
- `offer:coverage` WARN in preflight or "videos shipped without an offer" from the watchdog: run `python -m faceless offer --batch <day>`.
- `LINK_MISSING`: set `[site] base_url` in studio.toml.
- A pinned comment over 150 characters: shorten the product name in `channel/shop/catalog.json` or the copy in `[offer.copy]`.
- `offer check "text"` runs the claim check on any copy before it is used.
