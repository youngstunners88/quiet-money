import type { Config } from "../config.js";
import { DeviceError, type Runner } from "../exec.js";
import { pngSize, type ActionResult, type Backend, type DeviceInfo, type Key, type UiNode } from "./types.js";

type Fetch = typeof fetch;

/**
 * iOS control via WebDriverAgent (WDA), the open-source XCTest agent (BSD-3, maintained by the Appium project).
 * WDA is free to build and run on your own iPhone with a free Apple ID in Xcode. This backend only talks to
 * a WDA instance you run yourself; no cloud service is involved.
 */
export class IosBackend implements Backend {
  platform = "ios" as const;
  private sessionId: string | null = null;
  constructor(private cfg: Config, private run: Runner, private http: Fetch = fetch) {}

  owns(serial: string) {
    return serial.startsWith("ios");
  }

  private get base() {
    return this.cfg.iosWdaUrl.replace(/\/+$/, "");
  }

  private async call(method: "GET" | "POST" | "DELETE", path: string, body?: unknown): Promise<any> {
    if (!this.base) throw new DeviceError("IOS_NOT_CONFIGURED", "iOS control is not configured.", "Start WebDriverAgent on the iPhone and set iosWdaUrl (e.g. http://127.0.0.1:8100) in the config. See docs/IOS.md.");
    if (this.cfg.dryRun && method !== "GET") return { value: null, dryRun: true };
    let res: Response;
    try {
      res = await this.http(this.base + path, {
        method,
        headers: { "content-type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(this.cfg.commandTimeoutMs),
      });
    } catch (e) {
      throw new DeviceError("WDA_UNREACHABLE", `Cannot reach WebDriverAgent at ${this.base}: ${(e as Error).message}`, "Make sure WDA is running (xcodebuild test) and port 8100 is forwarded (iproxy 8100 8100).");
    }
    const json: any = await res.json().catch(() => ({}));
    if (!res.ok || json?.value?.error) {
      if (json?.value?.error === "invalid session id") this.sessionId = null;
      throw new DeviceError("WDA_FAILED", json?.value?.message ?? `WDA HTTP ${res.status}`, "Retry; if it persists, restart WebDriverAgent.", JSON.stringify(json?.value ?? {}).slice(0, 500));
    }
    return json;
  }

  private async session(): Promise<string> {
    if (this.sessionId) return this.sessionId;
    const j = await this.call("POST", "/session", { capabilities: { alwaysMatch: {} } });
    this.sessionId = j.sessionId ?? j.value?.sessionId;
    if (!this.sessionId) throw new DeviceError("WDA_FAILED", "WDA did not return a session id.");
    return this.sessionId;
  }

  private ok(command: string, extra: Partial<ActionResult> = {}): ActionResult {
    const warnings = [...(extra.warnings ?? [])];
    if (this.cfg.dryRun && !command.startsWith("GET")) warnings.push("dry-run: request was not sent");
    return { command, exitCode: 0, ...extra, warnings };
  }

  async listDevices(): Promise<DeviceInfo[]> {
    const out: DeviceInfo[] = [];
    if (this.base) {
      try {
        const s = await this.call("GET", "/status");
        const v = s.value ?? {};
        out.push({
          serial: "ios-wda",
          platform: "ios",
          state: v.ready === false ? "not-ready" : "device",
          authorized: true,
          model: v.device ?? v.ios?.name ?? "iPhone",
          osVersion: v.os?.version ? `iOS ${v.os.version}` : undefined,
          transport: "wda",
        });
      } catch (e) {
        out.push({ serial: "ios-wda", platform: "ios", state: "unreachable", authorized: false, transport: "wda", note: (e as DeviceError).message });
      }
    }
    // Optional: list USB-attached iPhones via libimobiledevice so the user can see them even before WDA runs.
    try {
      const r = await this.run(this.cfg.ideviceIdPath, ["-l"], { timeoutMs: 5000 });
      for (const udid of r.stdout.toString().split(/\s+/).filter(Boolean)) {
        out.push({ serial: `ios:${udid}`, platform: "ios", state: "attached", authorized: false, transport: "usb", note: "Detected over USB. Start WebDriverAgent and use serial 'ios-wda' to control it." });
      }
    } catch { /* libimobiledevice not installed; that's fine */ }
    return out;
  }

  private requireWda(serial: string) {
    if (serial !== "ios-wda") throw new DeviceError("IOS_NEEDS_WDA", `Device ${serial} is attached but not controllable yet.`, "Start WebDriverAgent and use serial 'ios-wda'. See docs/IOS.md.");
  }

  async screenshot(serial: string) {
    this.requireWda(serial);
    const j = await this.call("GET", "/screenshot");
    const image = Buffer.from(j.value ?? "", "base64");
    const size = pngSize(image);
    if (!size) throw new DeviceError("SCREENSHOT_FAILED", "WDA did not return a PNG.");
    let scale = 1;
    try { scale = (await this.call("GET", "/wda/screen")).value?.scale ?? 1; } catch { /* older WDA */ }
    return {
      command: "GET /screenshot", exitCode: 0, image,
      data: { ...size, scale, coordinateSpace: "points", pointsWidth: Math.round(size.width / scale), pointsHeight: Math.round(size.height / scale) },
      warnings: scale !== 1 ? [`iOS taps use points: divide screenshot pixel coordinates by ${scale}`] : [],
    };
  }

  async uiTree(serial: string, maxNodes: number, onlyInteractive: boolean) {
    this.requireWda(serial);
    const j = await this.call("GET", "/source?format=json");
    const all = flattenWda(j.value, onlyInteractive);
    return this.ok("GET /source?format=json", {
      data: { nodeCount: all.length, nodes: all.slice(0, maxNodes), coordinateSpace: "points" },
      warnings: all.length > maxNodes ? [`truncated: ${all.length} nodes, returned ${maxNodes}`] : [],
    });
  }

  private async pointer(path: Array<{ x: number; y: number; pause?: number }>) {
    const sid = await this.session();
    const actions: any[] = [{ type: "pointerMove", duration: 0, x: Math.round(path[0].x), y: Math.round(path[0].y) }, { type: "pointerDown", button: 0 }];
    for (let i = 1; i < path.length; i++) actions.push({ type: "pointerMove", duration: path[i].pause ?? 250, x: Math.round(path[i].x), y: Math.round(path[i].y) });
    if (path.length === 1) actions.push({ type: "pause", duration: path[0].pause ?? 50 });
    actions.push({ type: "pointerUp", button: 0 });
    await this.call("POST", `/session/${sid}/actions`, { actions: [{ type: "pointer", id: "finger1", parameters: { pointerType: "touch" }, actions }] });
    return `POST /session/${sid}/actions`;
  }

  async tap(serial: string, x: number, y: number, durationMs?: number) {
    this.requireWda(serial);
    return this.ok(await this.pointer([{ x, y, pause: durationMs || 50 }]));
  }

  async swipe(serial: string, x1: number, y1: number, x2: number, y2: number, durationMs: number) {
    this.requireWda(serial);
    return this.ok(await this.pointer([{ x: x1, y: y1 }, { x: x2, y: y2, pause: durationMs }]));
  }

  async typeText(serial: string, text: string) {
    this.requireWda(serial);
    const sid = await this.session();
    await this.call("POST", `/session/${sid}/wda/keys`, { value: [...text] });
    return this.ok(`POST /session/${sid}/wda/keys`);
  }

  async pressKey(serial: string, key: Key) {
    this.requireWda(serial);
    const sid = await this.session();
    switch (key) {
      case "HOME":
        await this.call("POST", "/wda/homescreen");
        return this.ok("POST /wda/homescreen");
      case "VOLUME_UP":
      case "VOLUME_DOWN":
        await this.call("POST", `/session/${sid}/wda/pressButton`, { name: key === "VOLUME_UP" ? "volumeUp" : "volumeDown" });
        return this.ok(`POST /session/${sid}/wda/pressButton`);
      case "ENTER":
      case "DELETE":
      case "TAB":
        await this.call("POST", `/session/${sid}/wda/keys`, { value: [key === "ENTER" ? "\n" : key === "TAB" ? "\t" : "\b"] });
        return this.ok(`POST /session/${sid}/wda/keys`);
      case "WAKEUP":
        await this.call("POST", "/wda/unlock");
        return this.ok("POST /wda/unlock");
      case "POWER":
        await this.call("POST", "/wda/lock");
        return this.ok("POST /wda/lock");
      default:
        throw new DeviceError("UNSUPPORTED", `iOS has no ${key} button.`, key === "BACK" ? "Tap the on-screen back button (usually top-left) or swipe from the left edge." : "Use HOME, then navigate.");
    }
  }

  async launchApp(serial: string, appId: string) {
    this.requireWda(serial);
    if (!/^[\w.-]+$/.test(appId)) throw new DeviceError("INVALID_ARGUMENT", `'${appId}' is not a valid bundle id.`);
    const sid = await this.session();
    await this.call("POST", `/session/${sid}/wda/apps/launch`, { bundleId: appId });
    return this.ok(`POST /session/${sid}/wda/apps/launch`);
  }

  async openUrl(serial: string, url: string) {
    this.requireWda(serial);
    const sid = await this.session();
    await this.call("POST", `/session/${sid}/url`, { url });
    return this.ok(`POST /session/${sid}/url`);
  }

  async currentApp(serial: string) {
    this.requireWda(serial);
    const j = await this.call("GET", "/wda/activeAppInfo");
    return this.ok("GET /wda/activeAppInfo", { data: { bundleId: j.value?.bundleId ?? null, name: j.value?.name } });
  }

  private unsupported(what: string): never {
    throw new DeviceError("UNSUPPORTED", `${what} is not available on iOS through WebDriverAgent.`, "On a Mac, use Xcode or 'xcrun devicectl' for app installs and file transfer.");
  }
  async listApps(): Promise<ActionResult> { this.unsupported("Listing installed apps"); }
  async installApp(): Promise<ActionResult> { this.unsupported("Installing apps"); }
  async uninstallApp(): Promise<ActionResult> { this.unsupported("Uninstalling apps"); }
  async pushFile(): Promise<ActionResult> { this.unsupported("Pushing files"); }
  async pullFile(): Promise<ActionResult> { this.unsupported("Pulling files"); }
  async logs(): Promise<ActionResult> { this.unsupported("Reading logs"); }
  async shell(): Promise<ActionResult> { this.unsupported("Shell access"); }
}

const IOS_INTERACTIVE = /Button|Cell|TextField|SecureTextField|Switch|Slider|Link|Key|Tab|SearchField|Image|Icon|MenuItem|PickerWheel|SegmentedControl|Stepper/;

export function flattenWda(root: any, onlyInteractive = true): UiNode[] {
  const out: UiNode[] = [];
  const walk = (n: any) => {
    if (!n || typeof n !== "object") return;
    const r = n.rect;
    const type = String(n.type ?? "").replace(/^XCUIElementType/, "");
    const text = n.value ?? n.label ?? undefined;
    const desc = n.label && n.label !== text ? n.label : undefined;
    const visible = n.isVisible !== false && n.isVisible !== "0";
    if (r && r.width > 0 && r.height > 0 && visible) {
      const clickable = IOS_INTERACTIVE.test(type) && n.isEnabled !== false;
      if (!onlyInteractive || clickable || text) {
        const bounds = [r.x, r.y, r.x + r.width, r.y + r.height] as [number, number, number, number];
        out.push({
          i: out.length,
          ...(text && { text: String(text) }),
          ...(desc && { desc: String(desc) }),
          ...(n.name && { id: String(n.name) }),
          cls: type,
          ...(clickable && { clickable }),
          bounds,
          center: [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)],
        });
      }
    }
    for (const c of n.children ?? []) walk(c);
  };
  walk(root);
  return out;
}
