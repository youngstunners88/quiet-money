---
name: faceless-longform
description: Build and upload Money Rules Weekly, Quiet Money's weekly 16:9 long-form episode re-cut from the week's most viewed Shorts (chapters, brand cards, thumbnail), and the weekly podcast edition. Covers the Sunday routine, the YouTube upload quota, the chapter and claim checks, and fixing a bad build. Use when the owner says long-form, weekly episode, Money Rules Weekly, watch hours, podcast episode, or when the Sunday upload did not run.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/longform.py, faceless/podcast.py
---

# Money Rules Weekly (C3) and the podcast edition (C4)

Long-form watch hours count toward the Partner Program; Shorts views go toward the separate Shorts threshold (`faceless-measure`).
The owner said yes to one long-form upload a week (2026-10-23, CLAUDE.md rule 9).

## Commands
- `python -m faceless longform build [--week YYYY-MM-DD]`: the week ending yesterday by default. It takes the passed Shorts with a
  committed final script, ranks them by measured views (latest reading per platform, summed) and keeps the top seven. Each story is
  voiced in one call. Cards are cut on the voice's word timings. Output in `distribution/longform/<week>/`: `episode.mp4`
  (gitignored), `thumbnail.jpg`, `EPISODE.md`, `episode.json`.
- `python -m faceless longform post [--apply] [--at ISO]`: a dry run without `--apply`. It refuses copy problems, a pause, and a week
  already posted (`state/longform-posts.jsonl`). It builds first if the mp4 is missing. It uploads through the channel-guarded upload,
  category Education, with AI content declared, then sets the thumbnail and adds the video to the Money Rules Weekly playlist (a
  refusal there is noted, never fatal).
- `python -m faceless podcast build [--week D]`: the audio edition (mp3 gitignored, `EPISODE.md` with chapters). Uploading it is the
  owner's step until a podcast host exists (gate `podcast`).

## The Sunday routine (06:41 UTC)
Build, look at three frames and the thumbnail, wait until 07:00:30 UTC, then `post --apply`. The upload quota belongs to Composio's
shared Google project and runs out within minutes of the reset, so the episode goes first. An HTTP 429 is waited out, never worked
around; schedule the retry for the next reset.

## Checks that hold an upload (`longform.problems`)
Title at most 100 characters, at most one link (rule 13), the claim check on our own words (chapter titles already passed the gauntlet
with their Shorts), chapters from 0:00, at least three, each at least 10 s including the last. Intro and outro are padded to 10.5 s.

## When something is wrong
- Fewer than 3 stories: the week was thin; report it, never pad with held videos.
- The free voice drops a call: `voice_all` retries once after 20 s; a second failure fails the build, so run it again.
- A wait loop on `pgrep -f "longform build"` matches its own shell; wait on the output file instead.
- Text clipped on a card: the fit loop shrinks to 36 px; shorten the line in the script, never the font floor.
