#!/usr/bin/env python3
"""TikTok post, steps 1-2 (verified-by-eye flow from 2026-11-04). usage: tt-phone-flow.py DAY NAME [prep|open|fill]
prep: push the video under a fresh per-day name with a fresh creation time (so the picker shows it first).
open: Create > gallery > '+' > newest tile > Done > first tile > Next > Next, stopping on the post page (check the cover by eye).
fill: More options: brand disclosure, AI-generated content ON (checked), caption from tiktok.txt + closing line. Never presses Post.
Wrong tiles post the wrong video: always screenshot the cover before pressing Post (801,2253)."""
import os,subprocess,sys,time
REPO=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
day,name,step=sys.argv[1],sys.argv[2],(sys.argv[3] if len(sys.argv)>3 else "prep")
SC=os.environ.get("TT_SCRATCH","/tmp"); fn=f"qm{day.replace('-','')}_{name}.mp4"
def adb(c): return subprocess.run(["adb","shell",c],capture_output=True,text=True).stdout
def tap(x,y,w=3): adb(f"input tap {x} {y}"); time.sleep(w)
if step=="prep":
    src=f"{REPO}/distribution/queue/{day}/{name}/video.mp4"; tmp=f"{SC}/{fn}"
    subprocess.run(["ffmpeg","-v","error","-y","-i",src,"-c","copy","-metadata",f"creation_time={time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}",tmp],check=True)
    subprocess.run(["adb","push",tmp,f"/sdcard/Download/QuietMoney/{fn}"],capture_output=True)
    adb(f"am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/Download/QuietMoney/{fn}"); time.sleep(3)
    print("prepared",fn)
elif step=="open":
    adb("am force-stop com.ss.android.ugc.trill"); time.sleep(1); adb("monkey -p com.ss.android.ugc.trill 1"); time.sleep(9)
    tap(540,2272,6); tap(113,2172,6); tap(185,808,7)      # create, gallery, '+'
    tap(150,1000,2); tap(896,2185,8)                       # newest tile in the system picker, Done
    tap(540,810,7)                                         # first tile in TikTok's grid
    tap(797,2248,8)                                        # Next -> the editor (Add sound, volume)
    if os.environ.get("TT_STOP_AT_EDITOR"): print("on the editor screen (add sound here, then tap Next at 801,2179)"); sys.exit(0)
    tap(801,2179,14)                                       # Next -> post page
    print("on post page (check the cover)")
elif step=="fill":
    import re,html
    def ui():
        return subprocess.run("adb exec-out uiautomator dump /dev/tty",shell=True,capture_output=True,text=True).stdout
    def where(label,wait=10):
        """centre of the first node whose text or description starts with label (the page layout shifts: an 'Add link' row appears on some posts)"""
        for _ in range(wait):
            for m in re.finditer(r'<node[^>]*?text="([^"]*)"[^>]*?content-desc="([^"]*)"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',ui()):
                t=html.unescape(m.group(1) or m.group(2))
                if t.startswith(label): return (int(m.group(3))+int(m.group(5)))//2,(int(m.group(4))+int(m.group(6)))//2,int(m.group(5))
            time.sleep(1.5)
        sys.exit(f"FAIL: '{label}' not on screen")
    want=open(f"{REPO}/distribution/queue/{day}/{name}/tiktok.txt").read().strip()+"\n\nEducation, not financial advice."
    x,y,_=where("More options"); tap(540,y,5)
    x,y,_=where("Content disclosure and ads"); tap(540,y,5)
    tap(948,472,4); tap(982,685,3); tap(541,2208,5); tap(740,1435,5)   # disclose commercial content, Your brand, Save, Continue
    x,y,r=where("AI-generated content"); tap(r-100,y,3)
    if 'AI-generated content,' in ui() and 'checked="true"' not in re.search(r'content-desc="AI-generated content,[^>]*',ui()).group(0): sys.exit("FAIL: AI label is not on")
    tap(1004,748,3); tap(344,477,2)                                    # close the sheet, caption box
    for li,line in enumerate(want.split("\n")):
        if li: adb("input keyevent 66"); time.sleep(0.2)
        for i in range(0,len(line),8): adb("input text '"+line[i:i+8].replace(" ","%s")+"'"); time.sleep(0.4)
    time.sleep(2); tap(900,785,2); print("filled; verify cover, AI label and caption, then Post")
