# Intake: lekt9/unbrowse-openclaw

- **Source:** https://github.com/lekt9/unbrowse-openclaw
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| npm_name | unbrowse-openclaw |
| pushed | 2026-05-10T06:25:38.444Z |
| weekly_downloads | 20 |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `license-unknown`:** no LICENSE file at the top level and the API was not reachable: check by hand
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npm test
npm run typecheck
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# unbrowse-openclaw

Use Unbrowse inside OpenClaw.

This plugin adds a native `unbrowse` tool, teaches agents to use it first for website tasks, and gives you a strict mode that can keep agents off the built-in `browser` tool.

Use it when you want API-first web work: structured extraction, reverse-engineered site actions, less brittle browser automation.

## Install

'''bash
openclaw plugins install unbrowse-openclaw
openclaw gateway restart
'''

Verify:

'''bash
openclaw plugins info unbrowse-openclaw
openclaw unbrowse-plugin health
'''

If you use plugin allowlists, trust it:

'''json5
{
  plugins: {
    allow: ["unbrowse-openclaw"]
  }
}
'''

## What agents get

Tool:

'''json
{
  "action": "resolve",
  "intent": "get pricing page API data",
  "url": "https://example.com"
}
'''

Actions: `resolve`, `search`, `execute`, `login`, `skills`, `skill`, `health`

Integration:

- bootstrap guidance plus a `before_agent_start` system-prompt hint each run
- a shipped `unbrowse-browser` skill so the replacement policy shows up in OpenClaw's skill surface
- strict-mode blocking of the built-in `browser` tool via `before_tool_call`

## Default web path

This plugin makes `unbrowse` the default web path in practice by:

- teaching the agent to prefer `unbrowse`
- shipping a skill that reinforces the policy
- optionally blocking `browser` in strict mode

### Fallback mode

Prefer Unbrowse
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: none.

OpenClaw plugin that reverse-engineers site APIs. No licence file, an agent platform we do not use, and the official APIs we need exist.
