## Planner tool stack: firecrawl-cli, icm-architect, FreeConvert (2026-10-12)

Read with `python -m faceless intake` (dossiers in `repo-farm/intake/2026-10-12/`). Dossiers made by `python -m faceless intake` (GitHub's API answered 403 for icm-architect, so facts come from raw files); FreeConvert read with Exa. Nothing was installed or run: the `npx -y firecrawl-cli@latest init --all --browser` line was read, not executed.

| resource | verdict | stage | why | worth taking |
|---|---|---|---|---|
| firecrawl-cli (npm) | **park** | ideate | Three HIGH flags (install hook, pipe-to-shell in its docs, asks for secrets) and the exact line the owner pasted, `init --all --browser`, installs skills into every detected coding agent globally and opens a browser login: that rewrites the agent environment, which intake rule 1 forbids and nothing about the planner needs. We already hold FIRECRAWL_API_KEY, so a scrape or search is one reviewed REST call from our own provider code if research ever needs it. Not needed for artwork, lessons or the PDFs. | Call Firecrawl's REST API directly from faceless/providers behind a cap when a research brief needs a page read; never run init. |
| icm-architect (RinDig, MIT) | **park** | package | A Claude skill that scaffolds 'folder structure as agent architecture'. This studio already works that way (CLAUDE.md routes, a CONTEXT.md per workspace, the filesystem is the state). Installing it adds nothing; reading it did: its ten invariants match ours and name two gaps worth closing. | Each stage folder's CONTEXT.md states inputs, process, outputs and what a human checks before the next stage; keep reference material apart from per-run products; generated indexes are rebuilt by script, never hand-edited (the planner's INVENTORY.md already is). |
| FreeConvert (freeconvert.com, API v1) | **trial** | visuals | A hosted file-conversion API (convert, compress, resize 200+ formats; job of import, convert, export/url). It has no watermark or handle removal, so it is not the cleaner: that stays local (OpenCV). Its real use here is turning picture formats Pillow cannot open (HEIC, TIFF, PSD, AVIF) into PNG before ingest. Free accounts get 20 conversion minutes a day, 5 minutes per file, API use needs a free account token; files are uploaded to FreeConvert and deleted after a few hours. Written as an optional provider, off until the owner creates the token and sets FREECONVERT_API_KEY; never used for anything that must stay private. | The job shape (import, convert, export/url, poll) and per-task refunds on failure. |

### Decisions only the owner can make

- **firecrawl-cli (npm):** Say whether the Firecrawl key should be used for research briefs; do not run `init --all` on any machine that holds other agents' skills.
- **icm-architect (RinDig, MIT):** none
- **FreeConvert (freeconvert.com, API v1):** Create a free FreeConvert account and put the API token in the environment as FREECONVERT_API_KEY (intake never signs up for anyone).
