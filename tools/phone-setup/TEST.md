# Testing the phone lane on your PC

Do these in order. Each step proves one thing, and nothing posts until step 5.

**Windows:** run commands in PowerShell, and run `.sh` scripts from Git Bash (it comes with Git for Windows): `bash tools/phone-run.sh`.

## 0. Get the repo and run the setup
```
git clone https://github.com/youngstunners88/quiet-money
cd quiet-money
```
Windows: `powershell -ExecutionPolicy Bypass -File tools\phone-setup\setup.ps1`  ·  Mac/Linux: `bash tools/phone-setup/setup.sh`

## 1. Phone connected
On the phone: Settings → About phone → tap **Build number** 7 times → Developer options → **USB debugging** on. Plug in with a data cable and tap **Allow**.
`adb devices` must say `device` (not `unauthorized`). `open-device-mcp doctor` must show your phone as `[ok]`.
Xiaomi/Oppo/Vivo: see `tools/open-device-mcp/docs/ANDROID.md` (extra switch for taps).

## 2. Sign in by hand, once, on the phone
YouTube (as @quietmoneyrule), TikTok, Chrome → labs.google/flow (Google account), Fiverr. Turn off the screen lock for now (or set **Stay awake** while charging), because taps don't land on a locked screen.

## 3. Claude can see the phone
```
claude
```
(in the repo folder) then ask: **"List my phones and take a screenshot."** You should see the phone's screen come back.

## 4. The jobs are waiting
`python -m faceless phone status` should show five `yt_community` jobs queued: the five original comics you loved, not yet posted anywhere. They come from the `phone-media` branch, so run `git fetch origin phone-media` first.

## 5. One post, with you watching
In `claude`, say:
> Use the faceless-phone skill. Run ONE job: `python -m faceless phone next --push`, follow the YouTube Posts tab recipe, but stop before tapping Post and show me a screenshot.

Check the picture, the caption and the channel (Quiet Money, @quietmoneyrule). If it's right, reply **"post it"**. Claude taps Post, screenshots the result, and records it with `phone done`.

## 6. The rest, unattended
`bash tools/phone-run.sh` works through every job whose gate is open (the other four comics, then TikTok and Flow jobs as they arrive). Watch the first run; if a step fails twice, the job is held and `python -m faceless phone status` says why.

## What to tell me afterwards
Paste anything that went wrong (the screenshot, or the `blocked` list from `phone status`). The recipes in `.claude/skills/faceless-phone/references/recipes.md` were written from memory of the apps, so the first real run is where they get corrected.
