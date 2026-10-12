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
3. When the owner returns audio and video, edit with the faceless-hyperframes skill: word-by-word captions, a pulse on the chorus, the cover as the first frame. Label AI on every post.

## Hard rules
- Original lyrics only; no real artist, song or brand in any prompt; no financial advice or income promise (CLAUDE.md rules 1, 2, 4).
- Never call Suno or any music service, never post or distribute (rule 9). Streaming distribution is the owner's decision: see `references/suno-playbook.md` (commercial rights, distributor AI rules).
- Songs are about people and feelings, not a lecture; the channel's tagline lives in the theme, not a sales line.

## References
- `references/suno-playbook.md`: prompt formula, section tags, lyric craft, rights and platform notes with sources and what is unverified.
