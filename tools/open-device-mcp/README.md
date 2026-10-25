# OpenDeviceMCP

A free, open-source MCP server that lets AI agents (Claude, Cursor, Codex, any MCP client) see and control **your own phones**.

- **Free forever.** MIT license. No subscription, no account, no API key, no cloud, no telemetry.
- **Any Android device.** Phones, tablets, and emulators from any brand, over USB or Wi-Fi, through Google's free `adb`.
- **iPhone and iPad too.** Uses WebDriverAgent, the free open-source XCTest agent. You need a Mac to set it up once (see [docs/IOS.md](docs/IOS.md)).
- **Runs on your computer.** Windows, macOS, or Linux. Nothing leaves your machine.
- **Safe by default.** Risky actions need explicit approval. There is also a read-only mode, a dry-run mode, allowlists, and an audit log.

## How it works

```
AI agent (Claude / Cursor / Codex)
        │  MCP over stdio
        ▼
open-device-mcp  ──  safety checks, audit log
        │
        ├── adb ───────────────► Android phones / emulators (USB or Wi-Fi)
        └── WebDriverAgent ────► iPhone / iPad (HTTP on 127.0.0.1)
```

## Quick start (Android, about 5 minutes)

1. **Install Node.js 20+** from [nodejs.org](https://nodejs.org).
2. **Install Android Platform Tools** (free, includes `adb`) from [developer.android.com/tools/releases/platform-tools](https://developer.android.com/tools/releases/platform-tools) and add the folder to your PATH.
3. **On the phone:** Settings → About phone → tap **Build number** 7 times → back to Settings → Developer options → turn on **USB debugging**. Plug it in and tap **Allow** on the prompt.
4. **Install OpenDeviceMCP:**
   ```bash
   git clone <your-repo-url> open-device-mcp
   cd open-device-mcp
   npm install
   npm run build
   npm link            # makes the `open-device-mcp` command available
   open-device-mcp doctor
   ```
   `doctor` should show your phone as `[ok]`.
5. **Add it to your AI client** (see below), restart the client, and ask: *"List my phones and take a screenshot."*

## Add to your MCP client

**Claude Desktop / Cursor / Windsurf / most clients** (`claude_desktop_config.json`, `.cursor/mcp.json`, etc.):
```json
{
  "mcpServers": {
    "open-device": {
      "command": "open-device-mcp",
      "args": ["serve"]
    }
  }
}
```

**Claude Code:**
```bash
claude mcp add open-device -- open-device-mcp serve
```

**Codex CLI** (`~/.codex/config.toml`):
```toml
[mcp_servers.open-device]
command = "open-device-mcp"
args = ["serve"]
```

If you skipped `npm link`, use `"command": "node"` and `"args": ["/full/path/to/open-device-mcp/dist/cli.js", "serve"]`.

## Tools

| Tool | Android | iOS | What it does |
|---|---|---|---|
| `list_devices` | ✓ | ✓ | Connected devices, model, OS version, ready or not |
| `select_device` | ✓ | ✓ | Pick the default device (auto-picked if only one) |
| `screenshot` | ✓ | ✓ | PNG image returned to the agent, copy saved to disk |
| `get_ui_tree` | ✓ | ✓ | On-screen elements with text, labels, ids, and tap centers |
| `tap` | ✓ | ✓ | Tap, or long-press with `durationMs` |
| `swipe` | ✓ | ✓ | Swipe, drag, or scroll |
| `type_text` | ✓ | ✓ | Type into the focused field |
| `press_key` | ✓ | partial | BACK, HOME, RECENTS, ENTER, TAB, DELETE, POWER, VOLUME_UP, VOLUME_DOWN, WAKEUP |
| `launch_app` | ✓ | ✓ | Open by package name or bundle id |
| `open_url` | ✓ | ✓ | Open a web URL or deep link |
| `current_app` | ✓ | ✓ | Foreground app |
| `list_apps` | ✓ | – | Installed packages |
| `install_app` / `uninstall_app` | ✓ (confirm) | – | Install an APK or remove an app |
| `push_file` / `pull_file` | ✓ (confirm) | – | Copy files to or from `/sdcard` |
| `read_logs` | ✓ | – | Filtered logcat |
| `adb_shell` | ✓ (allowlist) | – | Safe, allowlisted shell commands only |

Every tool returns the same JSON envelope: `ok`, `deviceSerial`, `platform`, `action`, `startedAt`, `finishedAt`, `command` (the exact adb command or WDA request), `exitCode`, `stdoutPreview`, `stderrPreview`, `artifacts`, `warnings`, and `data`. Errors return `error.code`, `error.message`, `error.stderr`, and `error.suggestion`, so the agent knows what to do next.

## Safety

| Setting | Default | Meaning |
|---|---|---|
| `mode` | `confirm-destructive` | Install, uninstall, push, and pull need `confirmed: true`, which the agent should only send after you approve. Use `read-only` to block every action, or `open` to skip confirmations. |
| `dryRun` | `false` | Risky commands are shown but never run. You can also pass `serve --dry-run`. |
| `deviceAllowlist` | `[]` (all) | Only these serials can be controlled. |
| `pathAllowlist` | `~/open-device-mcp` | Local folders for APKs and file transfers. |
| `shellAllow` / `shellDeny` | safe defaults | Regex rules. Pipes, redirects, `rm -r`, `reboot`, `su`, `fastboot`, and `dd` are always denied. |
| `auditLog` | `~/open-device-mcp/audit.jsonl` | One line per call. Typed text and file contents are never logged. |

Run `open-device-mcp init` to write the config to `~/open-device-mcp/config.json`, then edit it. Set `OPEN_DEVICE_MCP_CONFIG` to use a different path. See [SECURITY.md](SECURITY.md).

## More guides

- [docs/ANDROID.md](docs/ANDROID.md): Wi-Fi debugging, emulators, multiple phones, brand-specific quirks
- [docs/IOS.md](docs/IOS.md): iPhone setup with WebDriverAgent
- [docs/AGENT_PROMPT.md](docs/AGENT_PROMPT.md): a system prompt that helps agents drive phones reliably
- [ARCHITECTURE.md](ARCHITECTURE.md)

## Development

```bash
npm install
npm run build
npm test      # 19 tests: simulated adb, mocked WebDriverAgent, and a real stdio MCP session
```

## Legal

This is an independent implementation built only on public interfaces (adb, uiautomator, WebDriverAgent). It contains no code, assets, or text from any commercial product, and is not affiliated with any of them. Only control devices you own or have permission to use.
