---
name: faceless-songs
description: Write three original songs a day for Quiet Money as ready-to-paste Suno packs (style prompt, structured lyrics, cover-image prompt, post copy with the AI label), written by Claude Haiku 5.5 with the decision layer choosing between candidates. Never calls Suno, never uploads. Use when the user says "songs", "music desk", "Suno prompts", "lyrics", "drop the songs", "song cover image", or asks for audio and streaming content.
---

# Faceless songs

Three songs a day, ready before the owner starts. The owner makes the audio in Suno and the video; the studio then edits it (HyperFrames captions, motion, hook).

## What the code does (`faceless/songs.py`)
- `python -m faceless songs` writes `music/packs/<day>/song<N>-<lane>/` for N = 1..3: `SUNO.md` (everything to paste), `style.txt`, `lyrics.txt`, `image-prompt.txt`, `pack.json`. Idempotent; `--force` rewrites. `songs status` says whether all three exist (exit 1 if not).
- Haiku 5.5 (`[songs] model`, via OpenRouter) writes two candidates per slot from a rotating lane (sound) and theme (feeling). `decide.ask` (Jev / Laya / Clef, heuristic fallback, honours `[decide].dry_run`) picks one.
- Hard gates refuse: artist names or "in the style of", missing chorus twice, a lyric line count outside 24-64, style over 250 or lyrics over 2800 characters, money promises or buy/invest calls, links and handles, image prompts that ask for text or faces, near-duplicates of earlier songs (`state/songs.jsonl`). A refused song is retried once with the reasons.
- Spend: its own cap `[songs] daily_usd` (about $0.003 a song measured), the studio ceiling and `state/PAUSE` still apply.

## Steps in a routine run
1. `python -m faceless songs`; exit 1 means fewer than three: read the problems, fix the cause (usually a provider key or a gate), re-run.
2. Commit `music/` and `state/songs.jsonl`; send the three `SUNO.md` files and a one-line list of titles and hooks to the owner.
3. When the owner puts a song and its picture in the Drive folder, make the video: `python -m faceless songvideo IMAGE AUDIO "Title" music/videos/<day>/songN-<slug>.mp4 [--grade dusk|warm|deep]`. Look at a `--draft` first (frames at a few timestamps), then render the delivery file. `--poster IMAGE "Title" OUT.jpg` makes the 1080x1920 cover. The video has the QUIET MONEY wordmark at the top, only the song title low (no other text), a pan across the whole picture, bloom, particles, grain, a gold waveform, and a -14 LUFS mix (`faceless/songvideo.py`). Turn the platform's AI label on for every post (it is a toggle, not on-screen text).
4. Post copy: `python -m faceless songpost --day <day>` writes `POST.md` and `post.json` beside each pack (title with the subject, an answer-first description with Quick Answers for answer and generative engines, the full lyrics, one tracked link, the AI disclosure, three hashtags, a pinned-comment invitation to share with one friend who wants to exit the rat race). `songpost PACK_DIR VIDEO --at <UTC time> --apply` uploads through the studio's YouTube connection (category Music, synthetic-media flag on); without `--apply` it is a dry run. A 429 means the daily quota is spent: retry after 07:00 UTC. The five daily Shorts come first (rule 15); songs go in what quota is left.
5. Match the owner's file to its pack by the lane name in the file name (midnight, neon, hush, ...); say which title was used.

## Hard rules
- Original lyrics only; no real artist, song or brand in any prompt; no financial advice or income promise (CLAUDE.md rules 1, 2, 4).
- Never call Suno or any music service, never post or distribute (rule 9). Streaming distribution is the owner's decision: see `references/suno-playbook.md` (commercial rights, distributor AI rules).
- Songs are about people and feelings, not a lecture; the channel's tagline lives in the theme, not a sales line.

## References
- `references/suno-playbook.md`: prompt formula, section tags, lyric craft, rights and platform notes with sources and what is unverified.
