# Intake: snarktank/antfarm

- **Source:** https://github.com/snarktank/antfarm
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `pipe-to-shell`:** tells you to pipe a download into a shell
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
curl -fsSL https://raw.githubusercontent.com/snarktank/antfarm/v0.5.1/scripts/install.sh | bash
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Antfarm

<img src="https://raw.githubusercontent.com/snarktank/antfarm/main/landing/logo.jpeg" alt="Antfarm" width="80">

**Build your agent team in [OpenClaw](https://docs.openclaw.ai) with one command.**

You don't need to hire a dev team. You need to define one. Antfarm gives you a team of specialized AI agents — planner, developer, verifier, tester, reviewer — that work together in reliable, repeatable workflows. One install. Zero infrastructure.

### Install

'''bash
curl -fsSL https://raw.githubusercontent.com/snarktank/antfarm/v0.5.1/scripts/install.sh | bash
'''

Or just tell your OpenClaw agent: **"install github.com/snarktank/antfarm"**

That's it. Run `antfarm workflow list` to see available workflows.

> **Not on npm.** Antfarm is installed from GitHub, not the npm registry. There is an unrelated `antfarm` package on npm — that's not this.

> **Requires Node.js >= 22.** If `antfarm` fails with a `node:sqlite` error, make sure you're running real Node.js 22+, not Bun's node wrapper (see [#54](https://github.com/snarktank/antfarm/issues/54)).

---

## What You Get: Agent Team Workflows

### feature-dev `7 agents`

Drop in a feature request. Get back a tested PR. The planner decomposes your task into stories. Each story gets implemented, verified, and tested in isolation. Failures retry automatically. Nothing ships without a code review.

'''
plan → setup → implement
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: none.

MIT team of coding agents (planner, developer, verifier, tester, reviewer) for the OpenClaw platform, installed by a curl script. We run on Claude Code routines with a deterministic orchestrator and a gauntlet that already plays the verifier role.
