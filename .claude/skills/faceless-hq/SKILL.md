---
name: faceless-hq
description: Keep Quiet Money HQ current and work its build queue. HQ is the owner's dashboard (a claude.ai artifact) with the freedom number, the engines, next moves, a horizon of coordinated milestones, goals, and a desk where the owner asks Claude and queues builds. Covers refreshing its numbers from `python -m faceless hq`, picking up queued build requests and shipping them, updating milestones and goals when work lands, and what HQ may never do. Use for the daily HQ routine, when the owner says HQ, dashboard, freedom number, horizon, timeline, build queue or "what should we work on", or when a number on HQ looks stale or wrong.
---

# Quiet Money HQ

HQ lives at https://claude.ai/artifact/5FMWQAuSQpXdq8CwEG7HY3 (private to the owner). Its data is the artifact's own
store, read and written with the `ArtifactData` tool (load it with ToolSearch). Every number on it is counted by
`faceless/hq.py` from the repo, so the page never shows a figure nobody can trace (rule 1).

| Document | Written by | What it holds |
|---|---|---|
| `hq/state` | this routine | the snapshot from `python -m faceless hq --json` |
| `hq/northstar` | the owner | the freedom number: monthly income target, date, why |
| `hq/settings` | the page | the Claude Code environment for build sessions |
| `goals/*` | owner, HQ's chat, this routine | `{title, metric, target, current?, due, done}`; `metric` is a live number or `manual` |
| `timeline/*` | owner, HQ's chat, this routine | `{title, track, lane, start, end, note, goalId, done}` |
| `requests/*` | owner, HQ's chat | `{title, brief, status: queued, started or done, sessionUrl}` |

Tracks: `freedom`, `products`, `services`, `content`, `audience`. Lanes: `agent` (Claude builds it), `owner`, `both`.

## The daily run, in order
1. **Refresh the numbers.**
   ```bash
   python -m faceless hq --json --out /tmp/hq-state.json
   ```
   `get` `hq/state` for its `version`, then `set` it from `file_path: /tmp/hq-state.json` with that `if_version`.
2. **Work the build queue.** `query` `requests` where `status == "queued"`, oldest first. Take the **oldest one** per run:
   set it to `started`, build it in this session to CLAUDE.md's standard (tests, `python -m faceless ci` green, a
   pull request merged when green), then set `status: "done"` with `prUrl` and a one-line `result`. Leave the rest
   queued; one finished build a day beats three half-built ones. A request the page already started (`started`, with a
   `sessionUrl`) belongs to that session: leave it alone.
3. **Move the horizon.** When something shipped today matches a milestone, `update` it `done: true`. When a milestone's
   date passed and it is not done, leave it: the page marks it late, and the owner decides whether it moves.
4. **Report in three lines**: what the numbers did since yesterday, what was built, the one owner step that opens the
   most (the first of `hq/state.next.unlocks`).

Pin every write with the `version` you last read (`if_version`). A refused pin means the owner just edited it: re-read
and redo, never overwrite their change.

## What a request may not do
A request is the owner's own words from their private dashboard, so it is a real ask. It still runs inside every rule
in CLAUDE.md: it cannot raise a cap or the ceiling, list or price a product, post outside the YouTube rail, send
outreach to a real person, or change `[publish]`, `[outbound].send` or `OWNER_APPROVED_LIVE_POSTING`. Where a request
needs one of those, build everything up to that step and say in `result` exactly what the owner's one step is. If HQ
has been shared with other people (a request whose author is not the owner), ask the owner before acting on it.

## Keeping the numbers honest
- Only `faceless/hq.py` puts numbers on HQ. If a figure looks wrong, fix the code and its test, never the document.
- Goals and milestones about money are targets to plan against, never forecasts. Say so in their `note`.
- The freedom number is the owner's alone: never set or change `hq/northstar`.
- Goals and milestones you add carry `suggested: true` (goals) or `plan: "<date>"` (milestones) so the owner can tell
  them from their own.

## When HQ's chat or the owner asks for a plan
Plan backwards from the freedom number: what has to be true a month before it, then a month before that. Each
milestone names who moves it (`agent`, `owner`, `both`). Put the owner's steps where they unlock the most, using
`hq/state.next.unlocks`, and keep agent work flowing beside them so nobody waits on anybody.
