# Android setup

Works with any Android device that has Developer options: Samsung, Pixel, Xiaomi, OnePlus, Motorola, Oppo, Vivo, tablets, Android TV, and the Android Studio emulator. Android 5.0+ is supported; Android 11+ also supports wireless debugging without a cable.

## USB

1. Settings → About phone → tap **Build number** 7 times. (Samsung: Settings → About phone → Software information → Build number.)
2. Settings → System → Developer options → turn on **USB debugging**.
3. Plug in with a data cable. Unlock the phone and tap **Allow** (tick "Always allow from this computer").
4. Run `adb devices`. The phone should show as `device`, not `unauthorized`.

## Wi-Fi (Android 11+)

1. Developer options → **Wireless debugging** → turn it on → **Pair device with pairing code**.
2. On the computer: `adb pair <ip>:<pair-port>` and enter the code.
3. Then: `adb connect <ip>:<port>` using the port shown on the Wireless debugging screen.
4. `open-device-mcp doctor` lists it with `transport: wifi`.

For Android 10 and older, connect by USB once, run `adb tcpip 5555`, unplug, then run `adb connect <phone-ip>:5555`.

## Emulators

Create a device in Android Studio → Device Manager and start it. It shows up as `emulator-5554`. Headless option: `emulator -avd <name> -no-window`.

## Multiple phones

All connected phones show in `list_devices`. Ask the agent to `select_device` one, or pass `deviceSerial` on each call. To limit which phones the agent can touch, set `deviceAllowlist` in the config.

## Common issues

| Symptom | Fix |
|---|---|
| `unauthorized` | Unlock the phone and accept the prompt. If it never appears: Developer options → Revoke USB debugging authorizations, then replug. |
| `offline` | `adb kill-server && adb start-server`, then try another cable or port. |
| Taps do nothing (Xiaomi/Redmi/POCO) | Developer options → turn on **USB debugging (Security settings)**. This needs a Mi account. |
| Taps do nothing (Oppo/Realme/Vivo) | Developer options → turn on **Disable permission monitoring**. |
| Black screenshot | The app uses FLAG_SECURE (banking and DRM apps). This is by design and cannot be bypassed. |
| `get_ui_tree` fails | The screen is animating, or the app is a game or WebView canvas. Wait and retry, or fall back to screenshots. |
| Unicode text is not typed | `adb input text` only supports ASCII. Install the open-source ADBKeyboard IME for full Unicode. |
| Windows: no device | Install the OEM USB driver (Samsung, etc.) or Google USB Driver from Android Studio SDK Manager. |
