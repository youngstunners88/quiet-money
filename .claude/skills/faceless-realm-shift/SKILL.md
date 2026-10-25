---
name: faceless-realm-shift
description: Write and generate the owner's "realm shift" clips on Google Flow: one impossible, hyper-realistic world with a spoken line, made to break the rhythm of a plain Quiet Money Short. Use when the owner asks for a realm, an intense or surreal Flow video, a pattern interrupt, "send the audience somewhere else", or Omni 1.1 Flash clips, and before any CapCut edit of such clips.
metadata:
  author: quiet-money
  version: 1.0.0
---

# Realm shift (Flow clips)

A realm shift is a 8-10 second clip that drops the viewer into an impossible world so the rhythm of the video breaks. The owner's standard comes from their prompt document ("An example of good prompts"), read in full 2026-10-25. Used prompts: `references/realms-2026-10-25.json`.

## Anatomy of a prompt (every clip)
1. **Opening tag**: "Hyper-realistic, photorealistic 10-second anamorphic sequence in one continuous impossible shot."
2. **The realm**: one world that cannot exist, built from a money idea (a cathedral of glass ledgers, a storm of due-date envelopes, an orchard of hourglasses). Concrete objects, scale, weather, light.
3. **The character**: one fictional person, specific (age, skin, clothing made of the idea), with a physical struggle. Never a real person or a real brand.
4. **The spoken line**: the character looks into the lens, "opens his mouth wide and says in a [voice]:" then the line. Lines are short, true, education not advice (CLAUDE.md rule 2): public-domain proverbs or the owner's own words.
5. **Beats on words**: tie one visual event to named words ("At the words small leak, hundreds of cracks race across the hull"; "At the word first, a shockwave...").
6. **Camera plan**: push-in on the mouth, orbit, snap-zoom, whip-pan, crane; one move per beat.
7. **Style tail**: epic cinematic, volumetric light, chiaroscuro, anamorphic flares, 35mm grain, "mouth clearly articulating the words, lip-sync accurate, 24fps, no text, no numbers, no logos".
Flow's prompt limit is far above 1,000 characters: write 1,500-2,500 and be specific. ASCII only when typing through adb (straight quotes, hyphens).

## Flow settings and cost (owner's account, 2026-10-25)
Native app `com.google.android.apps.labs.whisk` ("Google Flow"). New project -> mode pill -> **Video**, **9:16**, **720p**, **x1**, duration, model **Omni 1.1 Flash** (the only video model to use). Credits: 4 s = 7, 6 s = 10, 8 s = 12, **10 s = 15**. The daily allowance is 50, so three 10 s clips (45) is the day. Read the "AI credits" label before Generate and stop if it is not what the table says. A clip renders in about a minute. Download: open the clip -> More options -> Download -> **720p original** (1080p and 4K are the paid plan; never tap "Get a Google AI plan"). The file lands in `/sdcard/Download/<digits>.mp4`; pull it from there.
When credits run out: stop. The owner allows switching to another Google account that is already signed in on the phone (the account picker); never type a password and never buy credits.

## Habits that saved credits
- A new project gives an empty prompt box; clearing a long box by select-all failed and blended two prompts into one clip.
- Check each clip's frames (ffmpeg contact sheet) before building on it. When a scene misses, **fix it in the edit** (cuts, light, effects), not by re-spending credits (owner, 2026-10-25).
- Keep the brand: the standard Quiet Money wordmark and gold on every finished video.

## After generation
Edit with `faceless-film-editing` (plan) and `faceless-capcut-phone` (do it on the phone), then post only through the gate (`faceless-phone`, AI label on).
