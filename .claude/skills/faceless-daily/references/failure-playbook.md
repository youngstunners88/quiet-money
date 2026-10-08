# Failure playbook

Each row is a real way a day can go wrong, how you will see it, and the move that is safe. A refusal from the studio's own safety layer
(kill switch, spend ceiling, provider cap) is the system working: report it, do not route around it. Anything that costs money beyond
the configured caps, or that posts publicly, needs the owner's yes.

| You see | Cause | Do |
|---|---|---|
| `preflight` FAIL `kill switch`, or `DAILY_HALTED` in the journal | `state/PAUSE` exists (someone paused the studio on purpose) | Read the reason in the file. Do not resume it yourself. Report the reason and stop the batch. The owner resumes with `python -m faceless pause --resume`. |
| `preflight` FAIL `spend today` | The $3 daily ceiling is reached | `python -m faceless status` shows who spent it. Report. Free providers still work, so a run with only free providers can continue; paid ones refuse by themselves. |
| `preflight` FAIL `keys:llm` | No script-writing key in the environment | Scripts fall back to the anonymous provider (weaker). Report to the owner; run the batch only if the gauntlet still passes what it makes. |
| `daily` or `make` prints `BLOCKED` and exits 4 | The built-in gate found a failure that makes rendering impossible (the same list `preflight` marks FAIL for tools, fonts, config, git state, disk) | Nothing was started and nothing was spent. Do the fix it prints, run `preflight`, then run again. `--skip-preflight` exists for emergencies only. |
| `preflight` FAIL `ffmpeg` or a missing Python module | The container lost its setup | `bash .claude/hooks/session-start.sh`, or `pip install -r requirements.txt` and `apt-get install -y ffmpeg`. Then run preflight again. |
| `preflight` FAIL `last daily batch` (older than 72 h) | The routine stopped running | Run the batch now. Say in the report that days were missed and read the routine's last session for why. |
| `preflight` FAIL `git state` | A merge or rebase was left unfinished | `git status`, then finish it or `git rebase --abort` / `git merge --abort`. Never start a batch on top of it. |
| `preflight` FAIL `secrets in git` | A live key's value is in a tracked file | Remove it from the file, tell the owner at once: the key is in git history and must be rotated. Never print it. |
| `preflight` FAIL `state:*` with conflict markers | A merge left `<<<<<<<` lines in a log | The logs merge by union (`.gitattributes`), so this means someone resolved by hand. Remove the marker lines and keep every JSON line; sort by `t`. Do not choose one side. |
| A still is blank or procedural | Every image provider refused or was out of quota | `python -m faceless doctor`: look at Cloudflare neurons and the Muapi wallet. Note the QA reserve in `studio.toml` keeps 2,500 neurons for checks. The video is still valid; report which provider ran dry. |
| Many stills replaced by cards (`qa_swapped`) | The semantic check saw text, a face or a logo in generated images | Normal in small numbers. If most stills swap, the prompts are drifting: read `images.json` for the flagged reasons and tighten the beat's visual prompt. |
| Voice failed | Edge TTS unreachable | The chain tries ElevenLabs then Gemini if keys exist. Re-run later; the day resumes. |
| `held` video | A hard gate failed | `faceless-gauntlet` skill. Never publish a held video without fixing its hard gates. |
| `failed` video | A step raised | `grep JOB_FAILED state/journal.jsonl | tail -3`, fix the root cause, `python -m faceless daily` refills only the open slots. |
| `git push` rejected | The remote moved (another session pushed) | `git fetch origin main`, then `git rebase origin/main` (or merge). The logs union-merge. Run the tests, then push again. Never force-push `main`. |
| Muapi says "credit exhausted" | The wallet is empty | The desk marks Muapi blocked for the day and the chain moves on. Report `python -m faceless muapi balance`; only the owner tops up. |
| Muapi job "failed" with an upstream message | The data provider behind that model is down | Nothing was charged. Use another model or try tomorrow; see the `muapi` skill, Troubleshooting. |
| Session is about to run out of time | A long batch | The run resumes. Commit `state/`, `script-lab/`, `gauntlet/reports/`, `analytics/` and push what is done; the next run fills the rest. |

## After any incident
Add one line to the report: what broke, what you did, what the owner should do (if anything). If the same thing happened twice, fix the cause in code with a
test (`tests/test_resilience.py` has the pattern: break one thing, check the day still ends well).
