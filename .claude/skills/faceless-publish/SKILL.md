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

## YouTube mode (the daily run posts by itself)
`[publish].mode = "youtube"` in `studio.toml` makes every video that passes the gauntlet get scheduled on the studio's channel (`[publish.youtube].channel_id`)
for its slot, through `composio_tools.youtube_upload` (Composio authorises, we send the bytes). It refuses to run if the connection acts as any other channel,
never uploads a job twice, stops at `max_per_day`, and treats a quota refusal as "try again after the reset" (the local pack is always written first).
First comments cannot go on a scheduled video, so `python -m faceless yt-comments` (also run at the start of every `daily`) posts them once the video is public;
pin the comment in YouTube Studio, the API cannot. While there are no metrics, the first three days of posting follow the launch order in `[publish.launch]`
(`faceless/launch.py`): the Escape series takes the slot we expect to do best. `state/PAUSE` stops all of it. When something here fails, use the `faceless-unblock` skill.

## Publish a job
- Automatic: `python -m faceless daily` schedules each gated video in its slot.
- Manual re-publish: `python -m faceless publish <job_id>` (uses an Idempotency-Key = job id, so retries don't duplicate).
  It refuses a job that has not passed the gauntlet: fix it, re-run `python -m faceless gauntlet <job_id>`, then publish.
  `--force` overrides only after a human has reviewed the video.

## Every post must have
- AI label ON (`tiktok_is_ai_generated`, `containsSyntheticMedia`; set automatically by the engine).
- Description disclaimers (added by `pipeline/package.py`): not financial advice, AI-assisted, affiliate disclosure if links.
- The post's call to action: the caption's "link in bio" line and the pinned-comment text in `OFFER.md` (see `faceless-offer`). The script's `first_comment`
  is the engagement question; the pinned comment is the offer. Links in captions and comments are not tappable, so the profile link (the hub page) carries them.

## Manual mode
Open `distribution/queue/<day>/slot<N>-<pillar>/POST.md` and follow its checklist; `OFFER.md` beside it holds the comment to pin. After pinning it, `python -m faceless offer mark <video id> pinned`.
