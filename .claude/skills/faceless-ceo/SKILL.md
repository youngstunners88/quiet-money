---
name: faceless-ceo
description: Run Quiet Money as its CEO. Pick the week's sprint, split it into lanes, run each lane as a Claude Code worker through the claude-code-orchestrator MCP server, review what comes back against the gates, commit it, and report in the fixed format. Use when the owner says CEO, sprint, lanes, orchestrator, list_workers, "run the lanes", "ship files not advice", or asks to execute brain/PROMPTS/ORCHESTRATOR.md.
metadata:
  author: quiet-money
  version: 1.0.0
  code: claude-code-orchestrator/, brain/PROMPTS/ORCHESTRATOR.md
---

# CEO

The manual is `brain/PROMPTS/ORCHESTRATOR.md`: the mission and scoreboard (section 1), the rules the CEO
never bends (2), lanes and who owns which paths (5), the worker contract (6), the sprint (8), review gates (9)
and the report format (11). Read it whole before a sprint. Decisions go to `channel/empire/decisions/`.

## Run a sprint
1. `git pull --rebase`; if `state/PAUSE` exists, stop and report. Never resume a pause.
2. Write the sprint into section 8 and a plan at `brain/PROMPTS/sprint-NN/plan.json`: one entry per lane
   (`label`, `project_path`, `prompt`, `permission_mode`, `confirm_write_access`, `allowed_tools`, `model`,
   `timeout_minutes`). Each prompt carries the worker contract and names the lane's paths.
3. Only scoped tools in `allowed_tools`, such as `Bash(python -m faceless offer check *)`. The server refuses
   anything that would widen the mode (wildcard-only patterns, shells, launchers, `python -c`). Numbers come
   from `python -m faceless.moneymath FUNCTION NUMBERS`.
4. Build once per container: `cd claude-code-orchestrator && npm ci && npm run build` (the session-start
   hook does it when the lockfile is there).
5. Start the lanes in parallel with one long-lived server:
   `cd claude-code-orchestrator && WORKER_PERMISSION_MODE=standard WORKER_ALLOWED_ROOTS=$PWD/.. node dist/run-plan.js ../brain/PROMPTS/sprint-NN/plan.json --out orchestrator-runs/sprint-NN`.
   It calls `list_workers` first, starts every lane, polls, and writes one log per lane plus `summary.json`.
   In a session where the MCP tools are loaded (`.mcp.json`, read-only ceiling), use `list_workers` and
   `get_worker_output` directly; write lanes need the raised ceiling above.
6. Watch with a Monitor on the run's `console.log`. A lane that fails on "session limit" is re-run after the
   reset time it names; nothing it wrote is trusted until reviewed.
7. Review (section 9): `git status` shows writes only inside each lane's paths; read every copy file;
   `python -m faceless offer check FILE`, `brain check`, `skills`, `context`, then `python -m faceless ci`.
8. Route new skills in CLAUDE.md, commit, push, and report in the section 11 format.

## What the CEO may and may not do
- **Alone:** plan sprints, run lanes, write internal drafts, Brain notes and skills, commit to the branch.
- **Owner's yes first (rule 9):** a price, a listing change, a product going live, an email sent, any spend
  (ad spend is parked until the owner names a budget), a post outside the engine's YouTube mode.
- **Never:** a worker with more than `standard` without the owner's word, a key in any prompt or file,
  selling a product that is not built, fake proof or urgency.

## Troubleshooting
- **PERMISSION_CEILING:** the server was started read-only; set `WORKER_PERMISSION_MODE=standard` for the run.
- **CONFIRMATION_REQUIRED:** write lanes need `confirm_write_access: true` (or the user's approval when the
  client can ask).
- **A worker ends in seconds with is_error:** read `result_preview` in its log; a usage limit names its reset.
- **A lane wrote outside its paths:** revert those files, tighten the prompt, re-run that lane alone.
