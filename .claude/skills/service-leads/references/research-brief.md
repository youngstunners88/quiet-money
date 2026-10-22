# The research brief (free models) and how to run it at volume

## The brief
Send one project per call. Paste the fetched page text into the brief rather than asking the model to browse: free
models have no tools, and a model asked to recall a project will invent it.

```
You are a research assistant. Below is text fetched from public pages about one Web3 project.
Return ONLY a JSON object, no prose, with exactly these keys:

{"what_it_is": "...", "category": "defi|gaming|infra|l1-l2|nft|exchange|wallet|other",
 "chains": ["..."], "stage": "pre-launch|launched|established",
 "size_signal": {"value": "...", "source": "URL"},
 "posts_video": true|false, "cadence": "...", "last_posts": ["...", "..."],
 "content_gap": "one sentence on what their short-form is missing",
 "dated_event": {"what": "...", "when": "YYYY-MM-DD or null", "source": "URL"},
 "budget_signal": {"what": "raise|grants|paid-KOLs|none", "source": "URL"},
 "contact": {"route": "...", "value": "...", "source": "URL"},
 "unknown": ["names of the keys above you could not fill from the text"]}

Rules: every fact must come from the text below. If the text does not say it, put null and name the key in
"unknown". Never guess an email address. Never state a number the text does not state.

SOURCES: <url list>
TEXT:
<fetched text, trimmed to the parts about the project>
```

The `unknown` list is the quality signal: a card with `content_gap` or `contact` unknown is a skip, not a thin card
to pitch anyway.

## Volume pattern
- One call per project, several projects in flight. `panel.ask` is a plain HTTP call, so run a handful of candidates
  per message rather than one at a time.
- Trim the fetched text hard. Free models have small effective context and a 2,000-token answer limit
  (`[panel].max_tokens`); send the about page, the last ten posts and the news item, not whole sites.
- Rotate the models named for the `research` job across a batch. If one slug starts erroring or rate-limiting, move
  the batch to the next one and note it in the report.

## When a model misbehaves
| Symptom | Fix |
|---|---|
| `{"error": "not a JSON object"}` or `unreadable` | Re-send once with "Return ONLY JSON" first in the brief. Then switch model. |
| `{"error": "http 429"}` | The free pool is spent for now. Switch to the next slug for this job; if all are spent, the session does the remaining cards itself and the report says so. |
| `{"error": "http 404"}` | The slug is wrong or retired. Re-resolve it (`service-scoring`) and update `models.json`. |
| Confident facts not in the text | Drop that card's unsourced fields and note the model; two batches of this and the slug comes out of `models.json`. |
| Prose with JSON inside | `panel.ask` already extracts an embedded object; if it fails twice, switch model. |

## Honest limits
`ProviderUnavailable` is raised when `OPENROUTER_API_KEY` is unset or the `[panel]` daily cap is reached. Free models
record $0, so they do not consume that cap - but a paid slug would. Keep `models.json` to `:free` slugs for this desk;
if a job genuinely needs a paid model, that is an owner decision written into the owner queue, not a cap raise.
