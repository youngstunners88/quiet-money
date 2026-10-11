# Intake: t3knobox/klik-anim-skill-creation

- **Source:** https://github.com/t3knobox/klik-anim-skill-creation
- **Looked at:** 2026-10-11 12:38 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `license-unknown`:** no LICENSE file at the top level and the API was not reachable: check by hand
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only

## Commands its docs tell you to run (read, do not run)

```
npx remotion skills add        # or: npx skills add remotion-dev/skills
npx remotion skills update     # pull newer Remotion patterns later
git clone https://github.com/t3knobox/klik-anim-skill-creation
npx remotion skills update                         # keep Remotion's skills current too
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# Klik Motion-Graphics System

Claude skills for producing industry-standard motion graphics with
[Remotion](https://www.remotion.dev/).

| Skill | What it does | Requires |
|---|---|---|
| **`klik-anim`** | Element-animation craft: laws for everything that moves **within** the shot (easing, timing, choreography, hierarchy, gaze path, reading holds, device ledger, boundaries, material & finish + effect recipes) + pre-flight checklist. Auto-triggers on any Remotion/animation work. | Nothing — standalone |
| **`klik-cam`** | Camera-movement craft: the camera dial (C0, 1–5) and camera grammar — signature variation, focus discipline, 3D hygiene, shutter blur — + CAM checklist. | `klik-anim` (its base laws bind the camera) |
| **`klik-remotion-method`** | End-to-end video production from a prompt: Discovery (fixed questioning → SSOT) → visual storyboard approved as **rendered stills** → frozen execution plan → build on Opus (timing contract first) → QA in a fresh context. Decides **what** gets made and in what order. | `klik-anim` + `klik-cam` |

**Choose your install:**
- Only want great single animations → **Option A** (klik-anim + klik-cam).
- Want full videos created end-to-end → **Option B** (all three).

**Heads up — tokens & models:**
- Producing videos of ~30 seconds or longer **will run you out of session
  usage limits a few times** — animations eat tokens like they're fre
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [x] **PARK**: useful later; name the phase
- [ ] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-11)

**PARK**, pipeline stage: render.

No licence file found and no README text the dossier could judge; unverified.

**Worth taking:** Unknown.

**Only the owner can:** Check the licence and README by hand before using any of it.
