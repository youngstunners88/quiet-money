import json, sys, time, datetime
sys.path.insert(0, "/home/user/quiet-money")
from faceless.providers import composio_tools as ct
m = json.load(open("/home/user/quiet-money/distribution/queue/2026-10-07/slot2-psychology/meta.json"))
for attempt in range(1, 9):
    try:
        res = ct.execute("YOUTUBE_POST_COMMENT", {"videoId": "GwRaBiGtr74", "channelId": "UC9B1QBr3_8Eulok8IdQbCqQ", "textOriginal": m["first_comment"]})
        print(datetime.datetime.now().isoformat(), f"attempt {attempt}: comment posted", flush=True)
        raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as e:
        print(datetime.datetime.now().isoformat(), f"attempt {attempt} failed: {str(e)[:200]}", flush=True)
        time.sleep(180)
raise SystemExit(1)
