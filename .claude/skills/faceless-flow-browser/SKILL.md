---
name: faceless-flow-browser
description: Make a day's beat pictures on Google Flow through the desktop app's built-in browser pane (the owner keeps flow.google.com open there), 0 credits, then bring them into production/cache/flow/ so the render uses them. Use when the owner says Flow is open in the browser, asks for today's or tomorrow's images on Flow, or when scripts need pictures and the phone is not connected.
metadata:
  author: quiet-money
  version: 1.0.0
---

# Flow pictures through the browser pane

Worked end to end on 2026-10-26: 143 pictures, 0 credits. The pictures are Nano Banana 2.1 at 768x1376 (9:16), good enough for the render. The visual rules are in `faceless-visual-charge`.

## Steps
1. **Prompts.** `visual` of every beat of every script (`script-lab/final/<job>.json`), ASCII only. Save the ordered list; the position in it is the beat's identity.
2. **Project.** In the pane's Flow tab: cookie banner -> **No thanks**; **New project**. The composer chip must read `Nano Banana 2.1 | 9:16 | x1` (Settings trigger -> Image, 9:16, x1).
3. **Helper in the page** (javascript_tool): `window.__q(text)` focuses the `[role=textbox]` whose aria-label contains "create", selects all, deletes, `execCommand('insertText')` of `text + ' Vertical 9:16, cinematic photoreal, no text, no numbers, no logos or brands, no real person face.'`.
4. **Submit with a real click.** Scripted clicks and Enter are ignored (not trusted events). Use `browser_batch` with pairs `[javascript_tool __q(prompt), computer left_click (418,653) on the send arrow]`, 12 pairs per call (25 actions max). Flow runs them in parallel (about 35 s each); no waits needed between pairs. **Count the tiles afterwards: a batch's last prompts can silently not submit** (4 of 66 were lost); resubmit those with a 2 s wait after each click.
5. **Harvest.** The grid is virtual (about 14 tiles rendered). Scroll the `div.cdk-virtual-scrollable.page-container` in 250 px steps, record every `flow-image-tile img` whose src contains `flow-content` with `y` and `x`; sort by (y, x): **newest first, left before right**. The nth-newest is index n-1; the beat submitted k-th of N is index N-k.
6. **Move the bytes.** The page cannot reach localhost, and the pane has no download folder. `fetch(signedUrl)` -> blob -> base64, and **return it as the tool result: a result over the size limit is saved to a file** (`.claude/projects/.../tool-results/*.txt`, a JSON array with `.[0].text`); 8 pictures (about 8 MB) per call works. Tag each picture (`BEAT12:<b64>|...`) and decode with Python.
7. **Check by eye.** Build a numbered contact sheet and compare with the numbered prompt list before filing: a lost submission shifts every later picture.
8. **File.** `production/cache/flow/<day>/<job_id>/beatNN.jpg` (NN = beat number from 1). `faceless/pipeline/visuals.py` uses a file there instead of generating one.

## Gotchas
- javascript_tool calls time out at 45 s: poll in one call, collect in another.
- Never put the signed CDN URL in a file or a commit (it expires, but treat it as private).
- Pane viewport emulation breaks Flow's layout; leave it at the pane's own size and drive it by structure, not coordinates (the send arrow stays at about (418, 653)).
- Cookie banner: always the non-tracking choice.

## Flow's bot detection (learned 2026-10-26)
After about 320 scripted submissions in one session, Flow answered every new request with "Failed: We noticed some unusual activity. Note that browser extensions that modify the page may cause issues." (not charged). That is anti-automation: **stop, do not retry, do not switch clients to get around it, and tell the owner.** Keep volume low (a day's set is about 65 pictures; do not add art batches on top of it in the same session), pace the clicks (a few seconds between submissions, not back to back), and make anything that does not need photographic generation (gig art, layouts, cards) in code instead.
