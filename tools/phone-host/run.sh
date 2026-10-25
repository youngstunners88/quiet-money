#!/usr/bin/env bash
# Runs on an always-on computer at home (mini PC, Raspberry Pi 5, or an old laptop left on). The owner's phone stays at home on the
# charger and the home Wi-Fi with Wireless debugging on; this works through the due phone jobs while the owner is out (skill
# faceless-phone-host). PHONE_ADB_ADDR (ip:port from the phone's Wireless debugging screen) lives in ~/.config/quiet-money/phone.env.
set -uo pipefail
cd "$(dirname "$0")/../.."
git pull --rebase --quiet origin main || true
beat() {   # heartbeat: pushed when the host's state changes (or every 3 h), so `phone status` in the cloud sees the host is alive
  if python -m faceless phone heartbeat "${PHONE_ADB_ADDR:-none}" "$@" | grep -q '"commit": true'; then
    git add state/phone/host.json && git commit -q -m "phone host: $*" && { git push -q origin main || { git pull -q --rebase origin main && git push -q origin main; }; } || true
  fi
}
if [ -f state/PAUSE ]; then echo "paused: $(head -1 state/PAUSE)"; beat --note "paused"; exit 0; fi
if [ -z "${PHONE_ADB_ADDR:-}" ]; then echo "PHONE_ADB_ADDR is not set (~/.config/quiet-money/phone.env)"; exit 1; fi

reach() { adb connect "$1" >/dev/null 2>&1; [ "$(adb -s "$1" get-state 2>/dev/null)" = "device" ]; }
if ! reach "$PHONE_ADB_ADDR"; then
  # Wireless debugging picks a new port after a restart; a paired phone announces itself over mDNS, so find it there.
  found=$(adb mdns services 2>/dev/null | awk '/_adb-tls-connect/ {print $NF; exit}')
  if [ -n "$found" ] && reach "$found"; then
    sed -i "s/^PHONE_ADB_ADDR=.*/PHONE_ADB_ADDR=$found/" "$HOME/.config/quiet-money/phone.env" 2>/dev/null || true
    PHONE_ADB_ADDR="$found"
  else
    echo "phone not reachable (off the home Wi-Fi, Wireless debugging off, or not paired with this host)"
    beat --unreachable --note "phone not reachable"
    exit 0
  fi
fi
export ANDROID_SERIAL="$PHONE_ADB_ADDR"          # every adb call (ours and the MCP server's) goes to this phone

adb shell svc power stayon true >/dev/null 2>&1 || true      # screen stays on while it charges
adb shell input keyevent WAKEUP >/dev/null 2>&1 || true
adb shell wm dismiss-keyguard >/dev/null 2>&1 || true         # works when the phone has no PIN; with a PIN the run stops at the lock screen
if adb shell dumpsys window 2>/dev/null | grep -Eq "mDreamingLockscreen=true|isKeyguardShowing=true|mShowingLockscreen=true"; then
  echo "phone is locked: nothing can be tapped until it is unlocked"
  beat --note "phone locked"
  exit 0
fi

tools/phone-run.sh || { beat --note "run failed"; exit 1; }
beat --note "ok"
