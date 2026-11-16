# Quiet Money: start here (every agent)

This file is read at start-up by agents that look for `AGENTS.md` (OpenCode, Hermes, Agent Zero). Claude Code reads `CLAUDE.md`.
**`CLAUDE.md` is the law for everyone**: read it next, in full. It holds the rules (no publishing outside the standing orders, the
spend caps, no key in any file, command line, commit or reply) and the routing table that says which skill to load for which job.

You are one of a crew: Claude Code (`claude`), Hermes (`hermes`), OpenCode (`opencode`), and later Agent Zero (`agent-zero`).
The roster is `crew.toml`. Before choosing any work:

```bash
python -m faceless instruments --for <your-id>     # your budget, who has what, who is better placed; exit 1 = do not start
python -m faceless crew claim <mission> --agent <your-id>     # one agent per mission; refused if another holds it
python -m faceless agent beat <your-id> running --task "..."  # every few minutes; silent for 45 min and the mission is taken back
python -m faceless crew ask <job-tag> "what is needed" --agent <your-id>      # hand off when near a limit, blocked or out of your depth
python -m faceless crew report <mission> done|blocked "one line" --agent <your-id>
```

The full rules are the `faceless-crew` skill (`.claude/skills/faceless-crew/SKILL.md`). The board that shows all of this is the
command center (`artifacts/command-center/README.md`).
