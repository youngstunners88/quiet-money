---
name: faceless-context
description: Keep Quiet Money's Markdown map true, the coach's structure of one identity file (CLAUDE.md), one short CONTEXT.md per workspace, and skills wired in through a routing table. Run the check, then update the file that drifted, after a build, a decision or a lesson learned. Use when a session changes how the studio works, when a new skill, command or workspace is added, when Claude read the wrong file or missed a rule, or at the end of a weekly review.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/contextlint.py
---

# Keep the map true

The structure (from the owner's coach, lessons 1.2, 1.3, 3.1, 3.2): **CLAUDE.md** names the project and routes every task; each workspace has a **CONTEXT.md** under a page; **skills** plug in through the routing table's Skill column. The layers do not change, the labels do. The files are working notes, edited whenever Claude gets something wrong.

## Steps
1. Run `python -m faceless context`. FAIL means a file, skill or command the map names does not exist: fix the map now. WARN means drift: a skill nobody routes to, a workspace with no CONTEXT.md, a CONTEXT.md over 70 lines.
2. Put each fact in the one place that owns it:
   - what a workspace is and how its work flows: that workspace's `CONTEXT.md` (detail beyond a page goes in a file it links to);
   - which task goes where, which skill, which command: a row in the `CLAUDE.md` routing table;
   - a rule that must never be broken: `CLAUDE.md` Rules, with a number;
   - how to do a repeatable job: a skill, not a CONTEXT.md.
3. After a session that built or decided something, add the row, rule or line **in the same commit**. A new command or skill without its routing row is unfinished.
4. Prompts carry the per-task part (task, constraints, output); the files carry the persistent part (identity, context, rules). Do not paste into a prompt what a CONTEXT.md already says.
5. Do not automate or build what the next model gives for free. Spend effort on what only exists in this studio: its numbers, decisions and data.

## Ask first
Moving a workspace, splitting or merging CLAUDE.md, renaming a folder, or rewriting a CONTEXT.md wholesale. Small edits (a row, a line, a fixed path) need no question.

## Troubleshooting
- **FAIL for a path in a routing cell:** the name may be shorthand; the check accepts a bare file name found anywhere in the repo. If it still fails, the file moved or was deleted: fix the row.
- **CONTEXT.md too long:** move the tables to a sibling file and link it.
