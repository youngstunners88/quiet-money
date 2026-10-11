---
name: faceless-youtube-seo
description: Make Quiet Money easy to find and easy to keep watching on YouTube, and keep the channel running on its own. Covers the channel page (description, keywords, banner, series playlists), what every video must carry (title, first line, tags, language, AI label, series, first comment), how Shorts spread, the weekly learning loop, and the commands that apply and verify it all. Use when setting up or changing the channel page, writing or reviewing a title or description, picking keywords, checking that the day's uploads are live, or asked how to grow on YouTube.
---

# YouTube discoverability and growth (Shorts only, for now)

Nothing here can promise a viral video. What it can do is make every upload findable, keep the first seconds strong, and learn from the numbers every week.

## On autopilot (the daily run does these)
- Each video that passes the gauntlet is scheduled for its slot on the channel, filed in its series playlist, tagged `en`, and labelled as AI-assisted.
- `python -m faceless yt-verify` reads every video from the last 14 days back from YouTube (still there, processed, public on time; views and likes). Run it after each daily batch and again a few hours later. A problem means follow `faceless-unblock`; never re-upload the same content blindly.
- `python -m faceless yt-comments` posts each video's first comment once it is public. The owner pins it in Studio (the API cannot).
- `python -m faceless yt-channel` shows what differs between `studio.toml [youtube]` and the live channel; `--apply` fixes it. Edit the wording in `studio.toml`, never by hand in Studio, so it stays in the repo.

## The channel page
- The first line of the description is what search shows. It leads with the searchable phrase, then the promise. The rest names the six series, one CTA (the hub link) and the disclaimer.
- Keywords and series playlist titles use phrases people actually type, taken from YouTube's search autocomplete (`references/search-phrases.md`; refresh with `scripts/autocomplete.py`).
- Banner `channel/brand-kit/banner-youtube.png` keeps its text inside the centre 1546 by 423 px. Profile picture `avatar.png` and channel links are set by hand in Studio (not in the API).
- A Short cannot be the channel trailer (YouTube ignored it). Set `trailer` in `studio.toml` once there is a long video.

## Every video
1. Title: 60 characters or fewer; the viewer's phrase or a number-and-tension hook in the first words (`Why Your Brain Hates Your Future Self`). No clickbait the video does not pay off.
2. Description: first line is a plain sentence with the topic phrase; then the one CTA; the disclaimer; hashtags last. YouTube shows the first three hashtags above the title, so those carry the topic; `#shorts` stays.
3. Tags are secondary. They help with misspellings, not ranking.
4. The first second decides whether a Short is swiped away. The script's opening line is the hook; the last line leads back into the first so it loops.
5. First comment is a question viewers can answer in one line. Reply to every comment in the first hour (`faceless-growth`).

## How Shorts spread (what is known and what is not)
YouTube shows a new Short to a small test audience and widens it when viewers stay and do not swipe away. Watch percentage, loops and "viewed versus swiped away" matter most. Posting times are a weak lever (sources disagree and none covers finance); the launch order in `studio.toml [publish.launch]` is an assumption until `yt-verify` and the analytics review give real numbers.

## Weekly loop
1. `python -m faceless yt-verify` for views and likes per video; feed them to `faceless-analytics` (weights shift towards what works).
2. Read the retention of the top and bottom three Shorts in Studio; rewrite the weakest hook pattern.
3. Refresh search phrases once a month; apply with `yt-channel --apply`.
4. Set the channel trailer when there is a long video; replace the launch-order assumptions with measured slots.

## Never
Buy views, subscribers or comments; join engagement pods; mislead in a title; promise income or returns; skip the AI-content label; hide that the narration is AI-assisted. Money claims pass the claim check (`python -m faceless offer check TEXT`).
