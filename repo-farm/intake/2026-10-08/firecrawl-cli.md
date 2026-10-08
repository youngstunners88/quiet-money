# Intake: firecrawl-cli

- **Source:** https://www.npmjs.com/package/firecrawl-cli
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** Command-line interface for Firecrawl. Scrape, crawl, and extract data from any website, and search a ~43M-abstract research paper index (PubMed, bioRxiv, medRxiv, arXiv), directly from your terminal.

| fact | value |
|---|---|
| version | 1.26.3 |
| license | ISC |
| created | 2026-01-07T22:36:33.089Z |
| pushed | 2026-10-06T22:46:42.766Z |
| weekly_downloads | 28677 |
| versions | 139 |
| maintainers | ['hello_sideguide', 'abimaelmartell'] |

## Red flags

- **HIGH `install-hook`:** runs code when installed: prepare: husky
- **HIGH `pipe-to-shell`:** tells you to pipe a download into a shell
- **HIGH `asks-for-secrets`:** asks you to paste a key, password or seed phrase
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `telemetry`:** mentions telemetry or usage analytics: find out what is sent
- **INFO `needs-keys`:** mentions keys: FIRECRAWL_API_KEY

## Commands its docs tell you to run (read, do not run)

```
npm install -g firecrawl-cli
npx -y firecrawl-cli@latest init -y --browser
curl -fsSL https://firecrawl.dev/install.sh | bash -s -- --agent openclaw
npx skills add firecrawl/skills
npx firecrawl-cli@latest alexandria terms show benzinga --pretty
npx firecrawl-cli@latest alexandria terms accept benzinga \
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# 🔥 Firecrawl CLI

Command-line interface for Firecrawl. Search, scrape, interact, crawl, map, search research papers, developer sources, and government sources, and run agent jobs directly from your terminal.

## Installation

'''bash
npm install -g firecrawl-cli
'''

Or set up everything in one command (install CLI globally, authenticate, and add skills across all detected coding editors):

'''bash
npx -y firecrawl-cli@latest init -y --browser
'''

- `-y` runs setup non-interactively
- `--browser` opens the browser for Firecrawl authentication automatically
- skills install globally to every detected AI coding agent by default

### Setup Skills, Workflows, and MCP

If you are using an AI coding agent like Claude Code, you can also install skill groups manually — one command per family:

'''bash
firecrawl setup core       # scrape/search/crawl/interact primitives + index skills ("skills" is an alias)
firecrawl setup build      # app-integration skills for the Firecrawl API
firecrawl setup workflows  # end-to-end recipes (lead gen, deep research, ...)
'''

Or install a single skill by name — the `firecrawl-` prefix is optional:

'''bash
firecrawl setup developer-index
firecrawl setup seo-audit
'''

If no API key is found afterwards, an interactive terminal offers a browser login (pass `--browser` to log in without the prompt); non-interactive runs never block — they print a hin
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: ideate.

ISC, 28,677 weekly downloads, mature. Firecrawl is already a connected research tool with a key in the environment, so the CLI adds nothing a routine needs. `init -y --browser` installs skills into every detected agent and signs in through a browser, and its docs include a curl installer: not run.

**Worth taking:** Its `alexandria` data-terms commands suggest paid dataset access; not needed.
