# Intake: scaledown-team/SLM_Agent

- **Source:** https://github.com/scaledown-team/SLM_Agent
- **Looked at:** 2026-10-14 12:28 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| npm_name | @scaledown/migration-agent |
| pushed | 2026-09-11T15:55:57.760Z |
| weekly_downloads | 33 |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `license-unknown`:** no LICENSE file at the top level and the API was not reachable: check by hand
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: SCALEDOWN_API_KEY

## Commands its docs tell you to run (read, do not run)

```
npm install -g @scaledown/migration-agent
git clone https://github.com/scaledown-team/SLM_Agent
npm install
npm run build       # compile TypeScript → dist/
npm run dev         # run without compiling (via tsx)
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# SLM Agent by ScaleDown

An MCP server + Claude Code plugin that scans your codebase for AI API calls and shows you exactly where and how to integrate [ScaleDown](https://scaledown.ai) SLMs to cut costs by up to 95%.

> **Privacy**: This plugin analyzes your code locally. No source code or codebase data is ever sent to ScaleDown servers. The only network calls are to ScaleDown's API endpoints at runtime, when *your application* calls them with the `SCALEDOWN_API_KEY` you provide.

## What it does

1. **Evaluates** — scans your project for OpenAI, Anthropic, LangChain, LlamaIndex, Cohere, and other AI API calls
2. **Plans** — generates a structured migration plan showing which ScaleDown SLM fits each call site:
   - `sd_compress` — reduce context tokens 50–70% before calling your LLM (for RAG, long docs)
   - `sd_classify` — replace frontier LLM classification calls (~95% cheaper)
   - `sd_extract` — replace frontier LLM entity extraction calls (~95% cheaper)
   - `sd_summarize` — replace frontier LLM summarization calls (~90% cheaper)
3. **Migrates** — applies the changes to your code with your approval, adapting to your real variable names
4. **Optimizes** — tunes the prompt you pass to a ScaleDown SLM against your own sample data and benchmarks it against the frontier-model output it replaced, with a reproducible eval

## Installation

### Claude Code (recommended)

First ad
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-14)

**PARK**, pipeline stage: none.

It is not a Claude Code token saver. Its README says it scans an application's code for AI API calls and migrates them to ScaleDown's paid small-model API (compress, classify, extract, summarize), which needs SCALEDOWN_API_KEY and sends our prompts to a third party. No licence file was found, it has 33 weekly downloads, and its install runs unpinned code. The `dietcode` package the owner named is a different thing: neither the repo's README nor the quickstart page describes it or what `dietcode setup` changes, so it cannot be reviewed. A tool that installs hooks into Claude Code's own settings and may route session context to an outside service needs its code read first.

**Worth taking:** The idea of compressing long context before a model call. The engine's own calls are small (Haiku at about $0.003 a song); the real token burn is this long session, not the pipeline.

**Only the owner can:** If you still want DietCode: send its README or repo link so it can be read, say whether sending session context to ScaleDown is acceptable, and confirm a key is yours to use. Install it on your own computer, since it edits local Claude Code settings; it cannot work in this cloud container.
