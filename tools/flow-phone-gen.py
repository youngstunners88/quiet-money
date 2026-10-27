import subprocess,re,sys,time,html,os,glob
REPO="/home/kofibeatz/Documents/Quiet Money/quiet-money"
def adb(c,**k): return subprocess.run(["adb","shell",c],capture_output=True,text=True,**k).stdout
def tree():
    adb("uiautomator dump /sdcard/ui.xml"); x=adb("cat /sdcard/ui.xml"); out=[]
    for m in re.finditer(r'(?:text|content-desc)="([^"]+)"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',x):
        out.append((html.unescape(m.group(1)).replace("\n"," "),(int(m.group(2))+int(m.group(4)))//2,(int(m.group(3))+int(m.group(5)))//2))
    return out
def find(pred):
    for t,x,y in tree():
        if pred(t): return t,x,y
def tap(p): adb(f"input tap {p[1]} {p[2]}")
def typetext(text):
    for pi,part in enumerate(text.split("'")):
        if pi: adb("input keyevent 75")
        for i in range(0,len(part),26):
            adb("input text '"+part[i:i+26].replace(" ","%s")+"'"); time.sleep(0.25)
def gen(prompt,outname):
    before=set(os.listdir("/dev/null")) if False else None
    dl_before=set(adb("ls /sdcard/Download").split())
    am=find(lambda t:t=="Add media")
    if not am: print("no add media"); return False
    box=("",400,am[2]-120)
    tap(box); time.sleep(1.5); typetext(prompt); time.sleep(1.5)
    g=find(lambda t:t=="Generate")
    if not g: print("no generate"); return False
    tap(g); time.sleep(10)
    for i in range(24):
        time.sleep(10)
        if not any(re.fullmatch(r"\d+%",t) or t.startswith("Generating") for t,_,_ in tree()): break
    else: print("timeout generating"); return False
    time.sleep(2)
    adb("input keyevent 111")  # hide keyboard if any
    tile=find(lambda t:t.endswith(", 1 item") or ", 1 item" in t)
    if not tile: print("no tile", [t for t,_,_ in tree()][:12]); return False
    tap(tile); time.sleep(4)
    mo=find(lambda t:t=="More options")
    tap(mo); time.sleep(2)
    d=find(lambda t:t=="Download"); tap(d); time.sleep(2)
    r=find(lambda t:t.startswith("720p")); tap(r); time.sleep(1)
    dd=[(t,x,y) for t,x,y in tree() if t=="Download"]
    tap(dd[-1]); time.sleep(10)
    new=[f for f in adb("ls -t /sdcard/Download").split() if f.endswith(".mp4") and f not in dl_before]
    if not new: print("no new download"); return False
    dest=os.path.join(REPO,"channel/flow/inbox",outname)
    subprocess.run(["adb","pull","/sdcard/Download/"+new[0],dest],capture_output=True)
    print("saved",dest,os.path.getsize(dest)); 
    adb("input keyevent 4"); time.sleep(2)
    if not find(lambda t:t=="Add media"): adb("input keyevent 4"); time.sleep(2)
    time.sleep(2)
    return True
if __name__=="__main__":
    plist=sys.argv[1]; name=sys.argv[2]
    ok=gen(open(plist).read().strip(),name); sys.exit(0 if ok else 1)
