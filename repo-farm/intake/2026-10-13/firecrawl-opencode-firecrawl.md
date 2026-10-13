# Intake: firecrawl/opencode-firecrawl

- **Source:** https://github.com/firecrawl/opencode-firecrawl
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| npm_name | @firecrawl/opencode |
| license | ISC (read from LICENSE) |
| pushed | 2026-10-06T02:54:07.747Z |
| weekly_downloads | 115 |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: FIRECRAWL_API_KEY

## Commands its docs tell you to run (read, do not run)

```
npx -y firecrawl-cli@latest init -y --browser
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# @firecrawl/opencode

[OpenCode](https://opencode.ai) plugin for [Firecrawl](https://firecrawl.dev). It gives your agent primary-source answers from the Firecrawl developer index, structured data from Firecrawl Alexandria providers, and web scraping, crawling, and search through the [Firecrawl CLI](https://github.com/firecrawl/cli).

## Installation

The plugin supports OpenCode 2 and OpenCode 1 (1.18.29 or later) from the same package.

### OpenCode 2

'''bash
opencode plugin add @firecrawl/opencode
'''

Or add it to `opencode.jsonc` yourself:

'''jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": ["@firecrawl/opencode"]
}
'''

### OpenCode 1

Add it to `opencode.json`:

'''json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["@firecrawl/opencode"]
}
'''

OpenCode installs the package on the next start. The developer search tool works right away, with no API key and no CLI.

For the web skills (scrape, crawl, map, search, agent), install the Firecrawl CLI:

'''bash
npx -y firecrawl-cli@latest init -y --browser
'''

## Authentication

On OpenCode 2, run `/connect` in the TUI (or `opencode auth login`), pick Firecrawl, and choose **Sign in with Firecrawl**. OpenCode opens Firecrawl in your browser; approve access and you are connected, with no API key to copy. OpenCode keeps the sign-in fresh on its own. Pasting an API key from [firecrawl.dev](h
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-13)

**KILL**, pipeline stage: none.

Plugin for the OpenCode agent, which we do not run.
