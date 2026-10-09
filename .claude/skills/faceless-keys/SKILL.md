---
name: faceless-keys
description: Check which API key of each service in the environment actually works and what is left on it, then pick the right variable and the right tool for a job. The environment holds several keys for some services (spares, restricted keys, keys of other projects), so the name alone does not say which is live. Use before relying on a key, when a provider call fails with 401 or 403, when a balance or quota matters, at the start of a weekly review, or when the owner asks what tools the studio can operate.
---

# Keys and tools

`python -m faceless keys` asks every service one free, read-only question per variable (who am I, what is my balance) and prints
`service  VARIABLE  state  fact`. `python -m faceless keys muapi` checks one service; `--json` is for scripts. Nothing is spent, nothing is
written, and a key's value is never printed. States: `works`, `rejected` (bad or expired), `no credit`, `forbidden` (valid but this key lacks the permission),
`unreachable`, `not set`.

## How to use it
1. Run it before a task that depends on a service, and at the start of the weekly scout. A `works` variable is the one to read; the first `works` per
   service is what `keys.best()` returns.
2. A key that is `works` for one question can still be `forbidden` for another (a restricted ElevenLabs key lists models but refuses the account page).
   Treat `works` as "this key is live", not "it can do everything".
3. Report dead keys and low balances to the owner in the daily or weekly report: name the variable and the dashboard, never the value.
4. Never try a variable against a service it does not belong to, and never print, write or commit a value. Keys live in the environment.
5. A balance is the owner's money. Say so before a large or repeated paid run, and use the free path first (see `references/tools.md`).

## What to do with the result
- `rejected` on the variable the code reads: tell the owner; do not paper over it with another service.
- `no credit`: the key is fine and the account is empty; the owner tops it up.
- OpenRouter below $5 or Muapi below $5: say so in the report; the studio's paid fallbacks are what run out first.

`references/tools.md` lists each tool, what it is for here, which variable is live (as of the last check), what it costs, and its known gotchas.
