---
name: faceless-phone-host
description: Run the Quiet Money phone lane with nobody home. The owner's phone stays at home on the charger and Wi-Fi, a small always-on computer drives it every 30 minutes through the day with Claude Code on Opus 5.5, finds the phone again when its Wi-Fi debugging port changes, keeps it awake, and reports a heartbeat the cloud can see. Use when the owner wants the phone to work while they are out, asks about the home host, mini PC or Raspberry Pi, says the phone jobs stopped, or `phone status` shows the host stale or unreachable.
metadata:
  author: quiet-money
  version: 1.0.0
  code: tools/phone-host/run.sh, faceless/phone.py (heartbeat, host)
---

# The home phone host

## What it is
The phone can't be driven from outside the house. Something on the home network has to talk to it over adb. So the owner leaves the **phone** at home, and a small **host computer** that stays on drives it. The owner's own laptop and desktop can be off.

```
cloud routines ──git──► host at home (systemd timer, every 30 min 08:00-21:30)
                          run.sh: find phone (saved ip:port, else mDNS) → wake, stay on → unlocked? → phone-run.sh
                          phone-run.sh: claude -p --model claude-opus-5-5 + open-device MCP → jobs → receipts → push
                          heartbeat → state/phone/host.json (pushed when its state changes, or every 3 h)
```

## Set up once
1. **Host:** any Linux machine that stays on: a mini PC, a Raspberry Pi 5 (8 GB), or an old laptop. Install git, Node 20+, Python 3.11+ with the repo's requirements, Android Platform Tools (`adb`), and Claude Code. Sign in to Claude Code on the host with the owner's account.
2. **Repo:** clone into `~/quiet-money`. Give the host push access to `main` through its own GitHub sign-in (`gh auth login` or a deploy key), never a key in the repo.
3. **Phone server:** `cd tools/open-device-mcp && npm ci && npm run build && npm link`, then `claude mcp add open-device -- open-device-mcp serve`.
4. **Phone:** Developer options → **Wireless debugging** on, plus **Stay awake** (while charging). Pair once: "Pair device with pairing code", then on the host `adb pair <ip>:<pair-port>`. For autonomy, use no screen lock, or Smart Lock "trusted place" at home. With a PIN active, runs stop at the lock screen. That is a trade-off the owner decides; say it plainly.
5. **Address:** `mkdir -p ~/.config/quiet-money && echo "PHONE_ADB_ADDR=<ip>:<port>" > ~/.config/quiet-money/phone.env`. The port is on the Wireless debugging screen.
6. **Schedule:** `cp tools/phone-host/phone-host.{service,timer} ~/.config/systemd/user/ && systemctl --user daemon-reload && systemctl --user enable --now phone-host.timer`, then `loginctl enable-linger $USER`, so it runs with nobody logged in.
7. **Test:** `systemctl --user start phone-host.service; journalctl --user -u phone-host.service -n 50`. In the cloud, `python -m faceless phone status` shows `host.seen: true`.

## How it stays autonomous
- **Port changes:** a restart gives Wireless debugging a new port. `run.sh` falls back to `adb mdns services`, connects to the paired phone, and writes the new address to `phone.env`.
- **Sleep:** `svc power stayon true`, then a wake key and `wm dismiss-keyguard` before every run.
- **One phone:** `ANDROID_SERIAL` is set, so every adb call, including the MCP server's, goes to that phone.
- **Model:** Opus 5.5 by default (owner, 2026-10-25: autonomy first). Recipes drift as apps change, and the strongest model recovers best. `PHONE_MODEL` in `phone.env` overrides it.
- **Kill switch:** `state/PAUSE` is checked before the phone is touched.
- **Gates:** unchanged. The host only runs what `phone next` hands out (skill `faceless-phone`).

## Health: what the cloud sees and does
`phone status` → `host`: `seen`, `at`, `age_hours`, `reachable`, `note`, `stale` (no run for 6 h, or the phone did not answer).
- The daily routine reports the host state with the phone queue. `stale` during the day is the one thing to tell the owner, in one line with the fix from the table below.
- Never "fix" a stale host by posting another way. The jobs stay queued and run on the next good pass.

| `note` / symptom | Cause | Fix (owner) |
|---|---|---|
| `phone not reachable` | phone off the home Wi-Fi, Wireless debugging switched off, or a new pairing needed after an OS update | phone on home Wi-Fi with Wireless debugging on; if still failing, pair again (`adb pair`) |
| `phone locked` | screen lock came back | unlock it, or set Smart Lock trusted place at home |
| `run failed` | Claude Code signed out on the host, git push refused, or the MCP server missing | on the host: `claude` (sign in), `git push` (credentials), `open-device-mcp doctor` |
| `paused` | `state/PAUSE` exists | nothing; the owner lifts it |
| host not seen for hours | host off, asleep, or lost power | power settings: never sleep; check `systemctl --user list-timers` |
| jobs `held` | an app needed a person (login, verification, missing AI-label switch) | see `phone status` → `blocked`; sign in on the phone by hand |

## Rules
1. The host is the owner's own machine at the owner's home, driving the owner's own phone. No cloud phone, no shared device, no second account.
2. Nothing on the host stores a key in the repo. Claude Code's sign-in and GitHub credentials live in the host user's own config.
3. Don't run jobs overnight (the timer stops at 21:30), and don't run more than one host per phone.
4. A change to `run.sh`, the timer or the heartbeat is engine code: run `python -m faceless ci` before pushing.
