# After the planner goes live on Gumroad

1. **URL.** The agent runs `python -m faceless shop publish daily-quiet-money-planner --rail gumroad --yes`, then writes the platform-returned URL into `[offer] shop_urls` in studio.toml. Never type a URL by hand (rule 13). From then the offer rotation can use the planner (paid_every = 3, free checklist first).
2. **Storefront.** The account shows the display name "T Chris" at chrisclassroom4.gumroad.com. Decide whether the storefront should say "Quiet Money" (Gumroad > Settings > Profile). Your call; it is a public change.
3. **Affiliates (D10).** Record the Gumroad global-affiliate setting before the product can reach Discover. Default: decide at Day 30 with data.
4. **Refund policy** on the account page matches the 30-day promise in the listing.
5. **In-app link test.** Open the hub and the product link once from inside the YouTube, TikTok and Instagram apps on your phone; Gumroad's checkout inside an in-app browser is unproven. Tell the agent what breaks.
6. **No self-purchase** to test (Gumroad can suspend for it). The agent reads the first real sale to confirm the `src` tag arrives (experiment X0).
7. **Support.** Gumroad's support email goes to your address; reply within 2 business days; refunds are yours.
8. **Sales read.** `python -m faceless shop sales` runs in the Monday brief and writes `analytics/sales.jsonl` (no buyer details).
