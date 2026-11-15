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

## 7. 2026-11-14: resumed on the owner's machine (herdr, Hermes, desktop app)

This is the first session that ran on the real computer, so the "not proven" items above were re-checked here.

- **herdr is real and the path works.** herdr 0.9.1 at `/usr/bin/herdr`; `herdr server` was started headless and `herdr api snapshot`
  answered. `scripts/qm-command-center.sh start` created the `qm-cc` workspace (w1), ran the server in pane `w1:p1`, and `status` returned
  `up: http://192.168.0.5:8787/`. `scripts/qm-hermes-workspace.sh start` created `qm-hermes` (w2) and `herdr agent list` reports
  `agent: hermes, agent_status: idle` in pane `w2:p1`.
- **Hermes is included.** New tab **Hermes** (`faceless/hermes.py`): installed version, channel, update-available flag, gateway state,
  desktop-app presence, `hermes://` launch link and copyable `hermes chat`, plus the newest 8 session labels/models/counts read from
  `~/.hermes/state.db` **read-only**. Session message content is never selected or rendered. `overview.build()["hermes"]` feeds it.
- **The page no longer depends on the system Python.** The renderer needs Pillow for its icons; `scripts/qm-command-center.sh` now prefers
  `$ROOT/.venv/bin/python`, which fixed `ModuleNotFoundError: No module named 'PIL'` and made `start` answer health checks.
- **It is an app on this machine.** `~/.local/share/applications/qm-command-center.desktop` → `scripts/qm-command-center-app.sh`, which starts
  the server if needed and opens the signed-in URL from `scripts/qm-command-center.sh url`.
- Tests: 27 pass (`tests/test_command_center.py`), including two new Hermes tests that assert absent ≠ zero and that message content never
  reaches the projection. Screenshot of the Hermes tab at 390×844: `/tmp/opencode/qm-hermes.png` (session artifact, not committed).
- **Grok's build** (`~/Downloads/money-command-center.zip`) is still the mock-data Next.js skeleton (`src/data/mock.ts`). It is not the
  shipped app and nothing depends on it; this repo's shape B is the live command center.
- Still needs the owner's devices: a real phone on Wi-Fi with the cable out, Tailscale, and iOS Safari. Those cannot be proven here.

## 8. 2026-11-14 (later): the app shell, scrolling, Agents and Models

The first pass still felt like a phone page in a browser, so this pass changed the shell and added the two tabs that were missing.

- **Desktop app window.** `scripts/qm-command-center-app.sh` now opens a dedicated Chromium app window (`--app=$URL`, `--class=qm-cc`, its
  own profile in `~/.config/qm-command-center/chromium`) instead of a browser tab; `xdg-open` is the fallback. The `.desktop` entry uses it.
- **Desktop layout.** At `min-width:900px` the bottom tab bar becomes a 224px left sidebar, `main` grows to 1180px and the KPI grid to four
  columns. Below that the phone layout is unchanged. Verified at 1280×900: sidebar 224px, content 1041px, `scrollTo(500)` moved to 500.
- **Scroll fix.** Removed `overscroll-behavior-y:contain`; added explicit `overflow-y:scroll` on `html`, `overflow-y:visible` on `body`,
  `-webkit-overflow-scrolling:touch`, a sideways-scrollable tab bar, and no fixed-height shell. Verified at 390×844 and 1280×900:
  `scrollHeight` 3342/2963 vs viewport 844/757, and `scrollTo(700/500)` reached 700/500.
- **Agents tab** (`faceless/agents.py`): herdr workspaces, panes and live agent states from `herdr api snapshot`; installed Claude Code
  (2.1.322), Codex (0.161.0), OpenCode (2.0.29), Hermes (0.21.6), Gemini CLI (0.68.0) and Ollama (0.40.3) with version, default model and
  copyable launch command. The former Hermes tab is folded in here: gateway state, desktop link and the newest session labels/counts,
  still read-only and still without message content.
- **Models tab** (`faceless/models.py`): each agent's configured default (`sonnet`, `gpt-6.1-sol`, Hermes `nvidia/nemotron-3-ultra-550b-a55b:free`),
  local Ollama models (none pulled), and the OpenCode catalog summary (235 providers, 8,967 models). Full searchable catalog is
  `/models.json` (~565 KB), token-gated and fetched only when the tab opens; `overview.json` stays ~33 KB.
- Tests: 28 pass, including `/models.json` 401 without the token, 200 with it, and a non-empty provider list. Browser checks were run with
  ChromeDriver at both viewports (screenshots under `/tmp/opencode/`), not committed.

## 9. Income rails today

See `channel/empire/INCOME-RAILS.md` (regenerated by `python -m faceless money`) and today's brief in `outbound/brief/`. No rail has a
receipt. Checked on 2026-11-11:
- the hub page is live and lists the free checklist and the four products, but has **no email form** (`[newsletter] form_action` is empty), so it collects no address
- the last recorded site measurement (`analytics/site.jsonl`, 2026-10-23) shows 0 pageviews and 0 shop clicks; no newer pull exists, so there is no click count to report
- the Fiverr brand-kit gig copy and samples exist in `channel/services/brand-kit/`; the gig is not published
- no affiliate link exists; none was added
- the Etsy pack for the printables is built; nothing is published; the Etsy rail is not connected
- the email sequence is written; no email service is connected, so it is not live and no issue can be sent

## 10. Control surface (2026-11-14)

The page was a viewer; it now acts. Full reference: `artifacts/command-center/README.md`.

- **The dead clicks had one cause.** The page's element helper was rewritten to take `oninput`/`onchange`, and the `on:` shorthand every
  tab button and copy button uses stopped being bound to `click`. Fixed in `faceless/dashboard.py`; a test now asserts the binding.
- **Action desk.** `faceless/actions.py`: an allowlist of names, each one existing command, run without a shell with a timeout, one per
  lane. Each click is one `CC_ACTION` line in `state/journal.jsonl`; nothing else is stored. `faceless/serve.py` gained `POST /action`
  (header token, JSON body, same origin), `GET /actions.json` and `GET /job.json?id=`.
- **Engine verbs added for the buttons.** `python -m faceless retry <job_id>` (a failed, held or unfinished video job again; packages,
  never uploads), `python -m faceless phone requeue <id>` (a held phone job back to the queue when its gate is open) and
  `python -m faceless phone park` (hold queued jobs whose media is gone from the media branch and this disk, with the reason).
- **Non-stop.** A toggle on Today, off by default. The decision is `actions.plan_tick`; the loop is the open page, so there is no daemon.
- **Projection.** `overview.py` gained the phone lane (next job, adb device, held, blocked, media missing), open DM drafts from earlier
  days (they were invisible once their day passed), targets read from `studio.toml` only, the activity list, and alerts in the owner's
  order with the action that answers each.
- **Checked on the real page** (headless Chromium, desktop and 390 px): tabs switch, View steps loads a job's history, Release on a
  gate-blocked phone job is refused with the reason, Park held 35 TikTok jobs whose videos were gone, Advance phone handed out the next
  job, Non-stop reported `waiting` for it.
- **Found while doing it.** 35 of the 38 queued TikTok jobs (2026-10-25 to 2026-11-06) had no video on `phone-media` (it keeps three
  days) and none on this disk, with the oldest at the head of the queue, so `phone next --push` could only fail. They are now held with
  that reason. Posting them needs the machine that has the renders to stage them again, then Release.
- Tests: `python -m pytest -q tests/test_command_center.py`.

## 11. Mission control (2026-11-15)

- `crew.toml` is the roster; `faceless/missions.py` derives the to-do list from the overview, routes each mission (engine first, then the
  cheapest installed agent that lists the job), dispatches through herdr and reads reports from `CC_MISSION` journal lines. No store.
- `python -m faceless crew board|plan|dispatch|report|ask`. The Mission tab is the page's first tab; Autopilot is its toggle.
- Proven live: a test mission was sent to Hermes, which could not answer (OpenRouter rejects its key, HTTP 401), was benched, and the
  mission went to a freshly started OpenCode pane, which reported `done` on the board.
- Autopilot's first live tick started today's batch (`daily --no-publish`).

## 12. Prospect machine and toolbox (2026-11-15)

- `faceless/prospects.py`: people who wrote under our videos (drop folder fed by `prospect add`, YouTube comments when Composio is
  connected) are sorted in code and handed to the DM desk as its prospect list. 0 tokens, never contacts anyone, one batch a day.
  Board cards: `prospect-<day>` (engine) and `harvest-comments-<day>` (phone agent reads the TikTok inbox).
- `faceless/toolbox.py`: offline search over the Awesome REA catalog (1,166 tools, 4,025 case studies at sync time).
- Autopilot gained `max_cost` (default 1): the timer never starts a paid agent.
- Not yet proven live: no real comment has gone through the machine. This machine has no `COMPOSIO_API_KEY`, so the YouTube source
  reports unavailable, and the phone was busy with another session, so the harvest mission has not run.
- Found while testing: the OpenRouter account is out of credit (paid models answer 402) and the free Gemma model was rate-limited
  (429). Two more free models were added to `[llm] openrouter_models`; they answered.
