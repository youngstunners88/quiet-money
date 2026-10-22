# Running the loop, step by step

Everything below runs from the repo root. `W = channel/services/web3-video`.

## 0. Before anything
```bash
python -m faceless keys            # is OPENROUTER_API_KEY live? (free models and Jev both need it)
cat state/PAUSE 2>/dev/null        # a pause stops this desk too: stop and report
python -m faceless status          # the daily machine's state; this desk must not disturb it
```
If `OPENROUTER_API_KEY` is missing, the loop still runs: the session itself does the research and drafting
(the `fallback: "agent"` in `W/models.json`) at lower volume. Say so in the report.

## 1-5. The loop itself
```bash
python -m faceless outbound run                              # the whole thing, with the caps from studio.toml [outbound]
python -m faceless outbound run --candidates 60 --packages 12   # a bigger screen when the backlog is empty
```
What it does, and which skill covers the judgement in each step:

| Step | What the engine does | Skill |
|---|---|---|
| 1 Discover | DeFiLlama's public protocol list (no key), filtered to the size band, needing a public X handle and a site; freshly listed first | `service-leads` |
| 2 Research | fetches the project's own site, docs and public X page, and a free model turns them into a sourced lead card | `service-leads` |
| 3 Score | Jev answers fit, budget, gap, timing, pursue; thresholds in code; a thin or unconfident answer falls back to the heuristics | `service-scoring` |
| 4 Draft | a free model writes the first touch and a three-step sequence from the card and `PROOF.md` | `service-outreach` |
| 5 Gate | banned language and price in code, then Jev on personalization and spam; one rewrite, then a hold | `service-scoring` |

Leads that cannot be pitched are written as skips with a reason, so the next run does not look at them again:
`pages_unreadable`, `no_content_gap`, `no_public_contact`, `below_fit`.

The engine makes no judgement calls a person would disagree with silently: it never invents a fact (an unsupported
field stays null and the card becomes a skip), never pads a batch, and never sends.

## 6. Batch report
`outbound run` writes it to `W/reviews/batch-<day>.md` and prints it: counts, the queue strongest first with each
one's angle, channel and contact route, what was held and why, what was skipped and why, and the owner's one action.
Relay that report to the owner as it is - do not paste draft bodies into the reply; they are in the package files and
`python -m faceless outbound package <slug>` prints one.

When a run was heuristic-only (no key, or Jev below the confidence floor), say so in the relay: the scores came from
code, not from a model.

## 7. Outcomes
```bash
python -m faceless outbound outcome <slug> sent
python -m faceless outbound outcome <slug> reply-positive "asked for examples"
python -m faceless outbound review
```
Events: `sent`, `no-reply-14d`, `reply-positive`, `reply-negative`, `reply-question`, `call-booked`, `quoted`,
`closed`, `lost`, `unsubscribe`, `complaint`. Record them as the owner reports them - the loop learns from nothing
else. The weekly read is `service-pipeline`.

## When a step comes back thin
| Symptom | Do this |
|---|---|
| Few candidates found | Widen the source list in `SOURCES.md` order, not the quality bar. Try a different category (gaming, infra) before a second pass at one. |
| Research cards missing signals | The page was JS-only or empty. Try Exa's cached text, then the project's docs site, then skip with a reason. Do not fill from memory. |
| Everything scores low | That is information, not a failure: report which signal is missing across the batch (usually budget). Do not lower the threshold on your own. |
| Drafts keep failing the personalization gate | The lead cards are thin, not the drafts. Go back to step 2 with fewer leads. |
| A model slug 404s | Re-resolve it (`service-scoring`, "Resolve the slugs") and write the new slug into `W/models.json`. |
| Jev cap reached | Stop scoring, queue what passed, report. Never raise `decisions_daily_usd`. |

## Scheduling it
It runs **daily** as a scheduled routine on the owner's account (set 2026-10-22): one session a day runs
`python -m faceless outbound run`, relays the batch report, and ends. `.github/workflows/outbound.yml` is an
optional manual runner for the same thing (it needs `OPENROUTER_API_KEY` as an Actions secret; the normal path uses
the keys already in the Claude Code environment).

A run that died halfway is safe to repeat: lead cards and packages are written per slug, the hashed index in
`state/outbound-seen.json` means nothing is researched twice, and nothing has been sent.

**The memory that survives a container** is `state/outbound-seen.json` (hashed project index) and
`state/outbound-outcomes.jsonl` (hashed outcome log). Both are committed and hold no company names. The lead cards,
packages and reports are gitignored, so a queued draft reaches the owner through the session's report or the
workflow artifact - not through the repo.
