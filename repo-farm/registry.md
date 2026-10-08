# Registry

## ACTIVE (in use now)
| Repo / tool | Job in the studio | How it is used |
|---|---|---|
| TypeSafe **Jev** (`typesafe-ai/skills`, `typesafe-sdk`) | Decision layer | `faceless/decide.py`: publish/hold and safe-to-publish questions; dry-run until `TYPESAFE_API_KEY` is set and records are reviewed |
| **keel** (codejunkie99/keel) | Design pattern only (macOS app) | Borrowed rules: host validates every choice; invalid or stale choice falls back to the ordinary route; decision records as JSONL |
| Edge neural TTS (`edge-tts`) | Voice (free) | Primary voice with word timings |
| Cloudflare Workers AI (FLUX.2 klein) | Images (free tier) | Primary image model, neuron-capped in the ledger |
| Gemini API | Scripts, judge, fallback TTS | Primary LLM chain |
| OpenRouter | LLM + image fallback | Second in both chains |
| Pollinations | Free image/text fallback | Third in chain |
| ElevenLabs | Premium voice | Opt-in (`--voice elevenlabs` or chain order) |
| Upload-Post API | Posting to TikTok/YouTube/IG | `publish.mode = "upload_post"` |
| FFmpeg + libass, Pillow, OpenCV | Render | Core of `pipeline/render.py` |
| anthropics/skills: **skill-creator** | Dev workflow | Used to shape `.claude/skills/faceless-*` |
| **agent-reach** (osp.fyi/agent-reach; also `skills/agent-reach`) | Trend research | Referenced by the `faceless-trends` skill for platform research |
| **Composio** (ComposioHQ/composio skill + `composio` SDK) | Connected apps: YouTube, TikTok, Instagram, Drive, Gmail | `providers/composio_tools.py`, `faceless composio ...`, skill `faceless-composio` |
| **HyperFrames** (heygen-com/hyperframes, Apache-2.0, pinned 0.8.136) | Motion cards: count-up numbers, charts, kinetic text; replaces AI stills for numeric beats and placeholder-art beats | `pipeline/cards.py`, skill `faceless-hyperframes`. Local render only, no API key; its `init`-installed agent skills are NOT used |
| Exa / Firecrawl / TinyFish (connected tools) | Trend + fact research | `faceless-trends` and `faceless-script` skills |

## PARKED (named future phase)
| Repo / tool | Phase | Why parked |
|---|---|---|
| elstongun/leviathan (`leviathan-index` crate) | Agent memory | Pattern adopted, binary not installed: it is a thin Rust CLI over SQLite FTS5 + BM25, and Python ships both. Crate was 1 day old (v0.1.0, 8 downloads) when evaluated 2026-10-06. Our version: `faceless/memory.py`, `python -m faceless memory`. Revisit if the corpus passes ~100k records. |
| **remotion-dev/remotion** (`npx create-video@latest`) | Phase 2: motion | React video for animated number counters/charts in the math pillar; adds Node render stack to CI |
| **HeyGen API** (video catalog, edit scenes) | Phase 3: avatar/presenter | Paid per minute; not needed for a faceless format yet |
| heygen-com/liveavatar-gpt-live-demos | Phase 3 | Live avatars: not part of the short-form pipeline |
| Bingeljell/image-to-3dlab | Phase 2 | Image → 3D/depth for 2.5D parallax shots from stills (cheap motion upgrade) |
| Veo 3.1 (via Gemini API) | Phase 2 | Text/image → short clips for hook shots; paid |
| transcriptx.ai | Phase 2 | Transcribe competitor/top videos for hook research |
| n8n-io/n8n | Ops | Visual workflows/webhooks if posting moves off GitHub Actions |
| stanfordnlp/dspy | Phase 2: optimization | Optimize the script prompt against real retention data once `metrics.jsonl` has 200+ rows |
| unslothai/unsloth | Phase 3 | Fine-tune a small script model on our winning scripts |
| Portkey-AI/gateway, diegosouzapw/OmniRoute | Scale | LLM gateway/router; `providers/llm.py` chains cover it for now |
| jlowin/fastmcp | Ops | Expose the engine as MCP tools (make, status, gauntlet) for any agent |
| tavily-ai/tavily-mcp | Research | Alternative search MCP if Exa/Firecrawl quotas run out |
| mendableai/firecrawl (self-host) | Research | Hosted API already available via key |
| 199-biotechnologies/claude-deep-research-skill | Research | Long-form topic research for story scripts |
| muratcankoylan/agent-skills-for-context-engineering | Dev workflow | Context-file patterns (already applied: CLAUDE.md → CONTEXT.md layering) |
| obra/superpowers | Dev workflow | TDD/planning skills for engine development sessions |
| anthropics/skills frontend-design, nextlevelbuilder/ui-ux-pro-max-skill, pbakaus/impeccable | Phase 2: dashboard | For a studio dashboard / link-in-bio landing page |
| D4Vinci/Scrapling | Research | BSD-3, very active (85k stars). Useful for ToS-permitted public pages only; its headline features are anti-bot/Cloudflare bypass, which we won't use. Our scanner needs only free APIs (autocomplete). Revisit if a needed source has no API. |
| Panniantong/Agent-Reach | Research | Multi-platform read access for agents *(unverified; from a social post)*. Evaluate licence and platform terms before any use. |

## REJECTED
| Repo / tool | Reason |
|---|---|
| Oros42/IMSI-catcher | Cellular surveillance tool: irrelevant and legally risky. Never use. |
| TheTom/turboquant_plus | LLM KV-cache quantization for local inference; we use hosted APIs |
| starknet.io | Blockchain L2; no role in a content business |
| camel-ai/owl | General multi-agent framework; the orchestrator is simpler and deterministic |
| huginn/huginn | Overlaps GitHub Actions + n8n |
| giancarloerra/SocratiCode | Codebase Q&A; unrelated to production *(unverified)* |
| joedhawan/Helios | Unrelated to the pipeline *(unverified)* |
| keel as an app | macOS/Apple Silicon only; we use its pattern, not the app |
| Yoinks (video downloader, repo unverified) | Downloads other creators' videos from 1,800+ sites: copyright and platform-ToS risk, and we make our own footage. *(unverified; from a social post)* |
| whaleyxbt/patchright-enhanced | Scrapes sites without APIs by mimicking real browsers; anti-detection use risks our accounts. *(unverified)* |
| Stanley (AI brand assistant) | Paid product promoted in an article; our weekly review loop and `faceless-scout` cover the same ground. |

## Intake 2026-10-08 (verified from dossiers in `repo-farm/intake/2026-10-08/`)

Each row was read from the project's own README, manifest, licence file or registry entry; nothing was installed or run. Stars and dates were unavailable where the GitHub API is closed to this machine.

### Active or adopted

| Tool | Stage | Why |
|---|---|---|
| antiwork/gumroad-cli | sell | Official Gumroad CLI (MIT), built for people and agents. |
| heygen-com/hyperframes | render | Already ACTIVE: Apache-2.0, pinned to 0.8.136, local render only. |
| anthropics/skills | dev workflow | Anthropic's skills reference repository. |
| TokConnect (mcp.tokconnect.com) | ideate | Read-only research MCP over public TikTok data. |
| Agent-Reach (osp.fyi/agent-reach) | ideate | Already referenced by the trends skill for platform research; the post describes a Python page-to-text fetcher. |
| Composio Gumroad toolkit | sell | Seven read tools (user, products, sales, license verification, webhooks), wired through the existing Composio setup. |

### Parked (named condition)

| Tool | Stage | Why |
|---|---|---|
| sov2000/etspi-cli | sell | GPL-3.0 command-line client for the Etsy API v3 (OAuth, listing and variant management). |
| administrativetrick/etsy-mcp-server | ideate | MIT, read-only Etsy API v3 server (search listings, shop info, trending, reviews) using an API key only; no OAuth, so it cannot write. |
| diffusionstudio/lottie | visuals | MIT text-to-Lottie agent skill (`npx skills add`). |
| AgriciDaniel/claude-ads | sell | MIT paid-media operations kit (audits, plans, creative briefs across twelve ad platforms), read-only by default with approval gates before any live change. |
| firecrawl-cli (npm) and firecrawl/cli | ideate | ISC, 28,677 weekly downloads, mature. |
| volcengine/OpenViking | ideate | AGPL-3.0 context database for agents (a filesystem-style memory). |
| nextlevelbuilder/ui-ux-pro-max-skill | package | MIT. |
| microsoft/agent-lightning | measure | MIT reinforcement-learning framework for training agents. |
| elevenlabs/skills | voice | MIT agent skills for text-to-speech, speech-to-text, sound effects, music, voice changing, noise isolation and dubbing. |
| Kapso (kapso.ai) | post | WhatsApp Business API platform (CLI, MCP, webhooks). |
| Monid (monid.ai, SKILL.md and docs) | ideate | A pay-per-use marketplace of data endpoints (mostly Apify actors and data vendors) behind a Bearer-key HTTP API. |
| Etsy developer MCP (mcp.api.etsycloud.com) | sell | Documentation-oriented, no shop actions (checked earlier this session). |
| youngstunners.etsy.com | sell | The shop page returns 403 to every fetcher here, so its state could not be audited. |

### Rejected (recorded so nobody re-evaluates)

| Tool | Stage | Why |
|---|---|---|
| cartesiancs/map3d | visuals | MIT. |
| diffusionstudio/editor | render | AGPL-3.0 desktop video editor for macOS and Windows that an agent drives. |
| next-state/open-dreamer | none | Research code and blog post on training a world model (Dreamer 4 reproduction, CoinRun, JAX). |
| gooseworks (npm) and GooseWorks | sell | MIT package from a SaaS: skills for ads and growth that run through its own MCP server, Google sign-in, a credentials file and a cloud 'Company Brain'. |
| mauriceboe/NOMAD (now TREK) | none | AGPL-3.0 self-hosted collaborative travel planner. |
| lekt9/unbrowse-openclaw | none | OpenClaw plugin that reverse-engineers site APIs. |
| calesthio/Crucix | ideate | AGPL-3.0 intelligence terminal over 27 sources, mostly geopolitics and trading: off-brand for a money-education channel. |
| x1xhlol/system-prompts-and-models-of-ai-tools | none | GPL-3.0 collection of extracted system prompts from commercial AI products. |
| ruvnet/wifi-densepose | none | MIT. |
| snarktank/antfarm | none | MIT team of coding agents (planner, developer, verifier, tester, reviewer) for the OpenClaw platform, installed by a curl script. |
| muapi-cli (npm and PyPI) | visuals | MIT, 386 downloads a week. |
| elevenlabs/cli and @elevenlabs/cli | voice | MIT. |
| mistralai/mistral-vibe | none | Apache-2.0 coding-agent CLI from Mistral, installed by a script, asking for a key. |
| imageflow.dev | visuals | A free browser image editor with no API, CLI or MCP. |
| Freebuff (freebuff.com) | none | An ad-funded coding agent. |
| opensourceprojects.dev post (MiroFish-Offline) | none | A blog post about a local-first agent playground that needs a local language model. |
| LiquidAI system-one-arcade (Hugging Face Space) | none | A Docker Space whose page gave no readable description from here. |

## Intake 2026-10-08b (verified from dossiers in `repo-farm/intake/2026-10-08b/`)

Each row was read from the project's own README, manifest, licence file or registry entry; nothing was installed or run. Stars and dates were unavailable where the GitHub API is closed to this machine.

### Active or adopted

| Tool | Stage | Why |
|---|---|---|
| Claude Haiku 5.5 (Anthropic announcement, 2026-10-07) | visuals | Anthropic's cheapest model: $0.10 in and $0.50 out per million tokens for prompts up to 100k, adaptive thinking on by default, 1M context. |
| SpringPrompt: Claude Haiku 5.5 review (2026-10-08) | measure | An independent benchmark write-up, used as the cross-check on Anthropic's own numbers: far better than Haiku 4.5, behind GPT-6 Luna on listings, decks and ad planning, wordy at the default medium effort (a product listing cost… |

### Parked (named condition)

| Tool | Stage | Why |
|---|---|---|
| superdesigndev/treg (treg.to) | ideate | A hosted per-call tool gateway ('OpenRouter for agent tools', Apache-2.0, self-hostable) whose lead-signals skill finds B2B buyers by hiring, funding, tech-stack and job-change signals and then looks up their emails and phones. |
| treg.to lead-signals and tutorial pages | ideate | Vendor pages: marketing claims only (a 4,710-signal run for $0.52 on 26 September 2026; 78.2% against 43% on People Search Bench for the same agent with and without treg). |

### Rejected (recorded so nobody re-evaluates)

| Tool | Stage | Why |
|---|---|---|
| morluto/rea (rea-agents) |  | A reverse-engineering toolkit (MIT, MCP server) for binaries, applications and runtime behaviour. |
