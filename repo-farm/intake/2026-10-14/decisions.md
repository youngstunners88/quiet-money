## ScaleDown SLM_Agent and DietCode, from the owner's message (2026-10-14)

Read with `python -m faceless intake` (dossiers in `repo-farm/intake/2026-10-14/`). Dossier by `python -m faceless intake`; the quickstart page was read with WebFetch. Nothing was installed or run.

| resource | verdict | stage | why | worth taking |
|---|---|---|---|---|
| SLM Agent (scaledown-team/SLM_Agent, npm @scaledown/migration-agent) | **park** | none | It is not a Claude Code token saver. Its README says it scans an application's code for AI API calls and migrates them to ScaleDown's paid small-model API (compress, classify, extract, summarize), which needs SCALEDOWN_API_KEY and sends our prompts to a third party. No licence file was found, it has 33 weekly downloads, and its install runs unpinned code. The `dietcode` package the owner named is a different thing: neither the repo's README nor the quickstart page describes it or what `dietcode setup` changes, so it cannot be reviewed. A tool that installs hooks into Claude Code's own settings and may route session context to an outside service needs its code read first. | The idea of compressing long context before a model call. The engine's own calls are small (Haiku at about $0.003 a song); the real token burn is this long session, not the pipeline. |

### Decisions only the owner can make

- **SLM Agent (scaledown-team/SLM_Agent, npm @scaledown/migration-agent):** If you still want DietCode: send its README or repo link so it can be read, say whether sending session context to ScaleDown is acceptable, and confirm a key is yours to use. Install it on your own computer, since it edits local Claude Code settings; it cannot work in this cloud container.
