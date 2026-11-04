#!/usr/bin/env python3
"""Set a YouTube Shorts upload to publish later (phone app, adb + UI tree). Skill: faceless-youtube-schedule.
usage as a module: schedule_on_details(datetime) from the 'Add details' page (taps Visibility, sets Schedule date and time, comes back).
usage as a CLI (a Visibility sheet already open or the details page): yt_schedule.py "YYYY-MM-DD HH:MM"   (phone local time)
The sheet's title is not in the UI tree; its date field is (content-desc like 'Nov 5, 2026, 00:00'), so that is how it is found."""
import datetime, html, re, subprocess, sys, time

def adb(c): return subprocess.run(["adb", "shell", c], capture_output=True, text=True).stdout
def dump():
    x = subprocess.run("adb exec-out uiautomator dump /dev/tty", shell=True, capture_output=True, text=True).stdout
    for m in re.finditer(r'<node[^>]*?text="([^"]*)"[^>]*?resource-id="([^"]*)"[^>]*?content-desc="([^"]*)"[^>]*?bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x):
        yield html.unescape(m.group(1)), m.group(2), html.unescape(m.group(3)), ((int(m.group(4)) + int(m.group(6))) // 2, (int(m.group(5)) + int(m.group(7))) // 2)
def tap_node(pred, wait=8, pause=1.5):
    end = time.time() + wait
    while True:
        for t, rid, cd, c in dump():
            if pred(t, rid, cd): adb(f"input tap {c[0]} {c[1]}"); time.sleep(pause); return True
        if time.time() >= end: return False
        time.sleep(1.2)
DATE_FIELD = re.compile(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}, \d{2}:\d{2}$")
def date_field(t, r, c): return bool(DATE_FIELD.match(c or t))
def field_text():
    for t, r, c, _ in dump():
        if DATE_FIELD.match(c or t): return c or t

def schedule_on_details(d, die=sys.exit):
    """from 'Add details': open Visibility, expand Schedule, set date and time, return to the details page"""
    if not field_text():
        adb("input tap 540 1135"); time.sleep(2.5)                  # the Visibility row sits at a fixed place on the details page
        adb("input tap 540 1176"); time.sleep(2.5)                  # the Schedule row expands
    if not field_text(): die("schedule sheet did not open")
    set_on_sheet(d, die)
    adb("input keyevent 4"); time.sleep(2.5)

def set_on_sheet(d, die=sys.exit):
    if not tap_node(lambda t, r, c: date_field(t, r, c), 6): die("date field missing")
    time.sleep(1.5)
    for _ in range(max(0, (d.year - 2026) * 12 + d.month - 11)):    # calendar opens on the default month (Nov 2026 when this was built): arrow to later months
        tap_node(lambda t, r, c: "next month" in c.lower() or r.endswith("next_month") or r.endswith("month_navigation_next"), 3)
    if not tap_node(lambda t, r, c: c == d.strftime("%d %B %Y"), 6): die("calendar day " + d.strftime("%d %B %Y") + " not found")
    if not tap_node(lambda t, r, c: t == "OK", 5): die("date OK missing")
    time.sleep(2)
    tap_node(lambda t, r, c: r.endswith("toggle_mode") or "text input" in c.lower(), 4)   # clock face -> typed hour and minute
    time.sleep(1.5)
    for rid, val in (("input_hour", f"{d.hour}"), ("input_minute", f"{d.minute:02d}")):
        if not tap_node(lambda t, r, c, rid=rid: r.endswith(rid), 4): die("time field " + rid + " missing")
        adb("input keyevent 123"); [adb("input keyevent 67") for _ in range(3)]
        adb(f"input text {val}"); time.sleep(0.8)
    if not tap_node(lambda t, r, c: t == "OK", 5): die("time OK missing")
    time.sleep(2)
    want = d.strftime("%b ") + str(d.day) + d.strftime(", %Y, %H:%M")
    got = field_text()
    if got != want: die(f"schedule not set: wanted '{want}', sheet shows '{got}'")
    print("scheduled for", want)

if __name__ == "__main__":
    when = datetime.datetime.strptime(sys.argv[1], "%Y-%m-%d %H:%M")
    (set_on_sheet if field_text() else schedule_on_details)(when, lambda m: sys.exit("FAIL: " + m))
