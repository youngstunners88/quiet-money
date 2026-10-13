---
name: faceless-photopea
description: Drive photopea.com headlessly from the studio through its official live-messaging API, to crop, resize or export a picture the way the owner does by hand, with a Pillow check on every result and a Pillow fallback. Use when asked to use Photopea, to batch-edit pictures in it, or when a Photopea crop fails, hangs or comes back wrong.
metadata:
  author: quiet-money
  version: 1.0.0
  code: faceless/planner_photopea.py
---

# Photopea driver

`faceless/planner_photopea.py`: `with Photopea() as pp: pp.crop(bytes, (l, t, r, b))`. Chromium (pre-installed under `/opt/pw-browsers`) runs Photopea in an iframe on a tiny local host page; the page talks to it with `postMessage`. Docs: photopea.com/api/live. Photopea says files stay on the device; the editor's own code and ads load from photopea.com.

## Rules
1. Playwright (Apache-2.0) is imported only inside the driver. `pip install playwright` needs no browser download here. It is optional: no Playwright, no Chromium or a blocked site means the Pillow crop is used and the report says so.
2. Every wait has a timeout (90 s to start, 60 s per step). No unbounded loops.
3. The local host page serves one fixed path and nothing else (a test checks that no directory is exposed).
4. Check every result against a Pillow crop of the same box (`agrees`). A mismatch uses the reference.
5. No logins, no uploads to a Photopea account, no site features that send a file out.

## The protocol that works (learned the hard way)
- Open the iframe at `https://www.photopea.com#%7B%22files%22%3A%5B%5D%7D` (a hash with a JSON config). **Without the hash it shows the marketing landing page and never says `done`.**
- Photopea sends the string `done` when ready and after every command. Send an ArrayBuffer to open a file, a string to run a script.
- Crop: `app.activeDocument.crop([left, top, right, bottom]);` then `app.activeDocument.saveToOE("jpg:0.95");` returns an ArrayBuffer message, then `done`. Close with `app.activeDocument.close(SaveOptions.DONOTSAVECHANGES);`.
- Proxy: Chromium needs `proxy={"server": HTTPS_PROXY, "bypass": "127.0.0.1,localhost"}`; the local host page is not reachable through the proxy.
- A `set_content` page has a null origin and never gets the hello; serve the host page over `http://127.0.0.1`.
- Timing here: about 3 s to start, under 1 s per crop.

## Troubleshooting
- **No `done` within 90 s:** check the hash, the proxy bypass, and `curl -I https://www.photopea.com`. Run `curl http://127.0.0.1:35669/__agentproxy/status` for blocked hosts (never route around a policy denial).
- **Live test:** `PLANNER_PHOTOPEA_LIVE=1 python -m pytest -q tests/test_planner_mcp.py -k live`.
- Other scripts (resize, layers, export formats) use the same two messages; see photopea.com/learn/scripts. Add a method to the driver with a test; do not send arbitrary strings from outside input.
