# Architecture

```
src/
  cli.ts              serve | doctor | list-devices | init
  server.ts           DeviceHub (device resolution) + MCP tool registration + wrap()
  safety.ts           mode/confirmation, device/path/shell allowlists, audit log
  config.ts           zod-validated JSON config
  exec.ts             Runner: spawn with timeout, output cap, structured errors (injectable)
  backends/
    types.ts          Backend interface shared by all platforms
    android.ts        adb: input, screencap, uiautomator, am, pm, logcat
    ios.ts            WebDriverAgent HTTP: W3C actions, /screenshot, /source
test/
  fake-adb.mjs        executable adb stand-in used by tests
  server.test.ts      tool, safety, parser, iOS (mocked fetch), and real stdio tests
```

## Call flow

```
MCP client ──tools/call──► wrap(action, risk, fn)
                              1. Safety.checkRisk (mode / confirmed)
                              2. DeviceHub.resolve (explicit → selected → only device) + device allowlist
                              3. tool-specific validation (paths, package names, shell allowlist)
                              4. Backend method → Runner (adb argv) or fetch (WDA)
                              5. Build envelope, write audit line, attach PNG if screenshot
                           ◄── { content: [json envelope, image?] }  or  { isError, error{code,message,suggestion} }
```

## Adding a platform

Implement `Backend` in `src/backends/<name>.ts`, give it an `owns(serial)` rule (for example a serial prefix), and push it into `DeviceHub.backends`. All tools, safety checks, and auditing work without changes.

## Design choices

- **stdio only.** No open ports means nothing to expose. Every major MCP client supports stdio.
- **adb CLI, not a protocol reimplementation.** It's the most compatible option across vendors and Android versions, and users already trust the binary.
- **UI tree before pixels.** `get_ui_tree` returns compact JSON with tap centers, which uses fewer tokens and is more accurate than having the agent read screenshots.
- **Zero runtime dependencies** besides the MCP SDK and zod.
