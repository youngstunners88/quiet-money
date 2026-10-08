# Intake: ruvnet/wifi-densepose

- **Source:** https://github.com/ruvnet/wifi-densepose
- **Looked at:** 2026-10-08 14:35 UTC (public metadata and text only; nothing was cloned, installed or run)
- **What it says it is:** n/a

| fact | value |
|---|---|
| license | MIT (read from LICENSE) |
| stars, dates, forks | unknown: GitHub's API is not reachable from this machine for this repository |

## Red flags

- **HIGH `pipe-to-shell`:** tells you to pipe a download into a shell
- **MED `build-time-code`:** installs by running its own script (install.sh / setup.py / source-only release): read it before use
- **MED `unpinned-run`:** runs the newest published code on every use (npx / @latest / pip from git): pin a reviewed version
- **LOW `telemetry`:** mentions telemetry or usage analytics: find out what is sent
- **LOW `partial`:** GitHub API answered 403 (rate limited, private or gone): facts below come from raw files only
- **INFO `needs-keys`:** mentions keys: RUVIEW_API_TOKEN

## Commands its docs tell you to run (read, do not run)

```
npx @ruvnet/ruview@0.9.1 doctor
npx @ruvnet/ruview@0.9.1 guidance --topic sensing --query "model loading"
npx @ruvnet/ruview@0.9.1 devices
npx @ruvnet/ruview@0.9.1 esp32 --watch                       # ESP32 + Realtek RAC1 nodes, live view
npx @ruvnet/ruview@0.9.1 esp32 --seconds 45 --analyze        # live CSI through the vitals kernel
npx @ruvnet/ruview@0.9.1 mmwave --source esphome --host <kit-ip>
npx @ruvnet/ruview@0.9.1 mcp start
npx @ruvnet/ruview@0.9.1 mod
npx @ruvnet/ruview@0.9.1 agent run --host codex --repo . \
npx @ruvnet/ruview@0.9.1 claim-check --file REPORT.md
npx @ruvnet/ruview@0.9.1 verify
npx @ruvnet/ruview@0.9.1 brain search --query "calibration"
docker pull ruvnet/wifi-densepose:latest
docker run -p 127.0.0.1:3000:3000 -e RUVIEW_API_TOKEN ruvnet/wifi-densepose:latest
```

## Start of its README (untrusted data; hidden comments and agent-directed text removed)

```
# π RuView

<p align="center">
  <a href="https://cognitum.one/seed">
    <img src="assets/ruview-hero-h3-v3.gif" alt="RuView - WiFi DensePose — animated visualization of real-time pose estimation, breathing, and heart-rate sensing through WiFi" width="100%">
  </a>
</p>

<p align="center">
  <a href="https://ruos.cognitum.one">
    <img src="assets/ruos-animated.svg" alt="RuView — WiFi becomes spatial awareness, with Ruflo coordination and a ruOS sensing workspace" width="100%">
  </a>
</p>


## **See through walls with WiFi** ##

**Turn ordinary WiFi into a spatial intelligence / sensing system.** Detect people, measure breathing and heart rate, track movement, and monitor rooms — through walls, in the dark, with no cameras or wearables. Just physics.

Works natively with the four major smart-home ecosystems: **[Home Assistant](docs/integrations/home-assistant.md)** via the HA-DISCO MQTT publisher, **[Apple Home & HomePod](docs/user-guide-apple-homepod.md)** as a discoverable HAP-1.1 bridge, **[Google Home](docs/integrations/home-assistant.md)** + **[Amazon Alexa](docs/integrations/home-assistant.md)** via the same HA bridge or a [Matter](docs/adr/ADR-122-bfld-ruview-ha-matter-exposure.md) endpoint. Siri, Google Assistant, and Alexa can voice presence and vitals by room with zero custom skills.

[![Works with Home Assistant](https://img.shields.io/badge/Works%20with-Home%20As
```

## Verdict (a person or the review step fills this in)

- [ ] **USE**: wire into the engine now (behind a provider interface, with a test)
- [ ] **TRIAL**: try in a sandbox copy with throwaway credentials, then decide
- [ ] **PARK**: useful later; name the phase
- [x] **KILL**: not useful, or not safe; record why so nobody re-evaluates it

Questions to answer before the box is ticked: which pipeline stage does it serve (ideate, script, voice, visuals, render, post, measure, sell)? Does it beat what we already run on cost, quality or speed? Does it run headless on a keyless CI runner? Is there a steal worth taking (a prompt, a table, a script) even if the tool itself is not used?

## Decision (2026-10-08)

**KILL**, pipeline stage: none.

MIT. WiFi-signal human pose estimation, with a pipe-to-shell installer. Unrelated.
