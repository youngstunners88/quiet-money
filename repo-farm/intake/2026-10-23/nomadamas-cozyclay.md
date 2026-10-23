# Intake: NomaDamas/CozyClay

- **Source:** https://github.com/NomaDamas/CozyClay
- **Looked at:** 2026-10-23 15:19 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| npm_name | cozyclay |
| license | AGPL-3.0 (read from LICENSE) |
| pushed | 2026-10-23T06:10:55.438Z |
| weekly_downloads | 540 |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **MED `restrictive-license`:** copyleft or non-commercial terms: read before using in a paid product
- **LOW `telemetry`:** mentions telemetry or usage analytics: find out what is sent
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npx cozyclay
git clone https://github.com/NomaDamas/CozyClay.git && cd CozyClay
npm install
npm run dev     # http://127.0.0.1:5180/app/
npm test
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <img src="docs/images/cozyclay-logo.png" alt="CozyClay" width="340">
</p>

<p align="center">
  <b>Make the scene first. Then make it a video.</b><br>
  <em>Open source previs in a browser tab: block the set, move the cast, cut the camera, hand the shot to an AI video model.</em>
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: AGPL-3.0" src="https://img.shields.io/badge/license-AGPL--3.0-blue"></a>
  <a href="https://www.npmjs.com/package/cozyclay"><img alt="npm" src="https://img.shields.io/npm/v/cozyclay"></a>
  <img alt="Node 22.19+" src="https://img.shields.io/badge/node-22.19%2B-brightgreen">
  <a href="https://github.com/NomaDamas/CozyClay/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/NomaDamas/CozyClay?style=flat"></a>
  <a href="https://discord.gg/Hp9V5wwgjF"><img alt="Discord" src="https://img.shields.io/badge/discord-join-5865F2?logo=discord&logoColor=white"></a>
</p>

<p align="center">
  <a href="https://cozyclay.org/#try">Try it in the browser</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="INSTALL_FOR_AGENTS.md">Guide for AI agents</a> ·
  <a href="#docs">Docs</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="https://discord.gg/Hp9V5wwgjF">Discord</a>
</p>

<table>
  <tr>
    <td width="50%"><video src="https://github.com/user-attachments/assets/00f28c2f-e8e2-43eb-b253-b6c2436e1818" co
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [x] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-23)

**TRIAL**, pipeline stage: visuals.

A free browser previs studio: block a 3D set, move capsule or rigged cast, cut the camera on a timeline, and export a first frame, a greybox clip, a camera and a prompt for an AI video model, or a storyboard animatic and contact sheet. Node 22 only, no GPU, no model download. It fits the Flow lane (the owner makes clips in Google Flow): a greybox reference gives the same camera and timing every take, so fewer re-rolls, and it is a source of a new look for a variations series (3D-blocked scenes, storyboard animatics). Licence AGPL-3.0-or-later: using it as a tool and using its exports is fine; copying or hosting modified code is not, so never vendor it into our engine. Flags: MED unpinned npx (pin 3.1.2), LOW telemetry (turn off with `cclay telemetry off`, done in the trial). Live tools did not load here, so the MCP route is unproven.

**Worth taking:** The method, in our own code: block the shot first, then generate, with a greybox reference clip and the real framing in the prompt (adds to faceless-flow prompts); storyboard-first stills with captions and an animatic for any long-form vibe.

**Only the owner can:** Run it on your own computer where a Chromium browser exists: `npx -y cozyclay@3.1.2`, then `cclay telemetry off`; build one greybox for a Flow clip and compare the Flow result with and without the reference. If the first clip looks better, tell me and I write the faceless-flow greybox step.
