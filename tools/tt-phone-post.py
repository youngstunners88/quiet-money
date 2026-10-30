#!/usr/bin/env python3
"""Post one video to TikTok through the app on the owner's phone (adb + UI tree). usage: tt-phone-post.py VIDEO.mp4 CAPTION.txt [--page-only]
Flow: Create -> gallery -> '+' (grant the new file) -> pick the newest tile -> Next -> Next -> caption -> More options -> AI-generated content on -> Post."""
import re,subprocess,sys,time,html,difflib,os
SC=os.environ.get("TT_SCRATCH","/tmp")
def adb(c): return subprocess.run(["adb","shell",c],capture_output=True,text=True).stdout
def tree():
    x=subprocess.run("adb exec-out uiautomator dump /dev/tty",shell=True,capture_output=True,text=True).stdout
    out=[]
    for m in re.finditer(r'<node[^>]*?text="([^"]*)"[^>]*?content-desc="([^"]*)"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',x):
        t=html.unescape(m.group(1) or m.group(2)).replace("\n"," ")
        if t: out.append((t,(int(m.group(3))+int(m.group(5)))//2,(int(m.group(4))+int(m.group(6)))//2))
    return out
def find(pred,wait=0):
    end=time.time()+wait
    while True:
        for t,x,y in tree():
            if pred(t): return t,x,y
        if time.time()>=end: return None
        time.sleep(1.5)
def tap(p): adb(f"input tap {p[1]} {p[2]}")
def shot(n): subprocess.run(f"adb exec-out screencap -p > {SC}/tt_{n}.png",shell=True)
def die(msg): shot("fail"); print("FAIL:",msg); sys.exit(1)
def step(label,pred,wait=8):
    p=find(pred,wait)
    if not p: die(label)
    tap(p); time.sleep(2.5); return p
def ascii_safe(x): return x.replace("—",", ").replace("–","-").replace("’","'").replace("‘","'").replace("“",'"').replace("”",'"')
def rawtype(s):
    for pi,part in enumerate(s.split("'")):
        if pi: adb("input keyevent 75")
        for i in range(0,len(part),10):
            adb("input text '"+part[i:i+10].replace(" ","%s")+"'"); time.sleep(0.45)
def newlines_type(s):
    for li,line in enumerate(s.split("\n")):
        if li: adb("input keyevent 66"); time.sleep(0.2)
        rawtype(line)
def caption_text():
    c=[t for t,_,_ in tree() if t.startswith(want[:25])]
    return max(c,key=len) if c else None
def sync(rounds=5):
    wn=want.replace("\n"," ")
    for attempt in range(rounds):
        adb("input keycombination 113 29"); time.sleep(0.5); adb("input keyevent 67"); time.sleep(0.8)
        newlines_type(want); time.sleep(2)
        got=caption_text()
        if got and re.sub(r"\s+"," ",got).strip().lower()==re.sub(r"\s+"," ",wn).strip().lower(): return True   # the keyboard capitalizes a word after some hashtags or periods: cosmetic
        print("caption differs:",repr(got)[:200])
    return False
video,capfile=sys.argv[1],sys.argv[2]
page_only="--page-only" in sys.argv
dur=(sys.argv[sys.argv.index("--dur")+1] if "--dur" in sys.argv else "")   # mm:ss of the video, to pick the right tile
want=ascii_safe(open(capfile,encoding="utf-8").read().strip())
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),".."))
from faceless import ttpolicy                                      # skill faceless-tiktok-policy: refuse wording that can trip TikTok's rules
bad=ttpolicy.blockers(want)
if bad and "--allow-wording" not in sys.argv: die("risky wording, reword first:\n"+"\n".join(map(str,bad)))
PROMO=ttpolicy.needs_commercial_disclosure(want)
tags=re.findall(r"#\w+",want)
if len(tags)>5:
    for t in tags[5:]: want=want.replace(" "+t,"",1)
if any(ord(c)>127 for c in want): die("non-ASCII in caption")
if not page_only:
    fn=os.path.basename(video)
    subprocess.run(["adb","push",video,f"/sdcard/Download/QuietMoney/{fn}"],capture_output=True)
    adb(f"touch /sdcard/Download/QuietMoney/{fn}; am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Download/QuietMoney/{fn}")
    adb("am force-stop com.ss.android.ugc.trill"); time.sleep(1); adb("monkey -p com.ss.android.ugc.trill 1"); time.sleep(6)
    for _ in range(3):
        d=find(lambda t:t in("Don\u2019t allow","Not now","Dismiss"),2)    # permission and promo pop-ups: decline
        if d: tap(d); time.sleep(1.5)
    time.sleep(4)
    for attempt in range(4):                                           # the feed, camera and gallery load slowly when the phone is short of memory
        if not find(lambda t:t=="Recents",1):
            if not find(lambda t:t=="Add sound",1): adb("input tap 540 2272"); time.sleep(5)
            adb("input tap 113 2172"); time.sleep(4)                   # gallery thumbnail (bottom left of the camera)
            if not find(lambda t:t=="Recents",2): adb("input tap 113 2255"); time.sleep(4)   # same thumbnail when the camera permission screen shifts the layout
        if find(lambda t:t=="Recents",6): break
        adb("input keyevent 4"); time.sleep(2)
    if not find(lambda t:t=="Recents",3): die("gallery did not open")
    adb("input tap 185 808"); time.sleep(3)                            # '+' tile: pick more media for TikTok
    p=find(lambda t:t.startswith("Video taken on") and (not dur or t.endswith("duration "+dur)),8)
    if not p: die("system picker has no videos")
    tap(p); time.sleep(1.5)
    step("Done",lambda t:t=="Done",5); time.sleep(3)
    def avg(cmd):
        r=subprocess.run(cmd,shell=True,capture_output=True); return list(r.stdout[:3]) if len(r.stdout)>=3 else None
    want_rgb=avg(f'ffmpeg -v error -ss 0.3 -i "{video}" -frames:v 1 -vf scale=1:1 -f rawvideo -pix_fmt rgb24 -')
    def tray_matches():
        """the selected-video tray shows the first frame: its average colour must match the file we mean to post (a same-length older video is the usual mix-up)"""
        subprocess.run(f"adb exec-out screencap -p > {SC}/tt_sel.png",shell=True)
        got=avg(f'ffmpeg -v error -i {SC}/tt_sel.png -vf "crop=150:150:50:1930,scale=1:1" -frames:v 1 -f rawvideo -pix_fmt rgb24 -')
        if not got or not want_rgb: return False
        d=sum(abs(x-y) for x,y in zip(got,want_rgb)); print("tray colour",got,"want",want_rgb,"diff",d)
        return d<=45
    tiles=[(t,x,y) for t,x,y in tree() if dur and t==dur]
    if not tiles: tiles=[("newest",541,808)]
    picked=False
    for t,x,y in tiles[:6]:
        adb(f"input tap {x} {y}"); time.sleep(2.5)
        if tray_matches(): picked=True; break
        adb("input keyevent 4"); time.sleep(2)                         # wrong video: back to the gallery grid, try the next tile of that length
    if not picked: die("could not find the right video in the gallery (colour check failed for every tile of that length)")
    step("Next",lambda t:t=="Next",8); time.sleep(3)
    step("Next 2",lambda t:t=="Next",10); time.sleep(3)
if not find(lambda t:t.startswith("Add description") or t.startswith(want[:20]),10): die("post page missing")
adb("input tap 344 477"); time.sleep(1.5)
if not sync(): die("caption does not match")
print("caption ok")
if "mInputShown=true" in adb("dumpsys input_method"): adb("input tap 900 785"); time.sleep(1.5)   # close the keyboard by tapping blank space (the back key can leave the page)
time.sleep(1.5); adb("input tap 540 1383"); time.sleep(3.5)      # More options (fixed position; the UI tree is slow here)
if not find(lambda t:"AI-generated content" in t,10): die("AI-generated content row missing")
if PROMO:                                                          # promoting our own offer: TikTok requires Content disclosure -> Your brand
    adb("input tap 540 2013"); time.sleep(3)
    adb("input tap 948 472"); time.sleep(1.5); adb("input tap 982 685"); time.sleep(1.5); adb("input tap 541 2208"); time.sleep(2.5)
    c=find(lambda t:t=="Continue",5)
    if c: tap(c); time.sleep(3)
    if not find(lambda t:"AI-generated content" in t,6): die("did not return to More options after the disclosure setting")
    print("brand disclosure on")
if "--explore" in sys.argv: print("explore: stopped with More options open"); sys.exit(0)
def ai_on():
    x=subprocess.run("adb exec-out uiautomator dump /dev/tty",shell=True,capture_output=True,text=True).stdout
    return bool(re.search(r'content-desc="AI-generated content,[^>]*checked="true"',x))
adb("input tap 924 2172"); time.sleep(2)
shot("ai_on")
if not ai_on(): die("AI-generated content label did not turn on")
adb("input keyevent 4"); time.sleep(2)
if not find(lambda t:t=="Post",6): die("post button missing")
step("Post",lambda t:t=="Post",6)
for i in range(40):
    if find(lambda t:t in("Uploading","Posting"),2) is None and i>2: break
    time.sleep(3)
time.sleep(6); shot("after_post"); print("POSTED",os.path.basename(video))
