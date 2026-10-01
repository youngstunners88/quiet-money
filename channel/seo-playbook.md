# SEO + AEO playbook (extracted from the owner's research docs, adapted to Quiet Money)

Sources: "SEO" doc (Kimi's discoverability audit, written for Lil Blunt) and "Website/SEO mission" doc
(Promptwatch citation data, Nick Gray's backlink list, the preferred-sources tactic, and the Ahrefs podcast
with Dan Petrovic on answer-engine optimization). Each principle below is tagged with what we built.

## What changed in discovery (2026)
| Finding | Implication | Built |
|---|---|---|
| AI assistants answer from search indexes (ChatGPT ~ Bing, Gemini ~ Google, Claude ~ Brave) | Rank in those indexes or you're never in the consideration set | Crawlable site; robots.txt explicitly allows Bingbot, GPTBot, OAI-SearchBot, ClaudeBot, Claude-SearchBot, PerplexityBot, Google-Extended |
| Reddit fell from 15% of ChatGPT citations to ~0; review sites 7% → 0; **help centers/documentation +32%** | Own the documentation-style source instead of renting social platforms | Money Rules Library: one structured page per video (rule, story, key numbers, sources, FAQ) |
| Google grounds every answer (one claim, many citations); OpenAI grounds one-to-one | Be the single best page for each specific question | One rule per page, clear H1 = the question it answers |
| Models extract verbatim snippets, not summaries | The sentence that survives extraction must state the rule plainly | "The rule:" block + key-numbers list near the top of every page |
| Pre-training bias: models favor brands that are widely, consistently present on quality sites | Be consistent everywhere: same name, handle, description, links | `sameAs` schema + identical handle `@quietmoneyrules` on every platform |
| Topical centrality: a site that is about one thing ranks for that thing | No off-topic pages | Site is 100% money rules; series hubs cluster topics |
| Search engines measure engagement | Pages must give a quick win | Calculators (`/tools/`) and a printable checklist |
| llms.txt is cheap and harmless | Add it | `/llms.txt` lists every rule |
| Prompt "search volume" doesn't exist | Track quantized probes over time, not prompts | `python -m faceless aeo` → `analytics/aeo.jsonl` (mention rate, ordinal, citation share) |
| Generic AI copy is detectable by compression alone (Shannon/gzip) | Don't publish slop; quality filters will drop it | `voice_quality` gauntlet gate (`faceless/quality.py`) |
| Page → prompts reverse method | Know which questions each page should win | `aeo.page_to_prompts()` |

## Technical checklist (from the Kimi audit)
- [x] Meta description, canonical, Open Graph + Twitter card on every page
- [x] Schema.org JSON-LD: Organization, WebSite, Article, FAQPage, BreadcrumbList, VideoObject (when the YouTube id is known), WebApplication (calculators)
- [x] sitemap.xml, robots.txt, RSS feed, llms.txt
- [x] AI-readable About page in plain language (what it is, who it's for, how numbers are checked, what we don't do)
- [x] IndexNow key + `python -m faceless site indexnow` (pings Bing on every deploy)
- [x] "Add as a preferred source on Google" badge in the footer
- [ ] Google Search Console: add the property, paste the token into `studio.toml [site].google_verification`, submit the sitemap
- [ ] Bing Webmaster Tools: import from Search Console (one click), or paste `bing_verification`
- [ ] Custom domain (e.g. quietmoneyrules.com) once traffic justifies it; keeps all links if set up with redirects

## Backlinks and mentions (quality over quantity)
1. **Profiles that link back** (same day accounts exist): YouTube "Links", TikTok bio, Instagram bio, GitHub repo homepage, Linktree-style pages.
2. **Directories for personal/creator sites** (Nick Gray's list approach): submit the site to reputable creator/link directories; record each in `analytics/backlinks.md`.
3. **Citation mining**: `analytics/aeo.jsonl` stores the URLs engines cite for our entities ("best personal finance YouTube channels" listicles, etc.). Those pages are the outreach list: politely ask to be included, with a one-line pitch and the library link.
4. **Content platforms**: one weekly long-form post (Medium/Dev.to/Substack/LinkedIn) expanding a top-performing rule, linking to its library page.
5. **Communities**: help first, link second (r/personalfinance rules ban self-promo; answer questions with the library page only when it is the best answer).

## Virality hooks (adapted from the game's three hooks)
- **Shareable cards**: every rule's key number is a natural share image (e.g. "$6,000 at 24% = 21 years"). Post as carousels/pins linking to the rule page.
- **Series identity**: five named series let viewers binge; pinned comment points to the next part.
- **Character**: Ronald Read-style "quiet millionaire" stories are the memeable core; make them a recurring series.

## 30-day plan
| Week | Focus | Deliverables |
|---|---|---|
| 1 | Accounts + funnel | Create channels with the brand kit; site live; Search Console + Bing; first 35 videos posted |
| 2 | Index + community | IndexNow on every deploy; 10 directory submissions; answer 10 real questions with library links |
| 3 | Citation outreach | Mine `aeo.jsonl` cited URLs; pitch 10 listicle owners; 2 long-form posts |
| 4 | Double down | Weekly AEO probe trend; best pillar gets 2 slots/day; shareable cards for the top 5 rules |
