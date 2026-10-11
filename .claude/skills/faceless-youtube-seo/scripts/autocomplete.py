"""Print what YouTube's own search box suggests for each seed phrase (free, no key). Use the output to choose titles, series names and keywords.

    python .claude/skills/faceless-youtube-seo/scripts/autocomplete.py "personal finance" "compound interest"
"""

import sys
import time

import requests

for seed in sys.argv[1:] or ["personal finance", "money psychology", "how to save money"]:
    r = requests.get("https://suggestqueries.google.com/complete/search", params={"client": "firefox", "ds": "yt", "q": seed}, timeout=15)
    print(f"{seed}: {r.json()[1][:8]}")
    time.sleep(0.3)
