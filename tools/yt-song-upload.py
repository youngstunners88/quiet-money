#!/usr/bin/env python3
"""Upload one full-length song video (not a Short) through the YouTube app on the owner's phone.
usage: yt-song-upload.py VIDEO.mp4 TITLE_FILE DESC_FILE   (title and description as plain ASCII text files)
Starts the app's upload screen by sharing the file to YouTube (the Create button's gallery path makes a cropped Short instead)."""
import re,subprocess,sys,time,html,difflib,os
SC=os.environ.get("YT_SCRATCH","/tmp")
src=open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"yt-phone-upload.py"),encoding="utf-8").read()
exec(src.split("# --- package text")[0].replace("day,slot=sys.argv[1],sys.argv[2]",'day=slot=""'))   # adb/tree/find/tap/step/rawtype/sync helpers
video,tfile,dfile=sys.argv[1:4]
title=open(tfile,encoding="utf-8").read().strip(); desc=open(dfile,encoding="utf-8").read().strip()
if any(ord(c)>127 for c in title+desc): die("non-ASCII text")
fn="song_"+os.path.basename(video)
if not os.environ.get("SKIP_PUSH"):                               # YouTube can only read media the owner picked in its gallery ('+' tile) once: push, grant it by hand, then rerun with SKIP_PUSH=1
    subprocess.run(["adb","push",video,f"/sdcard/Download/QuietMoney/{fn}"],capture_output=True)
    adb(f"touch /sdcard/Download/QuietMoney/{fn}"); adb(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Download/QuietMoney/{fn}"); time.sleep(3)
adb("am force-stop com.google.android.youtube"); adb("am kill-all"); time.sleep(2)
adb(f"am start -a android.intent.action.SEND -t video/mp4 --eu android.intent.extra.STREAM file:///sdcard/Download/QuietMoney/{fn} -n com.google.android.youtube/com.google.android.apps.youtube.app.application.Shell_UploadActivity"); time.sleep(10)
adb("input tap 951 2254"); time.sleep(5)                       # Next (the preview hides the UI tree)
if not find(lambda t:t.startswith("Create a title"),15): die("details page did not open")
adb("input tap 540 1169"); time.sleep(1.5); rawtype(title); time.sleep(1.5)
if title not in [t for t,_,_ in tree()]: die("title not exact")
adb("input keyevent 4"); time.sleep(1.5)
sm=find(lambda t:t=="Show more",8)
if not sm: die("show more missing")
adb(f"input tap 540 {sm[2]-155}"); time.sleep(3)               # Select audience
adb("input tap 102 925"); time.sleep(1); adb("input keyevent 4"); time.sleep(2.5)   # 'No, it's not made for kids'
sm=find(lambda t:t=="Show more",8)
if not sm: die("show more missing after audience")
tap(sm); time.sleep(2.5)
adb("input swipe 540 1700 540 600 400"); time.sleep(2)
sl=find(lambda t:t=="Show less",5)
if not sl: die("show less missing")
base=sl[2]                                                       # rows above 'Show less': Attributes -152, Add description -(about 840)
ytop=base-152*0
adb("input tap 306 836"); time.sleep(3)                          # Add description (page was scrolled to the same place as the short flow)
if not sync(desc,desc.split("\n")[0][:25]): die("description does not match")
print("description ok")
for _ in range(3):
    if find(lambda t:t in("Upload","Show less"),2): break
    adb("input keyevent 4"); time.sleep(2)
def fix_title():
    for _ in range(3):
        cur=[(t,x,y) for t,x,y in tree() if t.startswith(title[:14])]
        if cur and cur[0][0]==title: return True
        if not cur: return False
        adb(f"input tap 540 {cur[0][2]}"); time.sleep(1.5)
        if cur[0][0]==title+"t": adb("input keyevent 123"); adb("input keyevent 67")
        else: adb("input keycombination 113 29"); time.sleep(0.5); adb("input keyevent 67"); time.sleep(0.8); rawtype(title)
        time.sleep(1.5); adb("input tap 900 785"); time.sleep(1.5)
    return False
fix_title()
sl=find(lambda t:t=="Show less",6)
if not sl: die("show less missing before attributes")
adb(f"input tap 480 {sl[2]-152}"); time.sleep(3)                  # Attributes (AI use, Tags)
ok=False
for attempt in range(3):
    adb("input tap 985 328"); time.sleep(3)
    if find(lambda t:t=="Add tags",1): adb("input keyevent 4"); time.sleep(2); adb(f"input tap 480 {sl[2]-152}"); time.sleep(3); continue
    adb("input tap 102 1026"); time.sleep(1.5); ok=True; break
if not ok: die("could not set AI use")
shot("ai_use"); adb("input keyevent 4"); time.sleep(2); adb("input keyevent 4"); time.sleep(2.5)
up=find(lambda t:t=="Upload",8)
if not up: die("upload button missing")
shot("before_upload"); tap(up); time.sleep(10)
print("UPLOAD STARTED",title)
