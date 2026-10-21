# Quiet Money product suite: five adjacent products and a 4-SKU line

DRAFT for the owner, written 2026-10-20 (sprint 01, lane A). Everything below is a proposal. Nothing is built, listed or priced by this file; the owner approves every product, price and listing (CLAUDE.md rule 9). No product here is for sale until it is built and approved ("never sell what is not built", `brain/PROMPTS/ORCHESTRATOR.md` section 2). No ad spend is assumed anywhere.

Labels: figures from a repo file carry the file. **U** = unverified outside figure (one creator's claim or a number I could not check). Prices are the owner's decision.

## 1. What already exists (so nothing is duplicated)

From `channel/shop/catalog.json` (the five products):

| id | Name | Kind | Price in catalog | What it does |
|---|---|---|---|---|
| `rat-race-escape-planner` | Rat Race Escape Planner | spreadsheet | $19 | Freedom number and the date it arrives; income streams tagged Active, Passive or Asset; Rule of 100 volume math; 40-year projection; 13-week log |
| `debt-payoff-planner` | Debt Payoff & Compound Interest Planner | spreadsheet | $19 | Up to eight debts, avalanche or snowball, debt-free month, compound growth table, pay-the-debt-or-invest check |
| `money-reset-printables` | Money Reset Printables | printable (6 pages) | $9 | Paper pages for the paycheck split, a subscription audit, bills that are not monthly, debts on one page and net worth (the five features named in the catalog; the pack has six pages) |
| `daily-quiet-money-planner` | The Quiet Money Daily Planner | printable (427 pages) | $17 | One picture, one lesson, one action a day; weekly check-in; 52 wellness pages |
| `money-reset-kit` | Money Reset Kit | bundle | $28 | The two spreadsheets plus the six printable pages |

Also checked, from `channel/empire/RANKING.md` (not products in the catalog, but opportunities someone may build): P5 typography posters (idea), P6 fillable PDF versions of the printable pack (vetted), C4 audio edition of the Shorts and a weekly podcast (a content rail, free), A1 newsletter (free). From `channel/empire/MARKETING.md` section 3: the owner has approved only the planner at $17; the Debt planner at $19 and the Printables at $9 have no owner approval yet, and a Daily + Debt bundle is not built before about 25 sales.

Rules these proposals respect: no cloning of a competitor's product or listing (`brain/topics/never.md`, rule "Copying a competitor's product"); nothing that reads as an income promise (Gumroad's prohibited list names quick-riches schemes and credit repair, `MARKETING.md` section 2); education, never advice (`channel/products/daily-quiet-money-planner/CONTEXT.md` rule 2).

## 2. Price reasoning (shared by all five)

- **Fee formula.** On a direct US card sale Gumroad takes 12.9% plus $0.80 (`MARKETING.md` section 0; sourced there as gum:F01). That is arithmetic I applied to each price below. It matches the net figures already in the plan: $9 gives $7.04, $14 gives $11.39, $17 gives $14.01, $19 gives $15.75 (`MARKETING.md` section 3). The ones that are not in the plan I computed the same way: $12 gives $9.65.
- **Market bands.** The plan's competitive map says Etsy volume sellers sell spreadsheets at about $1 to $13 (`MARKETING.md` section 2, sourced there as win:f1 to f3) and the nearest quiet planner rival sells 24 pages at $14.99 (win:f9). A creator video in the Brain claims a budget spreadsheet at $9.99 (`brain/sources/2026-10-20-mindvori-claude-gumroad-spreadsheet.md`, "In one line" and Tactics; that creator's figure is **U**).
- **Rule I applied.** Spreadsheets sit at $12 to $14, below the $17 planner and the $19 Debt planner, so each product has a clear step on the ladder. A price test is not planned: the plan itself says a price test needs far more conversions than we can produce (`MARKETING.md` section 3, price rules).
- **No anchor prices and no deadlines.** A compare-at price or a ticking timer is fake proof (`brain/topics/never.md`).

## 3. The five adjacent products

### 3.1 Quiet Money Monthly Tracker (spreadsheet, 12 months)

- **What it is.** One spreadsheet with a tab per month plus a year summary: money in, spending by category, the left-over number, saved or invested, debt paid, and the net worth line, with the percent-of-take-home column worked out by formula. It is the spreadsheet form of the free Monthly Money Snapshot page (`channel/offers/lead-magnets/monthly-money-snapshot/CONTENT.md`).
- **Who it is for.** Someone who did the free page for a month and wants the sums done for them across a year.
- **How it differs from the catalog.** The Printables' pages are one-time paper pages. The Debt planner models a plan for debts. The Rat Race planner projects 40 years from one set of numbers. None tracks twelve actual months side by side.
- **Engine module.** `faceless/products.py` (the spreadsheet factory: a `build_*` function, a `verify_*` that recalculates in LibreOffice and compares to independent Python math, a `listing_*` file, and a line in `build_all()`), with category sums from `faceless/moneymath.py` where a formula needs an independent check.
- **Effort.** M: a new workbook with twelve repeated tabs and a summary, plus its verification. The factory pattern already exists for two spreadsheets (`product_debt.py` and the escape planner in `products.py`).
- **Suggested price: $12** (proposal). Net about $9.65 on a direct US card sale (arithmetic on the 12.9% + $0.80 formula). Reasoning: it sits inside the $1 to $13 spreadsheet band (so it is not an outlier on Etsy), one step under the $14 Goal Planner and the $17 planner, and the page it comes from is free, so the paid step has to feel small.
- **Cross-sell line.** "If you want one page a day alongside your monthly sheet, the Quiet Money Daily Planner is 427 printable pages for $17."

### 3.2 Quiet Money Goal Planner (spreadsheet)

- **What it is.** One spreadsheet for goals with a date: an emergency fund, a deposit, a set of sinking funds. For each goal you enter the target, what you have and what you can put in monthly, and an assumed rate if you want one; it shows the months to target and what one extra monthly amount does. It uses the same math as `moneymath.months_to_target` and `moneymath.future_value_monthly`. Starting balances need a new moneymath function (`months_to_target` starts from zero), tested before the workbook uses it.
- **Who it is for.** Someone with a goal one to ten years away who wants to see the date, not 40 years of projections.
- **How it differs.** The Rat Race planner's single target is a freedom number on a 40-year line. The Debt planner is only about owing. The Printables' page for bills that are not monthly is paper and has no calculation. This one is several short goals, all calculated.
- **Engine module.** `faceless/products.py` again, with the date math from `faceless/moneymath.py` (`months_to_target`, `capital_for_income` for a goal stated as monthly income). The planner's own "Goals" lessons are a source of wording, not code.
- **Effort.** M: a goals tab, a summary, and a verify step; smaller than the Debt planner because it has no month-by-month engine tab.
- **Suggested price: $14** (proposal). Net $11.39 on the same formula (it is the same figure the plan already uses for a $14 sale, `MARKETING.md` section 3). Reasoning: the item that does the most calculation of the cheap pair, so it sits one dollar above the Monthly Tracker and under the Debt planner's $19; it stays under the $14.99 nearest-rival price point (win:f9, a printable) while being a different kind of thing.
- **Cross-sell line.** "If one of your goals is paying down debt, the Quiet Money Debt Planner lists up to eight debts and shows a payoff month for the numbers you enter."

### 3.3 Quiet Money Year-End Review (printable, 12 pages)

- **What it is.** A guided looking-back for the end of the year: income and spending by quarter, debt balances at the start and end, net worth at the start and end, the three best money decisions, the three worst, one number to change, and three goals with a first step each. Seasonal: made to be used in December and January.
- **Who it is for.** Someone who wants to start the year with a clear picture on paper and has no 365-day book.
- **How it differs.** The planner has a "Summary and goals" page (`CONTEXT.md`, "What is in the book") and a net worth snapshot with five check-in columns, but only as pages inside a book you buy to use all year. The Printables are tools, not a review. This is a standalone short review that works without any other product. This is the least differentiated of the five (it overlaps with the planner's summary page); I include it because it is cheap to build and seasonal. If the owner thinks the overlap is too close, drop it.
- **Engine module.** `faceless/product_print.py` (the printable pack builder that makes the six Money Reset pages in Letter and A4; the same page-drawing code).
- **Effort.** S: new page layouts in an existing builder; no formulas.
- **Suggested price: $9** (proposal). Net $7.04 (the plan's figure for $9, `MARKETING.md` section 3). Reasoning: the same price as the Printables, because it is the same kind of product (a short set of paper pages); a higher price would need more pages or a stronger reason.
- **Cross-sell line.** "If you want to review a little each day instead of once a year, the Quiet Money Daily Planner has a weekly check-in and a Sunday reset."

### 3.4 Quiet Money Household Money Meeting (printable, 8 pages)

- **What it is.** A kit for two or more people who share money: a one-page agenda for a monthly money meeting, a "who pays for what" page, a shared bills list, a joint goals page, a "what we each want from money" page to do alone first, and a short list of ground rules (for example, no big purchase over an agreed amount without a talk). It is a conversation tool, not a legal or financial document.
- **Who it is for.** Couples, flatmates and families who split costs and have no shared way of talking about it.
- **How it differs.** Everything in the catalog is for one person. This is the only one built for a shared household.
- **Engine module.** `faceless/product_print.py`.
- **Effort.** S to M: more text design than numbers, and every page of advice-like wording needs to pass `offer check` and the planner's education-not-advice rule; the "ground rules" page needs a careful write.
- **Suggested price: $12** (proposal). Net $9.65. Reasoning: eight pages of a new kind of use case, so a bit above the six-page $9 pack and a bit under the planner; the shared-use case is the reason to pay a little more than for the single-person printables. This is a guess; the plan says price is never tested with the traffic we expect, so the owner sets it.
- **Cross-sell line.** "If you are doing this alone first, the Quiet Money Daily Planner starts with a net worth snapshot and one small action a day."

### 3.5 Quiet Money Daily Planner: Audio Companion (52 short listens)

- **What it is.** One short spoken lesson per planner week (52 listens, a couple of minutes each), read from the planner's own Learn and Mindset lessons, so a buyer can listen on a walk and then do the day's page. No new advice; no new facts. Delivered as audio files.
- **Who it is for.** A planner owner who prefers to hear a lesson, or who has less time to read.
- **How it differs.** It only exists for planner owners; it does not stand alone as a product line. It is not the free Shorts or the free weekly podcast in `RANKING.md` C4.
- **Engine module.** `faceless/providers/tts.py` (the neural voiceover the Shorts already use), reading text from `faceless/planner_content.py` `load()`, so the audio can never drift from the book's words.
- **Effort.** L: 52 files to script, produce, check by ear and package; hosting and file size are unresolved (Gumroad file limits for audio were not looked up here, **U**); and the voice needs the same AI disclosure as the Shorts. Build it last.
- **Suggested price: $9** (proposal). Net $7.04. Reasoning: a companion should cost clearly less than the thing it accompanies ($17), and the content is the same text spoken, so the buyer is paying for a format, not new material. Proposal: sell only after the planner has sales, as an add-on, never as a launch item.
- **Cross-sell line.** Not applicable as a cold cross-sell; it is offered on the planner's Welcome page (after a rebuild) and in the after-purchase message ("If you would rather listen than read, the Audio Companion reads each week's lesson aloud.") once it exists.

## 4. Check against the five in the catalog

| New product | Rat Race Escape | Debt Payoff | Money Reset Printables | Daily Planner | Money Reset Kit | Verdict |
|---|---|---|---|---|---|---|
| Monthly Tracker | no (one projection, not twelve months) | no (debts only) | no (one-off pages) | no (lessons, not sums) | no | distinct |
| Goal Planner | partly (both use months-to-target math) but it is a 40-year freedom number vs several short goals | no | no (a paper page for non-monthly bills, no math) | no | no | distinct, closest to the Rat Race planner; the owner should check the wording stays about goals, not retirement |
| Year-End Review | no | no | partly (paper pages) | partly (summary and goals page) | no | distinct but the weakest; seasonal |
| Household Money Meeting | no | no | no | no | no | distinct (shared use) |
| Audio Companion | no | no | no | depends on it (same text) | no | distinct format; not standalone |

Considered and rejected for this list: a fillable-PDF edition of the Printables (RANKING P6: same product, new format; better as an upgrade to an existing product than a new SKU), typography posters (P5: idea stage, needs a print-on-demand account), any product about earning money without working or about side-income amounts (inside the rules the plan sets for the Rat Race series, `MARKETING.md` section 2), any credit-repair product (Gumroad bans it), and anything cloned from a competitor listing.

## 5. The 4-SKU suite

One naming rule: **Quiet Money + a plain word for the job + Planner or Tracker.** The existing catalog names do not follow it (for example, "Debt Payoff & Compound Interest Planner"). Renaming the existing products is the owner's call and a listing change; the table shows the proposed names and the names the catalog has now.

| SKU | Proposed name | Job (one word) | Format | Price | Status |
|---|---|---|---|---|---|
| 1 | **Quiet Money Daily Planner** (now "The Quiet Money Daily Planner") | Learn | Printable, 427 pages, Letter + A4 | $17 (owner-approved on Gumroad, `MARKETING.md` section 3) | Built, live per the brief at https://chrisclassroom4.gumroad.com/l/utwsfs |
| 2 | **Quiet Money Monthly Tracker** (new, 3.1) | Track | Spreadsheet, 12 months | $12 (proposal) | Not built |
| 3 | **Quiet Money Goal Planner** (new, 3.2) | Plan | Spreadsheet | $14 (proposal) | Not built |
| 4 | **Quiet Money Debt Planner** (now "Debt Payoff & Compound Interest Planner") | Pay down | Spreadsheet | $19 (catalog price; no owner approval yet) | Built (`product_debt.py`), not listed |

**The ladder.** Every free step leads to one paid product, the Daily Planner at $17 (SKU 1), the only paid offer in the plan's first 30 days (`MARKETING.md` section 3). SKU 4 is the second ask, offered only after purchase (the after-purchase message already points to it) or when X11 calls for it. SKU 2 and SKU 3 are never offered in front of the planner: a $12 or $14 step placed before a $17 planner gives the same viewer a cheaper way to say yes to something smaller.

**Why these four.** They cover the four things a person does with money in order: learn the basics (1), keep a record (2), set a goal date (3), pay down what they owe (4). Each one has a free page in front of it or a lesson in the planner that points to it (the planner's own after-purchase message already points to the Debt planner for the debt weeks, `catalog.json` `gumroad.after_purchase`).

**Held outside the suite, on purpose.**
- Rat Race Escape Planner ($19): the highest-risk content under the plan's compliance rules (its CTA must be the free checklist only, `MARKETING.md` section 2). Keep it out of the main ladder until the owner decides.
- Money Reset Printables ($9) and Money Reset Kit ($28): the entry item and the bundle. The plan holds the Kit back until its Rat Race content passes the compliance gate and says not to bundle the planner with other products until buyer evidence exists (`MARKETING.md` section 3).
- Year-End Review, Household Money Meeting, Audio Companion: later. Build after the first real sales show which of the four SKUs people ask for. I would not build more than one new product before the planner has its first sales.

**What I would build first, if the owner wants one thing.** Nothing new until the planner has its first sales and X1 has read. If a second ask is needed sooner, it is the Debt planner, which is already built (`product_debt.py`) and is the plan's named second ask (`MARKETING.md` section 3, X11). The Monthly Tracker (3.1) comes after that.

## 6. Where each number comes from

| Number | Source |
|---|---|
| Catalog prices $19, $19, $9, $17, $28 | `channel/shop/catalog.json` `price` for each id |
| $17 owner-approved; Debt and Printables not approved; bundle not before about 25 sales; Kit held back | `channel/empire/MARKETING.md` section 3 |
| 12.9% + $0.80 fee formula | `channel/empire/MARKETING.md` section 0 (sourced there as gum:F01) |
| Net $7.04, $11.39, $14.01, $15.75 | `MARKETING.md` section 3 |
| Net $9.65 on $12 | arithmetic on the same formula: 12 x 0.129 = 1.548, plus 0.80 = 2.348, 12 - 2.348 = 9.652 |
| Etsy spreadsheets at about $1 to $13; nearest rival 24 pages at $14.99 | `MARKETING.md` section 2 (sourced there as win:f1 to f3 and win:f9) |
| 427 pages, Letter + A4 | `catalog.json` `notes`; `CONTEXT.md` |
| Weeks 14 to 16 teach debt payoff and the Debt planner is mentioned after purchase | `catalog.json` `gumroad.after_purchase` |
| A $9.99 budget spreadsheet on Gumroad | `brain/sources/2026-10-20-mindvori-claude-gumroad-spreadsheet.md` (a creator's figure, **U**) |
| Audio file size limits on Gumroad | not checked, **U** |
