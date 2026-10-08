# Intake: diffusionstudio/lottie

- **Source:** https://github.com/diffusionstudio/lottie
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `install-hook`:** runs code when installed: postinstall: node scripts/copy-canvaskit.mjs
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npx skills add diffusionstudio/lottie
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <img src="assets/header.gif" alt="Text to Lottie" width="100%" />
</p>

[![](https://img.shields.io/discord/1115673443141156924?style=flat&logo=discord&logoColor=white&color=5865F2)](https://discord.com/invite/zPQJrNGuFB)
[![](https://img.shields.io/badge/Follow%20for-Updates-black?logo=x&logoColor=white)](https://x.com/diffusionhq)
[![](https://img.shields.io/badge/Combinator-F24-orange?logo=ycombinator&logoColor=white)](https://www.ycombinator.com/companies/diffusion-studio)

[English](README.md) | [繁體中文](README.zh-TW.md)

**Text-to-lottie** is an open-source framework for generating production ready Lottie animations with claude code/codex or any other coding agent supporting skills.

## Created with Text-to-Lottie
<table>
  <tr>
    <td>
      <img src="assets/demo-1.gif" width="350" />
    </td>
    <td>
      <img src="assets/demo-2.gif" width="350" />
    </td>
  </tr>
</table>

## Quick Start 
Install the skill:
'''bash
npx skills add diffusionstudio/lottie
'''
Then ask your coding agent to generate a Lottie animation using `text-to-lottie`.

Example prompt:
> Create a Lottie animation from the SVG path in https://github.com/JaceThings/SF-Hello/blob/main/SVG/hello-en.svg. Reveal the path with an animation that follows the natural path direction. Apply a premium apple themed gradient to the path. Use ease-in-out timing, a transparent background, and 
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**PARK**, pipeline stage: visuals.

MIT text-to-Lottie agent skill (`npx skills add`). Lottie JSON could drive animated icons, but our headless pipeline already renders motion with HyperFrames; rendering Lottie to video would add a second motion stack for no gain today.

**Worth taking:** Revisit for the website (animated icons) in the site redesign phase.
