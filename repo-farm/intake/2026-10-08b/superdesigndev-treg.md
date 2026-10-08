# Intake: superdesigndev/treg

- **Source:** https://github.com/superdesigndev/treg
- **Looked at:** 2026-10-08 16:53 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | Apache-2.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `pipe-to-shell`:** tells you to pipe a download into a shell
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: STRIPE_KEY, TREG_ADMIN_TOKEN, TREG_RESEND_API_KEY, TREG_SECRET_KEY, TREG_SESSION_SECRET

## Commands its docs tell you to run (read, do not run)

```
curl -fsSL https://treg.to/install.sh | sh
npx skills add superdesigndev/treg                        # every public skill
npx skills add superdesigndev/treg --skill lead-signals   # just one
uv sync                        # create the venv from uv.lock (pulls the server deps for dev)
uv run python -m treg upgrade  # prepare schema + run idempotent release tasks without serving
uv run python -m treg          # serve on 0.0.0.0:18790 (add --reload for dev)
uv run python -m treg keygen   # print a fresh Fernet key for TREG_SECRET_KEY
uv run --with pytest-xdist pytest -n auto -q   # daily local default (same shape as CI)
uv run --frozen python -m pytest -q            # serial: debugging one test, or order
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Treg (OpenRouter for Tools)

![treg — the tool catalog for your agent](docs/assets/treg-hero.png)

**OpenRouter, but for agent tools instead of models.** Point an agent at one base URL with one token
and it can do the job: **a curated catalog of thousands of endpoints across many providers** — SEO and backlinks,
social and trends, people and company enrichment, ads, scraping, image and video generation —
**priced per call, from a cent**,
with no provider signup. Plus your own team's keys, skills and CLIs, callable by every teammate's
agent without the credential ever leaving the server.

**Ask for the task, not the tool.** You do not need to know which vendor sells backlink data, or to
hold an account with them. Search for what you want to do, read the price, call it.

Built for the Superdesign team, live at [treg.to](https://treg.to) — anyone can self-host.

## Why it exists

The tools an agent needs for real work sit behind subscriptions nobody buys for a single run —
Semrush $139/mo, Moz $99/mo, Crunchbase $99/mo, Apollo $59/seat — behind signup walls, or behind no
public API at all (invite-only, partner-only, app-review-only). treg carries those accounts and
bills fractions of a cent per call.

## Two kinds of tool, one token

- **The catalog** — external endpoints treg can serve with its own key or through a verified public
  route that needs no provider key. Own-key cal
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: ideate.

A hosted per-call tool gateway ('OpenRouter for agent tools', Apache-2.0, self-hostable) whose lead-signals skill finds B2B buyers by hiring, funding, tech-stack and job-change signals and then looks up their emails and phones. Wrong audience for a consumer money channel, and contact lookup is the one thing we would not run. The data we do need (what people search, what is trending, page text) already comes from TokConnect, Exa, TinyFish and the Muapi desk at known prices. The gateway would add a prepaid balance and a bearer token held by a third party, an installer that pipes a download into a shell (HIGH), and vendor-only numbers (4,710 signals for $0.52; 78.2% against 43% on a benchmark it ran itself).

**Worth taking:** The pattern: describe the signal in one sentence, put it on a schedule, report only what is new (the weekly scout already does this for topics), and show the price before the call (the Muapi desk already does this).

**Only the owner can:** Nothing now. If backlink or SERP data is wanted later, trial it in a sandbox copy with a $5 prepaid balance and a spend cap, never with a production token.
