# Every tool and key in the environment is approved for use

**Decided by the owner, 2026-10-22, in the service-desk build conversation.** Recorded because it changes how every
future session behaves, not just this one.

## The decision

If a key is in the environment or a tool is connected, the answer is yes. Use it, and use the best tool for the job
rather than the cheapest-looking one. Firecrawl was the specific case that prompted this - it is approved for
research and page reads - but the decision is general and now sits in `CLAUDE.md` as rule 16.

Stop doing all of these:
- opening an "awaiting owner approval" question about a tool
- withholding a key from a routine or a GitHub workflow because nobody had said yes
- reporting a job as blocked when an available tool would have done it

## What still needs the owner's yes (unchanged)

Money and the outside world: raising a cap or the daily ceiling (rule 10), listing a product or changing a price,
posting anywhere but the engine's YouTube mode (rule 9), and sending outreach to a real person. A cap refusing a call
is still the system working - ask for the cap, never route around it.

## What changed in the repo

| File | Change |
|---|---|
| `CLAUDE.md` | rule 16 added (tools are approved; the narrow list that still needs a yes); the document-reading rule became 17 |
| `tests/test_hygiene.py` | `FIRECRAWL` added to the secrets an optional runner may read |
| `.github/workflows/outbound.yml` | gets the `FIRECRAWL` secret |
| `faceless/outbound.py` | the X profile is rendered through Firecrawl first, since the plain read is login markup |
| `channel/services/web3-video/SOURCES.md` | Firecrawl listed as an approved source, with its page cap |
| `channel/empire/RESOURCES.md` | the open question from 2026-10-12 marked answered |

## The honest limit found while wiring it

Firecrawl renders an X profile into clean text - bio, follower count, verified flag - where plain HTTP returns login
markup. **Neither reads the timeline:** X serves no posts to a logged-out reader, and we do not log in. So a lead's
content gap is judged from its profile and its own site and docs, and `posts_video` means "nothing we can see says
they post video". The follower count is now captured, because audience size is a real fit signal for this service.
