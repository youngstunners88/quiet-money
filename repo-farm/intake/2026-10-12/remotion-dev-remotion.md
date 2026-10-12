# Intake: remotion-dev/remotion

- **Source:** https://github.com/remotion-dev/remotion
- **Looked at:** 2026-10-12 15:09 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE.md) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `install-hook`:** runs code when installed: prepare: git config core.hooksPath .githooks
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npx create-video@latest
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <a href="https://github.com/remotion-dev/logo">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-dark.apng">
      <img alt="Animated Remotion Logo" src="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-light.gif">
    </picture>
  </a>
</p>

[![Discord Shield](https://img.shields.io/discord/809501355504959528?color=000000&label=Discord&logo=fdgssdf)](https://remotion.dev/discord)
[![NPM Version](https://img.shields.io/npm/v/remotion.svg?style=flat&color=black)](https://www.npmjs.org/package/remotion)
[![NPM Downloads](https://img.shields.io/npm/dm/remotion.svg?style=flat&color=black&label=Downloads)](https://npmcharts.com/compare/remotion?minimal=true)
<a href="https://twitter.com/remotion"><img src="https://img.shields.io/twitter/follow/remotion?label=Twitter&color=black" alt="Twitter"></a>

Video tools for the agent era.

## Video Creation

- **Make videos agentically**: Turn your idea into a video using your coding agent.
- **Make videos interactively**: Edit and animate using drag and drop.
- **Make videos programmatically**: Connect to data, and manage complexity with code.

React Code is the source of truth. Switch your workflow at any point.

## Video Automation

- **Design systems**: Create a library of animated assets for your organization.
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-12)

**PARK**, pipeline stage: render.

The code is MIT and it is the best-known React video renderer, with a large agent-facing skill set. It would be a second renderer beside HyperFrames, which already draws our cards, so there is no new capability to buy. The intake flagged a HIGH install hook: the package runs a git config step when installed. The licence for the repo is MIT, but Remotion's own terms ask companies above a size limit to buy a company licence, and the dossier did not check that. Both points must be settled before any use.

**Worth taking:** Nothing to take that HyperFrames and the card skill do not already give us.

**Only the owner can:** Check Remotion's company-licence terms on its site by hand, and say whether the business is above the free size limit. Revisit only if HyperFrames cannot do a scene we need.
