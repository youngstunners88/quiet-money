> Reviewed 2026-10-20. Corrections from the review: 14 refused videos, not 13 (one was refused at the channel check, which also shows the shared 10,000-unit bucket runs out); refusal times are inferred, not recorded; the backlog only posts renders that exist in the daily-run container, so hand uploads must have their video id recorded in the job before any `post-backlog` run, and hand uploads need the "altered or synthetic" label on.

**Upload block on Quiet Money's YouTube channel: cause, fix and owner steps (2026-10-20)**

**Summary.** The uploads are not failing because of our own quota. They fail because of Google project `1068312718386`, which owns the OAuth app that Composio manages for all its customers. That project's "Video Uploads per day" allowance is used up by about 09:30 UTC, 2.5 hours after the reset. The best fix is free. The owner creates their own Google OAuth app (about 30 minutes) and we add it to Composio as a custom auth config. That gives us our own 100 uploads a day. Until then, the owner can upload today's 5 by hand in YouTube Studio.

**1. The exact error.** None of the repository files hold the full error text: the engine throws the response body away. It is in the daily-run session (`session_0159czhKSFbiWtBSBmBvRK2c`, tool result at 2026-10-20T10:04:32Z):
```
429 {'error': {'code': 429, 'message': "Quota exceeded for quota metric 'Video Uploads' and limit 'Video Uploads per day' of service 'youtube.googleapis.com' for consumer 'project_number:1068312718386'.", ... 'reason': 'rateLimitExceeded'}], 'status': 'RESOURCE_EXHAUSTED', ... 'metadata': {'quota_unit': '1/d/{project}', 'consumer': 'projects/1068312718386', ...
```
- **Where it shows in the repo:**
  - `faceless/providers/composio_tools.py:129-130` turns any 403 or 429 into "YouTube refused the upload session (HTTP 429)…" and drops the body.
  - Each of today's five `state/jobs/2026-10-20-*.json` files has `artifacts.publish.youtube.skipped` set to that text.
  - The journal records `JOB_TRANSITION … "youtube": null`.
- **The daily report hides it.** `gauntlet/reports/daily-2026-10-20.md` says "published" for all 5, but that only means the local pack was written. None of the 5 reached YouTube. `OPERATIONS.md` has no entry for this.
- **Pattern.** 14 passed videos have been refused with a 429; 13 of them are still not on YouTube:
  - 2026-10-15: 4
  - 2026-10-19: 4
  - 2026-10-20: all 5
  - The 14th (2026-10-13) was uploaded later.

  Uploads that succeeded all landed between 07:22 and 13:25 UTC (8 of them on 2026-10-16). On bad days the 429s start around 09:25–09:40 UTC; on 10-13 the refusal came at 12:24 UTC.

**2. How uploads go through Composio today.**
1. `publish.publish()` writes the local pack, then calls `publish.youtube()`. That stops at `[publish.youtube] max_per_day = 5`, then calls `composio_tools.youtube_upload()`.
2. `youtube_upload()` checks which channel the connection acts as (`YOUTUBE_LIST_CHANNELS mine`, expecting `UC9B1QBr3_8Eulok8IdQbCqQ`).
3. It then opens a resumable session through `Composio().tools.proxy(POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable)` using connected account `ca_M76DljoB7OkG`, and sends the whole file to Google itself with a PUT.
4. Afterwards `ytchannel.add_to_series` adds the video to its playlist, and the first comment is posted once the video is public.

**3. The quota is Composio's, not ours.** I checked with read-only Composio calls:
- Our connection `ca_M76DljoB7OkG` belongs to auth config `ac_vUrPwRNQQn6Z`, which has `is_composio_managed: true` and the redirect `https://backend.composio.dev/api/v1/auth-apps/add`.
- It is the only YouTube auth config in our Composio project, so the OAuth client (and the consumer project in the error) is Composio's.
- Composio's own docs say so: "Composio's default OAuth app shares quota across all users. Your own app gets a dedicated quota."
- `studio.toml:167` already notes that the quota is "shared by the Composio project".

**4. YouTube Data API rules now** (Google docs, updated 2026-10-15):
- **Uploads have their own allowance.** Since June 1, 2026, `videos.insert` costs "1 unit in the Video Uploads quota bucket", and "Quota impact: 100 calls per day" per project. Everything else shares 10,000 units a day. A Dec 4, 2025 change had already cut the upload cost from about 1600 units to about 100.
- **Reset time.** Quotas reset at midnight Pacific.
- **Audit only for more.** Going above the default needs a compliance audit, requested through the Audit and Quota Extension Form.
- **Private lock.** The current `videos.insert` page says "Videos uploaded from unverified API projects are not restricted to private viewing mode." The 2020 change log entry that locked such uploads to private has no reversal entry, so we check this on the first upload. Note that the daily-run session told the owner new projects are locked private until audited; the current docs say the opposite.
- **Our usage per video.** Besides the upload, we spend about 103 units from the 10,000 (channels.list 1, playlists.list 1, playlistItems.insert 50, commentThreads.insert 50, videos.list 1). That is enough for roughly 95 videos a day.

**5. Options compared.**

| Option | Cost | Uploads/day | Verdict |
|---|---|---|---|
| A. Our own Google OAuth app, added to Composio as a custom auth config | $0, about 30 min of owner clicks | 100 (our own allowance) | **Best.** The engine's upload path and channel check stay as they are. |
| B. Our own Google project called directly, without Composio | $0 | 100 | Same allowance, but the engine would need its own OAuth flow and a stored refresh token. More code and more secrets than A. |
| C. Quota Extension Form | $0, weeks of audit | More than 100 | Only needed above 100 a day. We cannot use it on Composio's project. |
| D. Upload-Post (`upload_post` mode already exists) | Free plan is 10 uploads a month; Basic is $24 a month | Unlimited on paid plans | Free plan is too small (we need about 150 a month) and Basic is over the $10 budget. It also means changing `[publish].mode`, which needs the owner's yes. |
| E. Owner uploads in YouTube Studio | $0, about 5 min a day | Channel limit | Works today for today's 5 packs in `distribution/queue/2026-10-20/` and `distribution/queue/2026-10-21/`. |
| F. The 07:02 UTC scheduled task already set up (`trig_01RBd9BKDwVdAuJikDmvwDb5`, cron `2 7 * * *`) | $0 | Whatever other Composio customers leave | Fragile. From 2026-11-02 the reset moves to 08:00 UTC, so it will fire an hour early. If kept, it should be changed to `CRON_TZ=America/Los_Angeles 2 0 * * *`. |

**6. Owner's click-by-click steps for option A.** Sign in as the Google account that manages the Quiet Money brand channel.
1. Go to console.cloud.google.com/projectcreate. Name it `quiet-money-uploads` and click Create. No billing account is needed.
2. Go to console.cloud.google.com/apis/library/youtube.googleapis.com and click Enable.
3. Go to console.cloud.google.com/auth/overview and click Get started:
   - App name: Quiet Money Studio
   - Support email: your own
   - Audience: External
   - Contact email: your own
   - Agree, then click Create.
4. Go to console.cloud.google.com/auth/scopes, click "Add or remove scopes", tick these four, then click Update and Save:
   - `.../auth/youtube.upload`
   - `.../auth/youtube`
   - `.../auth/youtube.force-ssl`
   - `.../auth/youtube.readonly`
5. Go to console.cloud.google.com/auth/audience, click "Publish app", then Confirm.
   - In "Testing" mode the sign-in expires every 7 days.
   - Do not submit for verification. Google exempts personal-use apps with fewer than 100 users; you will just click past a warning once.
6. Go to console.cloud.google.com/auth/clients and click Create client:
   - Type: Web application. Name: composio.
   - Authorized redirect URIs: add both `https://backend.composio.dev/api/v3/toolkits/auth/callback` and `https://backend.composio.dev/api/v1/auth-apps/add`.
   - Click Create. Copy the Client ID and Client secret right away; the console may not show the secret again.
7. Go to dashboard.composio.dev, open the project, then Authentication management, then Create Auth Config:
   - Toolkit: YouTube, scheme OAuth2.
   - Turn on "Use your own developer credentials" and paste the Client ID and secret there only, never in chat.
   - Redirect URI: `https://backend.composio.dev/api/v3/toolkits/auth/callback`.
   - Use the same 4 scopes, then click Create.
8. Send the agent only the new `ac_…` id. It is not a secret.
9. Open the Connect Link the agent sends in a private window:
   - Choose the **Quiet Money** brand account on the chooser.
   - On "Google hasn't verified this app", click Advanced, then "Go to Quiet Money Studio (unsafe)", then Allow.

**7. What the agent does next** (after the owner's yes, through a PR).
1. Add `[composio] auth_configs = {youtube = "ac_NEW"}` and pin the new connected account. Pass both to `Composio().create(user_id=…, auth_configs=…, connected_accounts=…)`; SDK 0.26.0 supports both. This matters because, per Composio's docs, existing connections keep refreshing on the old auth config until we switch.
2. Make `composio_tools` record the 429 body (reason and consumer project) in the job's skip note. Add tests and run `python -m faceless ci`.
3. Run `python -m faceless composio connect youtube` to get the Connect Link. Afterwards, confirm `YOUTUBE_LIST_CHANNELS mine` returns `UC9B1QBr3_8Eulok8IdQbCqQ`.
4. Do one scheduled upload. Read it back at +5 and +20 minutes (it should be `private` with `publishAt` set), then confirm it is public after its time with a public oEmbed check returning 200.
   - If Google locks it private after all, file the Audit and Quota Extension Form at support.google.com/youtube/contact/yt_api_form and keep option E running meanwhile.
5. Run `python -m faceless post-backlog --apply` to post the 13 unposted videos. Propose raising `max_per_day` above 5 to clear the backlog faster.
6. Delete or fix the DST timing of the 07:02 scheduled task.
7. Correct the `faceless-composio` skill's "Quota" line, which is wrong since June 2026.
8. Deleting the old managed connection `ca_M76DljoB7OkG` is a destructive step, so it waits for the owner's explicit yes after the new connection is verified.

**8. Uploads per day after the fix.**
- **API limit:** 100 uploads a day on our own allowance; the other calls allow about 95 videos a day. Neither will bind.
- **Channel limit:** the real ceiling is YouTube's per-channel daily upload limit. YouTube does not publish the number; phone-verified channels get a higher one (owner: youtube.com/verify).
- **Engine cap:** the engine stops at `max_per_day` = 5 until that is raised. 5 a day is the standing order (rule 15); 8 to 10 a day is realistic while clearing the backlog.

**What I did.** Only reads. I ran `composio status` and read the connected account and auth configs without printing any secrets. I made no upload calls, changed no connections, and edited no files.

**Sources**
- Google: [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert), [Quota costs](https://developers.google.com/youtube/v3/determine_quota_cost), [Getting started](https://developers.google.com/youtube/v3/getting-started), [Revision history](https://developers.google.com/youtube/v3/revision_history) (entries of Jun 1 2026, Dec 4 2025 and Jul 28 2020), [Quota and compliance audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits), [Audit and Quota Extension Form](https://support.google.com/youtube/contact/yt_api_form)
- Composio: [Custom auth configs](https://docs.composio.dev/docs/auth-configuration/custom-auth-configs), [White-labeling and switching auth configs](https://docs.composio.dev/docs/authentication/white-labeling-authentication)
- Google OAuth: [7-day expiry in Testing](https://developers.google.com/identity/protocols/oauth2), [Publishing status and brand accounts](https://support.google.com/cloud/answer/15549945), [Personal-use exemption](https://support.google.com/cloud/answer/13464323), [Unverified apps](https://support.google.com/cloud/answer/7454865)
- YouTube: [Upload limit and verification](https://support.google.com/youtube/answer/9890437)
- Upload-Post: [Pricing](https://www.upload-post.com/llms-full.txt)

Files that hold the evidence:
- /home/user/quiet-money/faceless/providers/composio_tools.py
- /home/user/quiet-money/faceless/providers/publish.py
- /home/user/quiet-money/faceless/ytchannel.py
- /home/user/quiet-money/studio.toml
- /home/user/quiet-money/state/journal.jsonl
- /home/user/quiet-money/state/jobs/2026-10-20-s2-story-evelyn-adams-beating-1-in-17-tri.json
- /home/user/quiet-money/gauntlet/reports/daily-2026-10-20.md
- /home/user/quiet-money/.claude/skills/faceless-composio/SKILL.md