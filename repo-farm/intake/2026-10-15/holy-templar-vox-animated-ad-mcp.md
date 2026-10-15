# Intake: holy-templar/vox-animated-ad-mcp

- **Source:** https://github.com/holy-templar/vox-animated-ad-mcp
- **Looked at:** 2026-10-15 01:50 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | AGPL-3.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `restrictive-license`:** copyleft or non-commercial terms: read before using in a paid product
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
curl -o ~/.claude/skills/vox-animated-ad-mcp/SKILL.md \
claude mcp add --transport http maxfusion https://mcp.maxfusion.ai/mcp
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
'''
   _____                   _____            .__
  /     \ _____  ___  ____/ ____\_ __  _____|__| ____   ____
 /  \ /  \\__  \ \  \/  /\   __\  |  \/  ___/  |/  _ \ /    \
/    Y    \/ __ \_>    <  |  | |  |  /\___ \|  (  <_> )   |  \
\____|__  (____  /__/\_ \ |__| |____//____  >__|\____/|___|  /
        \/     \/      \/                 \/               \/
'''

# Vox Explainer Method

A [Claude](https://claude.com) skill that turns a single sentence into a complete Vox-style paper-collage animated video — researched script, per-clip prompts, every image and clip generated, chained into one continuous animation — without you ever leaving the chat.

It does two things:

- **Make ad videos** — Vox Style Ad Animation for your product or offer, ready to run paid or drop organic.
- **Make explainers for faceless YouTube channels** — editorial storytelling that sells nothing.

You give it a topic or a product. The skill walks a fixed gate flow — content mode, a quick research pass, script and prompt approval — then generates every clip through the [MaxFusion](https://maxfusion.ai) MCP (Google Omni, 10-second clips) and returns the finished clips in chat. The consistency trick: it extracts the last frame of each finished clip and passes it as the reference into the next clip's generation, which is why the result plays as one continuous animation instead of disconnected AI shots.

#
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?
