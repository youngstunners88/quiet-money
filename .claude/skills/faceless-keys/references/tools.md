# Tools the environment gives us (verified 2026-10-09 with `python -m faceless keys`)

Live variable per service, balances at the time of the check. Re-run the command before relying on a number here.

| Tool | Use it for | Live variable | State and cost | Gotchas |
|---|---|---|---|---|
| Muapi | image, video, audio, lipsync, 3D, edits, model search; the studio's Muapi desk | `MUAPI_API_KEY` | $20.19 | the desk (`faceless/muapi.py`) enforces a per-job cap, $2/day and the ledger. The CLI/MCP do not: MCP works over stdio (`muapi mcp serve`), HTTP shows "connected" with no tools. Files expire after about 30 days |
| OpenRouter | paid fallback for scripts and images, Haiku 5.5 motion scenes | `OPENROUTER_API_KEY` (`OPENROUTER_2` is the same account) | **$4.01 left** | the first thing to run dry; the image cap is 60 a day |
| Gemini | scripts, judge, embeddings, music library | `GEMINI_API_KEY` (`GEMINI` also works) | free tier | quota resets daily |
| Cloudflare | free FLUX stills, Clef quality checks, EmbeddingGemma, R2 | `CLOUDFLARE_API_KEY` with `CLOUDFLARE_ACCOUNT_ID` | free 10,000 neurons/day | `CLOUDFLARE_API_KEY2` and `CLAUDECLOUDFLARE_API` are other active tokens; `CLOUDFLARE_API_TOKEN` is rejected |
| Mistral | one more script-writing provider | `MINSTRAL_API_KEY` (and `…2`) | works, 46 models | misspelled variable name; read both spellings |
| Firecrawl | scrape, crawl, map, search, monitor public pages | **`FIRECRAWL`** (not `FIRECRAWL_API_KEY`, which is rejected) | 1,556 credits | use for public pages; TinyFish for logged-in or multi-step |
| TinyFish | search, fetch, multi-step browsing with profiles | **`TINYFISH_API_kEY2`** (`TINYFISH_API_KEY` is rejected); the connector also works | metered wallet | prefer fetch over full automation when both work |
| ElevenLabs | optional premium voice, sound effects, music, dubbing | `ELEVENLABS_API` or `ELEVENLABS_API_KEY` | models list works; account page forbidden | restricted keys: ask the owner to grant text-to-speech and user-read before depending on them; `_2` and `api_KEY2` are rejected |
| Monid | pay-per-use data endpoints when no dedicated tool covers the job | `MONID_API_KEY` | $9.71 | spends the owner's balance; prefer a dedicated tool |
| Vercel and v0 | deploys, env, v0 UI generation | `VERCEL`, `V0DEV_API` | work | the site lives on GitHub Pages; v0 for a redesign |
| Browser Use | a browser agent inside a product | `BROWSER_USE_API_KEY` (`BROWSERUSE` same) | works, **$0 credit** | needs a top-up before use |
| Tripo | 3D models | `TRIPO_API` | **rejected** | owner to reissue |
| xAI (Grok) | text/trend provider | `XAI_API` | **no credit** | the team has no credits yet |
| GitHub | repos, PRs, CI | `GITHUB_TOKEN` (also `GH_TOKEN`, `GITHUB_API_KEY`) | work, account youngstunners88 | the MCP connector is the normal route in sessions |
| Composio | connected apps (YouTube, Gumroad…) | `COMPOSIO_API` | works | reads only; writes need the owner's approval |
| PostHog, Sentry (`SENTRY_TOKEN`) | site analytics, error tracking | `POSTHOG_PERSONAL_API_KEY`, `SENTRY_TOKEN` | work | not wired in yet; `SENTRY_ORGANISATION_TOKEN` is forbidden |
| NameSilo | domain purchase (the short domain, O2) | `NAMESILO_API_KEY` | works | a purchase: the owner decides |
| AgentMail, Pixellab, itch.io | other projects | `AGENT_MAIL_API_KEY`, `PIXELLAB_SECRET` ($0), `ITCH_API_KEY` | work | not Quiet Money's; untouched |

Connectors that need no key (sessions only): Exa, TokConnect (TikTok research), Google Drive and Calendar, Cloudflare MCP, CoinGecko, Windsor.ai, Searchata, Advanced GSC.
Design-plugin connectors (Asana, Atlassian, Figma, Intercom, Linear, Notion, Slack) need the owner's one-time sign-in in claude.ai.

## Order of preference for a job
Free first (Cloudflare, Gemini, Edge TTS, HyperFrames), then Mistral, then the paid wallets (OpenRouter, Muapi) inside their caps, and Monid last.
