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

Cost honesty (corrected 2026-10-11 from `state/ledger.jsonl`): spend to date is $11.16. $9.79 of it was OpenRouter **images** (243 stills at $0.04) on 1 to 7 October,
before Muapi (about half a cent a still) joined the image chain on 8 October; since then OpenRouter images are a handful a day. Muapi is $1.24 so far (about $0.50 a day),
OpenRouter text and sketch calls are cents; Cloudflare, Gemini, Edge and Pollinations were free. The ledger look draws almost no stills, so it would cut the Muapi line too,
but that line is already small; its value is variation and a clean test of which look holds viewers.
