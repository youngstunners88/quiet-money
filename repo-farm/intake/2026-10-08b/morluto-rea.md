# Intake: morluto/rea

- **Source:** https://github.com/morluto/rea
- **Looked at:** 2026-10-08 16:53 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| npm_name | rea-agents |
| license | MIT (read from LICENSE) |
| pushed | 2026-10-08T09:46:32.646Z |
| weekly_downloads | 1291 |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `install-hook`:** runs code when installed: prepare: node scripts/prepare.mjs
- **MED `build-time-code`:** installs by running its own script (install.sh / setup.py / source-only release): read it before use
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npx rea-agents setup
npx -y rea-agents@latest analyze-javascript-application /absolute/path/to/app --json
npm install --global rea-agents
npx rea-agents@latest setup
npm install --global ${prefix_args[@]+"${prefix_args[@]}"} "$PACKAGE@$version" || fail "npm could not install REA. Check registry access and
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<div align="center">

**English** · [简体中文](README_zh.md) · [日本語](README_ja.md) · [한국어](README_ko.md) · [العربية](README_ar.md)

# REA: Reverse Engineer Anything

### One MCP for reverse engineering across binaries, applications, and runtime behavior.

**See a feature you like. Understand how it works, down to the binary level.**

[![npm version](https://img.shields.io/npm/v/rea-agents?style=flat-square&color=cb3837)](https://www.npmjs.com/package/rea-agents)
[![CI](https://img.shields.io/github/actions/workflow/status/morluto/rea/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/morluto/rea/actions/workflows/ci.yml)
[![MCP tool catalog](https://img.shields.io/badge/MCP-tool_catalog-5c4ee5?style=flat-square)](docs/mcp-contracts.md#generated-catalog)
[![Node.js 22+](https://img.shields.io/badge/Node.js-22.19%2B-339933?style=flat-square&logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![skills.sh](https://skills.sh/b/morluto/rea?style=flat-square)](https://skills.sh/morluto/rea/reverse-engineer-anything)
[![MIT license](https://img.shields.io/badge/license-MIT-f4c430?style=flat-square)](LICENSE)
[![Discord](https://img.shields.io/discord/1556595354999332884?logo=discord&logoColor=white&label=Discord&color=5865F2)](https://discord.gg/GkcryMnJDM)

<a href="https://trendshift.io/repositories/82054?utm_source=repository-badge&amp;utm_medium=badge&amp;utm_campaig
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: none.

A reverse-engineering toolkit (MIT, MCP server) for binaries, applications and runtime behaviour. Its purpose in the Grok document was to rebuild private platform APIs so an agent could drive Etsy or Flow with no official path, which means automating the owner's real seller account through endpoints the platform never published: the quickest way to lose the shop. The package runs a script when installed (`prepare`) and its docs run `npx -y rea-agents@latest`, unpinned. No pipeline stage needs it. Recorded again so nobody re-evaluates it (portfolio X5).
