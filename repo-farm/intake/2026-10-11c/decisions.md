## Motion designs: eight more repos from the owner's second Google Doc (2026-10-11)

Read with `python -m faceless intake` (dossiers in `repo-farm/intake/2026-10-11/`). Dossiers by `python -m faceless intake`; READMEs were mostly short, so these judgments rest on stated purpose, licence files and what the studio already runs.

| resource | verdict | stage | why | worth taking |
|---|---|---|---|---|
| claude-motion-design (howseen-ai) | **trial** | render | MIT. A Claude Code skill for motion videos in pure code with HTML, Playwright and ffmpeg: the same method the studio already runs (HyperFrames is HTML plus headless Chrome plus ffmpeg), and the same loop the JavaScript Claude video teaches (storyboard first, contact sheet, fix, re-render). Read from its README only. | Its storyboard-before-code step and contact-sheet check, as a gate for new drawn scenes. |
| hyperframes-motion-reel-skill (Sunwood-ai-labs) | **trial** | render | MIT. A skill for motion reels on HyperFrames, which is our renderer. Closest match to the stack, so the likeliest source of scene patterns that already respect HyperFrames' seek rules. | Reel structures and scene patterns for new card kinds. |
| motion-graphics-skills (charlie947) | **park** | render | MIT. A set of motion-graphics skills; the README gave the dossier little to judge, so it is not wired in. Our own skills (faceless-hyperframes, faceless-ledger) already cover the loop. | Prompts for specific effects, if one is missing. |
| claude-motion (whaleyxbt) | **park** | render | MIT, but the dossier found nothing about what it does. The same author's patchright-enhanced is already rejected in the registry (anti-detection scraping), which is no reason to reject this one, but it is a reason not to install it unread. | Unknown. |
| claude-remotion-skill (haidrrrry) | **kill** | render | MIT skill for Remotion. We render with HyperFrames; a Remotion skill would pull in a second renderer and a Node/React build for no gain. | Nothing. |
| Remotion (remotion-dev/remotion) | **kill** | render | React video renderer. The intake tool read the licence file as MIT, but Remotion's own terms are a source-available licence that asks companies above a small size to buy one; verify by hand before ever relying on it. It duplicates HyperFrames (HTML to MP4 locally, Apache-2.0, already pinned and hash-checked). Moves the registry's earlier PARK to KILL. | Its idea of a video as a function of the frame number, which the drawn series already uses. |
| klik-anim-skill-creation (t3knobox) | **park** | render | No licence file found and no README text the dossier could judge; unverified. | Unknown. |
| awesome-motion-design-agent-skills (frankxai) | **park** | render | A curated list (CC0 by its badge; the licence file text was not recognised, so check). Useful as a reading list, not a dependency. | Names of other skills worth a look. |

### Decisions only the owner can make

- **claude-motion-design (howseen-ai):** Read it once before building the next ledger scene kinds; do not install it.
- **hyperframes-motion-reel-skill (Sunwood-ai-labs):** Read its patterns when adding a card kind; copy ideas, not files.
- **motion-graphics-skills (charlie947):** Skim when a scene needs an effect we lack.
- **claude-motion (whaleyxbt):** Read the README by hand before any use.
- **claude-remotion-skill (haidrrrry):** None.
- **Remotion (remotion-dev/remotion):** None.
- **klik-anim-skill-creation (t3knobox):** Check the licence and README by hand before using any of it.
- **awesome-motion-design-agent-skills (frankxai):** Browse it when looking for a specific technique.
