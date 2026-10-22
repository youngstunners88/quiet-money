# Quiet Money HQ: the page source

`quiet-money-hq.html` is the source of the owner's dashboard, published as a claude.ai artifact:
https://claude.ai/artifact/5FMWQAuSQpXdq8CwEG7HY3 (private to the owner).

It is kept here so the page can be changed in a reviewed commit and republished, rather than living only in one session.
The numbers on it are not in this file: they live in the artifact's own store and come from `python -m faceless hq`
(see `.claude/skills/faceless-hq`). The page declares four capabilities: `db` (goals, horizon, build queue, the snapshot),
`user`, `sample` (the Ask HQ desk) and `mcp` with the Claude Code Remote connector's `create_session` and
`list_environments` (starting a build session from the build queue).

To change it: edit this file, then publish it to the same artifact URL with the Artifact tool (pass `url`), keeping the
capabilities as they are.
