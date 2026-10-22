# The weekly outbound review

`W = channel/services/web3-video`. Write the result to `W/reviews/<YYYY-WW>.md`. Reads only; changes are proposed in
the review and then made deliberately.

## 1. Count what happened (raw counts first, always)
```bash
W=channel/services/web3-video
python3 -I - <<'PY'
import json, collections
rows = [json.loads(l) for l in open("channel/services/web3-video/outcomes.jsonl")]
print("events:", dict(collections.Counter(r["event"] for r in rows)))
for key in ("angle", "proof_block", "channel", "tier_pitched"):
    sent = collections.Counter(r[key] for r in rows if r["event"] == "sent" and r.get(key))
    pos  = collections.Counter(r[key] for r in rows if r["event"].startswith("reply-positive") and r.get(key))
    print(key, {k: f"{pos[k]}/{v}" for k, v in sent.items()})
PY
```

## 2. The rates (and the minimum before any of them means anything)
| Rate | How | Acts only at |
|---|---|---|
| Reply rate | any reply / sent | 30 sent |
| Positive reply rate | reply-positive + reply-question / sent | 30 sent |
| Call rate | call-booked / sent | 50 sent |
| Close rate | closed / quoted | 10 quotes |
| Per angle, per proof block, per channel, per category | the same, split | 20 sent in that slice |

Below the minimum, the review says "too small to act on" and nothing moves. Two weeks pointing the same way is the
bar for a threshold change.

## 3. Read the pattern, turn the matching knob
| Pattern | Most likely cause | Change |
|---|---|---|
| Replies come only from one category | the others are not buyers, or the angle is wrong for them | weight discovery toward that category; try one new angle for one other |
| Good replies, no calls | the ask is too big or too vague | soften the ask to "two examples", not the proof |
| High reply rate, nothing closes | wrong size of prospect, or price shock | move up-market in `fit`, and get the owner's quote earlier |
| One angle gets every positive reply | it matches the real buying trigger | make it the drafter's default; keep one slot for a challenger |
| One proof block always precedes a reply | that is the credibility that lands | reorder the proof blocks in the drafting brief |
| Drafts keep failing `personalization` | thin lead cards | fewer leads, deeper research (`service-leads`) |
| `spam_risk` rising across a model's drafts | that slug has drifted to template language | swap the slug for the next one in `models.json` |
| Any complaint or unsubscribe | the targeting or the channel was wrong for that lead | tighten the contact-route rule; never loosen it |
| Nothing at all after 50 sent | the offer or the audience, not the copy | raise it with the owner as a positioning question (`service-offer`), not as a copy tweak |

## 4. Feed it forward
- Rewrite the angle table in `W/PACKAGES.md` so the best-performing angle is first.
- Update the examples in the `service-outreach` skill's drafting brief so the free models see what worked.
- Note a threshold change, with the counts behind it, in the review **and** in `service-scoring`'s threshold table.
- Record anything that changes how the business sells as a decision in `channel/empire/decisions/`.

## 5. The review format
```
Outbound review <week>
Sent <n> | replies <n> (<n> positive, <n> question, <n> negative) | calls <n> | quotes <n> | closed <n>
Best: <angle / proof / category> - <counts> (<too small to act on | acting>)
Worst: <...>
Changed: <what, and the counts behind it>
Not changed (too small): <...>
Owner decisions needed: <at most two, or none>
```
At most two owner decisions a week. Everything else is the desk's own work.
