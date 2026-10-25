---
name: faceless-capcut-phone
description: Edit a video in CapCut on the owner's Android phone, driven over adb (uiautomator tree plus taps): import clips, cut, speed-ramp, add effects, transitions, shake, flash, captions, brand text and music, then export. Use when the owner asks for a CapCut edit, an intense effects-heavy cut, or to finish Flow clips on the phone. Free-tier only: blue-diamond effects, never the Pro ones.
metadata:
  author: quiet-money
  version: 1.0.0
---

# CapCut on the phone

Package `com.lemon.lvoverseas`. The owner's tier allows **blue-diamond** assets only: use them freely, skip anything marked Pro/gold, never tap upgrade or buy. Plan the cut with `faceless-film-editing` first (establish, build, peak, aftermath; ramps into the hit; hard cuts; sound as partner). The owner's rule: a weak scene is fixed in the edit with cuts, light and effects.

## Driving the phone (same method as `faceless-phone`)
- Needs Developer options -> **USB debugging (Security settings)** on (HyperOS needs a SIM once). Keep the screen awake: `adb shell svc power stayon true`; the PIN lock screen is the owner's, never enter it.
- Read: `adb shell uiautomator dump` and match nodes by `text` / `content-desc`; tap a node's centre with `adb shell input tap`. CapCut's timeline is often a canvas: when the tree is empty, take `adb exec-out screencap -p`, look at it, tap by coordinates, and look again after every action.
- Put source clips in `/sdcard/Download/QuietMoney/` (`adb push`), run the media scanner broadcast, then pick them in CapCut's own gallery tab.
- Never put a login, code or card into CapCut. Decline permission pop-ups that are not needed (camera, microphone, notifications); allow photo access narrowly.

## Brand every export
Quiet Money look: gold (#F5C518-style) wordmark "QUIET MONEY", the channel handle @quietmoneyrule, no clutter, no other logos. End card or lower-third in gold on dark.

## Effects-heavy recipe (use the blue-diamond set)
Per clip: speed-ramp curve (slow before the hit, 150-300% through it), 3-6 frame freeze on the peak, push-in keyframe, camera shake on impacts, flash/white frame on the cut, glitch or RGB split on rhythm breaks, vignette and grain, contrast up and blacks crushed. Between clips: hard cut or a fast whip/zoom transition, never a slow dissolve. Subtitles: word-by-word captions for the spoken line, gold highlight on the key word. Music: a low drone plus an impact hit on each cut (CapCut's free sounds). Sync cuts to beats.

## Export and post
Export 1080p, 30 fps, to the gallery; pull with `adb pull`; check duration, loudness and a frame sheet; then queue the post through `faceless-phone` (AI label on, disclosure in the caption).
