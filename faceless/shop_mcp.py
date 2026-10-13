"""quiet-shop: a small MCP server (stdio) that lets an agent ship a product to Gumroad and Etsy with the studio's rules built in.

    python -m faceless.shop_mcp

Tools:
  shop_status       each rail: ready or the exact next step for the owner (never the key)
  shop_plan         what would be created for a product (no network, no cost)
  shop_draft        create DRAFTS on Gumroad and Etsy: unpublished, reversible, free; skips a listing that already exists
  shop_publish      set a draft live on one rail. Refused unless the owner's approval for this product's CURRENT price is in studio.toml [shop.approved]
  etsy_auth_url     the one-time login link for the owner's Etsy shop
  etsy_auth_finish  exchange the code Etsy gives after that login
  shop_sales        pull recent Gumroad sales into analytics/sales.jsonl
`state/PAUSE` stops every tool that spends or publishes. Credentials come from the environment and are never returned.
"""

from __future__ import annotations

from faceless import etsy, listing, shop
from faceless.mcp_stdio import Server, schema

RAILS = ["gumroad", "etsy"]


def t_status(_a: dict) -> dict:
    from faceless import safety
    return {"rails": shop.status(), "paused": safety.paused(), "products": [{"id": p["id"], "price": p["price"], "approved": {r: shop.approval(p["id"], r)[0] for r in RAILS}}
                                                                              for p in listing.products()]}


def t_plan(a: dict) -> dict:
    pid = a["product"]
    out = {"gumroad": shop.push(pid, run=False), "etsy": etsy.plan(pid)}
    out["live"] = {r: shop.approval(pid, r)[1] or "approved" for r in RAILS}
    return out


def t_draft(a: dict) -> dict:
    rails = tuple(a.get("rails") or RAILS)
    return {"results": shop.draft_all(a["product"], rails), "note": "drafts only: nothing is public until shop_publish, which needs the owner's approval"}


def t_publish(a: dict) -> dict:
    return shop.publish(a["product"], a["rail"], a.get("listing_id"))


def t_auth_url(_a: dict) -> dict:
    return {"open_this_signed_in_to_the_shop": etsy.auth_url(), "then": "Etsy sends the browser to the redirect address with ?code=...: pass that code to etsy_auth_finish"}


def t_auth_finish(a: dict) -> dict:
    return etsy.finish_auth(a["code"], a.get("state"))


def t_sales(a: dict) -> dict:
    fresh = shop.sales(int(a.get("days", 30)))
    return {"new_sales": len(fresh)}


TOOLS = {
    "shop_status": (t_status, "Every storefront rail: ready or the owner's exact next step; which products the owner has approved to go live.", schema({})),
    "shop_plan": (t_plan, "What would be created on Gumroad and Etsy for a product (no network, no cost) and whether it may go live.",
                  schema({"product": {"type": "string", "description": "catalog id, e.g. daily-quiet-money-planner"}}, ["product"])),
    "shop_draft": (t_draft, "Create unpublished DRAFT listings on Gumroad and Etsy from the built pack (files, cover, images, video, copy). Reversible; skips what already exists.",
                   schema({"product": {"type": "string"}, "rails": {"type": "array", "items": {"type": "string", "enum": RAILS}}}, ["product"])),
    "shop_publish": (t_publish, "Set a draft live on one rail. Refused unless studio.toml [shop.approved.<product>] names the product's current price and the rail; Etsy charges its listing fee.",
                     schema({"product": {"type": "string"}, "rail": {"type": "string", "enum": RAILS}, "listing_id": {"type": "string"}}, ["product", "rail"])),
    "etsy_auth_url": (t_auth_url, "Start the one-time Etsy login (PKCE): returns the link the owner opens while signed in to the shop. Needs ETSY_API_KEY.", schema({})),
    "etsy_auth_finish": (t_auth_finish, "Finish the Etsy login with the code from the redirect address; saves the tokens outside the repository.",
                         schema({"code": {"type": "string"}, "state": {"type": "string"}}, ["code"])),
    "shop_sales": (t_sales, "Pull recent Gumroad sales (needs the Composio connection) into analytics/sales.jsonl.", schema({"days": {"type": "integer"}})),
}

SERVER = Server("quiet-shop", "0.1.0", TOOLS)
handle, call, serve = SERVER.handle, SERVER.call, SERVER.serve

if __name__ == "__main__":
    serve()
