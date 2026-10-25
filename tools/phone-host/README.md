# Home phone host

The phone stays at home on the charger and Wi-Fi. A small computer that stays on at home drives it every 30 minutes from 08:00 to 21:30, using Claude Code on Opus 5.5, so the owner can leave with the laptop off.

- `run.sh`: one pass. It finds the phone (saved address, else mDNS), wakes it, stops if it is locked or paused, runs `tools/phone-run.sh`, and writes a heartbeat.
- `phone-host.service`, `phone-host.timer`: the systemd user units that run it.

Setup, health and fixes are in the skill: `.claude/skills/faceless-phone-host/SKILL.md`.
