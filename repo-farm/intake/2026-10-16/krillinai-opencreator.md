# Intake: krillinai/OpenCreator

- **Source:** https://github.com/krillinai/OpenCreator
- **Looked at:** 2026-10-16 05:33 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | Apache-2.0 (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
pnpm --version
git clone https://github.com/krillinai/OpenCreator.git
pnpm install
pnpm web:dev
pnpm daemon:dev
pnpm desktop:dev
pnpm --filter @opencreator/daemon test -- test/smoke/real-codex-smoke.test.ts
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<div align="center">

<h1>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./docs/images/OpenCreator_logo_vector_dark.svg" />
    <img src="./docs/images/OpenCreator_logo_vector.svg" alt="OpenCreator" width="380" />
  </picture>
  <br />
  The open-source AI workspace & Skills for creators
</h1>

<p>Bring visual settings, reusable Skills, and Agents together for scripts, video, images, voice, translation, and editing—all in one workspace.</p>

<p><strong>OpenCreator was formerly known as KrillinAI.</strong></p>

<a href="https://trendshift.io/repositories/13360" target="_blank"><img src="https://trendshift.io/api/badge/repositories/13360" alt="OpenCreator, formerly KrillinAI: #1 Repository of the Day on Trendshift" width="250" height="55" /></a>

**English** | [简体中文](./docs/zh/README.md) | [日本語](./docs/ja/README.md) | [한국어](./docs/ko/README.md) | [Bahasa Indonesia](./docs/id/README.md) | [Español](./docs/es/README.md) | [Français](./docs/fr/README.md) | [Deutsch](./docs/de/README.md) | [Português](./docs/pt/README.md) | [Русский](./docs/ru/README.md) | [العربية](./docs/ar/README.md) | [ภาษาไทย](./docs/th/README.md) | [Türkçe](./docs/tr/README.md) | [हिन्दी](./docs/hi/README.md) | [বাংলা](./docs/bn/README.md) | [اردو](./docs/ur/README.md) | [Tiếng Việt](./docs/vi/README.md) | [Filipino](./docs/fil/README.md)

[![GitHub Stars](https://badgen.net/github/stars/
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-16)

**PARK**, pipeline stage: render.

Apache-2.0. A desktop and web workspace built on Codex CLI, with ten creator tools (video translation to 101 languages, downloader, thumbnails, image and video generation, article, script, stick figure animation, dubbing). It needs a ChatGPT or Codex sign-in, its own account and credits through open-creator.ai, and paid image, video and voice services, so it is a second agent and a second bill beside our headless engine, not something to fork into it. The downloader pulls videos from other platforms, which stays out of scope for us. Skills text and templates were not read.

**Worth taking:** Three lanes to rebuild in our own code. (1) Stick figure animation: our comics already draw consistent stick figures as SVG, so a comic can become a 15-30 second animated Short (panel reveal, text typed, voice) with HyperFrames and ffmpeg at no per-video cost. (2) Video translation and dubbing: the same Shorts in Spanish and Portuguese with Edge voices and translated captions, a reach lever with no new model. (3) Versioning every revision instead of overwriting, for scripts. The repo's skills/ folder (subtitle, tts, render, cover) should be read once, text only, before copying any wording.

**Only the owner can:** Pick which lane to build first. Recommended: comics to animated Shorts.
