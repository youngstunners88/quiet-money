# Intake: diffusionstudio/editor

- **Source:** https://github.com/diffusionstudio/editor
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | AGPL-3.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `install-hook`:** runs code when installed: postinstall: patch-package
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **MED `restrictive-license`:** copyleft or non-commercial terms: read before using in a paid product
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
git clone https://github.com/diffusionstudio/editor.git
npm install
npm run dev
npm run link --workspace=@diffusionstudio/cli
npm run check    # typecheck all workspaces
npm run lint     # lint all workspaces
npm run test     # ensure tests are green
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <a href="https://diffusion.studio">
    <img src="assets/banner.png" alt="Diffusion Studio" width="700" />
  </a>
</p>

<p align="center">Turn your agent into a professional video editor</p>

<p align="center">
  <a href="https://www.diffusion.studio/download"><img src="https://img.shields.io/badge/Download-macOS%20%7C%20Windows-161616?style=flat&labelColor=000000" alt="Download for macOS or Windows" /></a>
  <a href="https://discord.com/invite/zPQJrNGuFB"><img src="https://img.shields.io/discord/1115673443141156924?style=flat&logo=discord&logoColor=F8F8F8&label=Discord&labelColor=000000&color=161616" alt="Discord" /></a>
  <a href="https://x.com/diffusionhq"><img src="https://img.shields.io/badge/Follow%20for-Updates-161616?style=flat&logo=x&logoColor=F8F8F8&labelColor=000000" alt="Follow on X" /></a>
  <a href="https://www.ycombinator.com/companies/diffusion-studio"><img src="https://img.shields.io/badge/Combinator-F24-161616?style=flat&logo=ycombinator&logoColor=F8F8F8&labelColor=000000" alt="Y Combinator F24" /></a>
</p>

<p align="center">
  <code>npx skills add diffusionstudio/skills</code>
</p>

<br />

<p align="center">
  <a href="https://app.diffusion.studio">
    <img src="assets/desktop-screenshot.png" alt="The Diffusion Studio editor" width="800" />
  </a>
</p>

<br />

## Diffusion Studio

Edit videos with Codex, Claude Code, OpenCode, or Pi. 
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: render.

AGPL-3.0 desktop video editor for macOS and Windows that an agent drives. Our render path is headless Python and ffmpeg on Linux; a desktop app cannot run in the routine, and AGPL adds obligations for no gain.
