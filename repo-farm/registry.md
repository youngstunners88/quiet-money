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
| Exa / Firecrawl / TinyFish (connected tools) | Trend + fact research | `faceless-trends` and `faceless-script` skills |

## PARKED (named future phase)
| Repo / tool | Phase | Why parked |
|---|---|---|
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
| volcengine/OpenViking | Scale | Context database for agents; overkill at current size |
| kapso.ai | Ops | WhatsApp notifications/approvals for held videos |
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
| mauriceboe/NOMAD | Travel planner; unrelated *(unverified)* |
| giancarloerra/SocratiCode | Codebase Q&A; unrelated to production *(unverified)* |
| joedhawan/Helios | Unrelated to the pipeline *(unverified)* |
| calesthio/Crucix | Unrelated to the pipeline *(unverified)* |
| lekt9/unbrowse-openclaw | Browser API discovery; not needed with official APIs *(unverified)* |
| freebuff.com | Coding assistant; not part of the runtime |
| keel as an app | macOS/Apple Silicon only; we use its pattern, not the app |
| Yoinks (video downloader, repo unverified) | Downloads other creators' videos from 1,800+ sites: copyright and platform-ToS risk, and we make our own footage. *(unverified; from a social post)* |
| whaleyxbt/patchright-enhanced | Scrapes sites without APIs by mimicking real browsers; anti-detection use risks our accounts. *(unverified)* |
| Stanley (AI brand assistant) | Paid product promoted in an article; our weekly review loop and `faceless-scout` cover the same ground. |
