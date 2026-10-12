# Intake: whaleyxbt/claude-motion

- **Source:** https://github.com/whaleyxbt/claude-motion
- **Looked at:** 2026-10-12 15:09 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `hidden-comment`:** a 137-character HTML comment, invisible when rendered: read it
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npm install && npx playwright install chromium
npm run sims                                                    # → sims/dist/<name>.html
npm run capture -- engine --size 1080x1350 --out out/engine.mp4  # 1440×1800, 60 fps
git clone https://github.com/whaleyxbt/claude-motion && cd claude-motion
npm install
npm run build        # the example video with sound → out/effort.mp4
npm run studio       # live preview
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# claude-motion

**A motion design toolkit for coding agents.** Remotion skills teach your agent the API. This teaches it taste, makes it check its own frames, and gives it a sound engine. And when the idea is a simulation, not a motion graphic, it renders web sims frame by frame to 60 fps video.

Works with Claude Code and Cursor out of the box (skills in `.claude/skills/`), and with Codex, OpenCode or anything else that reads `AGENTS.md`.

<p align="center">
  <img src="media/preview.gif" width="480" alt="22-second motion graphic made by Claude with this toolkit" />
</p>

<p align="center"><sub>Made by Claude with this toolkit from one prompt and one revision. No After Effects, no stock sounds. <a href="examples/01-effort/">How it was made →</a></sub></p>



## New: web sims → 60 fps video

<p align="center">
  <img src="media/sims/crawlers.gif" width="250" alt="256 spider agents crawling a wall of websites" />
  <img src="media/sims/dossier.gif" width="250" alt="Agents turning one username into a dossier with red threads" />
  <img src="media/sims/engine.gif" width="250" alt="Camera flying through a running rocket engine's chamber" />
</p>

<p align="center"><sub>Made by Claude with this toolkit. Left: <a href="https://x.com/whaleyxbt/status/2106099822088331481">the crawler swarm</a> (340K+ views on X). Middle: <a href="https://x.com/whaleyxbt/status/2106420024286031963">one
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-12)

**PARK**, pipeline stage: render.

MIT. A motion design toolkit for coding agents: skills that teach taste, a self-check of its own frames, a sound engine, and web simulations rendered to 60 fps video through Playwright. It is the most ambitious of the set and overlaps our render. The intake found a 137-character HTML comment that is invisible when rendered; by intake rule its content must be read by a person before any trial, and the install line runs the newest code on every use. Parked until the comment is read.

**Worth taking:** The sound engine idea (every effect placed at a measured peak) and the 'web sim to 60 fps' capture are worth a look once the code is read; both can be done with our existing tools.

**Only the owner can:** A person reads the repo's hidden comment and the sound engine's code (text only). Then decide whether a trial is worth the time.
