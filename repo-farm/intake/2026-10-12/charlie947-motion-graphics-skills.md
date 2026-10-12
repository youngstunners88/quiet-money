# Intake: charlie947/motion-graphics-skills

- **Source:** https://github.com/charlie947/motion-graphics-skills
- **Looked at:** 2026-10-12 15:09 UTC (public metadata and text only; nothing was cloned, installed or run)
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
npx skills add charlie947/motion-graphics-skills
git clone https://github.com/charlie947/motion-graphics-skills.git
npx skills add emilkowalski/skills --skill apple-design
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
  <a href="https://charliehills.substack.com">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/readme/hero-dark.png">
      <source media="(prefers-color-scheme: light)" srcset="assets/readme/hero-light.png">
      <img alt="Motion Graphics Skill Pack by Charlie Hills" src="assets/readme/hero-light.png" width="100%">
    </picture>
  </a>
</p>

<h1 align="center">Motion Graphics Skill Pack</h1>

<p align="center">
  <strong>15 skills that make launch-grade motion graphics with Claude Code. Every frame is code.</strong>
</p>

<p align="center">
  <a href="https://github.com/charlie947/motion-graphics-skills/stargazers"><img src="https://img.shields.io/github/stars/charlie947/motion-graphics-skills?style=flat-square&color=D97557&labelColor=00132F&label=stars" alt="GitHub stars"></a>
  <img src="https://img.shields.io/badge/skills-15-D97557?style=flat-square&labelColor=00132F" alt="15 skills">
  <img src="https://img.shields.io/badge/runs_in-Claude_Code_%C2%B7_Codex-58B6FF?style=flat-square&labelColor=00132F" alt="Runs in Claude Code and Codex">
  <a href="LICENSE"><img src="https://img.shields.io/github/license/charlie947/motion-graphics-skills?style=flat-square&color=FFFFFF&labelColor=00132F" alt="Licence"></a>
  <a href="https://charliehills.substack.com"><img src="https://img.shields.io/badge/newsletter-71k_readers-FFD11A?styl
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-12)

**PARK**, pipeline stage: render.

MIT. Fifteen skills for motion graphics written as code, aimed at Claude Code and Codex. The value is the craft text in the skills, which the intake did not read (only the README header was scanned). The install line `npx skills add` runs the newest published code on every use, so nothing should be installed as it stands. The README also suggests a second pack from another owner, which would need its own intake.

**Worth taking:** Unknown until the skill text is read. Candidate: the craft rules for timing and easing, if they are written as rules rather than as a sales page.

**Only the owner can:** Read the skill files on the repo page (text only, nothing installed) and say which one is worth a full intake of its own.
