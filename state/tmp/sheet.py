import json, subprocess, sys
from PIL import Image
v=json.load(open("/home/user/quiet-money/production/output/2026-10-11/2026-10-11-s0-ledger-the-1-management-fee-trap/voice.json"))
src=sys.argv[1]; frac=float(sys.argv[2]) if len(sys.argv)>2 else 0.62
t=0; frames=[]
for a,b in v["beats"]:
    d=max(0.5,b-a); frames.append(t+min(d*frac, d-0.2)); t+=d
for k,f in enumerate(frames):
    subprocess.run(["ffmpeg","-loglevel","error","-y","-ss",f"{f:.2f}","-i",src,"-frames:v","1","-vf","scale=300:533",f"cf{k}.png"],check=True)
ims=[Image.open(f"cf{k}.png") for k in range(len(frames))]
cols=6; rows=(len(ims)+cols-1)//cols
s=Image.new("RGB",(300*cols,533*rows))
for i,im in enumerate(ims): s.paste(im,((i%cols)*300,(i//cols)*533))
s.save(sys.argv[3] if len(sys.argv)>3 else "cast_sheet.png")
