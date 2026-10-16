---
name: faceless-quinton-weekly
description: The weekly drop from Quinton, Quiet Money's virtual host. Every Monday the routine writes his ten-second message, renders it with his locked face, voice and look, checks the frames, and registers it so the normal publisher posts it. Use for "the weekly drop", "Quinton's weekly video", "Monday host clip", or when the weekly host clip did not run.
---

# Quinton's weekly drop

Quinton is the host (bible: `channel/host/BIBLE.md`; the four locks and the commands are in `faceless-host`). The owner asked for the weekly drop on 2026-10-16, so `[host] enabled = true` in `studio.toml` and the routine "Quinton weekly drop" runs on Mondays (`[host] weekday = 0`).

## Steps (one run, about $0.75-$1.50)
1. `git pull --rebase origin main`; stop if `state/PAUSE` exists. `python -m faceless host status` must show the photo, voice profile, character and voice anchor.
2. Only if `host.due()` is true (it is Monday and this week's clip is not made): `from faceless import host`. Theme: one line on this week's videos or a community prompt ("comment your number"); never a repeat of the earlier lines in `host.json`.
3. `line = host.weekly_line(theme)` (checked: 20-26 words, complete sentences, no advice or promises). Price it first: `host.estimate(...)`; the desk limits apply (`[muapi]` $2/day, studio ceiling $3/day, `per_clip_usd`).
4. `host.make_clip(line, apply=True, max_usd=2.5)`, then extract three frames and LOOK at them: the same face as `reference.png`, the gold Q pin on the left lapel, the black blazer, natural lip-sync, a complete ending. Re-roll once with a different seed if any lock is broken; never ship a drifted face.
5. Clean clip: `host.register(video, line, "<Title>", approved=True)`. The normal publisher and `post-backlog` post it as a Short (AI-generated and synthetic flags on; the description says he is a virtual host). Any doubt: register with `approved=False`, send the clip and say which lock is in question.
6. Send the clip to the owner with the line, cost and job id; commit `state/` and `channel/host/`; if YouTube refuses with HTTP 429 the clip stays queued and the next daily run uploads it.

## Rules
- He is AI-generated and says so; he never gives personal financial advice, promises income, or claims credentials.
- One clip a week. No `--apply` on a second clip in the same week. Muapi balance low (under $3): stop and tell the owner.
- A face, voice or look that drifts is a held clip, not a post.
