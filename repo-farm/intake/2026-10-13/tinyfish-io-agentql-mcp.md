# Intake: tinyfish-io/agentql-mcp

- **Source:** https://github.com/tinyfish-io/agentql-mcp
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| npm_name | agentql-mcp |
| license | MIT (read from LICENSE) |
| pushed | 2026-02-21T03:07:54.621Z |
| weekly_downloads | 309 |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `install-hook`:** runs code when installed: prepare: npm run build
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: AGENTQL_API_KEY, YOUR_API_KEY

## Commands its docs tell you to run (read, do not run)

```
npm install -g agentql-mcp
npm install
npm run build
npm run watch
npm run inspector
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# AgentQL MCP Server

This is a Model Context Protocol (MCP) server that integrates [AgentQL](https://agentql.com)'s data extraction capabilities.

## Features

### Tools

- `extract-web-data` - extract structured data from a given 'url', using 'prompt' as a description of actual data and its fields to extract.

## Installation

To use AgentQL MCP Server to extract data from web pages, you need to install it via npm, get an API key from our [Dev Portal](https://dev.agentql.com), and configure it in your favorite app that supports MCP.

### Install the package

'''bash
npm install -g agentql-mcp
'''

### Configure Claude

- Open Claude Desktop **Settings** via `⌘`+`,` (don't confuse with Claude Account Settings)
- Go to **Developer** sidebar section
- Click **Edit Config** and open `claude_desktop_config.json` file
- Add `agentql` server inside `mcpServers` dictionary in the config file
- Restart the app

'''json title="claude_desktop_config.json"
{
  "mcpServers": {
    "agentql": {
      "command": "npx",
      "args": ["-y", "agentql-mcp"],
      "env": {
        "AGENTQL_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
'''

Read more about MCP configuration in Claude [here](https://modelcontextprotocol.io/quickstart/user).

### Configure VS Code

For one-click installation, click one of the install buttons below:

[![Install with NPX in VS Code](https://img.shields.io/badge/VS_C
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-13)

**PARK**, pipeline stage: ideate.

HIGH flag: install hook. Last change 2026-02. TinyFish's own MCP is already connected and works, so this adds nothing.
