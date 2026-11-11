# Income rails by distance to cash (2026-11-11)

Written by `python -m faceless money` from the engine's state. No projection is printed: 'first dollar' is unknown until a rail has a receipt in `state/receipts.jsonl` or `analytics/sales.jsonl`. Views, clicks and replies are not income.

| rail | artifact | blocker | owner action | first dollar | kill rule |
|---|---|---|---|---|---|
| 1. Paid products on Gumroad | channel/shop/*/gumroad/, studio.toml [offer] shop_urls | 4 listings live; not listed: rat-race-escape-planner; traffic to them is the open question | say the price for rat-race-escape-planner | unknown: no receipt on this rail yet | zero sales after 200 listing views, or refunds above 10% (PLAN.md) |
| 2. Warm DM > free checklist > list | outbound/drafts/, state/outbound.jsonl, the hub page | no email form on the hub: the checklist is given without an address; 0 DMs sent so far | send today's DMs by hand; pick an email service | unknown: a list earns only through a later product sale | no reply in 30 personal sends, or under 1 signup per 1,000 views after 60 days |
| 3. Fiverr brand-kit gig | channel/services/brand-kit/GIG.md, gallery/, samples/ | the gig is not published on Fiverr (owner's account) | create the gig and paste GIG.md | unknown: no receipt on this rail yet | fewer than 1 order in 30 days of an active gig (PLAN.md) |
| 4. Affiliates | channel/monetization.md (programs named, none joined) | no affiliate program joined and no link exists; [channel] has_affiliate_links stays false until one does | name one tool you actually use and can recommend honestly; join its program | unknown: no receipt on this rail yet | no click in 60 days after the first link is on the hub |
| 5. Etsy printables | channel/shop/money-reset-printables/etsy/, CHECKLIST.md | no Etsy listing; the rail is not connected | follow CHECKLIST.md by hand (about 15 minutes) or connect the Etsy rail | unknown: no receipt on this rail yet | rejected twice for the same reason, or zero sales after 200 views |
| 6. Email: 7-day sequence and weekly issue | channel/offers/autoresponder/, `python -m faceless kit --issue` | no email service, no form address, no postal address: the issue is marked NOT SENDABLE | pick the service; give a postal address | unknown: email earns only through a product sale | under 1 signup per 1,000 views after 60 days (PLAN.md) |
