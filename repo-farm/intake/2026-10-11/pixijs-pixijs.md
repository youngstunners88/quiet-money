# Intake: pixijs/pixijs

- **Source:** https://github.com/pixijs/pixijs
- **Looked at:** 2026-10-11 11:47 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `install-hook`:** runs code when installed: prepare: husky install
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npm create pixi.js@latest
npm install pixi.js
npm install --save-dev @types/web
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <a href="https://pixijs.com" target="_blank" rel="noopener noreferrer">
    <img height="150" src="https://files.pixijs.download/branding/pixijs-logo-transparent-dark.svg?v=1" alt="PixiJS logo">
  </a>
</p>
<br/>
<p align="center">
  <a href="https://npmjs.com/package/pixi.js"><img src="https://img.shields.io/npm/v/pixi.js.svg" alt="npm package"></a>
  <a href="https://npmjs.com/package/pixi.js"><img src="https://img.shields.io/npm/dm/pixi.js" alt="npm downloads"></a>
  <a href="https://opencollective.com/pixijs"><img src="https://opencollective.com/pixijs/tiers/badge.svg" alt="open collective"></a>
</p>
<p align="center">
 <a href="https://pixijs.com/8.x/guides">Guides</a> | <a href="https://pixijs.com/8.x/tutorials">Tutorials</a> | <a href="https://pixijs.com/8.x/examples">Examples</a> | <a href="https://pixijs.download/release/docs/index.html">API Docs</a> | <a href="https://discord.gg/QrnxmQUPGV">Discord</a> | <a href="https://bsky.app/profile/pixijs.com">Bluesky</a> | <a href="https://x.com/pixijs">𝕏</a>
</p>

# PixiJS ⚡️
> Next-Generation, Fastest HTML5 Creation Engine for the Web

- 🚀 [WebGL](https://en.wikipedia.org/wiki/WebGL) & [WebGPU](https://en.wikipedia.org/wiki/WebGPU) Renderers
- ⚡️ Unmatched Performance & Speed
- 🎨 Easy to use, yet powerful API
- 📦 Asset Loader
- ✋ Full Mouse & Multi-touch Support
- ✍️ Flexible Text Rendering
- 📐 Versatile 
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?
