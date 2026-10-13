---
name: faceless-product-structure
description: Decide and build how Quiet Money's products are packaged for sale: separate listings or a bundle, which parts overlap, what to price and test first, and how a bundle is added to the catalog and listing pack. Use when asked whether to sell two products or one bundle, to add a bundle, to change which products sit together, or to plan the storefront.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/listing.py
---

# Product structure

## Where things stand (decided 2026-10-12, `channel/empire/decisions/2026-10-12-daily-debt-bundle.md`)
Separate listings: Daily Quiet Money Planner ($17 test), Debt Payoff & Compound Interest Planner ($19), Rat Race Escape Planner ($19), Money Reset Printables ($9). One bundle: Money Reset Kit ($28 test; Rat Race + Debt + Printables, $47 apart). **No Daily + Debt bundle yet.** The Daily Planner's after-purchase message points at the Debt spreadsheet (no URL until it is live).

## Rules
1. **Overlap first.** Before any new bundle, list which parts are already inside another bundle (the Debt planner is inside the Kit). A second bundle with the same part cannibalises the first.
2. **Parts are listed apart before a bundle's discount is advertised** (studio rule in the Kit listing). Price the bundle from the start with that in mind.
3. **One structure change per test.** Test price first (about 20 views per step, studio rule), then structure.
4. **Evidence before listings.** The shop has no sales or reviews yet; every extra listing costs Etsy fees and attention. Add a bundle only on a trigger: buyers of one buy or ask for the other, or a price test shows the bundle converts clearly better.
5. **Decide with a panel** (skill `faceless-panel`) and record it; the owner approves prices, copy and accounts (rule 9).
6. Etsy: at most 5 files per listing, each 20 MB or less. The Daily Planner's two PDFs are about 17 MB each, so a bundle with them has room for 3 more files, not for a larger PDF. Gumroad has no such limit.
7. No income claims, no invented scarcity or reviews, no invented URLs (rule 13): a cross-sell link is added only when the owner has a live product URL (then `[offer] shop_urls`).

## Adding a bundle
1. Add the bundle to `channel/shop/catalog.json` with `kind: "bundle"`, `parts` (product ids), `parts_detail` (label and lines per part), price and test range, copy for both shops (see `money-reset-kit`).
2. The zip is assembled from the committed parts (`faceless/product_print.py` `assemble_kit`); a new bundle needs its own assemble function and its own pictures (`listing._bundle_images` is written for the Kit's three parts: generalise it before a second bundle).
3. `python -m faceless listing build <bundle-id>` then `python -m faceless listing check`: every hard gate passes; read the report.
4. `python -m faceless ci`.
5. Update the decision file with the trigger that caused the change and the panel's new vote.

## Troubleshooting
- **Listing gate says the discount claim is unverified:** list the parts separately first, or remove the claim.
- **Etsy rejects a file:** over 20 MB or an unsupported type; split the bundle into zip parts under the limit.
