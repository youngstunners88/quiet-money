# Outbound: what the owner sends by hand

Nothing in this folder is ever sent by the engine. It holds drafts and the daily brief; the owner copies, sends and records.

| What | Where | Made by |
|---|---|---|
| Today's DMs (first message, two follow-ups, the after-reply line) | `drafts/<day>.md` (+ `.json` for the command center) | `python -m faceless dm` |
| DMs made from a prospect list (real handles) | `drafts/<day>.private.md`, gitignored | `python -m faceless dm --prospects people.csv` |
| The daily money brief | `brief/<day>.md` | `python -m faceless money` |
| The block list (one handle per line) | `private/blocklist.txt`, gitignored | the owner |
| What happened to each draft | `state/outbound.jsonl` (handles stored as hashes) | `python -m faceless dm log <draft_id> sent\|replied\|clicked\|bought\|dead` |

Rules the code enforces (`faceless/dmdesk.py`): 20 drafts a day at most, one message per person per 3 days, no link in a first message or
a follow-up, only the hub page or a live listing in the after-reply line, 280 characters, the offer layer's claim check on every line,
nothing while `state/PAUSE` exists. A draft with `[first name]` or `[their words]` still in it is not sendable.

Skill: `faceless-cash`. The Web3 service's client hunt is a different desk (`channel/services/web3-video`, `faceless/outbound.py`).
