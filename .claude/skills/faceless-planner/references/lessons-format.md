# Lesson files

`channel/products/daily-quiet-money-planner/content/q1.txt` to `q4.txt`: 13 weeks each. A week starts with `# WEEK n | theme | motif1,motif2,motif3` (motifs from `planner_art.MOTIFS`).

| Line | Day | Fields |
|---|---|---|
| `L` | Monday, Learn | `L | title | lesson | task` |
| `N` | Tuesday, By the numbers | same; the lesson holds the computed figures |
| `D` | Wednesday, Do it | same |
| `M` | Thursday, Mindset | same |
| `A` | Friday, Action | same |
| `S` | Saturday weekly check-in | `S | prompt` |
| `R` | Sunday reflect and reset | `R | prompt` |
| `X` | bonus Day 365 (week 52 only) | like `L` |

Placeholders `{name:args}` (numbers and `+ - * / ( )` only): `usd x div pct num fv put lump gap fvgap r72 infl cmin_y cmin_i cpay_m cpay_i pmt pmti cap mtt`. Each calls `faceless/moneymath.py` or a thin wrapper in `planner_content.FUNCS`.

Style: short sentences, second person, concrete, 8th-grade reading level, no guru words. A title is one line; a lesson is 9 lines or fewer; a task 4 or fewer (`planner check` enforces both).
