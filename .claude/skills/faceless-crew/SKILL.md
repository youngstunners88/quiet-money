---
name: faceless-crew
description: The working rules for every agent on the Quiet Money crew (Claude Code, Hermes, OpenCode, and Agent Zero once installed) so they act as one team instead of colliding. Use at the start of any session that will pick up work from the mission board, before choosing a mission, when asked "what should I work on", "who is working on what", "check the instruments", "claim a mission", "hand this off", "am I near my limit", or when a mission prompt from the board arrives. Covers the pre-flight check, claim locks, heartbeats, handoffs and what Autopilot holds back.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/instruments.py, faceless/missions.py
---

# Working as one crew

The command center shows every agent as a lamp, a limit and a current task. It can only do that, and Autopilot can only route
well, if each agent does five small things. They cost no tokens: every command below is a local read or one line appended to a file.

Your crew id is the block name in `crew.toml`: `claude`, `hermes`, `opencode`, later `agent-zero`.

## 1. Pre-flight, before choosing work

```bash
python -m faceless instruments --for <your-id>
```

It prints your lamp and key state, your remaining budget (or "limit unknown", never a guess), what every other agent is doing,
which missions are already taken, which open missions are routed to you, and where another agent is better placed (cheaper and
able). Exit code 1 means do not start: your key is rejected, you are past the hold line of your limit, or the studio is paused.
Then hand the work over (step 4) instead of starting it.

## 2. Claim, before starting

```bash
python -m faceless crew claim <mission> --agent <your-id>
```

One agent per mission. If another agent holds it you are refused and told who; pick something else. A mission the board sent
you is already claimed for you. Give one back with `python -m faceless crew release <mission> --agent <your-id>`.

## 3. Heartbeat, while working

```bash
python -m faceless agent beat <your-id> running --task "what you are doing" [--done N --total M] [--tokens-in N --tokens-out N]
```

Every few minutes. Silent for 20 minutes while holding work and your lamp turns amber; silent for 45 and it turns red, your
mission goes back on the board for another agent, and Autopilot stops sending you work. Both numbers are in `crew.toml`
(`stale_minutes`, `dormant_minutes`).

## 4. Hand off, when near a limit, blocked, or outside your strengths

```bash
python -m faceless crew ask <writing|research|bulk|phone|code|review|hard> "what is needed" --agent <your-id>
```

This opens a mission for the cheapest able agent and draws a line from you to it on the board. Code, review and hard jobs go
to Claude Code only.

## 5. Report, when done or stuck

```bash
python -m faceless crew report <mission> done "one line on what changed" --agent <your-id>
python -m faceless crew report <mission> blocked "why" --agent <your-id>
```

Reporting releases your claim.

## What Autopilot will not do

It reads the same instrument before starting anything and holds a mission, with the reason in the journal and on the board as
"held because ...", rather than send it to an agent with a rejected key, one past 90% of its limit, a dormant one, or one
dearer than `[autopilot] max_cost`. Do not route around a hold; fix the cause or leave it for the owner.

## What no agent does from here

Nothing on the board sends a DM, posts or uploads, and `publish --force` is never run. Those wait in the YOU strip for the owner.
Never print, log or commit a key value; the instrument reports key health by variable name only.
