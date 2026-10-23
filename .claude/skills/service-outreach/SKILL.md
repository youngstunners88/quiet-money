---
name: service-outreach
description: Write the outbound messages for Quiet Money's Web3 video and KOL service: one personalized first touch per lead plus a 3-5 step follow-up sequence, drafted at volume by free OpenRouter models from a sourced lead card, gated before anything reaches the backlog, and sent only by the owner. Covers the drafting brief, the personalization rule, the channel choice (X DM, email to a published address, business form), what must never appear in a message, the rewrite loop and the send gate. Use when drafting or fixing outreach, writing follow-ups, when a reply needs an answer, or as step 4 of the service-outbound loop.
---

# Writing the outreach

Output: one package per lead at `channel/services/web3-video/outbound/<slug>.json` on the
`channel/services/web3-video/schema/outreach-package.json` shape. Read `POSITIONING.md`, `PROOF.md`, `PACKAGES.md`
and `templates/first-touch.md` before drafting. **Nothing here is sent.** The owner reads the backlog and sends.

## The one rule that makes this work
**Every message names something only research could know, and that thing has a source in the lead card.** A message
whose personalization line would fit any project is not a weaker message, it is a rejected draft: volume without
specificity burns the owner's accounts and the brand. If the card has no sourced observation, the lead goes back to
research or is skipped - the draft is never softened into a generic one to make the batch count.

## Draft only for pursue leads
Leads the scoring step marked `pursue` with confidence at or above the floor (`service-scoring`). A `review` lead is
listed for the owner, not drafted. A `skip` lead is never drafted.

## Pick the channel from the card's contact route
| Card route | Channel | Shape |
|---|---|---|
| DM-open X account | `x-dm` | Shape A, 55-80 words, **no link** |
| Published partnerships / marketing address | `email` | Shape B, 90-130 words, subject required |
| Public business enquiry form | `business-form` | Shape C, fits a short box |
No public business route means no draft (`service-leads`). Never guess an address, never message a personal account,
never contact an individual who is not the published route.

## Build each message
1. **Angle** from `PACKAGES.md` by the card's strongest signal (dated event beats content gap beats budget signal).
2. **Tier** to pitch: retainer for a project with a budget signal, test drop otherwise. **Never a price.**
3. **One proof block** from `PROOF.md`, exactly as written there, with its as-of date when it is a count. One, never two.
4. **The named deliverable**: the actual thing we would make first, in their terms ("a 20-second cut of the v3
   announcement, hook on the fee change"), not "content".
5. **One ask.** Usually: may I send two examples closest to your niche, or the portfolio index.
6. **Follow-ups** from `templates/followups.md`: three steps, each adding something new - proof, then an idea, then
   closing the loop. Five steps only for a retainer-sized prospect. A step that cannot say something new is dropped.

Drafting runs on the free models named for `first_touch` and `followups` in
`channel/services/web3-video/models.json`, called with `faceless.panel.ask`. The brief that returns a clean package,
the batching pattern and the rewrite prompt are in `references/drafting-brief.md`.

## Then gate it (always, before the backlog)
Run the draft gates from `service-scoring`: `personalization`, `spam_risk`, `promise_free`, `verdict`. A pass goes in
the backlog with its `gates` block filled. One failure gets one rewrite; a second failure is a hold, reported to the
owner with the reason. `promise_free` failing is a hold immediately - never a rewrite-and-hope.

## Never in a message
- A promised result: views, followers, holders, volume, price, "guaranteed", "viral", "pump", "10x".
- A price, a discount or fake scarcity. Pricing is a quote, and the owner's call (CLAUDE.md rule 9).
- Financial advice or anything about the token as an investment (rule 2). We sell production, not calls.
- A number that is not in `PROOF.md`, or a client we did not work with.
- TitanX as the opening or the frame - proof, never the pitch.
- More than one ask, more than one proof block, or a link in an X DM.

## Replies and the send gate
The owner sends, and the owner forwards what came back. When a reply arrives: answer it in the owner's voice as a
**draft for them**. The first reply to any interested lead asks the discovery questions (`templates/discovery.md`), so we know what the client wants and their budget before quoting; prices come only from `[outbound.prices]` ($65 for 30 s, $120 for 75 s). Keep the same rules (no promises), and record the outcome through
`service-pipeline`. Nothing in this desk ever contacts anyone directly, and the gate does not move without the
owner's explicit yes (`service-outbound`, autonomy levels). `references/reply-playbook.md` has the common replies -
"send examples", "what does it cost", "not now", "do you guarantee views" - and how each is answered honestly.
