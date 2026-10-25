# iPhone / iPad setup

Apple doesn't provide an adb equivalent, so iOS control goes through **WebDriverAgent (WDA)**. WDA is a free, open-source (BSD-3) XCTest app maintained by the Appium project. It runs on your iPhone and exposes a small HTTP API, which OpenDeviceMCP calls on `127.0.0.1`.

## What you need

- A Mac with Xcode (free from the App Store). The Mac is needed to build and start WDA; the MCP server can run on the same Mac.
- A free Apple ID. A paid developer account is optional.
- `libimobiledevice` for USB port forwarding: `brew install libimobiledevice`.

> With a free Apple ID, Apple expires the signing after 7 days. Re-run step 3 when that happens. A paid account lasts a year.

## Steps

1. **On the iPhone:** Settings → Privacy & Security → **Developer Mode** → on (iOS 16+), then restart. Plug it into the Mac and tap **Trust**.
2. **Get WDA:**
   ```bash
   git clone https://github.com/appium/WebDriverAgent.git
   cd WebDriverAgent
   open WebDriverAgent.xcodeproj
   ```
   In Xcode, select the **WebDriverAgentRunner** target → Signing & Capabilities → choose your Team (your Apple ID) and change the Bundle Identifier to something unique, e.g. `com.yourname.WebDriverAgentRunner`.
3. **Start WDA on the phone** (keep this terminal open):
   ```bash
   UDID=$(idevice_id -l | head -1)
   xcodebuild -project WebDriverAgent.xcodeproj -scheme WebDriverAgentRunner \
     -destination "id=$UDID" test
   ```
   The first time, go to iPhone Settings → General → VPN & Device Management → trust your developer profile.
4. **Forward the port** (second terminal): `iproxy 8100 8100`
5. **Enable iOS in OpenDeviceMCP:** run `open-device-mcp init`, then edit `~/open-device-mcp/config.json`:
   ```json
   { "iosWdaUrl": "http://127.0.0.1:8100" }
   ```
6. `open-device-mcp doctor` should list `ios ios-wda ... [device]`.

## iOS differences

- **Coordinates are in points, not pixels.** `screenshot` returns `scale` (2 or 3) and `pointsWidth`/`pointsHeight`. Divide pixel positions by `scale`. Centers from `get_ui_tree` are already in points, so prefer those.
- **There is no BACK button.** Tap the on-screen back control or swipe from the left edge.
- **Not available through WDA:** installing apps, file transfer, logs, and shell. Use Xcode or `xcrun devicectl` on the Mac for those.
- **iOS Simulator:** run step 3 with `-destination 'platform=iOS Simulator,name=iPhone 16'`. No `iproxy` is needed.
