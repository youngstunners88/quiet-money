# Page map (427 pages per PDF)

1 cover | 2 welcome | 3 net worth snapshot | 4 debt map | 5 year at a glance | then 365 day pages, each week ending Sunday with its Wellness Break page (52 pages) | summary and goals | money words | notes x2 | about this planner.

`FRONT = 5`, `BACK = 5` in `product_planner.py`; the wellness pages are `len(planner_wellness.kept())` (52 posters: the owner's 44 minus 4 duplicates is 40, plus twelve typeset by the studio, positions 45 to 56). `planner check` wants `FRONT + 365 + 52 + BACK`.

Weeks 41 to 52 use posters 45 to 56, made by `python -m faceless planner posters-make` (`faceless/planner_poster_make.py`): the scene and illustrations come from the Muapi desk once (kept in the repo folder assets/planner/wellness/made), the owner's light bulb is reused, and every word is typeset in code (an AI edit regenerates every pixel and changes words). Change a poster's words in `TEXT` there and its money line in `planner_wellness.POSTERS`, then rebuild.
