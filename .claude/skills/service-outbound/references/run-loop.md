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

## 1-2. Discover and research -> `service-leads`
Target: the step's candidate count from the SKILL table. Each candidate becomes `W/leads/<slug>.json` on the
`W/schema/lead-card.json` shape. A card with no sourced content-gap signal and no public business contact is written
with `status: "skip"` and its `skip_reason`, so the next run does not re-research it.

## 3. Score -> `service-scoring`
One `decide.ask` call per lead carrying all the questions for that lead. Fill the card's `decisions` block.
Leads scoring below the pursue threshold get `status: "skip"` with the score left in place.

## 4. Draft -> `service-outreach`
Only for `pursue` leads. One `W/outbound/<slug>.json` per lead, on the `W/schema/outreach-package.json` shape.

## 5. Gate -> `service-scoring`
The gate questions run on the drafted text. `verdict: "pass"` goes to the backlog; `"rewrite"` goes back to step 4
once; `"hold"` is reported to the owner with the reason and never queued.

## 6. Batch report (paste this in the reply, nothing else goes to the owner)
```
Outbound batch <date>
Screened <n> - cards <n> - scored <n> - pursue <n> - queued <n> - held <n>
Queued, strongest first:
  1. <Project> (<category>, <chain>) - fit <x>, <angle> - <channel> - <contact route>
  ...
Held: <Project> - <gate that failed and why>
Skipped (and why): <n> no public business route, <n> below fit, <n> no content gap
Owner action: review W/outbound/*.json, send the ones you like, tell me what came back.
Models used: <job: model slug> ... | Jev calls <n>, spend $<x> | Free-model spend $0
```

## 7. Outcomes -> `service-pipeline`
After the owner reports back, append one line per event to `W/outcomes.jsonl` and run the weekly review.

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
The loop is a prompt, so it schedules like any other: ask the owner to add a scheduled task that says
"run the service-outbound loop and report the batch". Keep it off the hour the daily video run uses. A run that dies
halfway is safe to repeat: lead cards and packages are written per slug and overwritten, and nothing has been sent.
