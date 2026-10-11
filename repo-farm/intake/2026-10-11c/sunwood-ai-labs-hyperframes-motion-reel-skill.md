# Intake: Sunwood-ai-labs/hyperframes-motion-reel-skill

- **Source:** https://github.com/Sunwood-ai-labs/hyperframes-motion-reel-skill
- **Looked at:** 2026-10-11 12:38 UTC (public metadata and text only; nothing was cloned, installed or run)
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
git clone https://github.com/Sunwood-ai-labs/hyperframes-motion-reel-skill ~/.claude/skills/hyperframes-motion-reel
git clone https://github.com/Sunwood-ai-labs/hyperframes-motion-reel-skill "$env:USERPROFILE\.claude\skills\hyperframes-motion-reel"
npm install
npm run docs:dev
npx hyperframes init "<project-dir>" --non-interactive --example=blank --skill=general-video
npx hyperframes render --fps 60 --quality draft    --output out/draft.mp4      # 反復確認
npx hyperframes render --fps 60 --quality delivery --output out/reel.mp4       # 最終
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<div align="center">
  <img src="./docs/public/header.svg" alt="HyperFrames Motion Reel" width="100%">
  <h1>HyperFrames Motion Reel Skill</h1>
  <p><strong>Showreel-grade motion graphics, written as code.</strong><br>
  A Claude Code skill that turns a one-line theme into a beat-synced, render-ready HyperFrames video.</p>
  <p>
    <img src="https://img.shields.io/badge/Claude%20Code-Skill-D97757?logo=anthropic&logoColor=white" alt="Claude Code Skill">
    <img src="https://img.shields.io/badge/HyperFrames-Apache--2.0-D7FF00?labelColor=050505" alt="HyperFrames Apache-2.0">
    <img src="https://img.shields.io/badge/GSAP-3-88CE02?logo=greensock&logoColor=white" alt="GSAP 3">
    <img src="https://img.shields.io/badge/120%20BPM-60%20FPS-050505" alt="120 BPM / 60 FPS">
    <a href="https://github.com/Sunwood-ai-labs/hyperframes-motion-reel-skill/actions/workflows/ci.yml"><img src="https://github.com/Sunwood-ai-labs/hyperframes-motion-reel-skill/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-F4F4F0?labelColor=050505" alt="MIT License"></a>
  </p>
  <p>
    <a href="./README.md"><img src="https://img.shields.io/badge/Language-English-blue.svg" alt="English"></a>
    <a href="./README.ja.md"><img src="https://img.shields.io/badge/Language-Japanese-lightgrey.svg" alt="Japanese"></a>
  </p>
</div>

`hyperfra
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [x] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-11)

**TRIAL**, pipeline stage: render.

MIT. A skill for motion reels on HyperFrames, which is our renderer. Closest match to the stack, so the likeliest source of scene patterns that already respect HyperFrames' seek rules.

**Worth taking:** Reel structures and scene patterns for new card kinds.

**Only the owner can:** Read its patterns when adding a card kind; copy ideas, not files.
