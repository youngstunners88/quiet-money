# Engine architecture

```
cli.py ──► orchestrator.py ──► pipeline/{ideate, script, voice, visuals, captions, render, music, package}
                │                         │
                │                         └──► providers/{llm, tts, images, publish}  (abstraction layer)
                ├──► gauntlet.py   (judgement: gates + scores, no side effects)
                ├──► decide.py     (typed decisions: Jev or heuristic, recorded)
                ├──► analytics.py  (metrics → pillar weights → slot allocation)
                └──► state.py / events.py / ledger.py  (state management + audit + spend)
```

## Separation of concerns
| Layer | Owns | Never does |
|---|---|---|
| `orchestrator` | sequencing, retries, routing slots → pillars | vendor calls, quality judgement |
| `pipeline/*` | one stage each: inputs → artifacts in the job folder | choose vendors, decide to publish |
| `providers/*` | vendor I/O behind four capabilities (llm, tts, image, publish) | business logic |
| `gauntlet` | gates and scores | write files other than reports |
| `decide` | answer typed questions (choice / score / yes-no) | generate content |
| `state`, `events`, `ledger` | persistence, audit trail, quotas | anything else |

## Abstraction layer
Each capability has an ordered fallback chain in `studio.toml`. `providers.run_chain()` tries them in order,
skipping unconfigured ones (`ProviderUnavailable`) and falling through on errors (`ProviderError`).
Swapping a vendor is a config change; adding one is a single function plus one dict entry.

## State management
- **Job state machine** (`state.py`): `planned → scripted → voiced → visualized → rendered → gated →
  packaged → published` (or `held` / `failed`). Transitions only move forward and are persisted to
  `state/jobs/<job_id>.json` with history.
- **Event journal** (`events.py`): append-only `state/journal.jsonl`, the studio's shared log (the
  agent-universe pattern). Every transition, provider call, gate result, and decision is one line.
- **Ledger** (`ledger.py`): per-day spend per provider/unit (`state/ledger.jsonl`). Free quotas are
  enforced before calls (`allow`), so a run never overspends: it falls to the next provider instead.
- **Decision records** (`state/decisions.jsonl`): every routing/approval question with the heuristic
  answer, the Jev answer (if any), and which one was acted on. Replayable for tuning.
- **Caches**: images keyed by prompt+seed hash (`production/cache/images`). Re-running a job is cheap.

## Routing
- **Slot routing**: `analytics.pillar_weights()` → `allocate()` → 5 of the 6 pillars for the day (weights decide, the skipped one rotates).
- **Topic routing**: `ideate.next_topic()` (backlog first, LLM top-up, dedupe).
- **Provider routing**: fallback chains + ledger quotas.
- **Decision routing**: `decide.ask()`: "LLM creates the work, Jev decides what happens next, code executes."

## Jev (TypeSafe System One) integration
Set `TYPESAFE_API_KEY`, `pip install typesafe-sdk`. `studio.toml [decide]` starts in `dry_run = true`:
Jev's answers are logged next to the heuristic ones in `decisions.jsonl` but not acted on. After a day of
records, compare, then set `dry_run = false`. Answers below `confidence_floor` or outside the option set
fall back to the heuristic (keel's "host validates every choice" rule).
