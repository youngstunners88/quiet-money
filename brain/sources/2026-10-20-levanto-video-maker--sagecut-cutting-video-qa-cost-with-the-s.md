---
id: 2026-10-20-levanto-video-maker--sagecut-cutting-video-qa-cost-with-the-s
source: https://docs.google.com/document/d/1RxuXvf4enzPHDq405dSmmTe2Ldvlj_P-WaNMhA7yufE
speaker: Levanto video maker (works for the vendor)
title: "SageCut: cutting video QA cost with the Sage decision model"
channel: none (a social post by the vendor's video maker, pasted into the owner's Google Doc "Video saving costs")
published: unknown
length: about 440 words (the post, a vendor skill summary and a setup note)
captured: 2026-10-20 (438 words, sha256 ed9dece73a930faf), read in full; the API key in the setup note was removed from the raw file and is not copied here
method: owner
fetch_quality: full
topics: [tools]
---
# SageCut: a vendor says a decision model cuts frame-by-frame video QA from $127 to 16 cents

## In one line
The speaker works for Levanto, the company that sells the Sage decision API, so every result is a claim about their own product; the idea of sending only defective frames to an expensive model is worth testing against our own gauntlet, but only after we measure it.

## Claims
| # | Claim | Label | Note |
|---|---|---|---|
| 1 | QA on one Remotion video cost $127 with Claude subagents reviewing every frame, and $0.16 with Sage | U | vendor employee, one video, no receipts shown |
| 2 | Across 6 A/B tests the output was "exactly the same", at one tenth the QA cost and one quarter the QA time | U | the one-tenth figure does not match claim 1 (a drop from $127 to 16 cents is far more than ten times); one of the two numbers is wrong or they measure different things |
| 3 | Sage read all 3,153 frames of the video | U | |
| 4 | Only frames Sage flags as defective go to a top model to fix | S | the design; its quality is untested |
| 5 | Before this, subagent frame review burned a Max plan and added 4+ hours a video | U | |
| 6 | Sage is an HTTP decision API with yes/no, choice, scale, sort and tags questions; yes/no, choice and tags answers return null when unsure, which should go to a human (scale returns an expectation plus a confidence) | S | from the owner's summary of the vendor's skill; matches how we treat Jev holds |
| 7 | Vendor prices: free plan $0.20 of usage a month at $0.05 per million input tokens; paid plans from $14 to $249 a month; output $10 per million tokens; web search $0.10 each | U | vendor's own price list, not checked on their site |
| 8 | Image inputs (beta) are base64 PNG, JPEG or WebP up to 4 MiB, no remote URLs; context about 32K tokens | S | from the owner's summary of the vendor's skill |
| 9 | The key is read from an environment variable and never logged or committed | S | in line with rule 11; no key is set in this environment today |

## Tactics
- Put a cheap yes/no model in front of an expensive reviewer; escalate only the failures.
- Treat "unsure" as its own answer and send it to a person.
- Batch the frames in one request instead of one call per frame.

## How Quiet Money could use it
1. `faceless-bench` and `faceless/decide.py`: the idea matches our semantic gates. Measure first: run Sage against a set of frames our gauntlet already labelled, on the free tier, and compare the misses before it gates anything. Needs a key from the owner (rule 11); we do not request one on our own.
2. `faceless-gauntlet`: if it passes the measurement, it could be one more advisory check that can only hold a video, never release one (the same rule as Jev in MARKETING.md section 11).
3. Cost: our spend is held under the $3 daily ceiling (rule 10), so the saving may be small; check the real QA spend with `python -m faceless status` before opening this.
4. `topics/tools.md`: logged as watched, not adopted, under `faceless-intake`.

## Reject
- Installing the SageCut skill or its release repo into this project before `faceless-intake` has read it (unreviewed code, rule 11).
- Quoting "$127 to 16 cents" or "1/10 the cost" in any script, listing or post: a vendor's unverified numbers (rule 1; never-do 1).
- Letting any external model release a video that our own gates held: the gauntlet's hard gates stay ours (rule 6).
- Copying the setup note's habit of pasting a key into a document: the raw file had a key removed; no key goes in a note, command or reply (rule 11).
- Sending frames to a service with no check of what it keeps or trains on: terms are unchecked.

## Open questions or tests
- Do the two vendor figures (one tenth and $127 to 16 cents) describe the same test? Ask the vendor or test.
- Does Sage catch the faults our gauntlet already catches in captions, face crops and flicker? Measure on a labelled set before any gate.

## Evidence
- "I'm the only video guy at Levanto."
- "Across 6 A/B tests the output was exactly the same, at 1/10 the QA cost and 1/4 the QA time."
- "Yes/No, Choice and Tags return null when unsure; send null to a human." (from the owner's summary of the vendor's skill, not the vendor's own text)
