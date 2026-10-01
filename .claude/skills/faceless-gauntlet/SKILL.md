---
name: faceless-gauntlet
description: Run the quality gauntlet loop on Quiet Money videos. Read gate reports, inspect frames and audio, find root causes in scripts, prompts, or engine code, fix them, and re-run until videos pass. Use when videos are held, scores drop, or when asked to "perfect", "harden", or "stress test" the pipeline.
---

# Gauntlet loop

The gauntlet has two levels:
- **Per video** (automatic): `faceless/gauntlet.py` gates + up to 2 rewrite rounds.
- **Ops** (this skill): you improve the engine itself so the next 100 videos pass on the first try.

## Loop
1. **Produce**: `python -m faceless daily --no-publish` (or `make` for one pillar).
2. **Measure**:
   - `gauntlet/reports/daily-<day>.md` and each `<job_id>.md`: failing gates.
   - `grep -E "PROVIDER_FAIL|JOB_FAILED|VOICE_REFIT" state/journal.jsonl | tail`: infra problems.
   - Look at frames: build a contact sheet of 8 frames per video and read it as an image. Check hook box,
     caption breaks, callout overflow, image/narration match, artifacts, first frame.
   - Loudness: `ffmpeg -i final.mp4 -af ebur128 -f null - 2>&1 | grep -A2 Integrated` (target -14 LUFS).
   - Speed: stage timestamps in the journal (target < 3.5 min per video).
3. **Diagnose the root cause**, not the symptom: a failing gate on 3 of 5 videos is a prompt or code bug.
4. **Fix** in the smallest place: prompt (`faceless/prompts.py`), config (`studio.toml`), stage code, or gate.
   Only loosen a gate if the gate itself is measuring the wrong thing (record why).
5. **Re-run** only what changed (cached images make re-renders cheap). Repeat until all pass.
6. **Log** the round in `gauntlet/CONTEXT.md` → Log (what failed, what changed, result), then run
   `python -m pytest -q tests` before committing.

## Common fixes
| Symptom | Fix |
|---|---|
| duration outside 61-72 s | adjust `words_range` / `edge_rate`; check `VOICE_REFIT` speeds stay within 0.95-1.18 |
| judge_facts fails | add a fact sheet entry in `moneymath.py`; tighten the topic in the backlog |
| captions clipped/odd breaks | `caption_chars_max`, `chunk_words()` |
| image ignores the subject | put the key object first in `visual`; make it concrete |
| provider failures | check keys and quotas (`python -m faceless status`), chain order in `studio.toml` |
