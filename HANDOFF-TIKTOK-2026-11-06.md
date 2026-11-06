# Post the five 2026-11-06 videos on TikTok (run this on the computer the phone is plugged into)

Do not ask questions. Post all five. Post ONLY these five: the older queued TikTok jobs (2026-10-25 to 2026-11-05) were mostly posted by hand through `tools/tt-phone-flow.py`, so running the whole queue would double-post.

## Setup (once)
```bash
git pull --rebase origin main
git fetch origin phone-media
adb devices                      # the phone must show as "device"; tap Allow if asked
```
The five finished videos are on the `phone-media` branch under `out/2026-11-06/<job>/final.mp4`. The posting packs (captions) are already in `distribution/queue/2026-11-06/slot1-myth` ... `slot5-escape` on main, but `video.mp4` is not committed, so copy it in:

```bash
for n in 1 2 3 4 5; do
  d=$(ls -d distribution/queue/2026-11-06/slot${n}-* | head -1)
  # the staged file for slot n is the job whose name starts with s$((n-1))-
  f=$(git ls-tree -r --name-only origin/phone-media | grep "out/2026-11-06/.*-s$((n-1))-.*/final.mp4")
  git show "origin/phone-media:$f" > "$d/video.mp4"
  # TikTok caption = the "TikTok / Instagram caption" section of POST.md, then the closing line the script adds
  python - "$d" <<'PY'
import sys, pathlib
sys.path.insert(0, ".")
from faceless import phone
d = pathlib.Path(sys.argv[1])
(d / "tiktok.txt").write_text(phone.short_texts((d / "POST.md").read_text())["tiktok"])
PY
done
```
(If `short_texts` leaves the "Education, not financial advice." line in the text, remove it: `tt-phone-flow.py fill` adds it itself.)

## For each slot (slot1-myth, slot2-math, slot3-psychology, slot4-playbook, slot5-escape)
```bash
python tools/tt-phone-flow.py 2026-11-06 slot1-myth prep   # pushes the video under a fresh per-day name
python tools/tt-phone-flow.py 2026-11-06 slot1-myth open   # Create > gallery > newest tile > Next > Next, stops on the post page
python tools/tt-phone-flow.py 2026-11-06 slot1-myth fill   # AI-generated content ON, brand disclosure, caption
```
Then screenshot the post page and check by eye that the COVER matches the slot's `cover.jpg` (a wrong tile posts the wrong video). If it matches, tap Post (801,2253). Wait for it to upload, then record it:

```bash
python -m faceless phone done <job_id> --url <tiktok url if visible> --ai-label yes
```
(job ids: `2026-11-06-tiktok-2026-11-06-s0-myth-...` through `s4-escape-...`; `python -m faceless phone status` lists them.)

## Rules
- AI-generated content label ON for every post (rule 4). No YouTube anything (rule 18).
- Do not post any video not listed here. If a screen differs from what the script expects, take a screenshot, fix the tap, and carry on; do not stop to ask.
- Commit `state/phone/` and push to main when all five are posted.
