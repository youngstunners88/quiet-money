# Page map (415 pages per PDF)

1 cover | 2 welcome | 3 net worth snapshot | 4 debt map | 5 year at a glance | then 365 day pages, each week ending Sunday with its Wellness Break page for weeks 1 to 40 (40 pages) | summary and goals | money words | notes x2 | about this planner.

`FRONT = 5`, `BACK = 5` in `product_planner.py`; the wellness pages are `len(planner_wellness.kept())` (40 posters: the owner's 44 minus 4 duplicates). `planner check` wants `FRONT + 365 + 40 + BACK`.

Weeks 41 to 52 have no wellness page until twelve more posters exist. Make them with the Muapi desk (skill `muapi`): generate the scene, typeset the words in code (an AI edit regenerates every pixel and changes words and numbers).
