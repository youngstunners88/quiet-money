# Intake: 3b1b/manim

- **Source:** https://github.com/3b1b/manim
- **Looked at:** 2026-10-11 11:47 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE.md) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `build-time-code`:** installs by running its own script (install.sh / setup.py / source-only release): read it before use
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
pip install manimgl
pip install -e .
git clone https://github.com/3b1b/manim.git
python3 -m pip install -e .
python3 -m venv venv
brew install ffmpeg mactex
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center">
    <a href="https://github.com/3b1b/manim">
        <img src="https://raw.githubusercontent.com/3b1b/manim/master/logo/cropped.png">
    </a>
</p>

[![pypi version](https://img.shields.io/pypi/v/manimgl?logo=pypi)](https://pypi.org/project/manimgl/)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](http://choosealicense.com/licenses/mit/)
[![Manim Subreddit](https://img.shields.io/reddit/subreddit-subscribers/manim.svg?color=ff4301&label=reddit&logo=reddit)](https://www.reddit.com/r/manim/)
[![Manim Discord](https://img.shields.io/discord/581738731934056449.svg?label=discord&logo=discord)](https://discord.com/invite/bYCyhM9Kz2)
[![docs](https://github.com/3b1b/manim/workflows/docs/badge.svg)](https://3b1b.github.io/manim/)

Manim is an engine for precise programmatic animations, designed for creating explanatory math videos.

Note, there are two versions of manim.  This repository began as a personal project by the author of [3Blue1Brown](https://www.3blue1brown.com/) for the purpose of animating those videos, with video-specific code available [here](https://github.com/3b1b/videos).  In 2020 a group of developers forked it into what is now the [community edition](https://github.com/ManimCommunity/manim/), with a goal of being more stable, better tested, quicker to respond to community contributions, and all around friendlier to 
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-11)

**PARK**, pipeline stage: render.

MIT and the right look for compounding and rule-of-72 graphs, but it is the OpenGL edition (ManimGL), built for a person at a desktop; the pipeline-friendly fork is Manim Community (cairo, pango, optional LaTeX), which needs system libraries and an install the keyless CI runner does not have. The graphs and number lines it is known for are reproducible in GSAP/SVG (cards already draw a compounding curve), and equations can use KaTeX in the page with no LaTeX install.

**Worth taking:** Its visual grammar: axes that draw themselves, a curve that traces, a number line that fills. Add these as ledger card kinds.

**Only the owner can:** Revisit if a sample of the ledger look still lacks equation morphing after KaTeX. Then trial Manim Community in a container build, not on every run.
