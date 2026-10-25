import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import type { Config } from "./config.js";
import { DeviceError, realRunner, type Runner } from "./exec.js";
import { Safety, type Risk } from "./safety.js";
import { AndroidBackend } from "./backends/android.js";
import { IosBackend } from "./backends/ios.js";
import type { ActionResult, Backend } from "./backends/types.js";

export const VERSION = "0.1.0";

export class DeviceHub {
  readonly backends: Backend[];
  readonly safety: Safety;
  active: string | null = null;

  constructor(readonly cfg: Config, runner: Runner = realRunner, http: typeof fetch = fetch) {
    this.backends = [new AndroidBackend(cfg, runner)];
    if (cfg.iosWdaUrl || process.platform === "darwin") this.backends.push(new IosBackend(cfg, runner, http));
    this.safety = new Safety(cfg);
  }

  async listDevices() {
    const lists = await Promise.allSettled(this.backends.map((b) => b.listDevices()));
    const devices = lists.flatMap((l) => (l.status === "fulfilled" ? l.value : []));
    const errors = lists.flatMap((l, i) => (l.status === "rejected" ? [`${this.backends[i].platform}: ${(l.reason as Error).message}`] : []));
    return { devices, errors };
  }

  /** Resolve which device a call targets: explicit serial, else the selected one, else the only one connected. */
  async resolve(serial?: string): Promise<{ serial: string; backend: Backend }> {
    let s = serial ?? this.active ?? undefined;
    if (!s) {
      const { devices } = await this.listDevices();
      const ready = devices.filter((d) => d.authorized && d.state === "device");
      if (ready.length === 1) s = ready[0].serial;
      else if (ready.length === 0) throw new DeviceError("NO_DEVICE", "No controllable device is connected.", "Plug in an Android phone with USB debugging on (or start WebDriverAgent for iPhone), then call list_devices.");
      else throw new DeviceError("DEVICE_AMBIGUOUS", `${ready.length} devices are connected.`, `Call select_device with one of: ${ready.map((d) => d.serial).join(", ")}`);
    }
    this.safety.checkDevice(s);
    const backend = this.backends.find((b) => b.owns(s!));
    if (!backend) throw new DeviceError("IOS_NOT_CONFIGURED", `No backend can handle ${s}.`, "Set iosWdaUrl in config for iPhones.");
    return { serial: s, backend };
  }
}

type Content = { type: "text"; text: string } | { type: "image"; data: string; mimeType: string };

function trim(s: string | undefined, n: number) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n) + `\n…[truncated ${s.length - n} chars]` : s;
}

export function createServer(hub: DeviceHub): McpServer {
  const cfg = hub.cfg;
  const server = new McpServer({ name: "open-device-mcp", version: VERSION });
  const serialArg = { deviceSerial: z.string().optional().describe("Device serial from list_devices. Omit to use the selected device.") };
  const confirmArg = { confirmed: z.boolean().optional().describe("Must be true, after the user explicitly approves this action.") };

  /** Wraps every tool: resolves device, enforces safety, times the call, writes the audit log, and builds the standard envelope. */
  const wrap = <A extends Record<string, any>>(
    action: string,
    risk: Risk,
    fn: (args: A, ctx: { serial: string; backend: Backend }) => Promise<ActionResult>,
    opts: { needsDevice?: boolean } = {},
  ) => async (args: A) => {
    const startedAt = new Date().toISOString();
    let serial: string | null = null;
    try {
      hub.safety.checkRisk(action, risk, args.confirmed);
      const ctx = opts.needsDevice === false ? { serial: "", backend: hub.backends[0] } : await hub.resolve(args.deviceSerial);
      serial = ctx.serial || null;
      const r = await fn(args, ctx);
      const envelope = {
        ok: true,
        deviceSerial: serial,
        platform: opts.needsDevice === false ? null : ctx.backend.platform,
        action,
        startedAt,
        finishedAt: new Date().toISOString(),
        command: r.command,
        exitCode: r.exitCode ?? 0,
        stdoutPreview: trim(r.stdout, cfg.maxOutputChars),
        stderrPreview: trim(r.stderr, 2000),
        artifacts: r.artifacts ?? [],
        warnings: r.warnings ?? [],
        ...(r.data && { data: r.data }),
      };
      const safeArgs: Record<string, any> = { ...args };
      if (action === "type_text" && typeof safeArgs.text === "string") safeArgs.text = `<${safeArgs.text.length} chars>`;
      hub.safety.audit({ device: serial, tool: action, args: safeArgs, ok: true, command: r.command, outputDigest: r.stdout ? Safety.digest(r.stdout) : null });
      const content: Content[] = [{ type: "text", text: JSON.stringify(envelope, null, 2) }];
      if (r.image && args.returnImage !== false) content.push({ type: "image", data: r.image.toString("base64"), mimeType: "image/png" });
      return { content };
    } catch (e) {
      const err = e instanceof DeviceError ? e : new DeviceError("INTERNAL", (e as Error).message);
      hub.safety.audit({ device: serial, tool: action, ok: false, code: err.code });
      const body = { ok: false, deviceSerial: serial, action, startedAt, finishedAt: new Date().toISOString(), error: { code: err.code, message: err.message, stderr: trim(err.stderr, 2000), suggestion: err.suggestion ?? null } };
      return { isError: true, content: [{ type: "text" as const, text: JSON.stringify(body, null, 2) }] };
    }
  };

  server.registerTool("list_devices", {
    title: "List devices",
    description: "List connected Android phones/emulators (via adb) and iPhones (via WebDriverAgent), with state, model, OS version and whether they can be controlled.",
    inputSchema: {},
  }, wrap("list_devices", "read", async () => {
    const { devices, errors } = await hub.listDevices();
    return { command: `${cfg.adbPath} devices -l`, data: { selected: hub.active, devices }, warnings: errors };
  }, { needsDevice: false }));

  server.registerTool("select_device", {
    title: "Select device",
    description: "Set the default device for later calls in this session.",
    inputSchema: { serial: z.string() },
  }, wrap<{ serial: string }>("select_device", "read", async ({ serial }) => {
    const { devices } = await hub.listDevices();
    const d = devices.find((x) => x.serial === serial);
    if (!d) throw new DeviceError("DEVICE_NOT_FOUND", `No device with serial ${serial}.`, `Available: ${devices.map((x) => x.serial).join(", ") || "none"}`);
    hub.safety.checkDevice(serial);
    hub.active = serial;
    return { command: null, data: { device: d } };
  }, { needsDevice: false }));

  server.registerTool("screenshot", {
    title: "Screenshot",
    description: "Capture the screen. Returns the PNG as an image plus its size. Saves a copy under the artifacts directory unless saveToDisk is false. On iOS, tap coordinates are in points (pixels / scale).",
    inputSchema: { ...serialArg, saveToDisk: z.boolean().default(true), returnImage: z.boolean().default(true) },
  }, wrap<{ deviceSerial?: string; saveToDisk: boolean; returnImage: boolean }>("screenshot", "read", async (a, { serial, backend }) => {
    const r = await backend.screenshot(serial);
    if (a.saveToDisk) {
      const file = join(cfg.artifactsDir, `screenshot-${serial.replace(/[^\w.-]/g, "_")}-${Date.now()}.png`);
      mkdirSync(cfg.artifactsDir, { recursive: true });
      writeFileSync(file, r.image);
      r.artifacts = [file];
    }
    return r;
  }));

  server.registerTool("get_ui_tree", {
    title: "Get UI tree",
    description: "Read the on-screen UI elements (text, accessibility labels, ids, bounds and tap centers). Prefer this over screenshots for finding what to tap.",
    inputSchema: { ...serialArg, maxNodes: z.number().int().min(1).max(1000).default(150), onlyInteractive: z.boolean().default(true).describe("Only return elements that are tappable or carry text.") },
  }, wrap<{ deviceSerial?: string; maxNodes: number; onlyInteractive: boolean }>("get_ui_tree", "read", (a, { serial, backend }) => backend.uiTree(serial, a.maxNodes, a.onlyInteractive)));

  server.registerTool("tap", {
    title: "Tap",
    description: "Tap at screen coordinates. Set durationMs for a long-press.",
    inputSchema: { ...serialArg, x: z.number().min(0), y: z.number().min(0), durationMs: z.number().int().min(0).max(10_000).optional() },
  }, wrap<{ deviceSerial?: string; x: number; y: number; durationMs?: number }>("tap", "act", (a, { serial, backend }) => backend.tap(serial, Math.round(a.x), Math.round(a.y), a.durationMs)));

  server.registerTool("swipe", {
    title: "Swipe",
    description: "Swipe or drag from (startX,startY) to (endX,endY). Use to scroll: swipe up to scroll down.",
    inputSchema: { ...serialArg, startX: z.number().min(0), startY: z.number().min(0), endX: z.number().min(0), endY: z.number().min(0), durationMs: z.number().int().min(50).max(10_000).default(300) },
  }, wrap<{ deviceSerial?: string; startX: number; startY: number; endX: number; endY: number; durationMs: number }>("swipe", "act", (a, { serial, backend }) =>
    backend.swipe(serial, Math.round(a.startX), Math.round(a.startY), Math.round(a.endX), Math.round(a.endY), a.durationMs)));

  server.registerTool("type_text", {
    title: "Type text",
    description: "Type text into the focused field. Tap the field first.",
    inputSchema: { ...serialArg, text: z.string().min(1).max(2000) },
  }, wrap<{ deviceSerial?: string; text: string }>("type_text", "act", (a, { serial, backend }) => backend.typeText(serial, a.text)));

  server.registerTool("press_key", {
    title: "Press key",
    description: "Press a hardware/navigation key. BACK and RECENTS are Android-only.",
    inputSchema: { ...serialArg, key: z.enum(["BACK", "HOME", "RECENTS", "ENTER", "TAB", "DELETE", "POWER", "VOLUME_UP", "VOLUME_DOWN", "WAKEUP"]) },
  }, wrap<{ deviceSerial?: string; key: any }>("press_key", "act", (a, { serial, backend }) => backend.pressKey(serial, a.key)));

  server.registerTool("launch_app", {
    title: "Launch app",
    description: "Open an app by Android package name (e.g. com.android.settings) or iOS bundle id (e.g. com.apple.Preferences).",
    inputSchema: { ...serialArg, appId: z.string(), activity: z.string().optional().describe("Android only: explicit activity, e.g. .MainActivity") },
  }, wrap<{ deviceSerial?: string; appId: string; activity?: string }>("launch_app", "act", (a, { serial, backend }) => backend.launchApp(serial, a.appId, a.activity)));

  server.registerTool("open_url", {
    title: "Open URL",
    description: "Open a URL or deep link on the device.",
    inputSchema: { ...serialArg, url: z.string().url() },
  }, wrap<{ deviceSerial?: string; url: string }>("open_url", "act", (a, { serial, backend }) => backend.openUrl(serial, a.url)));

  server.registerTool("current_app", {
    title: "Current app",
    description: "Return the app (and Android activity) currently in the foreground.",
    inputSchema: { ...serialArg },
  }, wrap<{ deviceSerial?: string }>("current_app", "read", (_a, { serial, backend }) => backend.currentApp(serial)));

  server.registerTool("list_apps", {
    title: "List apps",
    description: "Android: list installed package names.",
    inputSchema: { ...serialArg, thirdPartyOnly: z.boolean().default(true) },
  }, wrap<{ deviceSerial?: string; thirdPartyOnly: boolean }>("list_apps", "read", (a, { serial, backend }) => backend.listApps(serial, a.thirdPartyOnly)));

  server.registerTool("install_app", {
    title: "Install app",
    description: "Android: install an APK from an allowed local folder. Requires confirmed: true after the user approves.",
    inputSchema: { ...serialArg, ...confirmArg, apkPath: z.string(), allowDowngrade: z.boolean().default(false) },
  }, wrap<{ deviceSerial?: string; apkPath: string; allowDowngrade: boolean }>("install_app", "destructive", (a, { serial, backend }) => {
    const p = hub.safety.checkLocalPath(a.apkPath);
    if (!existsSync(p)) throw new DeviceError("FILE_NOT_FOUND", `APK not found: ${p}`);
    if (!p.toLowerCase().endsWith(".apk")) throw new DeviceError("INVALID_ARGUMENT", "File must end in .apk");
    return backend.installApp(serial, p, a.allowDowngrade);
  }));

  server.registerTool("uninstall_app", {
    title: "Uninstall app",
    description: "Android: uninstall a package. Requires confirmed: true after the user approves.",
    inputSchema: { ...serialArg, ...confirmArg, appId: z.string(), keepData: z.boolean().default(false) },
  }, wrap<{ deviceSerial?: string; appId: string; keepData: boolean }>("uninstall_app", "destructive", (a, { serial, backend }) => backend.uninstallApp(serial, a.appId, a.keepData)));

  server.registerTool("push_file", {
    title: "Push file",
    description: "Android: copy a local file (from an allowed folder) to /sdcard, /storage or /data/local/tmp. Requires confirmed: true.",
    inputSchema: { ...serialArg, ...confirmArg, localPath: z.string(), devicePath: z.string() },
  }, wrap<{ deviceSerial?: string; localPath: string; devicePath: string }>("push_file", "destructive", (a, { serial, backend }) => {
    const p = hub.safety.checkLocalPath(a.localPath);
    if (!existsSync(p)) throw new DeviceError("FILE_NOT_FOUND", `Local file not found: ${p}`);
    return backend.pushFile(serial, p, hub.safety.checkDevicePath(a.devicePath));
  }));

  server.registerTool("pull_file", {
    title: "Pull file",
    description: "Android: copy a file from the device to an allowed local folder. Requires confirmed: true.",
    inputSchema: { ...serialArg, ...confirmArg, devicePath: z.string(), localPath: z.string() },
  }, wrap<{ deviceSerial?: string; devicePath: string; localPath: string }>("pull_file", "destructive", (a, { serial, backend }) => {
    const p = hub.safety.checkLocalPath(a.localPath);
    mkdirSync(dirname(p), { recursive: true });
    return backend.pullFile(serial, hub.safety.checkDevicePath(a.devicePath), p);
  }));

  server.registerTool("read_logs", {
    title: "Read logs",
    description: "Android: read recent logcat lines, optionally filtered by tag and minimum level.",
    inputSchema: { ...serialArg, tag: z.string().optional(), level: z.enum(["V", "D", "I", "W", "E", "F"]).default("I"), maxLines: z.number().int().min(1).max(2000).default(200) },
  }, wrap<{ deviceSerial?: string; tag?: string; level: string; maxLines: number }>("read_logs", "read", (a, { serial, backend }) => backend.logs(serial, a)));

  server.registerTool("adb_shell", {
    title: "ADB shell (allowlisted)",
    description: "Android: run one shell command that matches the configured allowlist (e.g. 'getprop ro.product.model', 'wm size', 'dumpsys battery'). Pipes, redirects and destructive commands are always blocked.",
    inputSchema: { ...serialArg, command: z.string().min(1).max(500) },
  }, wrap<{ deviceSerial?: string; command: string }>("adb_shell", "act", (a, { serial, backend }) => {
    hub.safety.checkShell(a.command);
    return backend.shell(serial, a.command.trim());
  }));

  return server;
}
