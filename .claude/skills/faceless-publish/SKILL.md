---
name: faceless-publish
description: Publish or schedule Quiet Money posting packs to TikTok, YouTube Shorts, and Instagram Reels (Upload-Post API or manual), with AI and finance disclosures. Use when asked to post, schedule, re-post, or set up auto-posting.
---

# Publish

## Auto-posting setup (one time, needs the account owner)
1. Create the channel accounts (TikTok, YouTube, Instagram) with the handle from `studio.toml [channel].handle`.
2. Create an Upload-Post account, add a profile (its name = `UPLOAD_POST_USER`), connect the three accounts.
   The free plan is 10 uploads/month and excludes TikTok; daily TikTok posting needs a paid plan.
3. Add secrets `UPLOAD_POST_API_KEY` and `UPLOAD_POST_USER` (GitHub repo → Settings → Secrets → Actions,
   and/or the local environment).
4. Set `[publish].mode = "upload_post"` in `studio.toml`.

## Publish a job
- Automatic: `python -m faceless daily` schedules each gated video in its slot.
- Manual re-publish: `python -m faceless publish <job_id>` (uses an Idempotency-Key = job id, so retries don't duplicate).
  It refuses a job that has not passed the gauntlet: fix it, re-run `python -m faceless gauntlet <job_id>`, then publish.
  `--force` overrides only after a human has reviewed the video.

## Every post must have
- AI label ON (`tiktok_is_ai_generated`, `containsSyntheticMedia`; set automatically by the engine).
- Description disclaimers (added by `pipeline/package.py`): not financial advice, AI-assisted, affiliate disclosure if links.
- A pinned first comment (the script's `first_comment`).

## Manual mode
Open `distribution/queue/<day>/slot<N>-<pillar>/POST.md` and follow its checklist.
