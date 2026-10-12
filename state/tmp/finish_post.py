import json, sys, time, datetime
sys.path.insert(0, "/home/user/quiet-money")
from faceless.providers import composio_tools as ct
VID = "igEMZUQo65g"; CH = "UC9B1QBr3_8Eulok8IdQbCqQ"
m = json.load(open("/home/user/quiet-money/distribution/queue/2026-10-07/slot2-psychology/meta.json"))
def stamp(): return datetime.datetime.now().strftime("%H:%M:%S")
for i in range(1, 16):
    try:
        ct.execute("YOUTUBE_GET_VIDEO_DETAILS_BATCH", {"video_ids": [VID]})
        print(stamp(), f"check {i}: video is readable", flush=True)
        break
    except Exception as e:
        print(stamp(), f"check {i}: not readable yet ({str(e)[:120]})", flush=True)
        time.sleep(180)
else:
    print("gave up waiting for processing", flush=True); raise SystemExit(1)
try:
    ct.execute("YOUTUBE_POST_COMMENT", {"videoId": VID, "channelId": CH, "textOriginal": m["first_comment"]})
    print(stamp(), "first comment posted", flush=True)
except Exception as e:
    print(stamp(), "comment failed:", str(e)[:300], flush=True); raise SystemExit(1)
