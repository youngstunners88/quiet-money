---
name: faceless-ship
description: Ship a finished product to Gumroad and Etsy with the quiet-shop MCP server or `python -m faceless shop|etsy`: check the rails, connect Etsy once, create unpublished drafts, and go live only when the owner's approval of the current price is in studio.toml. Use when the owner says ship, list, publish, put it on Etsy or Gumroad, connect the shop, or asks what is left before it can sell.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/shop.py, faceless/etsy.py, faceless/shop_mcp.py
---

# Ship a product (drafts freely, live only with the owner's yes)

Tools (MCP `quiet-shop`, registered in `.mcp.json`): `shop_status`, `shop_plan`, `shop_draft`, `shop_publish`, `etsy_auth_url`, `etsy_auth_finish`, `shop_sales`. Without the tools use `python -m faceless shop status|plan|draft|publish` and `python -m faceless etsy status|auth|plan|draft`.

## The path
1. `shop_status`: each rail says ready or the owner's exact next step. Never guess a credential; never print one.
2. **Gumroad**: needs `GUMROAD_ACCESS_TOKEN` in the environment (Gumroad > Settings > Advanced > Applications) and the `gumroad` CLI. Install the CLI only from a reviewed release tag. Reading sales needs the Composio connect.
3. **Etsy**: needs `ETSY_API_KEY` (the keystring of the owner's app at etsy.com/developers/your-apps, redirect `https://localhost/callback`), then a one-time login: `etsy_auth_url`, the owner opens it signed in to the shop, then `etsy_auth_finish` with the `code` from the address bar. Tokens are saved under `~/.config/quiet-money/` (mode 600), never in the repo. A fresh cloud session starts without them: the owner redoes the login or sets `ETSY_REFRESH_TOKEN`.
4. `shop_plan` shows the exact listing. `shop_draft` makes unpublished drafts on every ready rail (files, images, video, copy); it skips a title that already exists and reports a rail that is not ready instead of hiding it. Drafts are free and reversible.
5. **Going live is the owner's yes (rule 9).** `shop_publish` refuses unless studio.toml has `[shop.approved."<product>"]` with `price` equal to the catalog price and the rail set to true, the listing gauntlet passes, and the studio is not paused. A price change cancels an old approval. Write that entry only when the owner has said the price and told you to go live, and quote their message in the commit. Never set the price yourself: the catalog price is a placeholder until the owner settles it.
6. After a live URL exists, add it to `[offer] shop_urls` (slug from the catalog). Never invent a URL (rule 13).

## Things a person still does
Etsy's AI-disclosure or creativity question on the listing form, if it asks one; Etsy charges a $0.20 listing fee when a listing goes live; billing and payout setup on both shops.

## Failure modes
- `Etsy refused the refresh token`: the owner runs the login again.
- `N Etsy categories are called Planners`: set `[etsy] taxonomy_id`.
- A PDF over 20 MB is refused by Etsy; lower image quality in the planner build, do not split the product without the owner.
- The Etsy rail was written to Etsy's documentation and has not yet run against the live API: treat the first real draft as a test and read what it created.
