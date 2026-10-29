#!/usr/bin/env python3
"""Upload one queued Short through the YouTube app on the owner's phone (adb + UI tree). usage: yt-phone-upload.py DAY SLOT"""
import re,subprocess,sys,time,html,difflib,os
REPO="/home/kofibeatz/Documents/Quiet Money/quiet-money"
SC=os.environ.get("YT_SCRATCH","/tmp")
day,slot=sys.argv[1],sys.argv[2]
def adb(c): return subprocess.run(["adb","shell",c],capture_output=True,text=True).stdout
def tree():
    adb("uiautomator dump /sdcard/ui.xml"); x=adb("cat /sdcard/ui.xml"); out=[]
    for m in re.finditer(r'(?:text|content-desc)="([^"]+)"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',x):
        out.append((html.unescape(m.group(1)).replace("\n"," "),(int(m.group(2))+int(m.group(4)))//2,(int(m.group(3))+int(m.group(5)))//2))
    return out
def find(pred,wait=0):
    end=time.time()+wait
    while True:
        for t,x,y in tree():
            if pred(t): return t,x,y
        if time.time()>=end: return None
        time.sleep(1.5)
def tap(p): adb(f"input tap {p[1]} {p[2]}")
def shot(n): subprocess.run(f"adb exec-out screencap -p > {SC}/yt_{n}.png",shell=True)
def die(msg): shot("fail"); print("FAIL:",msg); sys.exit(1)
def step(label,pred,wait=8):
    p=find(pred,wait)
    if not p: die(label)
    tap(p); time.sleep(2.5); return p
def rawtype(s):
    for pi,part in enumerate(s.split("'")):
        if pi: adb("input keyevent 75")
        for i in range(0,len(part),10):
            adb("input text '"+part[i:i+10].replace(" ","%s")+"'"); time.sleep(0.45)
def newlines_type(s):
    for li,line in enumerate(s.split("\n")):
        if li: adb("input keyevent 66"); time.sleep(0.2)
        rawtype(line)
def field_text(key):
    c=[t for t,_,_ in tree() if key in t]
    return max(c,key=len) if c else None
def sync(want,probe,rounds=6):
    """type want into the focused field, then repair the keyboard's small slips (single characters) from the end backwards"""
    wn=want.replace("\n"," ")
    for attempt in range(rounds):
        adb("input keycombination 113 29"); time.sleep(0.5); adb("input keyevent 67"); time.sleep(0.8)
        newlines_type(want); time.sleep(2)
        for fix in range(4):
            got=field_text(probe)
            if got is None: break
            if got==wn: return True
            ops=[o for o in difflib.SequenceMatcher(None,got,wn,autojunk=False).get_opcodes() if o[0]!="equal"]
            if len(ops)>8 or any((o[2]-o[1])>3 or (o[4]-o[3])>3 for o in ops): break
            adb("input keycombination 113 123"); time.sleep(0.5)
            pos=len(got)
            for tag,i1,i2,j1,j2 in reversed(ops):
                moves=pos-i2
                if moves>0: adb("input keyevent "+" ".join(["21"]*moves)); time.sleep(0.4)
                if i2>i1: adb("input keyevent "+" ".join(["67"]*(i2-i1))); time.sleep(0.4)
                if j2>j1:
                    adb("input text '"+wn[j1:j2].replace(" ","%s")+"'"); time.sleep(0.6)
                pos=i1+(j2-j1)
            time.sleep(2)
        if field_text(probe)==wn: return True
    return False
# --- package text
t=open(f"{REPO}/distribution/queue/{day}/{slot}/POST.md",encoding="utf-8").read()
blk=t.split("## YouTube Shorts",1)[1].split("## TikTok",1)[0].strip().split("\n")
title=blk[0].replace("Title:","",1).strip()
desc=re.sub(r"\s*Narration and visuals are AI-assisted\.?","","\n".join(blk[1:]).strip())
def ascii_safe(x): return x.replace("\u2014",", ").replace("\u2013","-").replace("\u2019","'").replace("\u2018","'").replace("\u201c",'"').replace("\u201d",'"')
desc=ascii_safe(desc); title=ascii_safe(title)
if any(ord(c)>127 for c in desc+title): die("non-ASCII characters remain in the text")
# --- file on phone
fn=f"yt_{slot}.mp4"
subprocess.run(["adb","push",f"{REPO}/distribution/queue/{day}/{slot}/video.mp4",f"/sdcard/Download/QuietMoney/{fn}"],capture_output=True)
adb(f"touch /sdcard/Download/QuietMoney/{fn}"); adb(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Download/QuietMoney/{fn}"); time.sleep(2)
adb("settings put system user_rotation 0"); adb("svc power stayon true")
adb("am force-stop com.google.android.youtube"); adb("monkey -p com.google.android.youtube -c android.intent.category.LAUNCHER 1"); time.sleep(7)
step("create button",lambda t:t=="Create")
step("add from gallery",lambda t:t=="Add from Gallery")
time.sleep(2)
if not find(lambda t:t==fn):
    step("select more media",lambda t:t=="Select more media"); time.sleep(2)
    d0=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f"{REPO}/distribution/queue/{day}/{slot}/video.mp4"],capture_output=True,text=True).stdout)
    pd=f"{int(d0)//60:02d}:{int(d0)%60:02d}"
    step("pick the new video in the picker",lambda t:t.startswith("Video taken on") and t.endswith("duration "+pd))
    step("picker done",lambda t:t=="Done"); time.sleep(3)
tile=find(lambda t:t==fn,10)
if not tile: die("the pushed file is not in YouTube's gallery")
tap(tile); time.sleep(2)
step("next 1",lambda t:t=="Next"); time.sleep(3)
step("next 2",lambda t:t=="Next",12); time.sleep(3)
# --- details
dur=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f"{REPO}/distribution/queue/{day}/{slot}/video.mp4"],capture_output=True,text=True).stdout)
want_dur=f"{int(dur)//60}:{int(dur)%60:02d}"
shot("details"); print("selected by file name; expected duration",want_dur)
adb("input tap 560 380"); time.sleep(1.5); rawtype(title); time.sleep(1.5)
if title not in [t for t,_,_ in tree()]:
    adb("input keycombination 113 29"); time.sleep(0.5); adb("input keyevent 67"); time.sleep(0.8); rawtype(title); time.sleep(1.5)
if title not in [t for t,_,_ in tree()]: die("title not exact")
adb("input keyevent 4"); time.sleep(1.5)
sm=find(lambda t:t=="Show more",8)
if not sm: die("show more missing")
adb(f"input tap 540 {sm[2]-151}"); time.sleep(2.5)            # Select audience sits 151 px above Show more
adb("input tap 102 925"); time.sleep(1); adb("input keyevent 4"); time.sleep(2.5)   # 'No, it's not made for kids'
sm=find(lambda t:t=="Show more",8)
if not sm: die("show more missing after audience")
y_sm=sm[2]; tap(sm); time.sleep(2.5)
adb(f"input tap 480 {y_sm}"); time.sleep(3)                    # 'Add description' takes the place of Show more
if not sync(desc,"#shorts"): die("description does not match package")
print("description ok")
for _ in range(3):
    if find(lambda t:t=="Upload Short"): break
    adb("input keyevent 4"); time.sleep(2)
def settle(pred,wait=8):
    return find(pred,wait)
def ensure_title():
    """the keyboard sometimes appends one stray character to the title: delete it, then close the keyboard"""
    t=[x for x,_,_ in tree() if x.startswith(title[:14])]
    if t and t[0]==title+"t" or (t and len(t[0])==len(title)+1 and t[0].startswith(title)):
        adb("input keyevent 123"); adb("input keyevent 67"); time.sleep(1.2)
        t=[x for x,_,_ in tree() if x.startswith(title[:14])]
    return bool(t) and t[0]==title
ok_ai=False
for attempt in range(3):
    if not ensure_title(): adb("input keyevent 4"); time.sleep(2); ensure_title()
    for _ in range(3):
        if find(lambda t:t in("Show more","Show less","Upload Short"),2) and not find(lambda t:t=="Add description",1): break
        adb("input keyevent 4"); time.sleep(2)
    adb("input swipe 540 600 540 1700 400"); time.sleep(2)
    sm=find(lambda t:t=="Show more",3)
    if sm: tap(sm); time.sleep(2.5)
    adb("input swipe 540 1700 540 600 400"); time.sleep(3)
    sl=find(lambda t:t=="Show less",4)
    if not sl: continue
    adb(f"input tap 480 {sl[2]-152}"); time.sleep(3)
    if not settle(lambda t:t=="Add tags",5): adb("input keyevent 4"); time.sleep(2); continue
    adb("input tap 985 328"); time.sleep(3)         # the AI use row is not in the UI tree: tap its chevron
    if find(lambda t:t=="Add tags",2): adb("input tap 985 328"); time.sleep(3)
    if find(lambda t:t=="Add tags",1): adb("input keyevent 4"); time.sleep(2); continue
    adb("input tap 102 1026"); time.sleep(1.5); ok_ai=True; break
if not ok_ai: die("could not set AI use")
shot("ai_use")
adb("input keyevent 4"); time.sleep(2); adb("input keyevent 4"); time.sleep(2)
up=find(lambda t:t=="Upload Short",6)
if not up: die("upload button missing")
def fix_title():
    adb("input swipe 540 600 540 1700 400"); time.sleep(1.5)
    for _ in range(4):
        cur=[t for t,_,_ in tree() if t.startswith(title[:12])]
        if cur and cur[0]==title: return True
        adb("input tap 560 420"); time.sleep(1.5)
        if cur and cur[0]==title+"t": adb("input keyevent 123"); adb("input keyevent 67")
        else:
            adb("input keycombination 113 29"); time.sleep(0.5); adb("input keyevent 67"); time.sleep(0.8); rawtype(title)
        time.sleep(1.5); adb("input keyevent 4"); time.sleep(2)
    return False
if not fix_title(): die("title still not exact before upload")
print("title verified")
up=find(lambda t:t=="Upload Short",6)
if not up: die("upload button missing")
shot("before_upload"); tap(up); time.sleep(8)
for i in range(30):
    if not find(lambda t:t.startswith("Uploading")): break
    time.sleep(10)
shot("after"); print("UPLOADED",slot,title)
