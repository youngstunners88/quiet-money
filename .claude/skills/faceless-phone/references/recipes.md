# Phone recipes

Each recipe is a goal and a checklist, not fixed coordinates: apps change their layout, so find every control in `get_ui_tree` by its text or description (`desc`) and tap its `center`. Observe after every action. The labels below are what the apps showed in October 2026; a near match ("Create" vs "+") is fine, a different screen is not.

Common start for every job:
1. `list_devices`; if more than one is ready, `select_device` with the owner's phone.
2. `python -m faceless phone next --push` gives the job JSON (`job.text`, `job.title`, `job.prompt`) and the files on the phone (`on_phone`, in `/sdcard/Download/QuietMoney`).
3. `press_key HOME`, then `launch_app` with the package below.

Typing long text: `type_text` takes ASCII only, up to 2000 characters, and turns new lines into nothing. For a caption with line breaks or emoji, type it in pieces, using `press_key ENTER` for each new line, or leave out characters it cannot type, and say so in the receipt note.

## YouTube Posts tab (picture post)
Package `com.google.android.youtube`. Job kind `yt_community`.
1. Tap **Create** (the + at the bottom) → **Post**. If it asks which channel, choose Quiet Money (@quietmoneyrule). Any other channel: stop, `held`.
2. Tap the image icon → **Download** or **QuietMoney** album → the job's `picture.png` → **Next**/**Done**.
3. Tap the text box, type `job.text`.
4. Leave visibility on Public, then tap **Post**. Wait until the post shows in the Posts tab, then take a screenshot.
5. `python -m faceless phone done ID posted --ai-label yes --note "Posts tab"`. The disclosure is the caption's "Illustrated with AI." line, so `yes` is correct when that line is in the posted text.

## YouTube Short upload
Package `com.google.android.youtube`. Job kind `yt_short`.
1. **Create** → **Upload a video** (or **Short** → gallery) → the job's `final.mp4` → trim untouched → **Next**.
2. Title: `job.title`. Description (via **Show more**, **Description**, or the pencil): `job.text`. The description includes the hub link, which is allowed for YouTube Shorts.
3. Audience: **No, it's not made for kids**.
4. **Altered or synthetic content**: **Yes**. Find it under the details or "Show more". Not found → do not upload: `held --note "no altered-content switch"`.
5. Visibility Public → **Upload**. Wait for "Upload complete", then open **You → Your videos**, copy the link (**Share → Copy link**), and take a screenshot.
6. `phone done ID posted --ai-label yes --url <link>`.

## TikTok upload
Package `com.zhiliaoapp.musically` (the US app; `com.ss.android.ugc.trill` elsewhere). Job kind `tiktok`.
1. **+** → **Upload** → the job's `final.mp4` → **Next** (no filters, no added sound: the video has its own music).
2. Caption box: `job.text` (hashtags included; there is no link, because the bio carries it).
3. **More options** → turn **AI-generated content** on. Not found → `held`.
4. **Post**. Wait for the upload bar to finish, open the profile, tap the new video, **Share → Copy link**, then take a screenshot.
5. `phone done ID posted --ai-label yes --url <link>`.

## Google Flow image
App: Chrome, `com.android.chrome`. Job kind `flow_image`. `phone next --push` has already noted what is in Download.
1. `open_url https://labs.google/fx/tools/flow`. If it asks for a sign-in, stop: `held --note "Flow sign-in needed"` (the owner signs in by hand).
2. New project → image mode (**Images** / **Create image**). Aspect: `job.aspect`.
3. Paste `job.prompt` into the prompt box, then tap **Generate**. Wait, taking a screenshot every 10 s, for up to 2 minutes.
4. Pick the strongest result: on subject, no text or letters, no watermark, no distorted hands or faces. Open it → **Download** (the highest size offered).
5. `python -m faceless phone pull ID`, then `phone done ID made`. Out of credits → `held --note "Flow credits used up"` and stop all Flow jobs for today.

## Fiverr inbox (read and draft)
Package `com.fiverr.fiverr`. Job kind `fiverr_inbox`. Read-only.
1. **Inbox** → each unread conversation: read the whole thread (scroll up until the first message).
2. For each one: `python -m faceless client reply --channel fiverr --gig studio "<their message>"` (or `--gig brandkit`), save the draft to `job.draft_dir/<buyer>.md`, then `python -m faceless phone reply <buyer> --draft <file>`.
3. Never tap Send. When done: `phone done ID drafted --note "<n> drafts"`. Tell the owner which threads have a draft waiting for `phone approve`.

## Fiverr reply (approved only)
Package `com.fiverr.fiverr`. Job kind `fiverr_reply`. `next` hands this out only after `phone approve ID`.
1. **Inbox** → the conversation for `job.thread`. Check that the last message is still the one the draft answers. If not: `held --note "new message since the draft"`.
2. Type `job.draft` exactly as written, then tap **Send**. Take a screenshot.
3. `phone done ID posted --ai-label no --note "sent"`. Fiverr messages need no AI label; the receipt field only records it.
