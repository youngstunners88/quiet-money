# The question bank

Copy these verbatim. Rewording changes the scores and makes batches incomparable. Every question is atomic: one
judgement, one answer. `fallback` is what the code uses when Jev cannot answer - it is a real heuristic, not a
placeholder, so the loop still runs with no key.

## Lead questions (state = the lead card)
```python
from faceless import decide

LEAD_Q = {
 "fit": decide.Q("score",
   "How well does this project match a buyer for short-form crypto promo video and KOL posts: a mid-to-large Web3 "
   "brand (DeFi, L1/L2, infrastructure, gaming, NFT, exchange, wallet) with a marketing budget and an audience to "
   "reach? Judge the project, not the quality of this research.",
   fallback=0.5,
   levels=["no fit: not a Web3 brand, or a micro-cap with no audience",
           "weak: real but tiny, or a category that does not market with video",
           "possible: real project, right category, size unclear",
           "good: established, right category, clear audience",
           "strong: large or well funded, right category, visibly markets itself"]),

 "budget": decide.Q("noul",
   "Does this state contain a public signal that this project pays for marketing - a funding round, a grants or "
   "marketing programme, paid KOL posts, an agency credit, or paid ads? Answer only from the state.",
   fallback=0.3),

 "gap": decide.Q("score",
   "How badly is this project's short-form video missing? Judge what their feed does now against what short vertical "
   "promo video would add.",
   fallback=0.5,
   levels=["no gap: they already post strong short-form video regularly",
           "small: some video, decent quality",
           "real: rare or weak video, mostly text and charts",
           "wide: no video at all, active text feed",
           "wide and urgent: no video, active feed, and something to announce"]),

 "timing": decide.Q("noul",
   "Does the state name a dated event in the next six weeks - mainnet, listing, token launch, season, conference, "
   "partnership or product release?",
   fallback=0.2),

 "pursue": decide.Q("choice",
   "Given fit, budget signal, content gap and timing, what should happen with this lead now?",
   fallback="review",
   options={"pursue": "worth a personalized first touch this week",
            "review": "plausible but something is missing or unclear; a person should look",
            "skip": "not a buyer, too small, wrong category, or no way to reach them properly"}),
}
```
Heuristic fallbacks when there is no key: `fit` 0.8 when the category is in scope and a size signal exists;
`budget` 0.9 with a sourced raise or paid-KOL signal; `gap` 0.8 when `posts_video` is false and cadence is weekly or
more; `timing` 0.9 with a dated event inside 42 days; `pursue` = pursue when fit and gap both clear their thresholds
and a public contact exists, else review.

## Draft gate questions (state = the drafted message plus the claims it makes)
```python
GATE_Q = {
 "personalization": decide.Q("score",
   "Does this message name something specific about this project that could only come from looking at it - a post "
   "subject, a dated event, a named product, a format choice - rather than flattery or anything that would fit any "
   "project?",
   fallback=0.5,
   levels=["generic: would fit any project unchanged",
           "shallow: names the project but nothing specific about it",
           "specific: names one real detail about them",
           "specific and useful: names a real detail and says what to do about it",
           "sharp: names a real detail, a dated moment, and the exact thing to make"]),

 "spam_risk": decide.Q("score",
   "Would a marketing lead at this project read this as a mass-sent pitch? Consider length, hype words, multiple "
   "asks, links, flattery and anything that reads as a template.",
   fallback=0.5,
   levels=["reads as written by a person to them specifically",
           "mostly personal, one templated line",
           "plausible but generic",
           "reads like a mail merge",
           "reads like spam: hype, several asks, or promises"]),

 "promise_free": decide.Q("noul",
   "Is this message completely free of promised results (views, followers, holders, volume, price), free of any "
   "stated price or discount, free of financial advice, and free of any claim about a token's value?",
   fallback=0.5),

 "verdict": decide.Q("choice",
   "What should happen to this draft?",
   fallback="rewrite",
   options={"pass": "ready for the owner to read and send",
            "rewrite": "the idea is right, the writing needs one more pass",
            "hold": "do not queue this: it breaks a rule or has nothing specific to say"}),
}
```
Heuristic fallbacks: `personalization` from whether the draft quotes a card field that has a source; `spam_risk` from
word count, hype-word hits and ask count; `promise_free` 0.0 on any hit in the banned list below; `verdict` from the
other three.

Banned-phrase list the heuristic checks (and the drafter must avoid): guaranteed, guarantee, viral, pump, moon, 10x,
100x, ROI, returns, "we will get you", "x views", "x followers", "best price", "% off", "limited slots", "financial
advice", "not financial advice" (if it is there, the draft is talking about the token, not the service).

## Calibration before any threshold moves
Jev's probabilities are not ground truth. Thresholds move only on recorded outcomes
(`channel/services/web3-video/outcomes.jsonl`), per `service-pipeline`'s weekly review: at least 30 sent messages,
and only when the direction is consistent two weeks running. The same discipline `faceless-bench` applies to any
model that decides - measure first, then trust.
