import json, sys, time, datetime
sys.path.insert(0, "/home/user/quiet-money")
from faceless.providers import composio_tools as ct
VID = "23eTM0G1z2s"; CH = "UC9B1QBr3_8Eulok8IdQbCqQ"
m = json.load(open("/home/user/quiet-money/distribution/queue/2026-10-07/slot2-psychology/meta.json"))
def stamp(): return datetime.datetime.now().strftime("%H:%M:%S")
def listed():
    r = ct.execute("YOUTUBE_LIST_CHANNEL_VIDEOS", {"channel_id": CH})
    for it in r["data"]["items"]:
        s = it["snippet"]
        if s.get("resourceId", {}).get("videoId") == VID:
            return s.get("title"), s.get("description", "")[:40]
    return None, None
ok_streak = 0
for i in range(1, 16):
    try:
        ct.execute("YOUTUBE_GET_VIDEO_DETAILS_BATCH", {"video_ids": [VID]})
        title, desc = listed()
        alive = bool(title) and title != "Deleted video"
        print(stamp(), f"check {i}: readable, listing title={title!r}", flush=True)
        ok_streak = ok_streak + 1 if alive else 0
    except Exception as e:
        print(stamp(), f"check {i}: NOT readable ({str(e)[:100]})", flush=True)
        ok_streak = 0
    if ok_streak >= 3:
        break
    time.sleep(120)
if ok_streak < 3:
    print(stamp(), "VERDICT: video did not stay up", flush=True); raise SystemExit(1)
try:
    ct.execute("YOUTUBE_POST_COMMENT", {"videoId": VID, "channelId": CH, "textOriginal": m["first_comment"]})
    print(stamp(), "VERDICT: video is up; first comment posted", flush=True)
except Exception as e:
    print(stamp(), "VERDICT: video is up; comment failed:", str(e)[:200], flush=True); raise SystemExit(2)
