import sys, time, datetime
sys.path.insert(0, "/home/user/quiet-money")
from faceless.providers import composio_tools as ct
def stamp(): return datetime.datetime.now().strftime("%H:%M:%S")
for wait in (360, 600):
    time.sleep(wait)
    r = ct.execute("YOUTUBE_LIST_CHANNEL_VIDEOS", {"channel_id": "UC9B1QBr3_8Eulok8IdQbCqQ"})
    print(stamp(), [(it["snippet"]["resourceId"]["videoId"], it["snippet"]["title"]) for it in r["data"]["items"]], flush=True)
