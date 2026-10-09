# Repository audit, 2026-10-09

Scope: the whole repository (engine, site generator, workflows, skills, tests). Method: static analysis (ruff bug classes, bandit, pip-audit), a script that
checks every network and subprocess call, a timing run of every module-level regular expression against pathological input, a fuzz run of the model-scene
gate, line-by-line review of everything that turns outside text into markup, a file path, a command or a fetch, and real renders after each change.
"Bug-free" is not a claim anyone can make; this lists what was checked, what was found, what was fixed, and what is left.

## Found and fixed (each has a regression test in `tests/test_audit.py` unless noted)

| # | Finding | Why it mattered | Fix |
|---|---|---|---|
| 1 | No state file was written atomically (`write_text` truncates first) | a routine stopped mid-write left a half JSON job file, and `all_jobs()` then crashed every command that lists jobs: daily run, site build, status, preflight | `fsutil.write_atomic` (temp file + rename) for jobs and every per-video artifact; `scan_jobs()` skips and reports an unreadable file; preflight check `state:jobs`; the site skips one unreadable script instead of failing the build |
| 2 | JSONL readers (spend ledger, journal, sales, offers, metrics, portfolio) crashed on a line that was valid JSON but not an object, or on a cut multi-byte character | a single damaged ledger line stopped every provider call, since each call checks the ledger first | one tolerant `fsutil.read_jsonl` used by all of them; ledger arithmetic tolerates a bad row |
| 3 | 13 ffmpeg/ffprobe/git calls had no timeout; the streaming encoder could block forever on a stalled pipe | a hung encoder would stall a routine until its session limit | timeouts everywhere; a kill timer on the streaming encoder; the CI mirror turns a hung step into a red one; a source test fails if a new call lacks a timeout |
| 4 | Vendor result URLs were fetched with no size limit, and some accepted plain http | a wrong or hostile address could fill memory or disk; plain http can be tampered with | `providers.fetch_bytes`: https only, streamed, cut off at a limit; used by Muapi, OpenRouter image, hook clip and the policy fetch |
| 5 | A request id or label from an API went into a file name | `../` in a name could steer where a file is written | names reduced to letters, digits, dash and underscore |
| 6 | The HyperFrames renderer ran third-party npm code with every key in its environment, and loaded GSAP from a CDN with no check (the compiler inlines it, so an `integrity` attribute is never evaluated) | a poisoned npm dependency or CDN file could read the keys or change the render | the renderer gets an environment with no key, token or secret; GSAP is fetched once, its sha384 checked in our code, and the verified copy is what the renderer loads (real render confirmed) |
| 7 | `redact()` only removed this process's own environment values and `?key=` queries | a vendor error echoing a rotated or foreign key would reach the public journal | also removes anything shaped like a known key (OpenAI/OpenRouter, Google, GitHub, Slack, AWS, JWT, Bearer/Apikey headers, private key blocks) |
| 8 | Owner-configured profile links could be `javascript:` URLs; `llms.txt` took titles with line breaks and brackets verbatim | a mistyped config value would become a clickable script; a title could start a fake heading in the file answer engines read | `site.safe_url` (http(s) only), `site.plain` |
| 9 | UTM tags were appended after a `#fragment`, where the browser drops them | a tagged product link would lose its attribution | tags go before the fragment |
| 10 | `new_job` overwrote an existing job with the same id | a retry of the same topic in the same slot erased the cost record and the reason the first attempt stopped | the run still starts from `planned`, but cost and notes are carried over |
| 11 | `date.today()` follows the machine's zone; everything else is UTC | on a laptop outside UTC, `offer --batch`, the policy watch and the kit would look for the wrong day for hours | `config.today_utc()`; a source test bans the naive forms |
| 12 | Two workflows had no `timeout-minutes` | a hung job runs for six hours | added; a hygiene test requires it on every job and forbids pasting event text into a `run:` script |
| 13 | Scene-gate regexes anchored with `$` accept a trailing newline; three display regexes are quadratic on a 30,000-character run of spaces | sloppy, not exploitable (output is escaped, inputs are a few words) | strict `\Z` anchors; length caps on the card parsers |
| 14 | Dead variables, unused imports, a mutable default in a test helper, SHA-1 used for non-security seeds | noise that hides real findings | removed; `usedforsecurity=False` |

## Checked and found sound
- HTML: every model- or script-sourced string reaches a page through `html.escape`; JSON-LD escapes `<`, `>`, `&`; the hub page's one script whitelists the query value to `[a-z0-9._-]` and uses no `innerHTML`. A test builds the whole site from a script made of attack strings and parses every page.
- Model scenes: the validator whitelists every type, field, colour, ease, path command and label; a 2,000-case fuzz found no scene that passed with markup in it.
- ASS captions: backslashes and braces are removed, so no override tag can be injected. ffmpeg arguments are lists, never a shell string; no `shell=True`, `eval`, `exec` or pickle anywhere (bandit: 0 high, 0 medium).
- Intake: https only, host allowlist, redirects refused, 1.5 MB cap. Skill-intake and policy text is treated as data.
- Workflows: every file declares `permissions`; the push/pull-request workflows see no secret; inputs enter shell steps through `env:` only; the only write-token workflows are the batch, the website and the weekly probe, and none runs on a pull request.
- Dependencies: `pip-audit` on `requirements.txt`: no known vulnerabilities. Every requirement has an upper bound.
- Committed files: no key-shaped string, no personal e-mail address (hygiene test, run on every push).

## Left, and why
- **GitHub Actions are pinned to major tags** (`actions/checkout@v4`), not commit hashes. They are GitHub's own actions; pinning to hashes needs the current hashes read from those repositories, which this session was not scoped to. Adding Dependabot for `github-actions` after hash-pinning is the standard next step.
- **`npx hyperframes@0.8.136`** pins the CLI but not its dependency tree. It now runs with no secrets in its environment, which removes the worst case; vendoring a lockfile would remove the rest.
- **Prompt injection through web pages** the scouts read cannot be ruled out by code. Mitigations in place: the skills say to treat fetched text as data, nothing a page says can reach a shell, and everything public passes the claim and compliance gates. Review the weekly scout report before approving any change it proposes.
- **Third-party skills** (`agent-browser`, `composio`) are instructions the routines obey. Their digests are pinned in `tests/test_audit.py`, so an upstream change is a deliberate commit, not a silent update.
- **Absolute paths** (`/home/user/...`) appear in committed job files. Not secret; harmless on a public repo.
- **The model's judgement** (script quality, factual accuracy) is the gauntlet's job, not this audit's; it is a statistical gate, not a proof.
