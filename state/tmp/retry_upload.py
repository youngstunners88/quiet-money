import os, sys, json, time, hashlib, urllib.request, datetime
from zoneinfo import ZoneInfo
os.environ.setdefault("COMPOSIO_API_KEY", os.environ.get("COMPOSIO_API", ""))
sys.path.insert(0, "/home/user/quiet-money")
from composio import Composio
from faceless.providers import composio_tools as ct

PT = ZoneInfo("America/Los_Angeles")
VIDEO = "/home/user/quiet-money/distribution/queue/2026-10-07/slot2-psychology/video.mp4"
OUT = "/home/user/quiet-money/state/tmp/upload_result.json"

def log(msg):
    print(datetime.datetime.now(PT).strftime("%H:%M:%S PT"), msg, flush=True)

now = datetime.datetime.now(PT)
reset = (now + datetime.timedelta(days=1)).replace(hour=0, minute=2, second=0, microsecond=0)
log(f"waiting until {reset:%Y-%m-%d %H:%M PT} for the YouTube upload quota to reset")
time.sleep(max(0, (reset - now).total_seconds()))

def stage():
    data = open(VIDEO, "rb").read()
    md5 = hashlib.md5(data).hexdigest()
    r = Composio().client.files.create_presigned_url(toolkit_slug="youtube", tool_slug="YOUTUBE_UPLOAD_VIDEO",
            filename="video.mp4", mimetype="video/mp4", md5=md5)
    req = urllib.request.Request(r.new_presigned_url, data=data, method="PUT", headers={"Content-Type": "video/mp4"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        assert resp.status == 200, resp.status
    log(f"staged video, key={r.key}")
    return r.key

args = json.load(open("/tmp/upload_args.json"))
key = "337066/youtube/YOUTUBE_UPLOAD_VIDEO/request/28434b60752ded4522234ec5f420128c"

for attempt in range(1, 6):
    try:
        args["videoFilePath"] = {"name": "video.mp4", "mimetype": "video/mp4", "s3key": key}
        res = ct.execute("YOUTUBE_UPLOAD_VIDEO", args)
        log(f"attempt {attempt}: upload succeeded")
        json.dump({"ok": True, "attempt": attempt, "result": res}, open(OUT, "w"), default=str, indent=1)
        sys.exit(0)
    except Exception as e:
        msg = str(e)
        log(f"attempt {attempt} failed: {msg[:300]}")
        if "429" in msg and "quota" in msg.lower():
            time.sleep(15 * 60)
        else:
            try:
                key = stage()
            except Exception as se:
                log(f"staging failed: {str(se)[:200]}")
                time.sleep(5 * 60)
json.dump({"ok": False}, open(OUT, "w"), indent=1)
log("gave up after 5 attempts")
sys.exit(1)
