# Intake: theatre-js/theatre

- **Source:** https://github.com/theatre-js/theatre
- **Looked at:** 2026-10-11 11:47 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| npm_name | theatre-monorepo |
| license | AGPL-3.0 (read from LICENSE) |
| pushed | 2023-01-24T21:19:42.102Z |
| weekly_downloads | 1 |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `install-hook`:** runs code when installed: postinstall: husky install && yarn workspace @theatre/app run prisma generate && yarn workspa
- **MED `restrictive-license`:** copyleft or non-commercial terms: read before using in a paid product
- **MED `stale`:** last change 3.7 years ago
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<h1 align="center">
  <a href="https://github.com/theatre-js/theatre#gh-dark-mode-only"><img src="https://raw.githubusercontent.com/theatre-js/theatre-docs/main/docs/.vuepress/public/public/theatrejs-logo-white.svg" alt="Theatre.js" width="200"></a><a href="https://github.com/theatre-js/theatre#gh-light-mode-only"><img src="https://raw.githubusercontent.com/theatre-js/theatre-docs/main/docs/.vuepress/public/public/theatrejs-logo-black.svg" alt="Theatre.js" width="200"></a>
</h1>
<p align="center">Motion Design, for the web</p>
<p align="center">
 <a href="#"><img alt="GitHub branch checks state" src="https://img.shields.io/github/checks-status/theatre-js/theatre/main?label=build"></a>
 <a href="https://discord.gg/Tku4CJKf4B"><img src="https://img.shields.io/discord/870988717190426644?label=Discord" alt="Join us on Discord"></a>
 <a href="https://twitter.com/theatre_js">
   <img alt="Follow Theatre.js on Twitter" src="https://img.shields.io/twitter/url?label=%40theatre_js&url=https%3A%2F%2Ftwitter.com%2Ftheatre_js">
 </a>
 <a href="https://www.youtube.com/channel/UCsp9XOCs8v2twyq5kMLzS2Q">
  <img src="https://img.shields.io/youtube/channel/views/UCsp9XOCs8v2twyq5kMLzS2Q?label=YouTube&style=social" alt="Watch on YouTube">
 </a>
 
</p>

> ✨ Update: Theatre.js 1.0 is around the corner. We have _temporarily_ moved development to a private repo so we can iterate faster. We'll push ou
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?
