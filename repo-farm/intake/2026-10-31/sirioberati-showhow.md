# Intake: sirioberati/showhow

- **Source:** https://github.com/sirioberati/showhow
- **Looked at:** 2026-10-31 04:26 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npm install
pip3 install numpy Pillow
claude mcp add showhow -- node "$(pwd)/mcp/server.mjs"
python3 scripts/voice.py my-reel        # ElevenLabs, voice id in reels/my-reel/reel.json
python3 scripts/tighten.py my-reel
python3 scripts/align.py my-reel
python3 scripts/check.py plan my-reel
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
<p align="center"><img src="docs/banner.png" alt="showhow, from tein" width="100%"></p>

# showhow

**Explainer reels drawn in code.** You write the script. An agent draws the scenes. Showhow voices it, times every move to
a spoken word, renders it at 1080×1920 and 60 fps, and checks it before anyone sees it. No presenter, no stock footage,
no cuts.

Free and open source, from [tein](https://tein.ai): one cheap API, MCP and workflows for every AI model provider.

<p><a href="https://tein.ai/waitlist"><img src="docs/join-tein.png" alt="Join tein" height="52"></a></p>

## Watch

Two full reels, with voice and music, made with the same engine and checks. Click one to watch it with sound.

<p align="center">
<a href="https://sirioberati.github.io/showhow/#airplanes"><img src="docs/airplanes.gif" alt="How a wing really makes lift" width="220"></a>
<a href="https://sirioberati.github.io/showhow/#world"><img src="docs/world.gif" alt="What if the Earth were flat?" width="220"></a>
</p>

- **[How a wing really makes lift ▶](https://sirioberati.github.io/showhow/#airplanes)** · 65 s. The myth, the Cambridge smoke test, pressure, speed and flaps.
- **[What if the Earth were flat? ▶](https://sirioberati.github.io/showhow/#world)** · 58 s. On a disc of rock, gravity pulls toward the pole.

## The demos

Three reels ship in this repo, voiced and timed, so each one renders with no key. Every 
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-31)

**PARK**, pipeline stage: render.

MIT. Code-drawn explainer reels with word-timed scenes, a 60 fps render and a check file with measured thresholds. We already draw word-synced scenes in code (cards.py, cast.py, the Ledger series on HyperFrames), voice with word timings, and gate every video. It installs an MCP server (claude mcp add) and uses ElevenLabs, which is out of quota; neither is needed. Its README carries a promo for tein.ai. Nothing cloned or run.

**Worth taking:** Check rules that carry a measure and a threshold set from approved videos (camera speed, how long a picture holds still, colour strength, voice loudness), run frame by frame, with the report listing what failed. Map them onto craftcheck.py and the gauntlet; tiers (express, standard, studio) for render effort.

**Only the owner can:** operator
