# The daily routine's prompt (source of truth)

The routine "Quiet Money daily batch" (cron `17 9 * * *`, UTC) stores this text as its instructions. A routine's prompt can be changed only from the
conversation it posts into, so when this file changes, ask that conversation to copy it into the routine. Keep the two identical.

Changed 2026-10-11: the old prompt ended with "Never: post or upload to any platform account ... use the Composio YouTube connection for writes",
which contradicted the daily run now scheduling videos on YouTube (the owner's yes is recorded in `tests/test_hygiene.py`). The old prompt also had
no read-back check; a YouTube upload that reports success can still be dropped minutes later.

---

Daily batch time. Produce 5 new Quiet Money videos, let the engine schedule them on the Quiet Money YouTube channel, verify they are really live, commit the run's state, and send the videos to the owner. Follow .claude/skills/faceless-daily/SKILL.md ("Scheduled routine run") and .claude/skills/faceless-youtube-seo/SKILL.md.

1. Sync first: `git pull --rebase origin main` (other sessions push state too). If the container is fresh, run `CLAUDE_CODE_REMOTE=true CLAUDE_PROJECT_DIR="$PWD" bash .claude/hooks/session-start.sh`. If state/PAUSE exists, stop and report why.
2. `python -m faceless doctor` and `python -m faceless composio status` (youtube must be connected; if not, still make the videos, local packs are written either way, and report it). Then in the background `python -m faceless daily --extra 5` (fills today's open slots first, then banks ahead). The engine itself schedules every video that passes the gauntlet on the Quiet Money YouTube channel at its slot time, files it in its series playlist, follows the launch order in studio.toml [publish.launch], and refuses any channel other than [publish.youtube].channel_id. Wait with a background until-loop, never a foreground sleep.
3. Review `gauntlet/reports/daily-<today>.md`. Held or failed rows: follow the skill; fix small in-scope root causes, then re-run `python -m faceless daily` to refill only the open slots. Spot-check one video's frames.
4. Verify YouTube, because a success response at upload time is not proof: run `python -m faceless yt-verify` right after the batch and again about 3 hours later (use send_later for the second check if you have it, otherwise a background wait with a hard timeout). Then run `python -m faceless yt-comments` (first comments on videos that have gone public) and `python -m faceless yt-channel` (it must say the live channel matches; if it differs, `--apply` is allowed). Any PROBLEM line or refusal: follow .claude/skills/faceless-unblock/SKILL.md, prove the cause, fix small things yourself and open a draft PR. A quota refusal means wait for the midnight-Pacific reset; the local packs stay ready and `python -m faceless publish <job>` retries one. Never re-upload a video YouTube removed until you know why.
5. Commit state/, script-lab/, gauntlet/, analytics/, distribution/ (POST.md/meta.json only; media is gitignored) and push to main (pull --rebase on rejection; retry network errors up to 4 times with backoff). Keep scratch files in state/tmp/ uncommitted.
6. Send each new video.mp4 from distribution/queue/<post date>/slot<N>-<pillar>/ to the owner with SendUserFile (re-encode a copy under 30 MB if needed). Report titles, scores, durations, post times, the live YouTube state and views from yt-verify, spend (`python -m faceless status`), anything held, and any provider that ran out (Cloudflare neurons, OpenRouter credit). Remind the owner to pin each first comment in Studio (the API cannot).

Allowed: the engine's own YouTube scheduling, `yt-comments`, `yt-channel --apply`, and fixing small faults per the faceless-unblock skill.
Never: change [publish].mode or OWNER_APPROVED_LIVE_POSTING; post to any platform other than through the engine's YouTube mode; delete a channel, a playlist, or anyone's video (the one exception: an empty zero-duration video your own probe created); remove, replace or revoke the Composio YouTube connection; work around any verification, policy or terms check; print or commit API keys; delete anything outside this run's files.
