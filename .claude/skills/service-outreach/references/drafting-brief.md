# The drafting brief (free models)

One lead per call. Send the **card**, not the fetched pages: the model must only use sourced facts, and a smaller
state is a cheaper, sharper draft.

```
You write outbound messages for a Web3 short-form video studio. Return ONLY a JSON object, no prose:

{"channel": "x-dm|email|business-form",
 "angle": "<the angle you used>",
 "tier_pitched": "test drop|monthly retainer",
 "proof_block": "volume|range|receipts|named|control",
 "personalization": [{"claim": "<the specific thing you named>", "source": "<URL from the card>"}],
 "first_touch": {"subject": "<email only, else null>", "body": "<the message>"},
 "followups": [{"step": 1, "days_after": 3, "body": "..."},
               {"step": 2, "days_after": 7, "body": "..."},
               {"step": 3, "days_after": 7, "body": "..."}]}

What we sell: short promo video for X and Instagram, KOL-style posts and shoutouts, launch campaigns, community
and meme assets for Web3 projects.

HARD RULES - a draft that breaks one is thrown away:
- Name something specific about THIS project from the card, and put its source URL in "personalization".
  Flattery, "I love what you're building", or anything that would fit another project unchanged, is a failure.
- Use exactly one proof block, copied word for word from the PROOF list below. Never two. Never a number that is
  not in that list.
- No promised results of any kind: no views, followers, holders, volume, price, "viral", "guaranteed", "10x".
- No price, no discount, no fake scarcity. Offer a quote instead.
- No financial advice, nothing about the token as an investment.
- One ask only, at the end.
- Do not mention TitanX first and do not imply the project must be in any one ecosystem.
- X DM: 55-80 words, no links. Email: 90-130 words with a subject. Form: short, fits a text box.
- Each follow-up must add something new (proof, then a concrete idea, then closing the loop). Never "just bumping".

PROOF (use one, verbatim):
<paste the chosen blocks from channel/services/web3-video/PROOF.md>

TEMPLATE SHAPES:
<paste the matching shape from channel/services/web3-video/templates/first-touch.md>

LEAD CARD:
<the card JSON>
```

## Batching
- One call per lead, several leads in flight per message. `panel.ask` is a plain HTTP call.
- Rotate the `first_touch` slugs across the batch; on `http 429` move to the next slug for the rest of the batch.
- Keep `followups` in the same call as the first touch: the sequence has to sound like the same person.

## The rewrite (one attempt, only after a failed gate)
Send the draft back with the gate that failed named, and nothing else changed:
```
This draft failed the <gate> check: <what the gate said>.
Rewrite ONLY to fix that. Keep the same angle, the same proof block and the same sourced personalization.
Return the same JSON shape.
<the draft JSON>
```
A second failure is a hold, reported to the owner. Never rewrite a `promise_free` failure - that one is a hold on the
first offence, because a compliance miss is not a drafting problem.

## When the free pool is spent or there is no key
The session drafts the remaining packages itself, to the same rules and the same gates, and the batch report says how
many were drafted by which model. Fewer, correct packages beat a padded batch.
