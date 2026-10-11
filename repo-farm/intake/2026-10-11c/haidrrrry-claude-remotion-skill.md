# Intake: haidrrrry/claude-remotion-skill

- **Source:** https://github.com/haidrrrry/claude-remotion-skill
- **Looked at:** 2026-10-11 12:38 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
git clone https://github.com/haidrrrry/claude-remotion-skill.git
npm install
npm run audio            # synthesize the SFX and music, no asset files needed
npm run render:selffix   # or render:codeedit / render:profile / render:focuscat
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# 🎬 Claude Remotion Skill — Make AI Video Editing & Motion Graphics with Claude

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Agent Skill](https://img.shields.io/badge/Claude-Agent%20Skill-8A63D2)](https://docs.anthropic.com/en/docs/claude-code)
[![Remotion](https://img.shields.io/badge/Built%20for-Remotion-00C2A8)](https://remotion.dev)
[![Star this repo](https://img.shields.io/github/stars/haidrrrry/claude-remotion-skill?style=social)](https://github.com/haidrrrry/claude-remotion-skill)

**An open-source [Claude](https://claude.com) agent skill that turns Claude Code, Claude Desktop, and Claude AI into a real motion-graphics editor.** It teaches Claude to create and edit professional **AI videos with [Remotion](https://remotion.dev)** — springs, staggered choreography, color grades, film grain, Ken Burns, word-synced captions, and sound design — from a single prompt. Text to video, the way an actual editor would do it.

> If you've ever asked an AI to "make a video" and gotten flat fades and linear motion, this is the fix. **Remotion is never the bottleneck — motion-design craft is.** This skill encodes that craft as hard rules plus a mandatory **render → inspect frames → fix → re-render** loop, so Claude verifies its own output instead of shipping blind.

## 🎥 Demo — made with this skill

[![Demo — motion graphics made with this ski
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-11)

**KILL**, pipeline stage: render.

MIT skill for Remotion. We render with HyperFrames; a Remotion skill would pull in a second renderer and a Node/React build for no gain.

**Worth taking:** Nothing.

**Only the owner can:** None.
