# Intake: airbnb/lottie-web

- **Source:** https://github.com/airbnb/lottie-web
- **Looked at:** 2026-10-11 11:47 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| npm_name | lottie-web |
| license | MIT (read from LICENSE.md) |
| pushed | 2025-05-21T17:23:47.456Z |
| weekly_downloads | 6266291 |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **MED `stale`:** last change 1.4 years ago
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
brew tap danielbayley/adobe
brew cask install lottie
npm install lottie-web
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Lottie for Web, [Android](https://github.com/airbnb/lottie-android), [iOS](https://github.com/airbnb/lottie-ios), [React Native](https://github.com/airbnb/lottie-react-native), and [Windows](https://aka.ms/lottie)

Lottie is a mobile library for Web,  and iOS that parses [Adobe After Effects](https://www.adobe.com/products/aftereffects.html) animations exported as json with [Bodymovin](https://github.com/airbnb/lottie-web) and renders them natively on mobile!

For the first time, designers can create **and ship** beautiful animations without an engineer painstakingly recreating it by hand. They say a picture is worth 1,000 words so here are 13,000:



# View documentation, FAQ, help, examples, and more at [airbnb.io/lottie](https://airbnb.io/lottie/)



![Example1](gifs/Example1.gif)


![Example2](gifs/Example2.gif)


![Example3](gifs/Example3.gif)


![Community](gifs/Community%202_3.gif)


![Example4](gifs/Example4.gif)


# Plugin installation

### Option 1 (Recommended):
**Download it from from aescripts + aeplugins:**
https://aescripts.com/bodymovin/

### Option 2:
**Or get it from the adobe store**
https://exchange.adobe.com/creativecloud.details.12557.html
CC 2014 and up.

## Other installation options:

### Option 3:
- download the ZIP from the repo.
- Extract content and get the .zxp file from '/build/extension'
- Use the [ZXP installer](https://aescripts.com/learn/zxp
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [x] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-11)

**TRIAL**, pipeline stage: render.

MIT, plays After Effects JSON animations in a page, and goToAndStop(frame) makes it seek-safe like GSAP. Value is a sticker layer (coin, arrow, check, stamp) that gives motion-designer polish without a designer. Two cautions: the last release was 2025-05 (stable, not abandoned, but not moving) and free Lottie libraries carry mixed licences, so only animations we generate ourselves or ones whose licence is read and recorded may ship. The earlier diffusionstudio/lottie dossier (text to our own Lottie) is the clean source.

**Worth taking:** Own-made Lottie stickers: no licence question, no per-asset cost.

**Only the owner can:** Trial in a sandbox copy: five stickers, rendered inside a card, frames checked.
