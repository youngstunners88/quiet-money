# Quiet Money Command Center

One page, served from this checkout, that shows the studio's real state and runs the commands that move it. On the computer it is an
app window; on the phone it is the same page over Wi-Fi or Tailscale.

It is a control surface, not a second system. Every number is read from the files that own it (`state/jobs`, `state/phone`,
`state/outbound.jsonl`, `state/receipts.jsonl`, `state/ledger.jsonl`, `studio.toml`, `herdr api snapshot`, agent config files). Every
button runs one existing `python -m faceless ...` or `herdr ...` command. There is no database and no background service of its own.

## The head-up display (the front page)

`/` is a read-only instrument panel (`faceless/hud.py`) fed by `GET /instruments.json` (`faceless/instruments.py`) every five seconds.
The action desk with the buttons is one link away at `/desk`. The display itself has no button and makes no POST.

| Area | What it shows | From |
|---|---|---|
| Top strip | Autopilot on/off/paused and its timer, the PAUSE file, server uptime, UTC clock, countdowns to the YouTube quota reset and the spend day, the YOU lamp | `crew.toml`, `state/PAUSE`, `systemctl --user is-active qm-autopilot.timer` |
| YOU | Everything that waits for a person, each with its one action: a rejected key, a screen to clear, a price, DMs to send, a paid agent that needs your click | derived missions, `state/tmp/keyhealth.json`, journal |
| Core | Spend today against the ceiling, Autopilot load (running against `max_parallel`), posted against the daily target with ready and held | `state/ledger.jsonl`, journal, `state/jobs` |
| Crew | One node per agent in `crew.toml` (a commented-out block is drawn "not installed"), lamp, plan, task, age of last beat, handoff lines | `state/agents/beats.jsonl`, claims, each agent's own store |
| Limits | Per agent: limit arc with 70% and 90% ticks, reset ring, burn marker, "empty in" and "resets in". Grey "unknown" with the reason when nobody has said | `crew.toml` plan fields, the agent's own store |
| Keys | present / ok / rejected / missing / placeholder / no-credit / unknown, by variable name. Never a value | env files, one free read-only question per service |
| Feed | Claims, skips ("held because ..."), handoffs, key changes, actions, newest first; repeats folded into one line with a count | `state/journal.jsonl` |

Source tags: `read` (a provider's API or a local file that is the record itself), `estimate` (counted or worked out by us: ledger
rows, Claude Code transcript lines, an agent's own beats, burn rates, reset clocks), `unknown`. An estimate is never shown as a read.

Lamps: live, idle, stale (holding work, silent past `stale_minutes`), dormant (past `dormant_minutes`; its mission is requeued),
blocked, benched (took a mission and went idle without a report), key-rejected, not-installed.

How the crew works together (skill `faceless-crew`, `AGENTS.md`): `instruments --for <agent>` before choosing work,
`crew claim <mission> --agent <id>` before starting (an O_EXCL file under `state/agents/claims/`), `agent beat` while working,
`crew ask` to hand off, `crew report` to finish. Autopilot (`crew tick`) checks key health, takes back missions from silent agents,
and holds a mission, logging the reason, rather than send it to an agent with a rejected key, one past `hold_percent` of its limit,
a dormant one or one dearer than `max_cost`.

To fill in a limit, edit the agent's block in `crew.toml` (`plan`, `limit`, `limit_unit`, `limit_window`, `reset`); the comment at the
top of that file lists the accepted values. No restart is needed.

## Mission control (the first tab)

The Mission tab is the whole business on one screen: revenue this month, the crew, and three columns.

- **To do** is derived from real state, in the order it pays. Nothing is typed in by hand, so a card disappears when the thing it
  names is no longer true.
- **In motion** is what has been sent and not yet reported.
- **Done today** is what was reported, with the one line the agent or the engine left.

Every card says who should do it and why:

| Route | Meaning |
|---|---|
| **Engine · 0 tokens** | A `faceless` command does it. No model is used. Always first. |
| **an agent · free / cheap / paid** | The cheapest installed agent that lists the job in `crew.toml`; among equals, one already awake. |
| **You** | Money and the outside world: sending a DM, setting a price. Never dispatched. |

**The crew is `crew.toml`.** One block per agent: `kind` (what herdr starts), `jobs` (what it is good at), `cost` (0 free, 1 cheap,
2 paid). Adding an agent is adding a block; any agent kind herdr can start can join.

**How agents work together.** Dispatch goes through herdr: an idle pane of that agent is used, or a `qm-<agent>` workspace is created
and the agent started in it. The agent is told to close the mission and how to ask for help:

```bash
python -m faceless crew report <mission> done "one line"     # or: blocked "why"
python -m faceless crew ask <writing|research|bulk|code|review|hard> "what you need"   # opens a card for a better-suited agent
python -m faceless crew board                                # the same board in a terminal
```

An agent that takes a mission and goes idle without reporting (a dead key, a login wall) sits out for the day and its mission is
offered to the next cheapest agent.

**Autopilot** has two drivers, and both take the same single step (`python -m faceless crew tick` is that step in a terminal):

- the toggle in the header, off by default: while the page is open it asks every 45 seconds;
- a systemd user timer every 5 minutes, with no window open, while `[autopilot] enabled = true` in `crew.toml`. Install it once:
  `cp tools/command-center/qm-autopilot.* ~/.config/systemd/user/ && systemctl --user daemon-reload && systemctl --user enable --now qm-autopilot.timer`.

A step starts the next mission a machine may do, up to `[autopilot] max_parallel`, one render at a time. It never does a "You" card,
never restarts a mission that reported blocked today, leaves the phone lane alone unless `[autopilot] phone = true`, and never starts
an agent dearer than `[autopilot] max_cost` (default 1: free and cheap agents only; a paid agent's card waits for your click).
Stop it with the toggle, `enabled = false`, `systemctl --user disable --now qm-autopilot.timer`, or `python -m faceless pause "why"`.

In `crew.toml`, `enabled = false` on an agent benches it, and `args` are passed when the board starts it (OpenCode's free model is
set there).

## The prospect machine

The DM desk writes a good message only when it knows who it is for. `python -m faceless prospect` supplies that: it collects people
who wrote under our videos (and creators who cover the same subject), sorts them by what they wrote, and hands the list to the DM
desk. The drafts appear on the DMs tab with the person's handle and their own words already in place. It is plain code: 0 tokens.
It never contacts anyone; you send.

| Source | How it is fed |
|---|---|
| Drop folder (`outbound/private/inbox/`, gitignored) | `python -m faceless prospect add --handle @x --text "their words" --video "title"`. The **Collect today's comments** mission sends a phone agent to read the TikTok inbox and add each comment this way. |
| YouTube comments on our own videos | Read on each run through the connected YouTube account. Says "unavailable" until `COMPOSIO_API_KEY` is set on this machine. |

A question is drafted first, then pushback, then someone describing their own situation, then peers. Promotion, emoji-only reactions,
anything older than 14 days, the block list and anyone already handled are dropped, with the reason kept. One batch a day. Reddit is
not a source: it refuses unsigned reads, and a stranger who never wrote to us is not a prospect.

On the board: **Turn N new comments into DM drafts** (Engine, 0 tokens) appears when the drop folder holds someone new; the DMs tab
has the same button. Skill: `faceless-prospect`.

## The toolbox

`python -m faceless toolbox find "what you need"` searches a local copy of the [Awesome REA](https://github.com/reacher-z/Awesome-REA)
catalog (about 1,100 reviewed tools and agent integrations for reading websites, apps, binaries and protocols, MIT). An agent finds
the right tool in one command instead of a web search. `toolbox sync` refreshes the copy into `state/tmp/toolbox.json`. A find is
vetted with `python -m faceless intake <url>` before anything is installed. Skill: `faceless-toolbox`.

## Launch

| How | What it does |
|---|---|
| App menu: **Quiet Money Command Center** | Runs `scripts/qm-command-center-app.sh` |
| `scripts/qm-command-center-app.sh` | Starts the server if it is down, then opens a dedicated Chromium app window (class `qm-cc`, own profile in `~/.config/qm-command-center/chromium`), already signed in. Falls back to the default browser. |
| `scripts/qm-command-center.sh start\|stop\|status\|open\|url` | The server in a herdr workspace named `qm-cc` (a background process when herdr is not running). `start` prints the QR code for the phone. |
| `python -m faceless serve --init-token` | Once per machine: makes the token (`QM_DASH_TOKEN` in `~/.config/quiet-money/env`). It is never printed. |

After changing code in `faceless/`, restart the server (`stop`, then `start`): it does not reload itself. A restart ends any action
that is still running.

## What each tab can do

A gold button runs something. A ghost "Copy" button copies a command or a message for you to use elsewhere. Text with a `source:` line
under it is display only.

| Tab | Button | What runs | Notes |
|---|---|---|---|
| Today | **Run today's batch** (tap twice) | `python -m faceless daily --no-publish` | Writes, renders, gates and packs. Nothing is uploaded: YouTube posting is off (CLAUDE.md rule 18) and passed videos reach TikTok through the phone lane. Can run for hours; the button shows "Running". |
| Today | **Advance phone** | `python -m faceless phone next --push` | Fetches the next phone job and puts its files on the phone. Posting is the phone driver's job; it closes the job with `phone done`. |
| Today | **Park jobs with no media** | `python -m faceless phone park` | Shown when queued jobs lost their video (the media branch keeps three days). Holds each with the reason so the lane has a head that can run. Undo one with Release after a re-stage. |
| Today | **Non-stop** toggle | see below | Off by default. |
| Money | **Write today's brief** | `python -m faceless money` | Writes `outbound/brief/<day>.md`. |
| Money | Open listing, Open DMs | a link, a tab change | |
| DMs | **Find people to write to** | `python -m faceless prospect` | Turns the drop folder and YouTube comments into drafts with real handles. Once a day. |
| DMs | **Draft today's DMs** | `python -m faceless dm` | Drafts only. Nothing is ever sent for you. |
| DMs | **Sent / Replied / Bought / No reply: close** | `python -m faceless dm log <id> <status> [--handle @x]` | Press after you sent or heard back by hand. The handle goes to the command and never to the journal. |
| DMs | Copy message, Copy | clipboard | |
| Jobs | **Retry** (failed) | `python -m faceless retry <job_id>` | Starts the job again from where it stopped. Packages; never uploads. |
| Jobs | **Release: re-run gates** (held) | `python -m faceless retry <job_id>` | Renders again from the files on disk and runs every gate. A pass becomes `packaged`; a fail stays `held` with the reason recorded. |
| Jobs | **Release** (phone job held) | `python -m faceless phone requeue <id>` | Back to the queue only if its gate is open; otherwise it stays held and says why. |
| Jobs | **View steps** | reads `/job.json?id=` | The job's own history, the error at the failing step, the gates that failed in its gauntlet report. |
| Agents | **Focus in herdr / Focus this pane** | `herdr workspace focus <id>`, `herdr agent focus <pane>` | Brings that workspace or agent pane to the front in herdr. |
| Agents | Copy: `claude`, `codex`, `hermes chat`, `hermes gateway run`, ... | clipboard | |
| Models | Search box, provider filter | filters the catalog | The tab starts, pulls and switches no model. |
| Alerts | The gold button on an alert | the same actions as above | Each alert names its fix; when the fix is an action, the button runs it. "Open Jobs" / "Open DMs" takes you to the buttons. |

### Display only, and why

- **Revenue, receipts, offers, spend**: money is counted only from receipts, and a price or a listing is the owner's decision.
- **Phone jobs blocked by a gate**: each gate is a switch or a daily cap in `studio.toml [phone]`.
- **Hermes sessions**: read from the session database; message content is never read.
- **Agent defaults, Ollama, the model catalog**: shown from config files and caches.
- **Targets**: only the ones written in `studio.toml` (`[production] videos_per_day`, `[outbound] ready_min_per_day`). There is no
  revenue target, so none is drawn.

### Not wired on purpose

- **Shipping a video that failed a gate.** The only override in the engine is `publish --force`, and it uploads to YouTube, which rule 18
  forbids. Release re-runs the gates; it cannot overrule them.
- **Resuming a pause.** Only the owner removes `state/PAUSE` (`python -m faceless pause --resume`).
- **Starting the Hermes gateway.** It is a long-running service; the page shows `hermes gateway run` to copy.

## After a click

1. The button shows the action's name with "…", and the strip under the header shows it running.
2. The server answers within about two seconds: either the result, or "running" for something slow. While anything runs the page asks
   again every two seconds.
3. When it ends the page reloads the state it changed. The strip shows the last action, its result and its exit code. Tap the strip (or
   open Alerts) for the activity log, with the command's own error text for anything that failed.

A refusal, a non-zero exit and a timeout are results. They are shown and journaled; nothing fails silently.

What happened is one `CC_ACTION` line per click in `state/journal.jsonl`, the same journal every stage writes. What is running right
now is held in the server's memory only.

## Non-stop

The rule comes from the Non-Stop Operating Spec (`~/open-device-mcp/nonstop/NON_STOP_OPS.md`): the moment a phone job is closed, the
next one is handed out with `python -m faceless phone next --push`.

With the toggle on, **this open page** asks the server every 30 seconds what to do. The server decides from the kill switch, the phone
queue and the journal:

| It says | Meaning |
|---|---|
| `run` | The staged job was closed (or nothing is staged): it runs **Advance phone** now. If the head of the queue has lost its video, it runs **Park** instead, so the lane keeps moving. |
| `waiting` | The next job is already on the phone. It is never pushed twice; it waits for the driver's `phone done`. |
| `idle` | The queue is empty, or everything left is stopped by a gate or a cap. |
| `tripped` | Two tries failed in a row. It stops for 30 minutes, then tries once more. Pressing Advance phone yourself, once the cause is fixed, re-arms it. |
| `paused` | `state/PAUSE` exists. Nothing runs. |
| `holding` | You are typing in a field on the page. Nothing runs until you leave it. |

It advances the phone lane only. It never starts a batch, retries a job or logs a DM.

It keeps the phone fed; it does not tap the phone. Posting still needs a phone driver recording `phone done` (an agent session using the
`faceless-phone` skill, or the home host in `tools/phone-host`).

### How to stop it

- Turn the toggle off. The setting is per browser and is off until you turn it on.
- Close the window. There is no background loop: no open page, no Non-stop.
- `python -m faceless pause "why"` (creates `state/PAUSE`). This also refuses every other button that moves the pipeline.

## Safety

- The token is required for the page, the data and every action. Buttons need it in the `Authorization` header; the `?t=` link opens the
  page and nothing else. A request from another origin is refused.
- Only the names in `faceless/actions.py` can run. Ids must be plain job, draft or pane ids, and commands run without a shell.
- One action per lane at a time (`phone`, `render`, `desk`, `herdr`). A second click on a busy lane is refused and says what holds it.
- With `state/PAUSE`, everything that moves the pipeline is refused. Logging a DM and focusing a pane still work.
- The journal is committed, so it gets a one-line summary per click: no command output, no handle.

## Alerts, in order

1. The studio is paused
2. Nothing ran today
3. Failed jobs, with the step most of them stopped at
4. Videos held for review
5. DM drafts and service-desk packages waiting for you to send
6. The Hermes gateway is down (only when a messaging platform is set up in `~/.hermes/.env`)
7. Everything else: unfinished videos, the phone lane, spend, follow-ups, unlisted products

## Files

| File | Role |
|---|---|
| `faceless/overview.py` | The projection: one JSON document from real state, the alerts, `job_detail` |
| `faceless/actions.py` | The allowlist, the runner, the journal line, the Non-stop decision |
| `faceless/serve.py` | The token server: GET reads, `POST /action` |
| `faceless/dashboard.py` | The page (one self-contained HTML file, phone layout below 900 px, sidebar above) |
| `faceless/missions.py`, `crew.toml` | The mission board, routing, dispatch, Autopilot |
| `faceless/prospects.py`, `faceless/toolbox.py` | The prospect machine; the tool catalog search |
| `faceless/agents.py`, `hermes.py`, `models.py` | Agents, Hermes and models, read only |
| `faceless/instruments.py`, `faceless/hud.py` | The instrument snapshot (crew, limits, keys, spend, feed) and the head-up display that shows it |
| `crew.toml`, `AGENTS.md`, `.claude/skills/faceless-crew` | The roster with plan and limit fields; the start-up note and working rules for every agent |
| `tests/test_instruments.py` | `python -m pytest -q tests/test_instruments.py` |
| `tests/test_command_center.py`, `tests/test_prospects.py` | `python -m pytest -q tests/test_command_center.py tests/test_prospects.py` |

## Log

### 2026-11-17

- **Head-up display.** `/` is now the instrument panel; the old page is `/desk`, unchanged. New: `faceless/instruments.py`, `faceless/hud.py`,
  `python -m faceless instruments [--json | --for <agent> | --probe]`, `GET /instruments.json`, `tests/test_instruments.py`.
- **Crew.** Codex and Gemini CLI are out of `crew.toml` and `faceless/agents.py`. The crew is Claude Code, Hermes, OpenCode, with Agent Zero as a
  commented block that is drawn "not installed". `code`, `review` and `hard` now route to Claude Code only, which costs 2, so Autopilot
  (`max_cost = 1`) holds those for a click.
- **Limits.** `crew.toml` gained `plan`, `provider`, `limit`, `limit_unit`, `limit_window`, `reset`, `key_env`, `key_file`, `usage`. Every limit is
  still "unknown" because nobody has said what the plans allow. Use is real: Hermes and OpenCode from their own session stores (`read`),
  Claude Code from its transcripts (`estimate`).
- **Symbiosis.** Claim locks (`crew claim`), requeue of a silent agent's mission (`crew reap`, run by every `crew tick`), Autopilot's gate and its
  skip log, `--agent <id>` on `crew claim|release|report|ask`. The dispatch prompt now tells every agent to run the pre-flight and to beat.
- **Keys.** Checked 2026-11-16 16:27 UTC: OpenRouter (engine), Composio, ElevenLabs and Hermes's own OpenRouter key all answered 200. The Composio
  line that once held a literal `***` now holds a real value in both `.env` and `~/.config/quiet-money/env` (one line each). Hermes's key was
  rejected (401) on 2026-11-15; it is accepted today. The board re-checks every ten minutes and writes a `CC_KEY` line when a state changes.
- **Ledger rows carry a time** (`t`) from now on, so spend has a burn rate. Rows written before have only a day; the burn says "unknown" until
  a timed row exists for the day.
- **Slow lane.** The overview takes about 20 s to build here. The panel never waits on it: a background thread refreshes it every 30 s into
  `state/tmp/instruments-slow.json` and the top strip shows its age.
- **Trap.** `/tmp` is a tmpfs with a per-user quota. When it fills, pytest and `python -m faceless ci` fail with "Disk quota exceeded" in tests
  that have nothing wrong. Stale `/tmp/faceless-ci-*` and `/tmp/pytest-of-*` folders are the usual cause.

### 2026-11-15

- **YouTube comments.** The board follows the last real read (`prospects.youtube_state()`), not the presence of a key. A project key (`ak_`) is in
  `.env` and `~/.config/quiet-money/env`; the read answers "quota used up" until midnight Pacific.
- **Client hunt.** `python -m faceless outbound run` had not run since 2026-10-24. It is now a board action (`outbound_run`) and an engine mission
  (`client-hunt-<day>`) offered once a day when no batch report exists; waiting packages become the owner mission `send-packages-<day>`.
- **Keys by hand.** `config.load_keys()` reads the studio `.env` and then the machine key file, so a typed command has the keys the timer has.
- **Known limit.** The "ready" tier needs Jev's own confident answer on spam risk and on pursue. In the first batch Jev gave neither for any
  package, so every package that passed the gates landed in "review". The thresholds are the owner's (`studio.toml [outbound]`); none was changed.
- **Restart trap.** `scripts/qm-command-center.sh stop` ends the shell that calls it when chained with other commands; run `stop` and `start` as
  separate commands.
- **First real YouTube read (08:02 UTC).** The source works. Of 48 comment threads on the channel, 47 are our own pinned comments and 1 is another
  person's, from 2026-10-21, with fewer than two words. YouTube currently holds nobody to write to; the prospect machine correctly drafted nothing.
- **Client hunt result.** 103 lead cards, 14 packages waiting on the owner (all "review"), 0 sent. Jev cost $0.0054.
- **Team board (e5d60da).** Every agent reports into `state/agents/beats.jsonl` with `python -m faceless agent beat <agent> <status> --task ...`
  (statuses: running, idle, refreshing, blocked, paused, error, done; optional --done/--total, --tokens-in/--tokens-out, --usd, --model, --run,
  --since). The Mission tab shows one card per agent with a status chip, task, progress bar and token/cost totals; a batch run (`--run batch-*`)
  counts the job files it made; a running agent silent for 20 min shows stale. Gauges show provider usage and spend from the ledger, free vs paid,
  against the $3 ceiling and Autopilot's max_cost. Targets get bars. "Alerts + sound" is opt-in (browser notification + short tone).
- **Prospect loop (fb85a2b).** A successful YouTube read with nobody in it kept the run on the board and Autopilot re-ran it every tick; now any
  read waits 6 hours.
- **10-video batch** runs as `daily --extra 10 --no-publish` with `TMPDIR=~/.cache/qm-tmp`: `/tmp` is a 3.9 GB RAM disk and preflight refuses
  below 1.5 GB free. Hermes runs the held-review mission directly (herdr is not running, so the board cannot dispatch to agents).
- **Per-model gauges (2ce82bf).** `ledger.spend` keeps `model`, `tokens_in`, `tokens_out` when given; the OpenRouter call passes them. The Models
  table fills from the next call made by a freshly started process.
- **Actions beat (3c1838f).** Every board action that moves the pipeline writes a running beat and a done/error beat under `engine-<lane>`.
- **Autopilot (6338aa0).** A mission whose dispatch failed (herdr down) is blocked for the day instead of retried every 45 s. Tests write beats to a
  scratch file (conftest).
- **TMPDIR.** `~/.config/quiet-money/env` sets `TMPDIR=~/.cache/qm-tmp`, so the timer, the board server and typed commands render on the main disk.
- **X desk.** `python -m faceless x` writes `outbound/x/<day>/<job>.md` for each finished video of the last 3 days (video to attach, numbered lead
  post under 280 characters with the AI line, thread replies, tracked hub link). `x log <job> posted --url` retires it. Board: engine mission
  `x-draft-<day>`, owner mission `post-x-<day>`, an "X posts" card. It never posts.
