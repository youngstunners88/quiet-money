# Phone recipes

Each recipe is a goal and a checklist, not fixed coordinates: apps change their layout, so find every control in `get_ui_tree` by its text or description (`desc`) and tap its `center`. Observe after every action. The labels below are what the apps showed in October 2026; a near match ("Create" vs "+") is fine, a different screen is not.

Common start for every job:
1. `list_devices`; if more than one is ready, `select_device` with the owner's phone.
2. `python -m faceless phone next --push` gives the job JSON (`job.text`, `job.title`, `job.prompt`) and the files on the phone (`on_phone`, in `/sdcard/Download/QuietMoney`).
3. `press_key HOME`, then `launch_app` with the package below.

Typing long text: `type_text` takes ASCII only, up to 2000 characters, and turns new lines into nothing. For a caption with line breaks or emoji, type it in pieces, using `press_key ENTER` for each new line, or leave out characters it cannot type, and say so in the receipt note.

## YouTube Posts tab (picture post)
Package `com.google.android.youtube`. Job kind `yt_community`. Verified on a POCO M8 5G (HyperOS 2, YouTube 21.42) on 2026-10-25: five posts went out with this exact path.
1. Tap **Create** (the + at the bottom). First time only, YouTube asks for camera and microphone: tap **Don't allow** (the post needs neither). The create screen has mode tabs **Video / Short / Live / Post**; tap **Post** (the tab at the bottom, not the grey Post button at the top). YouTube remembers the last mode, so check the title says **Create post** before tapping anything. The channel shown under the title must be **Quiet Money**; any other: stop, `held`.
2. Tap **Add an image** (the picture icon at the bottom). Photo access: choose **Allow limited access**. Android only keeps that grant while YouTube stays open, so a new job needs it again: if the grid says **No photos yet**, tap **Settings** in the banner, then **App permissions → Photos and videos → Edit selected photos for this app**, tick the job's picture (newest first), **Done**, then Back three times to the grid.
3. In YouTube's own grid, tap the picture's thumbnail (Next stays grey until you do), then **Next**.
4. YouTube opens an editor and **adds a suggested sound** (for example "Coastline") and says the post will be shared to the Shorts feed. Tap the sound pill at the top, then **Delete sound** (the pill must read **Add sound**), then **Done** (top right).
5. Tap the box that says **Write a message...**, type `job.text`, press Back once to hide the keyboard. Read the text field back and compare it with `job.text`; stop if it differs. Leave visibility on **Public**.
6. Tap **Post** (top right). The feed shows a **Post created** toast for a few seconds. It has a **View** link, but the toast disappears fast and a tap lands on whatever video is under it, so do not rely on it: open **You -> View channel -> Posts** to see the post. The app does not show a link for the new post.
7. `python -m faceless phone done ID posted --ai-label yes --note "Posts tab"`. There is **no "Altered or synthetic content" switch** on the Posts screen, so the disclosure is the caption's "Illustrated with AI." line.

Typing: `adb shell input text` types ASCII, with `%s` for a space; send each line separately and press ENTER between lines. Apostrophes and `#` work when the string is single-quoted for the phone's shell. On Xiaomi, taps need Developer options -> **USB debugging (Security settings)**, which HyperOS only turns on with a SIM in the phone and a Mi account signed in; the SIM can come out afterwards.

## YouTube Short upload
Package `com.google.android.youtube`. Job kind `yt_short`.
1. **Create** → **Upload a video** (or **Short** → gallery) → the job's `final.mp4` → trim untouched → **Next**.
2. Title: `job.title`. Description (via **Show more**, **Description**, or the pencil): `job.text`. The description includes the hub link, which is allowed for YouTube Shorts.
3. Audience: **No, it's not made for kids**.
4. **Altered or synthetic content**: **Yes**. Find it under the details or "Show more". Not found → do not upload: `held --note "no altered-content switch"`.
5. Visibility Public → **Upload**. Wait for "Upload complete", then open **You → Your videos**, copy the link (**Share → Copy link**), and take a screenshot.
6. `phone done ID posted --ai-label yes --url <link>`.

## TikTok upload
Package `com.ss.android.ugc.trill` (this phone; `com.zhiliaoapp.musically` is the US app). Job kind `tiktok`.
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
