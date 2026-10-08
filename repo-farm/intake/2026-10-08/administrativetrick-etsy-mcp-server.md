# Intake: administrativetrick/etsy-mcp-server

- **Source:** https://github.com/administrativetrick/etsy-mcp-server
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `install-hook`:** runs code when installed: prepare: npm run build
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: ETSY_API_KEY

## Commands its docs tell you to run (read, do not run)

```
npm install -g etsy-mcp-server
git clone <repository-url>
npm install
npm run build
npm run watch
npm run dev
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Etsy MCP Server

A Model Context Protocol (MCP) server that provides integration with the Etsy API v3. This server enables AI assistants to search for products, get shop information, retrieve listing details, and more on Etsy.

## Features

- 🔍 **Search Listings**: Search for active products on Etsy with filters
- 🏪 **Shop Information**: Get detailed shop data and reviews
- 📦 **Listing Details**: Retrieve comprehensive product information with images
- 🔥 **Trending Products**: Discover what's currently popular on Etsy
- ⭐ **Reviews**: Access shop reviews and ratings
- 📊 **Pagination Support**: Handle large result sets efficiently

## Prerequisites

- Node.js 18 or higher
- An Etsy API key (from Etsy Developer Portal)

## Getting an Etsy API Key

1. Go to [Etsy Developers](https://www.etsy.com/developers)
2. Sign in with your Etsy account
3. Create a new app in the [Developer Console](https://www.etsy.com/developers/your-apps)
4. Copy your API Key (also called "Keystring")

**Note**: For read-only operations (searching, viewing public data), you only need an API key. For operations that modify data (creating listings, managing shops), you would need OAuth 2.0 authentication, which is not currently implemented in this server.

## Installation

### From npm (when published)

'''bash
npm install -g etsy-mcp-server
'''

### From Source

'''bash
git clone <repository-url>
cd etsy-m
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: ideate.

MIT, read-only Etsy API v3 server (search listings, shop info, trending, reviews) using an API key only; no OAuth, so it cannot write. Its `prepare` script builds TypeScript at install. Useful for competitor and price research once the owner has an Etsy API key; Muapi search-volume data and TokConnect cover demand until then.

**Only the owner can:** An Etsy API keystring (free developer account) if Etsy research is wanted.
