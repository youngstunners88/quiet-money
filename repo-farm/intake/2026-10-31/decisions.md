## Showhow motion-graphics repos (Sirio Berati / tein) (2026-10-31)

Read with `python -m faceless intake` (dossiers in `repo-farm/intake/2026-10-31/`). Dossiers made by `python -m faceless intake`; GitHub's API answered 403, so facts come from raw README files. Nothing was cloned, installed or run.

| resource | verdict | stage | why | worth taking |
|---|---|---|---|---|
| Showhow (sirioberati/showhow) | **park** | render | MIT. Code-drawn explainer reels with word-timed scenes, a 60 fps render and a check file with measured thresholds. We already draw word-synced scenes in code (cards.py, cast.py, the Ledger series on HyperFrames), voice with word timings, and gate every video. It installs an MCP server (claude mcp add) and uses ElevenLabs, which is out of quota; neither is needed. Its README carries a promo for tein.ai. Nothing cloned or run. | Check rules that carry a measure and a threshold set from approved videos (camera speed, how long a picture holds still, colour strength, voice loudness), run frame by frame, with the report listing what failed. Map them onto craftcheck.py and the gauntlet; tiers (express, standard, studio) for render effort. |
| YouTube AI Motion Graphics (sirioberati) | **park** | render | MIT. A library of HTML motion boards (venn, timeline, 2x2 matrix, slope chart, heatmap, chart focus, scribble fill) exported to video by its own tools. Our HyperFrames cards cover the same job; the boards are a source of scene types, not a dependency. Its exporter runs a headless browser per frame, which our render already does. | Scene types we lack: slope chart (before and after), 2x2 matrix, timeline and venn. Re-draw them in our own card themes when a script needs one; credit the source in a comment. |
| Genjustsu Open Source Workflow (sirioberati) | **kill** | visuals | MIT. A character-swap video workflow that needs paid Seedance and Replicate keys (ENHANCOR_API_KEY, REPLICATE_API_TOKEN). It swaps people into existing footage, which does not serve a faceless money channel and raises likeness and platform-policy risk. Recorded so nobody re-evaluates it. | Nothing. |

### Decisions only the owner can make

- **Showhow (sirioberati/showhow):** operator
- **YouTube AI Motion Graphics (sirioberati):** operator
- **Genjustsu Open Source Workflow (sirioberati):** operator
