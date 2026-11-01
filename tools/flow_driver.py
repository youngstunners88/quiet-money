#!/usr/bin/env python3
"""Build the in-page Flow driver for one browser tab, and save finished stills.

  python tools/flow_driver.py js PLAN.json VIDEO_INDEX[,VIDEO_INDEX...] > driver.js   # paste into a Flow project tab (Image, 9:16, x1)
  python tools/flow_driver.py save PLAN.json RESULTS.json                             # curl every collected image into its beat file

The driver types each prompt into Flow's editor, presses generate, waits for the new image tile, and records its
signed CDN URL in window.__flow (beat file -> url). The CDN URL needs no login, so `save` fetches it with curl and
writes a 1080x1920 JPEG (Lanczos from Flow's 768x1376 original, light sharpen) where the pipeline looks for Flow stills.
"""
import json, subprocess, sys, tempfile
from pathlib import Path

DRIVER = r"""
(async () => {
  const jobs = __JOBS__;
  window.__flow = window.__flow || {}; window.__flowErr = window.__flowErr || {}; window.__flowDone = false;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const ids = () => new Set([...document.querySelectorAll('img')].filter(i => i.src.includes('flow-content.google/image/')).map(i => i.src.split('?')[0]));
  for (const j of jobs) {
    if (window.__flow[j.file]) continue;
    for (let attempt = 0; attempt < 2 && !window.__flow[j.file]; attempt++) {
      const before = ids();
      const ed = document.querySelector('.ProseMirror');
      ed.focus(); document.execCommand('selectAll'); document.execCommand('insertText', false, j.prompt);
      await sleep(600);
      const go = [...document.querySelectorAll('button')].find(b => b.innerText.trim() === 'arrow_forward');
      if (!go) { window.__flowErr[j.file] = 'no generate button'; break; }
      go.click();
      for (let t = 0; t < 120; t++) {
        await sleep(1500);
        const fresh = [...document.querySelectorAll('img')].find(i => i.src.includes('flow-content.google/image/') && i.naturalWidth > 200 && !before.has(i.src.split('?')[0]));
        if (fresh) { window.__flow[j.file] = fresh.src; break; }
      }
      if (!window.__flow[j.file]) window.__flowErr[j.file] = 'timed out (attempt ' + (attempt + 1) + ')';
    }
  }
  window.__flowDone = true;
})(); 'started ' + __N__ + ' prompts';
"""


def js(plan_path, idx):
    plan = json.load(open(plan_path))
    jobs = [{"file": b["file"], "prompt": b["prompt"]} for i in idx for b in plan["videos"][i]["beats"]]
    return DRIVER.replace("__JOBS__", json.dumps(jobs)).replace("__N__", str(len(jobs)))


def save(results_path):
    from PIL import Image, ImageFilter
    res = json.load(open(results_path))
    ok = 0
    for file, url in res.items():
        out = Path(file)
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".img") as tmp:
            r = subprocess.run(["curl", "-sf", "-o", tmp.name, url])
            if r.returncode:
                print("FAIL", out.name, "curl", r.returncode); continue
            im = Image.open(tmp.name).convert("RGB")
            if im.size != (1080, 1920):
                im = im.resize((1080, 1920), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
            im.save(out, "JPEG", quality=95)
            ok += 1
    print(f"saved {ok}/{len(res)}")


if __name__ == "__main__":
    if sys.argv[1] == "js":
        print(js(sys.argv[2], [int(x) for x in sys.argv[3].split(",")]))
    else:
        save(sys.argv[3])
