---
name: showhow-extension
description: Extend Quiet Money with 3 additional daily Showhow-style code-drawn explainer reels (motion graphics, word-synced canvas animation). This is an additive lane only — never replace or reduce the existing 5 faceless videos. Use when asked to "run the showhow lane", "make the extra 3", "showhow batch", "motion graphics shorts", or to produce higher-retention explainer variants alongside the daily machine.
---

# Quiet Money × Showhow Extension (Additive Lane)

**This is an extension, not a replacement.**

- The core Quiet Money machine continues to produce its **5 daily videos** exactly as before (`python -m faceless daily`).
- This skill adds a parallel **Showhow lane** that produces **3 additional** high-retention, code-drawn explainer Shorts per day.
- Total daily output target becomes **8 videos** (5 classic + 3 Showhow).
- All Quiet Money cost ceilings, gauntlet rules, pause switch, compliance gates, and brand rules remain in force.
- Showhow content must still pass Quiet Money’s gauntlet (or a compatible subset) before packaging.

## Why this exists

The classic lane (Ken Burns + FLUX stills) is cheap and reliable.  
The Showhow lane (Remotion + canvas/React, every move timed to a spoken word) produces tighter, more “premium” math/psychology explainers that retain better. Running both increases volume and average quality without raising the daily spend ceiling.

## Scope & limits (non-negotiable)

| Rule | Detail |
|------|--------|
| Additive only | Never skip, reduce, or replace any of the 5 classic slots |
| Count | Exactly 3 Showhow reels per day (or fewer if the day is short on approved topics) |
| Length | 55–72 seconds (match Quiet Money target) |
| Format | Vertical 1080×1920, 60 fps preferred |
| Voice | Prefer existing Quiet Money neural TTS + word timings when possible. ElevenLabs only if explicitly enabled and within budget |
| Cost | Must stay inside the studio-wide $3 daily ceiling and free-tier preference. Prefer canvas path over heavy 3JS |
| Brand | Same pillars, same compliance (no advice language, no promised returns, educational only) |
| Output location | `production/showhow/<YYYY-MM-DD>/` and posting packs under `distribution/queue/<day>/showhow-` |
| Gauntlet | Every finished reel must be checked. Prefer full Quiet Money gauntlet; at minimum run Showhow’s own motion/loudness/cut checks + Quiet Money originality + compliance gates |

## Prerequisites

1. Showhow engine available (clone or submodule under `repo-farm/showhow` or `tools/showhow`).
2. Node 22+, Python 3, ffmpeg, and the Showhow dependencies installed in the environment that runs Claude Code.
3. Quiet Money environment already healthy (`python -m faceless doctor` passes).
4. Optional: ElevenLabs key only if the classic neural TTS is insufficient for the lane.

## Daily workflow (run after or in parallel with faceless-daily)

### 0. Pre-flight
```bash
python -m faceless preflight
python -m faceless doctor
# Confirm studio is not paused and spend headroom remains
```

If the classic 5 are not yet running or finished, start them first. This lane never blocks the main machine.

### 1. Topic selection (3 slots)
- Pull from the same backlog / pillars as the classic lane, but prefer topics that benefit from precise visual explanation:
  - “The Math They Hide”
  - “Money Myths”
  - “Escape the Rat Race” frameworks
  - Clear cause → effect or number-driven stories
- Prefer topics already researched for the classic lane so research tokens are not doubled.
- Record the three chosen topics in `script-lab/showhow-batch-<day>.md`.

### 2. Script
- Write (or adapt) three short, spoken scripts.
- First sentence = strong hook that names the topic.
- Keep language educational, numbers concrete, no advice framing.
- Save under `script-lab/showhow/<slug>/script.txt` (or feed directly into Showhow’s expected layout).
- Get owner approval only on the first run of a new series or when the script changes the claim; otherwise proceed under standing orders.

### 3. Voice + word timings
- Prefer Quiet Money’s existing TTS + word-timing pipeline so the lane stays inside current providers.
- Fallback: Showhow’s `python3 scripts/voice.py` + tighten + align only if the classic TTS cannot supply word-level timestamps.
- Output must produce a reliable `words.json` (or equivalent) that Showhow can key animations to.

### 4. Plan & scenes (Showhow)
Follow the Showhow skill order:
1. Write `caption.txt` (blocks keyed to spoken words).
2. `plan.md` — one continuous world where possible.
3. Implement scenes as pure React/canvas components driven by `cue("word")`.
4. Prefer the fast **canvas** path. Use 3JS only for a single hero reel if the day’s budget allows.
5. Produce half-size DRAFT first (`node draft.mjs <slug>`).
6. Full render only after DRAFT is acceptable (`node render.mjs <slug>`).
7. Run every Showhow check (`check.py plan`, motion, joins, loudness). Fail → fix → re-render.

### 5. Quiet Money quality gate
After a Showhow reel is rendered:
```bash
# Adapt path as needed for the integration layer
python -m faceless gauntlet <job_id>   # or the showhow-compatible entry point
```
Minimum required gates even if full gauntlet is not yet wired:
- Duration, hook strength, originality, compliance (no advice / no promised returns)
- Loudness (−14 LUFS target)
- No freeze / no cut / no text-over-number violations
- AI-label readiness

Held or failed reels do **not** count toward the 3. Replace them with a fresh topic or repair.

### 6. Packaging & distribution
- Place final MP4s and metadata into the same posting-pack structure used by the classic lane, but clearly namespaced:
  - `distribution/queue/<day>/showhow-01/`, `showhow-02/`, `showhow-03/`
- Run the offer skill so every Showhow video also leaves with an offer line.
- Do **not** auto-post. Follow the same local-pack → owner review → phone/upload flow as the classic 5.
- Commit only text/state/reports (never media).

### 7. Report
At the end of the routine, report both lanes:

```
Classic lane: 5/5 shipped (or X held)
Showhow lane: 3/3 shipped (or Y held / Z failed)
Total for day: N videos packaged
Spend so far: $X.XX / $3.00 ceiling
Next action: …
```

## Integration points (what to wire once)

| Quiet Money path | Showhow extension action |
|------------------|--------------------------|
| `python -m faceless daily` | Continues unchanged for the original 5 |
| `script-lab/` | Add `showhow/` subfolder for the extra 3 scripts |
| `production/` | Add `showhow/<day>/` for renders and drafts |
| `gauntlet/` | Accept Showhow job IDs or run a thin adapter |
| `distribution/queue/` | Namespace packs with `showhow-` prefix |
| `.claude/skills/` | This skill lives alongside `faceless-daily` |
| CLAUDE.md routing table | Add row: “Extra 3 motion-graphics explainers → showhow-extension” |
| Cost ledger | Tag Showhow jobs so the $3 ceiling and per-provider caps still apply |

## Never

- Never reduce the classic 5 to free capacity for Showhow.
- Never raise the daily spend ceiling or un-pause the studio without owner instruction.
- Never publish a held Showhow reel.
- Never commit MP4 / WAV / large image assets.
- Never use paid image or video models when the pure canvas path can deliver the idea.
- Never let Showhow topics drift outside Quiet Money’s six pillars or compliance rules.

## First-time setup checklist (owner / Claude Code)

1. Clone showhow into `repo-farm/showhow` (or preferred tools location).
2. Install its Node + Python dependencies in the Claude Code environment.
3. Confirm a single test reel can be drafted and rendered.
4. Wire a thin adapter so finished Showhow MP4s can be handed to the existing gauntlet / packaging code.
5. Add this skill directory under `.claude/skills/showhow-extension/`.
6. Update CLAUDE.md routing table with one line pointing to this skill.
7. Run one end-to-end test day producing the classic 5 + 1 Showhow reel before enabling the full +3.

## Success metric

The day is successful when:
- Classic 5 are produced and packaged as usual, **and**
- Exactly 3 additional Showhow reels are produced, checked, and packaged under the same cost and compliance roof.

Volume up. Quality floor maintained. Cost ceiling respected. That is the only goal of this extension.
