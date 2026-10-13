# Intake: monid-ai/plugins

- **Source:** https://github.com/monid-ai/plugins
- **Looked at:** 2026-10-13 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npx plugins add monid-ai/plugins
npx plugins discover .                # must print "1 skill, mcp"
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Monid Plugins

Official agent plugins for [Monid](https://monid.ai) — discover and run hundreds of data endpoints (web scraping, people and company enrichment, social media, search results, media generation) through one interface.

This repo is the distribution package. It works with Claude Code, Cursor, Codex, Grok Build, Kimi Code, GitHub Copilot CLI, and VS Code.

---

## Install

### Any supported agent (recommended)

'''bash
npx plugins add monid-ai/plugins
'''

Auto-detects every agent installed on your machine and installs to all of them.

### Claude Code

'''
/plugin marketplace add monid-ai/plugins
/plugin install monid@monid
'''

### Cursor

Open **Customize** in the sidebar and search for `monid`, or install from the [Cursor Marketplace](https://cursor.com/marketplace).

### No install — MCP only

Add this as a custom MCP server / connector in any MCP-capable client (ChatGPT, Claude.ai, Cursor, VS Code):

'''
https://mcp.monid.ai/v1
'''

It uses OAuth — there is no API key to paste.

---

## What you get

The plugin ships **two transports** for the same capabilities, plus a skill that tells your agent which to use.

| | MCP server | CLI |
|---|---|---|
| Setup | None — OAuth on first use | `npm i -g @monid-ai/cli` + API key |
| Works without a shell | Yes | No |
| Results go to | Conversation context | Context **or** a file (`-o`) |
| Best for | Everything by defau
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-13)

**PARK**, pipeline stage: ideate.

MIT, unpinned run lines. Nothing beyond the CLI.
