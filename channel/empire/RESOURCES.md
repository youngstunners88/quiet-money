# Resource deep-dive (2026-10-08)

The coach's list ("how to build effectively") plus everything else wired into this environment, judged against our pipeline.
Facts come from the primary pages read on the date above (sources in each row). Verdict key: **built** = in the pipeline now,
**adopt pattern** = the idea is useful, the product is not, **park** = revisit when a condition changes, **kill** = do not use.

## The coach's list
| resource | what it is (verified) | verdict | what we did with it |
|---|---|---|---|
| [OpenAI Decisions API](https://developers.openai.com/api/docs/guides/decisions) | `POST /v1/decisions`, public beta, `gpt-6-luna`: typed answers (predicate probability, choice, score) about 10x faster than the Responses API; text and images | **adopt pattern** | The idea (judge with calibrated probabilities, not prose) is the core of our new QA layer. We have no OpenAI key, so the free open equivalent runs instead; the request shape is the same family. |
| [OpenRouter decision rankings](https://openrouter.ai/rankings/decisions) | Live ranking of decision models by request volume: Jev 1.13 (982M requests a week), Span-01 Lite, d1, Kev 4B, **Cloudflare Clef / Clef Flash**, Perplexity Decider, Upstage Solar Decide | **built** | Picked Cloudflare Clef: Apache-2.0, on Workers AI, reachable with the Cloudflare key we already hold, vision-capable. Jev stays a drop-in (`decide.py`). |
| [Cloudflare Clef](https://developers.cloudflare.com/changelog/post/2026-10-01-clef-workers-ai/) (found through the ranking) | 27B multimodal decision model, Jev-API compatible, $0.24 per M input tokens, up to 4 images per request | **built** | `faceless/providers/clef.py`, `qa.py`: stills are checked for readable text, faces and logos (a flagged beat becomes a designed card); scripts for promised returns, product pushing and hype. Calibrated on real data: positive controls flagged (face 0.92, text 0.98), a real calculator-keys still flagged (0.77), 0 false positives on 30 published scripts. About 28 neurons per still against 417 to generate it. |
| [EmbeddingGemma 2](https://blog.google/innovation-and-ai/technology/developers-tools/embeddinggemma-2/) | Google open model (Apache-2.0, released 2026-10-06): text, images, video, audio in one 768-d space, Matryoshka truncation, 8K context | **built (family)**, **park (v2)** | v2 is not hosted on Workers AI yet and local use needs torch. `embed.py` uses the hosted EmbeddingGemma 1 and Gemini's free embeddings behind one config line, so v2 is a one-word swap. Result: a variety audit and a semantic duplicate gate; they already found two same-day "10-year delay" videos and three near-identical "frugal secretary" stories. |
| [Meituan LongCat](https://github.com/meituan-longcat) (the doc's link had a typo: `longca`) | MIT-licensed model family: LongCat-2.0/2.5 (agentic LLM, 1M context, OpenAI-compatible API with a free allowance), Image (Apache-2.0, 6B), Video (MIT, 13.6B), AudioDiT, DeepResearch | **built (LLM)**, **park (image/video)** | `llm.longcat()` joins the script chain behind Gemini; skipped until the owner adds `LONGCAT_API_KEY`. Image and video models need GPUs: revisit if a free hosted endpoint appears, because hook clips and image supply are our two binding constraints. |
| [morluto/rea](https://github.com/morluto/rea) | MIT. "Reverse engineer anything with agents": decompile apps, understand a feature, rebuild it. `setup` registers MCP servers and a skill in every detected agent | **kill** | Recreating other people's features is the same IP trap as cloning best-sellers (X1/X5), and nothing in our rails needs it. We do not run `rea setup`. |
| [Orgo](https://docs.orgo.ai/introduction) | Cloud Linux desktops for agents, driven over an OpenAI-compatible API; sub-second boot, paid | **park** | Useful only where a task needs a full GUI that has no API. Our GUI-only chokepoints (Flow, account creation) are owner-only by design, so there is no job for it today. |
| [bops](https://github.com/nickvasilescu/bops) | FSL-1.1 Mac app: a team of bots, each with its own Orgo computer, AgentMail inbox and AgentPhone number, Composio apps, Honcho memory | **adopt pattern**, **kill product** | Agent-created accounts break platform rules (X3); the app needs an OpenAI key, an Orgo account and macOS. Patterns we already use or now copy: approvals before sending, paying or deleting; standing watches (the policy watchdog); least-privilege per agent; shared memory (`memory.py`). |

## Everything else wired into this environment
| resource | state today | verdict | note |
|---|---|---|---|
| [Muapi](https://muapi.ai) (a key already in the environment) | Pay-as-you-go media API: FLUX.2 klein 4B turbo $0.0052 per image, Seedance image-to-video about $0.15 per 5 s clip at 720p; public catalog at `/api/v1/models`, balance at `/api/v1/account/balance`; wallet $21.09 | **built** | Second image provider behind the free Cloudflare tier: about 8 times cheaper than OpenRouter ($0.0052 against $0.04), which makes the $5 Cloudflare plan the dearer option at our volume. Daily dollar cap, wallet runway in `forecast`, a top-up proposal 21 days out, NSFW rejection handled. Hook clips (Seedance) are built and live-tested but ship OFF until the owner approves the spend. |
| Exa (web search/fetch) | works | **adopt** | The weekly session fetches the six rule pages plain HTTP cannot read, then `faceless policy --record`. |
| TinyFish | needs the owner to sign in again | **park** | Would add monitors and browser runs; not needed while Exa covers fetching. |
| Windsor.ai (free plan) | one connected account, belonging to another channel | **park** | Can read TikTok Organic and write Instagram posts once the Quiet Money accounts exist. We do not read the unrelated account. Metrics loop (O3) can use it or Composio. |
| Cloudflare MCP | works; R2 not enabled (needs the dashboard), two unrelated Workers exist | **park** | R2 would host podcast audio; a podcast host does that for free, so no need. Do not touch the existing Workers. |
| Google Drive | works (account is the same one that holds your docs) | **adopt** | Used once to prove our spreadsheet functions behave the same in Google Sheets (NPER, FV, COUNTIF with `">"&cell`, INDEX/MATCH, IFERROR, N): all matched our numbers. The scratch file was trashed. |
| Gemini API | free tier works for text, embeddings and the experimental Lyria RealTime | **built** | Paid Lyria 3 / 3.5 return 429 (no free tier). RealTime built the music library. |
| Searchata, Advanced GSC | no Search Console property connected | **park** | Light up when the site is verified in Search Console (owner step in `faceless-seo`). |
| CoinGecko | works | **kill** | Crypto content is the highest-risk corner of finance and off-brand. |
| Caffeine | works | **park** | Builds apps on the Internet Computer; our calculators are static pages. |
| HyperFrames skills + media-use (installed 2026-10-06) | present as reference docs | **adopt pieces** | Bundled sound effects are Pixabay-licensed (fine in videos; not redistributable, so never committed). BGM, image and voice catalogs need a HeyGen login (owner gate, parked). Local pieces (Kokoro voice, transcription, background removal) are not needed today. |
| Composio | YouTube connected | **keep** | Reads only. Writes stay owner-approved. |

## What changed in the pipeline because of this
1. Every generated still is checked for readable text, faces and logos before it is rendered; flagged beats become designed cards.
2. Every script is checked for promised returns, product pushing and hype by a decision model, and for sameness against our own history by embeddings.
3. Videos use real instrumental beds chosen by series instead of one synthetic bed.
4. A policy watchdog and a verified rule digest (`channel/compliance/`) guard the revenue rails; a variety audit tracks the monetization risk YouTube's rule creates.
5. LongCat is a third script provider the moment a key exists.
6. Image supply is free Cloudflare, then Muapi at $0.0052 per image; the month costs about $6 instead of about $42 on OpenRouter.
7. Hook clips (Muapi Seedance, $0.15 each, checked frame by frame before use) are built and off; two a day is about $0.30.
