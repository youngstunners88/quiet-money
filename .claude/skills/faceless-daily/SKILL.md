---
name: faceless-daily
description: Produce, gate, and package the Quiet Money channel's daily batch of 5 faceless videos, then report what shipped. Use when asked to "run today's videos", "make the daily batch", "produce videos", or when a scheduled run needs checking or repair.
---

# Faceless daily run

Produces the day's videos end to end with the repo root and leaves posting packs in
`distribution/queue/<day>/`.

## Steps
0. `python -m faceless preflight` (add `--offline` to skip the wallet call). It prints a traffic light per check, with the fix for each, and writes nothing.
   Any FAIL: stop and follow `references/failure-playbook.md` before starting. WARN lines go into your report. If the studio is paused
   (`state/PAUSE`), do not resume it: report the reason and stop.
1. `python -m faceless doctor`. Fix any `ERR` line before continuing
   (`pip install -r requirements.txt`; ffmpeg via apt). Missing optional keys are fine.
2. Run the batch: `python -m faceless daily` (5 videos; `--count N` to change, `--no-publish` to only package).
   Expect ~3-5 minutes per video. Run it in the background for full batches. It resumes: re-running only
   fills today's slots that have no finished video (held/failed slots get a fresh topic).
   `--extra N` makes N more now; they bank into the next free posting slots (tomorrow's first), and the
   next daily run skips slots that are already banked.
3. Read `gauntlet/reports/daily-<day>.md`. For every row that is not `published`:
   - `held`: open `gauntlet/reports/<job_id>.md`, read the failing gates, then use the `faceless-gauntlet` skill.
   - `failed`: `grep JOB_FAILED state/journal.jsonl | tail -3` shows the trace; fix the root cause, then
     re-run `python -m faceless daily` (it refills only the open slots).
4. Spot-check at least one video visually: extract frames at 0.5 s, 3 s, mid, and end
   (`ffmpeg -ss <t> -i final.mp4 -frames:v 1 frame.jpg`) and look at them: hook box readable, captions not
   clipped, images match the narration, no text artifacts in images.
5. Check the supply and QA: `python -m faceless doctor` shows the Muapi wallet and whether the semantic checks are on. A video's `images.json` rows carry `qa` and
   `qa_swapped` (stills replaced by cards because a decision model saw text, a face or a logo). If Muapi's wallet is under 21 days of runway the weekly scout proposes a top-up (owner).
6. Report: titles, scores, durations, spend (`python -m faceless status`), and anything held.

## Delivering videos
- Posting packs: `distribution/queue/<day>/slot<N>-<pillar>/` (video.mp4, POST.md, cover.jpg).
- Chat upload limit is 30 MB: re-encode a copy with
  `ffmpeg -i video.mp4 -c:v libx264 -crf 22 -maxrate 6M -bufsize 12M -c:a copy out.mp4` if needed.

## Scheduled routine run (the default runner)
The batch runs daily as a Claude Code routine in the owner's cloud environment, which already holds the API
keys as environment variables, so no key is stored on GitHub. `.claude/hooks/session-start.sh` installs the
Python dependencies when the session starts. In a routine session:
1. Steps 1-4 above.
2. Commit `state/`, `script-lab/`, `gauntlet/reports/` and `analytics/` (never media) and push to `main`;
   the push rebuilds the website. If the push is rejected, the remote moved: `git fetch origin main`, rebase onto it (the logs in
   `state/` merge by union, so both sessions' lines survive), run the tests, push again. Never force-push.
   `python -m faceless watchdog` should say `healthy` afterwards; the same check runs every six hours on GitHub and opens an "Ops alert" issue
   when it does not.
3. Send the finished `video.mp4` files to the owner (re-encode any copy over 30 MB), then report as in step 5.

### Also in every routine run (the printing press)
- **Repurposing kit**: each published pack gets `<pack>/kit/` automatically (thread, LinkedIn post, newsletter item, pin, carousel, audio).
  If a pack lacks one, run `python -m faceless kit <post day>`. Commit the kit's text files (images and audio are gitignored).
- **Flow lane**: owner-made clips in `channel/flow/inbox/` are claimed as hook shots by the next video of their series. Run
  `python -m faceless flow` (writes `channel/flow/shotlists/<today>.md`, commit it) and `python -m faceless flow status`, and put
  the 3 prompts and the clip count in the report so the owner can run their own Google Flow session. Never log in to Flow for them.

## When something breaks
`references/failure-playbook.md` maps each symptom to its cause and the safe move. The studio has a kill switch (`python -m faceless pause "reason"`,
`--resume` to undo), a $3 daily spend ceiling across all providers, and per-provider caps; a refusal from any of them is the system working.

## Never
- Never resume a paused studio, raise a spend cap, or turn on posting or hook clips without the owner's yes.
- Never publish a `held` video without fixing its hard gates.
- Never commit media (mp4/wav/jpg); state, scripts, and reports are what get committed.
