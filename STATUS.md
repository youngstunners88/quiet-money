# Command center and income desk: status (2026-11-11)

Written by the build session of 2026-11-11. Every statement below was checked in that session unless it says "not verified".

## 1. Which checkout is authoritative

**This session could not compare the two checkouts, and did not guess.** It ran in a cloud container with exactly one checkout:

| Checkout | Seen in this session | Branch / commit | Uncommitted work |
|---|---|---|---|
| `/home/user/quiet-money` (cloud container) | yes, worked here | `claude/elegant-hamilton-smccix`, identical to `origin/main` at `69e9fc7` (2026-11-10 09:19 UTC) before this work | none before this work |
| `~/quiet-money` (your computer) | **no: not on this machine** | unknown | unknown |
| `~/Documents/GitHub/quiet-money` (your computer) | **no: not on this machine** | unknown | unknown |

What is known: `origin/main` holds the newest *pushed* state (262 job files, last job day 2026-11-10). Neither local checkout was touched.
To settle it on your computer, run this in each folder and keep the one whose `state/` is newest and has no unpushed work; leave the other alone:

```bash
git -C ~/quiet-money status -sb && git -C ~/quiet-money log -1 --format='%h %ci' && ls ~/quiet-money/state/jobs | tail -1
```

```bash
git -C ~/Documents/GitHub/quiet-money status -sb && git -C ~/Documents/GitHub/quiet-money log -1 --format='%h %ci' && ls ~/Documents/GitHub/quiet-money/state/jobs | tail -1
```

Then `git pull` this work into the authoritative one. The command center reads whichever checkout it is started from and shows that
path, branch and commit at the top of the page, so a wrong checkout is visible, not silent.

## 2. What was read

Read in full: `CLAUDE.md`, `OPERATIONS.md`, `studio.toml` (`[publish]`, `[offer]`, `[offer.match]`, `[safety]`, `[site]`, `[shop]`, `[newsletter]`),
`faceless/CONTEXT.md`, `faceless/state.py`, `faceless/ledger.py`, `faceless/fsutil.py`, `faceless/cash.py`, `faceless/hq.py`, `faceless/safety.py`,
`channel/empire/PLAN.md`, `channel/empire/RANKING.md`, `channel/monetization.md`, `channel/compliance/AUDIT.md`,
`channel/compliance/platform-rules.md`, `channel/shop/catalog.json` (structure and the Rat Race entry), `.gitignore`, `.gitattributes`.
Read in part (the sections this work touches): `faceless/cli.py` (command table, `status`, `cash`, `hq`), `faceless/offer.py` (header, settings, claim
list, function list), `faceless/config.py`, `faceless/marketing.py`, `faceless/shop.py`, `faceless/outbound.py`, `faceless/phone.py`, `faceless/empire.py`.
Counted, not read line by line: `state/jobs/` (262 files), `state/ledger.jsonl` (7,977 rows), `state/offers.jsonl` (117), `analytics/opportunities.jsonl` (18).

**Could not be read, because they are not on the machine this session ran on:** `QMARCHITECTURE.md` (not in the repo either),
`~/Downloads/money-command-center.zip`, `~/.config/herdr/config.toml`, `herdr --help` and its socket metadata (herdr is not installed here),
`~/.config/quiet-money/env`, `~/.config/quiet-money/x-dm-profile`. The herdr commands used in `scripts/qm-command-center.sh` come from
herdr's published documentation (herdr.dev/docs/socket-api, read 2026-11-11), not from a running herdr.

## 3. Where the brief was out of date

- **Offers are not drafts with no listing.** `studio.toml [offer] shop_urls` holds four live Gumroad listings, each fetched on 2026-11-11:
  Daily Planner $17, Money Reset Kit $28, Money Reset Printables $9, Debt Payoff Planner $0+ (free gift). The one built product without a
  listing is the **Rat Race Escape Planner** (catalog test price $19, alternates $12 and $29).
- **The zip was not unpacked**, because it is not reachable from here. Nothing replaced it: the command center was built from the repo's
  own patterns (shape B: one Python projection, one static page, no Node, no React, no mock data anywhere in the shipped path). If you
  want the zip kept as reference, put it in `artifacts/money-command-center/` yourself; nothing in the build depends on it.
- **Revenue is $0.00 from 0 receipts.** No `analytics/sales.jsonl` or `state/receipts.jsonl` exists, and this environment has no Gumroad
  read token, so a sale that happened on Gumroad is not visible here until it is pulled or typed in.

## 4. What was built

| Piece | File | Command |
|---|---|---|
| Projection (real state in, one JSON out) | `faceless/overview.py` | `python -m faceless overview` -> `state/overview.json` (gitignored) |
| Phone page (5 tabs, dark, one column, 64 KB with data) | `faceless/dashboard.py` | `python -m faceless dashboard` -> `site/command-center/` (gitignored) |
| LAN server (token, rate limit, GET only, QR) | `faceless/serve.py`, `faceless/qr.py` | `python -m faceless serve` |
| herdr tab `qm-cc` | `scripts/qm-command-center.sh` | `start`, `stop`, `status`, `open` |
| DM desk | `faceless/dmdesk.py` | `python -m faceless dm`, `dm log`, `dm status` |
| Receipts | `faceless/receipts.py` | `python -m faceless receipts`, `receipts add` |
| Daily money brief and rails table | `faceless/moneybrief.py` | `python -m faceless money` |
| Tests (25) | `tests/test_command_center.py` | `python -m pytest -q tests/test_command_center.py` |

Shape decision: **B**, as the brief recommended. No blocker was found. No npm dependency and no Python dependency were added (the QR
encoder is 150 lines in the repo and is tested by decoding its output).

## 5. Proven in this session, and not

Proven with command output (cloud container, loopback and the container's own network address):
- job counts equal the job files: 262 total; published 150, held 54, failed 32, packaged 19, visualized 4, scripted 2, planned 1
- no token or a wrong token -> 401 for the page and the data; ten wrong tokens -> 429; POST -> 405; the server does not answer on loopback when bound to the LAN address
- `curl -I`: `Cache-Control: no-store`, `X-Robots-Tag: noindex, nofollow, noarchive`, no `Set-Cookie`, the token is not in any header or in the page
- a 390x844 touch browser loads all five tabs with no horizontal scroll, no page error and no external request; the copy button works on plain HTTP
- server killed -> the open page keeps its state and says "Server not reachable. Showing the last known state from ..."
- the script's `start`, `status`, `stop` in its fallback mode (background process)
- screenshots: `artifacts/command-center/review/`

**Not proven, because it needs your devices:**
- a real phone on your Wi-Fi with the cable unplugged (nothing here can stand in for it)
- Tailscale (not installed in the container; the instructions are in `OPERATIONS.md`, "Command center", and are not enabled)
- the herdr path of the script (no herdr here); it checks each verb against `herdr --help` before using it and otherwise falls back
- iOS Safari itself (the test browser was Chromium with a phone viewport)
- cold reopen with the server down over plain HTTP does **not** work in any browser (no service worker without HTTPS); it works over Tailscale HTTPS

## 6. Defaults taken where you were not asked

1. **DM account:** drafts only. No browser profile was read, and none will be without your yes. Tell me the handle and whether `~/.config/quiet-money/x-dm-profile` is the one to use.
2. **Tailscale:** LAN only for now; the Tailscale steps are written, not enabled.
3. **Rat Race Escape Planner price:** $19 assumed as the first test ($12 and $29 as alternates). Nothing was listed and no price was set; it waits for your line.

## 7. Income rails today

See `channel/empire/INCOME-RAILS.md` (regenerated by `python -m faceless money`) and today's brief in `outbound/brief/`. No rail has a
receipt. Checked on 2026-11-11:
- the hub page is live and lists the free checklist and the four products, but has **no email form** (`[newsletter] form_action` is empty), so it collects no address
- the last recorded site measurement (`analytics/site.jsonl`, 2026-10-23) shows 0 pageviews and 0 shop clicks; no newer pull exists, so there is no click count to report
- the Fiverr brand-kit gig copy and samples exist in `channel/services/brand-kit/`; the gig is not published
- no affiliate link exists; none was added
- the Etsy pack for the printables is built; nothing is published; the Etsy rail is not connected
- the email sequence is written; no email service is connected, so it is not live and no issue can be sent
