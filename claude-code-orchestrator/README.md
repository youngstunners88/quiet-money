# claude-code-orchestrator

A local MCP server (stdio) that lets one Claude Code instance, the **orchestrator** (for example the desktop app),
start, prompt, monitor and collect output from other Claude Code instances running as terminal processes, the
**workers**. Workers run `claude -p` (non-interactive) in a project folder you name, read-only unless you say otherwise.

Built with TypeScript, the official MCP TypeScript SDK (`@modelcontextprotocol/sdk`) and Zod. Node.js 18+.

## Quick start

Run these from this folder:

```bash
npm ci                    # install the pinned dependencies from package-lock.json
npm run build             # compile to dist/ (entry points: dist/index.js and dist/run-plan.js)
npm test                  # build + unit tests (a fake Claude CLI; no API calls, no cost)
RUN_INTEGRATION=1 npm test   # also start ONE real read-only worker (costs a few cents; model: haiku)
```

Register the server with Claude Code (from this folder, or use an absolute path from anywhere):

```bash
claude mcp add claude-code-orchestrator -- node dist/index.js
claude mcp add claude-code-orchestrator -- node /absolute/path/to/claude-code-orchestrator/dist/index.js
```

A relative `dist/index.js` only resolves when Claude Code runs in this folder, so the absolute form is the one to
use for other projects. Add `-s user` to make it available in every project, or `-s project` to write it to the
project's `.mcp.json`. Settings go in with `-e`:

```bash
claude mcp add claude-code-orchestrator -e WORKER_PERMISSION_MODE=standard -e WORKER_ALLOWED_ROOTS=/home/me/code \
  -- node /absolute/path/to/claude-code-orchestrator/dist/index.js
```

Verify it:

```bash
claude mcp list           # should show claude-code-orchestrator ... Connected
```

Inside a Claude Code session, run `/mcp` and check that `claude-code-orchestrator` is connected with six tools.

Example orchestrator prompt:

> "Use the claude-code-orchestrator MCP to start a worker in /path/to/project, ask it to analyze the codebase, then review its output and suggest improvements."

## Tools

| Tool | Inputs | Returns |
|---|---|---|
| `start_worker` | `project_path`, `initial_prompt?`, `allowed_tools?`, `model?`, `permission_mode?` (`read_only` default), `confirm_write_access?`, `timeout_minutes?`, `label?` | the worker's status (with `worker_id`) |
| `send_prompt` | `worker_id`, `prompt`, `wait_seconds?` (default 120, max 600), `timeout_minutes?` | `status`, `response` text, `session_id`, `turn_cost_usd` |
| `get_worker_status` | `worker_id` | `status`, `reason`, `elapsed_ms`, `last_activity`, `pid`, `session_id`, `cost_usd`, `exit_code`, `result_preview`, ... |
| `get_worker_output` | `worker_id`, `tail_lines?` (default 200, max 2000) | newest lines, each labelled `[stdout]` or `[stderr]` |
| `stop_worker` | `worker_id` | final status (`terminated`) and the last 50 lines |
| `list_workers` | none | running and recently finished workers (last 50): id, label, project path, status, mode, start time; plus the limits |

Every reply is JSON text. Every error is MCP text content with `isError: true` holding:

```json
{ "error_code": "CONFIRMATION_REQUIRED", "message": "...", "worker_id": null, "suggested_fix": "..." }
```

Error codes: `INVALID_INPUT`, `UNKNOWN_TOOL`, `PROJECT_PATH_NOT_FOUND`, `PROJECT_PATH_NOT_ALLOWED`,
`PERMISSION_CEILING`, `CONFIRMATION_REQUIRED`, `TOOL_NOT_PERMITTED`, `TOO_MANY_WORKERS`, `WORKER_NOT_FOUND`,
`WORKER_BUSY`, `WORKER_TERMINATED`, `FOLLOWUP_UNSUPPORTED`, `SPAWN_FAILED`, `INTERNAL_ERROR`.

### Worker statuses

`starting` (process spawned, no output yet), `running`, `waiting_for_input` (created without `initial_prompt`;
`send_prompt` starts it), `completed`, `failed` and `terminated`. `reason` says why a worker failed or ended:
`timeout`, `exit_code_N`, `killed_by_SIGNAL`, `result_error: <subtype>`, `no_result_event`, `spawn_error: ...`,
`stopped_by_request`, `server_shutdown`.

### Output

stdout is Claude Code's `stream-json`, rendered to short lines: `system: session ... started`, `assistant: ...`,
`tool: <name> <short input>`, `tool_error: ...`, `result: ...` and `result_meta: ...`. Lines that are not JSON are
kept as they are. Each worker keeps its newest 5000 lines; replies stop at 20,000 characters, dropping the oldest
lines first and saying so on the first line.

### Follow-up prompts

`claude -p` answers one prompt per process, so there is no live session to type into. A follow-up therefore starts
`claude -p "<prompt>" --resume <session_id>` in the same folder with the same permissions, under the same
`worker_id`. If a worker never reported a session id (it crashed early), `send_prompt` returns
`FOLLOWUP_UNSUPPORTED` and suggests starting a new worker with the accumulated context in `initial_prompt`.
While a turn runs, `send_prompt` returns `WORKER_BUSY`.

## Safety and permissions

Write access needs **two keys**: the server ceiling and the user's approval.

1. `WORKER_PERMISSION_MODE` (environment) is the ceiling: `read_only` (default), `standard` or `full_access`.
   A `start_worker` above it fails with `PERMISSION_CEILING`.
2. Any mode other than `read_only` also needs the user's yes. When the MCP client supports elicitation, the server
   asks the user itself (mode, project path, tools, task) and starts the worker only on an explicit approval; a
   decline, a cancel or no answer within 10 minutes returns `CONFIRMATION_REQUIRED` (logged as `start_refused`), and
   `confirm_write_access` is ignored, so the calling model cannot approve on the user's behalf. Clients without
   elicitation (run-plan, where the user writes the plan file) fall back to `confirm_write_access: true`, which the
   orchestrator may only set after the user approved write access.

| Mode | Tools offered to the worker | Flags |
|---|---|---|
| `read_only` (default) | Read, Glob, Grep | `--tools Read,Glob,Grep --allowedTools Read,Glob,Grep --disallowedTools Edit,Write,NotebookEdit,Bash` |
| `standard` | + Edit, Write (+ scoped extras such as `Bash(python -m pytest *)`) | `--permission-mode acceptEdits`, Bash and NotebookEdit denied unless an extra scopes them |
| `full_access` | + Bash (+ any extras) | `--permission-mode acceptEdits` |

Every worker also gets `--permission-prompts none` (anything not pre-approved is denied instead of waiting for an
answer nobody can give), `--strict-mcp-config` (no MCP servers inside workers) and, unless `WORKER_RESTRICTED=0`,
`--restricted` (settings files with their hooks and allow rules are ignored, and file tools stay inside the project
folder). `--dangerously-skip-permissions` and `bypassPermissions` are never used, and `allowed_tools` can never
widen a mode: read_only accepts only Read/Glob/Grep patterns; standard accepts other tools only when scoped to a
literal command or path. A pattern may not contain parentheses, backslashes or commas inside its specifier (Claude
Code would split such an entry into extra rules), wildcard-only patterns (`Bash(***)`, `Bash(* * *)`,
`WebFetch(domain:*)`) are refused, and a scoped Bash pattern must start with a real command that does not itself run
other commands or inline code: shells and launchers (`sh`, `bash`, `env`, `xargs`, `sudo`, `nohup`, `timeout`,
`npx`, ...) are refused, interpreters only with a script or `-m module` (`Bash(python -m pytest *)` yes,
`Bash(python -c *)` no), and `uv run`/`npm exec`-style runners only with a named command after them.

Other rules:

- The worker's working directory is the real path of `project_path` (symlinks resolved); the path must exist and be a
  directory, and when `WORKER_ALLOWED_ROOTS` is set it must sit inside one of those roots. No `--add-dir` is passed.
- At most `WORKER_MAX_CONCURRENT` (3) workers run at once. Each task has a timeout (`WORKER_TIMEOUT_MS`, 10 minutes;
  `timeout_minutes` can change it up to `WORKER_MAX_TIMEOUT_MS`). On timeout, `stop_worker` or server shutdown the
  worker's process group gets SIGTERM, then SIGKILL after 5 seconds. Claude Code runs Bash tool commands detached, in
  sessions of their own, so each run also carries a `CCO_RUN_ID` marker in its environment: on Linux every process
  of the same user that still carries it (dev servers, watchers, long test runs) gets the same signals, and whatever
  is left when the worker exits is killed. A command that drops its environment (`env -i ...`) escapes the marker.
- Workers do not inherit the server's environment. They get an allowlist: `PATH`, `HOME`, `USER`, `LOGNAME`,
  `SHELL`, `LANG`, `LC_*`, `TERM`, `TMPDIR`, `TZ`, `XDG_*` dirs, the proxy and CA variables (`HTTPS_PROXY`,
  `HTTP_PROXY`, `NO_PROXY`, `ALL_PROXY`, `NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, ...) and Claude Code's own auth and
  provider variables (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL`, model overrides,
  `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_USE_BEDROCK`/`VERTEX`, plus `AWS_*` only with Bedrock
  and `GOOGLE_*`/`CLOUD_ML_*`/`VERTEX_REGION_*` only with Vertex). `WORKER_ENV_PASS` adds names; `WORKER_ENV_STRIP`
  removes names. Variables that tie a process to the parent Claude Code session (`CLAUDECODE`,
  `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_REMOTE*`, `CLAUDE_CODE_MESSAGING_*`,
  `*SESSION_INGRESS*`) are never passed, not even through `WORKER_ENV_PASS`. The environment is never logged,
  returned or put in an error.
- Every start, prompt, completion and termination (and every refused start or prompt) is appended to
  `logs/orchestrator.jsonl`: `ts`, `event`, `worker_id`, `project_path`, `permission_mode`, `model`, `prompt`
  (redacted, at most 2000 characters), `status`, `reason`, `cost_usd`.
- Key-like strings are removed before anything is logged or returned: `sk-...`, `sk-ant-...`, `lv_live_...`,
  `ghp_`/`gho_`/`github_pat_...`, `AKIA...`, JWTs, `Bearer <token>`, `NAME=value` where NAME contains KEY, TOKEN,
  SECRET or PASSWORD, private key blocks (every line from `BEGIN ... PRIVATE KEY` to `END`), and the literal values of
  the server's own credential-like environment variables. Text is redacted whole before it is split into lines or
  shortened, so a key cannot leak in pieces.

Known limits, worth knowing before raising the ceiling:

- When the Bash tool is available (full_access, or a scoped Bash extra in standard), Claude Code itself auto-approves
  read-only shell commands such as `ls` or `pwd`, and under `acceptEdits` also simple file commands such as `touch`
  or `mkdir` inside the project.
- `--restricted` confines Claude Code's file tools to the project, but a shell command run in full_access can still
  reach other paths the user account can reach. For untrusted work, run the server inside a container or sandbox.

## Configuration

All settings are environment variables; `.env.example` lists them with their defaults. A `.env` file in this folder
is read at start-up on Node 20.12+ (variables already set in the environment win).

| Variable | Default | Meaning |
|---|---|---|
| `WORKER_PERMISSION_MODE` | `read_only` | Ceiling for worker permission modes |
| `CLAUDE_BIN` | `claude` | Claude Code CLI used for workers |
| `WORKER_MAX_CONCURRENT` | `3` | Workers running at once |
| `WORKER_TIMEOUT_MS` | `600000` | Default timeout per task |
| `WORKER_MAX_TIMEOUT_MS` | `7200000` | Largest timeout a caller may ask for |
| `WORKER_KILL_GRACE_MS` | `5000` | SIGTERM to SIGKILL wait |
| `WORKER_ALLOWED_ROOTS` | unset | Colon-separated roots that project paths must sit in |
| `ORCHESTRATOR_LOG_DIR` | `<package>/logs` | Where `orchestrator.jsonl` goes |
| `WORKER_RETAIN_FINISHED` | `50` | Finished workers kept for `list_workers` |
| `WORKER_MAX_OUTPUT_LINES` | `5000` | Output lines kept per worker |
| `WORKER_RESTRICTED` | `1` | Pass `--restricted` to workers |
| `WORKER_ENV_PASS` | unset | Extra comma-separated variable names passed to workers on top of the allowlist |
| `WORKER_ENV_STRIP` | unset | Extra variable names removed from the worker environment |

## run-plan: several workers from one file

The workers live inside the server process, so a plan has to go through one server that stays up until the end.
`run-plan` does that over stdio with the client library in `src/client.ts`:

```bash
node dist/run-plan.js plan.json --out runs/today          # --poll-seconds 15 by default
```

```json
{
  "workers": [
    {
      "label": "structure",
      "project_path": "/path/to/project",
      "prompt": "List the files in this repository and explain the project structure",
      "permission_mode": "read_only",
      "model": "sonnet",
      "timeout_minutes": 10
    },
    {
      "label": "tests",
      "project_path": "/path/to/project",
      "prompt": "Run the test suite and summarise the failures",
      "permission_mode": "full_access",
      "confirm_write_access": true,
      "allowed_tools": ["Bash(npm test *)"]
    }
  ]
}
```

**Verifier lane.** A write lane may carry `done_when`, a list of 1-12 acceptance criteria (a read-only lane may not: it produces no diff). When the lane completes, `run-plan` captures `git diff HEAD` (plus untracked file names), starts a fresh read-only worker that is given only the task, the criteria and that diff (never the builder's summary or result), and parses the last standalone `VERDICT: PASS` or `VERDICT: FAIL` line from its output. `summary.json` gets `claimed_done`, `verified` (`pass`, `fail`, `unverified` when there was no verdict, `not_required` without `done_when`), `verification_evidence` and `verifier_log`, plus `all_verified`; the exit code is 0 only when every lane completed and every verified lane passed.

It prints `list_workers`, starts every entry (in parallel up to the concurrency limit, queueing the rest), polls
`get_worker_status` every 15 seconds until all are completed, failed or terminated, writes each worker's
`get_worker_output` (tail 2000) to `<out>/<label or worker_id>.log` and a `summary.json`, and exits 0 only if every
worker completed (and every lane with `done_when` was verified). Relative `project_path`s are read against the plan file's folder. Each worker's log is written as
soon as it finishes. Ctrl-C stops the running workers first: run-plan starts its server with
`ORCHESTRATOR_PARENT_HANDLES_SIGINT=1`, so the server ignores the terminal's SIGINT, and run-plan stops the workers,
writes their logs and `summary.json` (stopped workers show `terminated`), then closes the server.

## Layout

```
src/config.ts           environment -> typed configuration (ceiling, limits, paths)
src/permissions.ts      permission modes -> Claude Code CLI flags; allowed_tools checks
src/process-manager.ts  worker lifecycle: spawn, stream capture, timeouts, stop, resume, retention
src/stream-parser.ts    stream-json lines -> readable lines + session id, result, cost
src/redact.ts           key and token redaction
src/logger.ts           JSONL audit log
src/errors.ts           OrchestratorError and the JSON error payload
src/format.ts           reply size cap and tail fitting
src/tools.ts            MCP tool definitions (Zod schemas) and the server
src/index.ts            stdio entry (dist/index.js)
src/client.ts           typed client over the SDK's StdioClientTransport
src/run-plan.ts         plan runner CLI (dist/run-plan.js)
test/                   node:test suites; test/fixtures/fake-claude.mjs stands in for the CLI
```

The server uses the SDK's low-level `Server` so that schema failures come back as the same JSON error payload as
every other error (`McpServer.registerTool` answers those with plain text). Adding a tool (code review, test runs,
multi-worker delegation) is one more `defineTool({...})` entry in `TOOLS` in `src/tools.ts`: give it a Zod schema
and a handler; validation, the JSON schema in `tools/list` and structured errors come with it.

## Design plan (as built)

1. One `WorkerManager` owns every worker: a record with status, output ring buffer and the current `claude -p` run.
2. Each run is spawned without a shell, in its own process group, stdin closed, with stream-json output parsed line
   by line; the session id from the CLI makes follow-ups possible with `--resume`.
3. Permissions are enforced twice: by the flags passed to Claude Code, and by refusing any request above the
   ceiling, without confirmation, or with tools outside the mode.
4. Every boundary (logs, replies, errors) passes through redaction; every reply is capped.
5. Tests drive the real code against a fake CLI (lifecycle, output, timeouts, invalid inputs, resume, stop, redaction,
   audit log, stdio server, run-plan), and one opt-in integration test runs a real read-only worker.
