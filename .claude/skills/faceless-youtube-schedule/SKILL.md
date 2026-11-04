---
name: faceless-youtube-schedule
description: Handle YouTube's daily upload cap by scheduling instead of publishing now. Use when a Short shows "Daily upload limit reached" or "Upload failed", when more than about 5 Shorts are ready in a day, when stuck uploads must be re-sent, or when the owner says schedule, daily cap, daily upload limit, or spread the posts. Gives the phone scheduler (YT_SCHEDULE), the slot plan, and the rules for failed tiles.
metadata:
  author: quiet-money
  version: 1.0.0
  code: tools/yt_schedule.py, tools/yt-phone-upload.py
  owner-order: 2026-11-04, "this is what the solution is so set the skill for daily caps to be scheduled"
---

# Schedule past the daily cap

## The rule
TikTok posts go out the moment they render. **YouTube uploads that would pass the day's cap are uploaded with a schedule** (Visibility > Schedule), spread across the next days, never retried blind and never dropped. A failed "Daily upload limit r..." tile is not a post: re-send the video as a scheduled upload.

## Facts learned 2026-11-04
- The channel's Shorts tab showed 6 tiles stuck on "Daily upload limit r..." (4 distinct videos; two of them were duplicate failed copies). Today's 10 uploads on 11-03 and 11-04 all published.
- Visibility sheet on the phone: Publish now (Public/Unlisted/Private) or **Schedule** (date field, default tomorrow 00:00 local time). The date picker exposes each day as content-desc "07 November 2026"; the time picker has a text-input mode (`android:id/toggle_mode`, fields `input_hour`, `input_minute`).
- Times are the phone's local time (KST on this phone). The sheet's title is not in the UI tree; its date field is.
- Whether a scheduled upload counts against the daily cap is not proven: if an upload is refused again, stop, note the time, and retry after the 24 h window; scheduling still spreads *publishing* so the audience sees steady output.

## How
1. One video: `YT_SCHEDULE="2026-11-05 10:00" YT_SCRATCH=<dir> .venv/bin/python tools/yt-phone-upload.py DAY nN` (local time, 24 h). It uploads, sets the schedule, verifies the sheet shows the exact date and time, then taps Upload/Schedule and waits for "Uploaded".
2. Only the sheet: `python3 tools/yt_schedule.py "2026-11-05 10:00"` (with the details page or the sheet open).
3. Slot plan (phone local time): 10:00, 13:00, 16:00, 19:00, 22:00, five a day, oldest or strongest first; the next day continues the same slots. Check the channel's scheduled list afterwards (Studio or the Videos tab) so no two share a minute.
4. The pack must exist (`tools/pack_queue.py DAY SLOT NAME`): video.mp4 + POST.md. Old renders: run `tools/sharpness_check.py`; a soft render (< 6 Mbps) is flagged to the owner but may be scheduled when the owner ordered it, since a scheduled post can still be cancelled.

## Failed tiles
- Never delete the stuck tiles or any post: the owner does that by hand. Say how many there are and which are duplicates (same title twice).
- Do not schedule a duplicate of a video that is already scheduled or live.

## After each run
Journal: which videos are scheduled for which slots, which are still waiting for the next cap window, and the time of the last refusal. Put it in the handoff.
