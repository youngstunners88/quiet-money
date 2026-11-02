---
name: faceless-flow-stills
description: Make every still for one or more Shorts in Google Flow (Image mode, 0 credits, Nano Banana 2.1) across up to three Flow accounts at once - two browser-pane tabs plus the phone - and drop them where the pipeline uses them before any paid image model. Use when the owner says "use Flow for the images", "re-render with Flow", "all 3 flows", or when stills must not come from Muapi/Cloudflare.
---

# Flow stills, three lanes in parallel

Owner rule (2026-11-01): stills for re-renders come from Flow, not Muapi; never the FLUX 4B model ([[feedback-never-flux-4b]]). Flow Image mode costs 0 credits.

## How the pipeline takes them
`faceless/pipeline/visuals.py` uses `production/cache/flow/<day>/<job id>/beatNN.jpg` for a beat before calling any image generator. Job ids are `<UTC day>-s<slot>-<pillar>-<slug(title)>`, so plan and render on the same UTC day with the same slot.

## Steps
1. **Plan.** `PYTHONPATH=. .venv/bin/python tools/flow_stills_plan.py channel/flow/stills/plan-<name>.json SCRIPT.json:PILLAR:SLOT ...` writes every beat that needs a picture (card beats are skipped), its exact prompt and target file.
2. **Lanes.** The owner opens Flow in the browser pane with two accounts (tabs `seed` and `tab-1`); the phone app is the third account. Split the videos: about half per browser tab, one video to the phone (a background agent drives it over adb; see the phone notes below).
3. **Browser tabs.** New project in each tab, set Image, 9:16, x1 (check "0 credits"). Install a helper with `javascript_tool`: `window.__rows=[[key, prompt-without-suffix]...]`, `window.__SUF` (the shared style suffix), `window.__put(i)` (focus `.ProseMirror`, `execCommand('selectAll')`, `execCommand('insertText', ...)`, push key to `window.__sub`), and `window.__collect()` (when no "NN%" is on the page, pair the new `flow-content.google/image/` tiles, reversed DOM order, with the pending keys).
   - The generate button needs a REAL click: synthetic `.click()`/`dispatchEvent` is ignored (untrusted events). Use `find "Start generation"` once per tab for its ref, then per prompt: `__put(i)` + `computer left_click ref`.
   - Five prompts per tab per `browser_batch` (25 actions max), both tabs in the same batch, wait about 30 s, `__collect()` both. Four to five concurrent generations per tab work; a round of ten stills takes about 40 s.
   - Keys are `s<slot>b<NN>`. Read `window.__map` back compactly (strip the URL host and KeyName) and rebuild the URLs.
4. **Save.** `.venv/bin/python tools/flow_save.py PLAN.json MAP.json SHEET.jpg`: curl each signed CDN URL (no login needed), Lanczos 768x1376 to 1080x1920 with a light unsharp, write the beat file, build a contact sheet. LOOK at the sheet: every picture must match its key's prompt (catches a mapping slip) and show no text, logos or mangled hands.
5. **Render.** `faceless make --pillar P --slot SLOT --script S.json --no-publish` (two at a time in the background). Beats with a Flow still cost nothing.

## Gotchas
- The page's CSP blocks fetching scripts from localhost: paste helpers directly, keep them compact (shared suffix, short keys).
- Downloads from the browser pane do not reach disk; the 2K "upscaled" menu option is not reachable that way. Use the 1K CDN URL.
- Menu misclicks can hit "Move to trash"; an "Undo" toast appears (find "Undo", click it).
- Phone lane: Flow app, New project defaults to Image; set 9:16 x1; never Video, never the "AI credits" link, never add accounts. `adb shell input text` breaks on ( ) ' " & ; characters. Pull the downloaded file, resize as above.

## Phone lane notes (2026-11-01 run, 12/12 stills)
- If `adb devices` lists nothing: `adb kill-server; adb start-server`.
- Settings chip reads "Image x1"; the prompt box sits about 150 px above "Add media". The keyboard autocorrects words while `input text` types ("no logo" became "no logos"); harmless, but check.
- Download: More options > Download > 1K (original size, preselected). Files land in /sdcard/Download as `<digits>_<digits>.jpg`, 768x1376.
- Find the new image by the ordered tile labels ("<short title>, 1 item", newest top-left); only about 6 tiles are visible, so counts do not work. The UI dump can lag right after Generate.
- The owner may use the phone mid-run: check that Flow is in the foreground before each tap and pause if not.
- A phone lane runs at roughly 4 minutes per still; give it the smallest share.

## Run notes 2026-11-02 (the phone was the only lane that survived)
- The PC browser pane lost its Google sign-in when it closed overnight; Flow showed the sign-in page and Claude in Chrome was not connected. Never enter credentials: fall back to the phone lane.
- The Gemini API image models (incl. `gemini-nano-banana-2.1`) return 429 on the free key; they are paid-only.
- Phone lane: ONE agent for the whole batch, all beats, about 30 to 95 s per still (49 stills in about 80 min). Give it the plan JSON, tell it to message "main" after each video so rendering can start on finished videos while the phone continues.
- Render each finished video immediately (`faceless make --pillar P --slot N --script S.json --no-publish`, two at a time), look at a stills contact sheet (`tools/stills_sheet.py SLOT OUT.jpg`) and pack it (`tools/pack_queue.py DAY SLOT NAME`).
- Fix before posting: the gauntlet's judge_hook (rewrite beat 1 with a number and a "you"), a hard first-frame fail (a near-black first still: lift it with gamma 0.5), and ignore the self-duplicate flag (the script matches its own saved copy).
- Posting: portrait lock (`adb shell cmd window fixed-to-user-rotation enabled; adb shell wm user-rotation lock 0`), delete old pushed copies in /sdcard/Download/QuietMoney so each new video has one gallery tile.
