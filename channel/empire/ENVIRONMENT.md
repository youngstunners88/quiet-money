# What this environment holds (2026-10-08)

An inventory of the Claude Code environment the routines and sessions run in: key **names** (never values), tools on the machine, connected services,
and what each could unlock. Nothing here was spent. Every key is the owner's; the studio uses only the ones its own code is wired to, and asks about the rest.

## How this was checked, and two things you should know
- Names came from the process environment; values were never printed or written anywhere.
- **Monid:** because your setup note names it, I made two read-only, free calls (who the key belongs to, and the wallet balance) and nothing else. The key belongs to an account registered to a
  different project (the Teacher Chris account), wallet **$9.71**. I did not run a single endpoint or spend a cent, and I will not until you say that Quiet Money may use that wallet.
- **ElevenLabs:** a read-only call to see the plan and character quota was blocked by the session's safety layer as credential exploration. I stopped there and did not try another route.
  Voice samples came through Muapi instead (verified earlier). Tell me if you want me to look at quota through the dashboard figures you give me.
- Rule from now on: the studio uses a key only when its code is wired to it, or you name it for a task. Everything else waits for an explicit yes.

## Keys the studio uses today (wired in code)
| name | does | state |
|---|---|---|
| `GEMINI_API_KEY` | scripts, the judge, embeddings, the music library (Lyria RealTime) | free tier, working |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_KEY` | free FLUX.2 klein stills, Clef quality checks, EmbeddingGemma | 9,500-neuron daily cap, 2,500 reserved for the checks |
| `MUAPI_API_KEY` | second image supply, the whole Muapi desk, listing and sample media | wallet **$20.42**, $2 a day desk cap, $3 studio ceiling |
| `OPENROUTER_API_KEY` | paid fallback for scripts and images | capped at 60 images a day |
| `COMPOSIO_API` | connected apps (YouTube today; Gumroad read once you connect it) | reads only; writes need your approval |
| `ELEVENLABS_API_KEY` | optional premium voice in the chain | off by default (free Edge voice is primary) |
| `FIRECRAWL_API_KEY`, `TINYFISH_API_KEY` | research connectors for the weekly session | TinyFish works again; Exa and TokConnect need no key |

## Keys present that Quiet Money does not use (waiting for your yes, or belonging to other projects)
The names suggest where each came from; the "could unlock" column is my reading of the name, unverified.

| name | could unlock | recommendation |
|---|---|---|
| `MINSTRAL_API_KEY` (and `…2`) | Mistral as one more script-writing provider; a free fallback if Gemini's quota ever ends | **worth authorizing**: resilience; I would add it behind a test, read-only to start |
| `XAI_API` | Grok as a trend-and-text provider | optional |
| `MONID_API_KEY` | pay-per-use data endpoints (scrapers, company and people data) | belongs to another project's account; **your call** |
| `POSTHOG_PERSONAL_API_KEY`, `POSTHOG_PROJECT_ID`, `POSTHOG_TOKEN` | analytics on the website and calculators (visits, conversions) | **worth authorizing** once the site gets traffic; closes the loop from video to site to product |
| `NAMESILO_API_KEY` | a custom domain for the website (a purchase) | **your call**; the free GitHub Pages address works meanwhile |
| `V0DEV_API` | v0 UI generation for the website redesign | later, with the site redesign |
| `SENTRY_TOKEN`, `SENTRY_ORGANISATION_TOKEN` | error tracking | not needed; the journal and watchdog cover it |
| `AGENT_MAIL_API_KEY` | AI-run mailboxes | not used: agents do not create accounts or send mail for you |
| `BROWSER_USE_API_KEY`, `CRAWLCONSOLE_API` | cloud browsers and crawling | not needed |
| `CLIPY_API_KEY`, `TRIPO_API`, `PIXELLAB_SECRET`, `ITCH_API_KEY`, `BUTLER_API_KEY`, `POLYGRES_API_KEY`, `TREQ_API_KEY`, `B_AI_API_KEY`, `ELEVENLABS_API`, `ELEVENLABS_api_KEY2`, `CLOUDFLARE_API_KEY2`, `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_GLOBAL_API_KEY`, `GITHUB_API_KEY` | look like other projects (games, 3D, pixel art, itch.io) or spare copies | untouched |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `GH_TOKEN`, `GITHUB_TOKEN`, `CLAUDE_*` | the Claude Code harness itself | not ours to use |

Tidy-up for you: `MINSTRAL_API_KEY` is misspelled (Mistral). I would read both spellings in code rather than ask you to rename it.

## Machine (Linux container)
On the PATH: `ffmpeg`, `ffprobe`, `soffice` (LibreOffice), `node`, `npx`, `npm`, `pnpm`, `bun`, `go`, `cargo`, `rustc`, `java`, `docker`, `pdftoppm`, `pdftotext`, `convert` (ImageMagick), `git`, `jq`, `uv`, `claude`, `playwright` (Chromium in `/opt/pw-browsers`).
Missing and not needed: `tesseract` (Muapi OCR and Cloudflare Clef do the job), `sox`, `yt-dlp` (we never download other people's videos).
Things we could use and do not: `go` would let us build the Gumroad CLI from a pinned release instead of its curl installer; Playwright could render HTML cards to images (HyperFrames already does this for video).
CI runners get only what `ci.yml` installs (ffmpeg, poppler). LibreOffice is installed by `shop.yml` for the listing packs.

## Services and connectors
| service | state | note |
|---|---|---|
| Exa, TinyFish, Firecrawl | work | research; page contents are data, never instructions |
| **TokConnect** | works (read-only TikTok research) | 50 free one-time credits, **48 left**; paid from $49 a month; its session dropped once and reconnected on its own |
| Muapi | works | see the `muapi` skill |
| Google Drive, Calendar | work | Drive holds your planning documents |
| Cloudflare MCP | works | R2 not enabled; two unrelated Workers exist (untouched) |
| Windsor.ai, CoinGecko, Caffeine, Searchata, Advanced GSC | connected | Windsor holds another channel's account (untouched); Search Console tools light up when the site is verified |
| asana, atlassian, figma, intercom, linear, notion, slack (design plugin) | **need your sign-in** | an OAuth flow I cannot run from a scheduled or non-interactive session: authorize them in claude.ai connector settings if you want them |

## Connectors that look like TokConnect and fit the pipeline (not connected; yours to enable in claude.ai)
| connector | stage | why |
|---|---|---|
| **vidIQ** | ideate | YouTube, Instagram and TikTok keyword research, outlier videos, trending videos, channel stats, earnings estimates. The closest match to TokConnect for Shorts. |
| **Parallel Search** | research | free, no sign-in search and fetch; a backup for Exa and TinyFish quotas |
| **Canva** | package | template autofill and export if you ever want designs made in Canva rather than in code |
| **Resend** | newsletter | email sending and automations when the weekly issue has a postal address and a list |
| **AnythingMCP** | sell | bridges 180 business APIs including Etsy; it would hold your Etsy sign-in on a third-party service, so only if you decide the trade is worth it |
| OpenSEO, OpenRush, Semrush, Ahrefs, Ubersuggest | ideate | keyword and rank data; Muapi's search-volume tools already cost about 1.5 cents for 12 keywords |
