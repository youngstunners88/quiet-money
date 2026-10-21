# CEO decisions, 2026-10-20

The owner's message of 2026-10-20 settled three open questions and handed one to the agent.

## 1. No ad spend until further notice (owner)
The $10 is withheld. Every paid traffic test (Pinterest promoted pins, Meta boosts, YouTube Promote, Reddit,
TikTok Promote, paid creator posts) is parked; `channel/offers/launch/BUDGET-10.md` keeps the research for the
day a budget is named. The first sprint (`brain/PROMPTS/ORCHESTRATOR.md` section 8) is built for $0: page,
lead magnets, emails, product suite, content calendar. Provider spend inside the existing caps (`[safety]`
$3 a day) is unchanged; it makes the videos, it does not buy traffic.

## 2. Quinton is AI-generated (owner)
The owner made Quinton in Google Flow. He is not a photo of a real person, so rule 3 does not apply to him,
and the listing line "a virtual AI-generated character, not a real person" is true. Updated:
`channel/host/BIBLE.md`, `.claude/skills/faceless-host/SKILL.md`, `channel/empire/WEEK-2026-10-20.md`.
His uploads keep the synthetic-media label (rule 4).

## 3. Git history: no rewrite (the agent's call, as the owner asked)
The question: the paid planner PDFs, printables and spreadsheets sit in this public repository's past commits.
**Decision: do not rewrite history.** Reasons:
- A rewrite would not remove them from GitHub. Every pull request (#1 to #31) keeps its commits reachable
  through `refs/pull/N/head`, which we cannot delete. GitHub's own guide for removing data says the last step
  is asking GitHub Support to purge cached views and pull-request references.
- It would force-push `main` and about 25 branches, and break the nine scheduled tasks that
  push to `main` (eight of them start with `git pull --rebase origin main`).
- The exposure is small: 0 stars, 0 forks, and the files are not linked from the site or the shop.
- Making the repository private would close it fully, but GitHub Pages (the Money Rules Library site) on a
  private repository needs a paid plan. That is a spend, so it is parked with the ad budget.

What does close the gap now: **merging PR #31**, which takes the paid files out of `main`'s current tree. Until
it is merged, anyone browsing `main` can download them. Going forward `.gitignore` keeps them out, and the shop
workflow builds them in CI instead of reading them from git.
Revisit if a copy of the planner appears anywhere for free (the monthly scout can search for the title).

## 4. Levanto Sage (SageCut): parked
The owner's "Video saving costs" doc proposes Sage, a paid decision API, for cheap frame QA. Our frame
checks already run through `faceless/decide.py` and `faceless-bench`; Sage would need its key in the
environment as `SAGE_API_KEY` (it is not set) and a measurement under `faceless-bench` before it judges
anything. The doc holds a live key in plain text. The agent did not copy it anywhere. The owner should move it
to the environment's secrets and delete it from the doc.

## 5. The CEO runs lanes through the claude-code-orchestrator MCP
Built from the owner's spec (the "Claude Code MCP" doc) in `claude-code-orchestrator/`, read-only by default,
write access only with a raised ceiling and an explicit confirmation per worker. The operating manual is
`brain/PROMPTS/ORCHESTRATOR.md`.
