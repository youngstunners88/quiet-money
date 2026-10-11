# Motion stack (2026-10-11)

From the owner's Google Doc "Motion Studio" (nine repos). Full reasons: `repo-farm/intake/2026-10-11/decisions.md`. How to run the new look: `.claude/skills/faceless-ledger/SKILL.md`.

| Repo | Verdict | One line |
|---|---|---|
| GSAP | use | already the clock under every scene; check the licence terms by hand once |
| Playwright | use | camera for our own web pages (calculators as real b-roll) and frame QA |
| lottie-web | trial | sticker layer, only with Lottie we make ourselves |
| manim | park | right look, wrong install for a keyless runner; copy its graph grammar into GSAP |
| PixiJS | park | particles are slow in headless Chrome; not needed yet |
| WhisperX | park | only the Gemini fallback voice lacks word timings |
| anime.js | kill | duplicates GSAP |
| Theatre.js | kill | AGPL and a human-at-an-editor tool |
| theater.js | kill | typing effect GSAP already does |
| VideoDB | kill | paid cloud, sends our videos to a third party for what ffmpeg does |

## Workflow with both looks
script (one text for both looks) -> voice -> **look chosen per video** (hash of id; ledger only for math, escape, playbook, when `[production.ledger].mode = "on"`)
-> cinematic: stills + cards | ledger: hook still + every later beat drawn -> same captions, music, grade, loudness -> gauntlet -> publish -> analytics per look.

Cost honesty: measured spend to date is $11.16, of which $9.79 is OpenRouter text calls and $1.24 Muapi images; Cloudflare, Gemini, Edge and Pollinations were free.
The images the ledger look avoids are a small part of the bill. What it buys is variation and a clean test of which look holds viewers.
