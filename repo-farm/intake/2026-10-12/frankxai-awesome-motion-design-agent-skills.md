# Intake: frankxai/awesome-motion-design-agent-skills

- **Source:** https://github.com/frankxai/awesome-motion-design-agent-skills
- **Looked at:** 2026-10-12 15:09 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | unrecognised text in LICENSE |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **MED `binary-download`:** ships or downloads prebuilt binaries: unreviewed code
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Awesome Motion Design Agent Skills [![Awesome](https://awesome.re/badge.svg)](https://awesome.re)


<p align="center"><img src="assets/banner.png" width="100%" alt="Awesome Motion Design Agent Skills — Interface motion, cinematic web and programmatic video — installable in one line."></p>


[![Stars](https://img.shields.io/github/stars/frankxai/awesome-motion-design-agent-skills?style=flat)](https://github.com/frankxai/awesome-motion-design-agent-skills) [![Last commit](https://img.shields.io/github/last-commit/frankxai/awesome-motion-design-agent-skills?style=flat)](https://github.com/frankxai/awesome-motion-design-agent-skills/commits/main) [![License: CC0](https://img.shields.io/badge/license-CC0--1.0-lightgrey?style=flat)](LICENSE)


[![Install: any agent](https://img.shields.io/badge/npx%20skills%20add-any%20agent-000000?style=for-the-badge&logo=npm)](#install) [![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757?style=for-the-badge&logo=anthropic&logoColor=white)](https://code.claude.com/docs/en/discover-plugins) [![Download for Claude.ai](https://img.shields.io/badge/Claude.ai%20%2F%20Cowork-download%20.zip-D97757?style=for-the-badge&logo=anthropic&logoColor=white)](https://github.com/frankxai/awesome-motion-design-agent-skills/releases)


> The motion-design stack for AI agents — curated GSAP, Motion, Remotion, Lottie and Rive resources, plu
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-12)

**PARK**, pipeline stage: render.

A curated list of motion-design skills and resources (GSAP, Motion, Remotion, Lottie, Rive), which the intake read as a directory. Its LICENSE is unrecognised text while the README says CC0, so the licence is unclear. It ships or downloads prebuilt binaries (MED flag), which is unreviewed code, and its install lines run the newest code on every use. A directory is useful only as a list of leads: each entry needs its own intake.

**Worth taking:** A list of leads to check one at a time. Nothing copied from it.

**Only the owner can:** None now. If a lead from this list looks right, send that one repo through intake on its own.
