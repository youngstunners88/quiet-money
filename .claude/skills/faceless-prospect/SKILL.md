---
name: faceless-prospect
description: Feed and run Quiet Money's prospect machine, which turns what real people wrote under our videos into the DM desk's drafts for the owner to send by hand. Use when a mission says to collect comments, when asked to find people to write to, to add a commenter or a peer creator to the drop folder, or to turn waiting comments into DM drafts. Read-only toward the outside world, it never replies, likes, follows or messages.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/prospects.py
---

# The prospect machine

People who already wrote to us are the only prospects. The machine reads them, sorts them and hands them to the DM desk, which
drafts. The owner sends. No model is used, so a run costs nothing.

```bash
python -m faceless prospect status      # what is waiting, per source
python -m faceless prospect             # collect, sort, write today's list, draft through the DM desk
```

## Who counts

| Kind | Who | What `--text` holds |
|---|---|---|
| `comment` (default) | someone who wrote under one of **our** videos | their exact words |
| `peer` | a creator who covers the same subject | what their video is about, in a few words |

Nobody else. The drafts open with "you asked under our video": that sentence has to be true.

## Adding people

One command per person. It checks the row, so never write the drop files by hand.

```bash
python -m faceless prospect add --handle @their_handle --text "their exact words" --video "the video title" --platform tiktok
python -m faceless prospect add --handle @creator --kind peer --text "sinking funds for irregular bills" --platform tiktok
```

- Copy their words exactly. Do not tidy, translate or summarise them.
- Skip emoji-only reactions and anything selling something. The machine drops those anyway.
- `--platform` is `tiktok`, `youtube` or `instagram`. `--name` is their first name when the profile shows one.

## Collecting from the phone (the harvest mission)

1. TikTok > Inbox > Activity. Read the comments on our videos from the last three days.
2. Run `prospect add` for each real one.
3. Run `python -m faceless prospect`, then `python -m faceless crew report <mission> done "N added, M drafted" --agent <your-id>`
   (pre-flight, claim and heartbeat first: the `faceless-crew` skill).

Read only. Never reply, like, follow, open a DM or tap a profile's message button. Stop at a login wall or a verification screen
and report blocked.

## What the machine does with a row

- **asked** (a question), **disagreed** (pushback), **shared** (their own situation), **peer**: drafted, in that order.
- Dropped, with the reason kept: promotion, a reaction too short to answer, older than 14 days, on the block list, already handled.
- One batch a day, at most the DM desk's cap. The rest waits for tomorrow.

## Privacy

The repo is public. Rows, lists and drafts stay in the gitignored `outbound/private/` and `outbound/drafts/*.private.*`. Never paste
a handle or a comment into a commit, a journal line, a mission report or a file outside those folders.
