---
name: faceless-collab
description: Find small, active personal-finance podcasts from public data and draft one honest collaboration note each (a free credited Short built on one of their episodes), gate it, and hand it to the owner to send. Covers the run, the gates, privacy, recording outcomes and the kill rule. Use when the owner says collaborations, collab, podcast outreach, partner with creators, cross-promotion, or asks who to reach out to for growth.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/collab.py
---

# Collaboration notes (O19)

## Run
`python -m faceless collab run --limit 5` finds shows through Apple's documented podcast search, keeps small and active ones (12 to
400 episodes, an episode in the last 45 days, networks and brands excluded), reads each show's own RSS feed safely (defusedxml,
emails stripped: contacts are never collected), has Claude Haiku 5.5 draft one note, gates it, and writes `channel/collab/drafts/`
(gitignored). Relay every passing note in your reply: the drafts do not survive the container.

## What a note must be
Built on one real recent episode by its exact title, honest about what we know (titles and the description only; a note never claims
we listened), one concrete offer (a free 60-second Short built on that episode's idea, crediting the show), one ask, 70 to 140 words,
no link, no price, no promised result. Code holds a note that breaks any of these before Jev is asked; Jev's personalisation and spam
scores count only above the confidence floor, otherwise the code's proof stands.

## Outcomes and the kill rule
After the owner sends one: `python -m faceless collab outcome <slug> sent` (then `replied`, `declined`, `collab`, `no_reply`).
`collab status` shows the reply rate. Kill: no reply from 30 sent notes. The committed memory is hashes only; never commit a show
name. A yes means a Short about their episode: facts about the host need a research brief first (rule 8).
