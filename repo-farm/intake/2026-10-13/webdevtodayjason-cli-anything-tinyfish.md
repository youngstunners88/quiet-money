# Intake: webdevtodayjason/cli-anything-tinyfish

- **Source:** https://github.com/webdevtodayjason/cli-anything-tinyfish
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: TINYFISH_API_KEY

## Commands its docs tell you to run (read, do not run)

```
pip install cli-anything-tinyfish
pip install -e ".[dev]"
python3 -m pytest cli_anything/tinyfish/tests/test_core.py -v     # unit (no network)
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# cli-anything-tinyfish

Agent-native CLI for the [TinyFish Web Agent](https://tinyfish.ai) — all four
TinyFish products from your terminal, over the REST APIs: **Search** (ranked
web results), **Fetch** (clean page extraction), **Agent** (natural-language
browser automation), and **Browser** (remote CDP sessions for
Playwright/Puppeteer control).

Built for the [CLI-Anything Hub](https://clianything.cc): JSON on stdout,
JSON errors on stderr, exit codes that mean something, API-key auth from the
environment. No browser OAuth, ever — which is the point: TinyFish's official
MCP server requires an interactive OAuth 2.1 browser flow, which headless
agents and kiosk machines can't complete. This CLI talks to the REST APIs
(`X-API-Key`) instead.

## Install

'''bash
pip install cli-anything-tinyfish
'''

## Authenticate

Create a free key at [agent.tinyfish.ai/api-keys](https://agent.tinyfish.ai/api-keys):

'''bash
export TINYFISH_API_KEY="sk-tinyfish-..."
cli-anything-tinyfish auth status
'''

Search and fetch are credit-free; agent runs consume TinyFish credits.

## Use

'''bash
# Search the web
cli-anything-tinyfish search "best react state management" --location US --pretty

# Fetch up to 10 URLs as clean markdown (JS-rendered, boilerplate stripped)
cli-anything-tinyfish fetch https://example.com/article --format markdown

# Natural-language browser automation
cli-anything-tinyf
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-13)

**KILL**, pipeline stage: none.

Third-party wrapper over a vendor we already reach through its official MCP and key. No reason to trust a stranger's wrapper.
