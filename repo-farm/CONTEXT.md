# Repo farm

Every external repo or tool considered for the studio gets one row in `registry.md` with a verdict:

- **ACTIVE**: wired into the engine or the workflow today.
- **PARKED**: useful for a named future phase; revisit when that phase starts.
- **REJECTED**: not useful for this business (or risky). Recorded so nobody re-evaluates it.

## How to add one
1. Name the job it would do in the studio (scripting, visuals, voice, render, posting, analytics, decisions, dev workflow).
2. Check it beats what the engine already does on cost, quality, or speed, and that it runs headless in CI.
3. Add a row. If ACTIVE, add it behind a provider interface (`faceless/providers/`) so it stays swappable.

Verdicts are based on each project's stated purpose. Rows marked *(unverified)* were not
inspected in depth; re-check before relying on them.
