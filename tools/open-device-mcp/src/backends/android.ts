import type { Config } from "../config.js";
import { DeviceError, quoteForDisplay, type Runner } from "../exec.js";
import { pngSize, type ActionResult, type Backend, type DeviceInfo, type Key, type UiNode } from "./types.js";

const KEYCODES: Record<Key, number> = {
  BACK: 4, HOME: 3, RECENTS: 187, ENTER: 66, TAB: 61, DELETE: 67,
  POWER: 26, VOLUME_UP: 24, VOLUME_DOWN: 25, WAKEUP: 224,
};

const PKG_RE = /^[a-zA-Z][\w]*(\.[a-zA-Z_][\w]*)+$/;
const ACTIVITY_RE = /^[\w.$]+$/;

export class AndroidBackend implements Backend {
  platform = "android" as const;
  constructor(private cfg: Config, private run: Runner) {}

  owns(serial: string) {
    return !serial.startsWith("ios");
  }

  private async adb(serial: string | null, args: string[], opts: { risky?: boolean; timeoutMs?: number; allowFail?: boolean } = {}) {
    const full = serial ? ["-s", serial, ...args] : args;
    const display = quoteForDisplay(this.cfg.adbPath, full);
    if (opts.risky && this.cfg.dryRun) {
      return { command: display, exitCode: 0, stdout: Buffer.alloc(0), stderr: "", dryRun: true };
    }
    const r = await this.run(this.cfg.adbPath, full, { timeoutMs: opts.timeoutMs ?? this.cfg.commandTimeoutMs });
    if (r.exitCode !== 0 && !opts.allowFail) {
      throw new DeviceError("ADB_FAILED", `adb exited with code ${r.exitCode}.`, suggestFromStderr(r.stderr), r.stderr.trim());
    }
    const s = r.stderr.trim();
    if (/device unauthorized|device offline|device '.*' not found|no devices\/emulators found/i.test(s)) {
      throw new DeviceError("DEVICE_UNAVAILABLE", s, suggestFromStderr(s), s);
    }
    return { ...r, command: display, dryRun: false };
  }

  private result(r: { command: string; exitCode: number; stdout: Buffer; stderr: string; dryRun?: boolean }, extra: Partial<ActionResult> = {}): ActionResult {
    const warnings = [...(extra.warnings ?? [])];
    if (r.dryRun) warnings.push("dry-run: command was not executed");
    const out = r.stdout.toString();
    // `adb shell` returns 0 even when the on-device command fails; surface common error text.
    if (/^(Error|Exception|Failure|java\.lang\.)/m.test(out)) warnings.push("device reported an error in stdout");
    return { command: r.command, exitCode: r.exitCode, stdout: out, stderr: r.stderr, ...extra, warnings };
  }

  async listDevices(): Promise<DeviceInfo[]> {
    const r = await this.adb(null, ["devices", "-l"]);
    const devices: DeviceInfo[] = [];
    for (const line of r.stdout.toString().split(/\r?\n/).slice(1)) {
      const m = line.trim().match(/^(\S+)\s+(\S+)(.*)$/);
      if (!m) continue;
      const [, serial, state, rest] = m;
      const model = rest.match(/model:(\S+)/)?.[1]?.replace(/_/g, " ");
      const transport = serial.startsWith("emulator-") ? "emulator" : /:\d+$|_adb-tls-connect/.test(serial) ? "wifi" : "usb";
      const info: DeviceInfo = { serial, platform: "android", state, authorized: state === "device", model, transport };
      if (state === "unauthorized") info.note = "Unlock the phone and tap 'Allow' on the USB debugging prompt.";
      if (state === "device") {
        try {
          const v = await this.adb(serial, ["shell", "getprop", "ro.build.version.release"], { timeoutMs: 5000, allowFail: true });
          info.osVersion = "Android " + v.stdout.toString().trim();
        } catch { /* best effort */ }
      }
      devices.push(info);
    }
    return devices;
  }

  async screenshot(serial: string) {
    const r = await this.adb(serial, ["exec-out", "screencap", "-p"], { timeoutMs: 20_000 });
    const size = pngSize(r.stdout);
    if (!size) throw new DeviceError("SCREENSHOT_FAILED", "Device did not return a PNG image.", "Make sure the screen is on and the device is unlocked. Some secure apps block screenshots.", r.stderr);
    return { command: r.command, exitCode: 0, image: r.stdout, data: { ...size, coordinateSpace: "pixels" } };
  }

  async uiTree(serial: string, maxNodes: number, onlyInteractive: boolean): Promise<ActionResult> {
    const remote = "/sdcard/.open-device-mcp-ui.xml";
    await this.adb(serial, ["shell", "uiautomator", "dump", remote], { timeoutMs: 20_000 });
    const r = await this.adb(serial, ["exec-out", "cat", remote]);
    const xml = r.stdout.toString();
    if (!xml.includes("<hierarchy")) {
      throw new DeviceError("UI_DUMP_FAILED", "uiautomator did not produce a hierarchy.", "The screen may be animating or showing secure content. Wait a second and retry.", xml.slice(0, 500));
    }
    const all = parseUiXml(xml, onlyInteractive);
    const nodes = all.slice(0, maxNodes);
    const warnings = all.length > maxNodes ? [`truncated: ${all.length} nodes, returned ${maxNodes}`] : [];
    return { command: r.command, exitCode: 0, data: { nodeCount: all.length, nodes }, warnings };
  }

  async tap(serial: string, x: number, y: number, durationMs?: number) {
    const args = durationMs && durationMs > 0
      ? ["shell", "input", "swipe", `${x}`, `${y}`, `${x}`, `${y}`, `${Math.round(durationMs)}`]
      : ["shell", "input", "tap", `${x}`, `${y}`];
    return this.result(await this.adb(serial, args));
  }

  async swipe(serial: string, x1: number, y1: number, x2: number, y2: number, durationMs: number) {
    return this.result(await this.adb(serial, ["shell", "input", "swipe", `${x1}`, `${y1}`, `${x2}`, `${y2}`, `${Math.round(durationMs)}`]));
  }

  async typeText(serial: string, text: string) {
    const warnings: string[] = [];
    if (/[^\x20-\x7e]/.test(text)) warnings.push("non-ASCII characters are not supported by 'adb shell input text' and may be dropped; install an ADB keyboard IME for Unicode input");
    // adb joins shell args into one string that the device's sh parses, so single-quote it for the device.
    const escaped = text.replace(/%/g, "\\%").replace(/ /g, "%s").replace(/'/g, `'\\''`);
    return this.result(await this.adb(serial, ["shell", `input text '${escaped}'`]), { warnings });
  }

  async pressKey(serial: string, key: Key) {
    return this.result(await this.adb(serial, ["shell", "input", "keyevent", `${KEYCODES[key]}`]));
  }

  async launchApp(serial: string, appId: string, activity?: string) {
    if (!PKG_RE.test(appId)) throw new DeviceError("INVALID_ARGUMENT", `'${appId}' is not a valid Android package name.`);
    if (activity) {
      if (!ACTIVITY_RE.test(activity)) throw new DeviceError("INVALID_ARGUMENT", `'${activity}' is not a valid activity name.`);
      return this.result(await this.adb(serial, ["shell", "am", "start", "-W", "-n", `${appId}/${activity}`]));
    }
    const r = await this.adb(serial, ["shell", "monkey", "-p", appId, "-c", "android.intent.category.LAUNCHER", "1"]);
    if (/No activities found/i.test(r.stdout.toString())) {
      throw new DeviceError("APP_NOT_FOUND", `No launchable activity for ${appId}.`, "Check the package name with list_apps.");
    }
    return this.result(r);
  }

  async openUrl(serial: string, url: string) {
    if (!/^[a-z][a-z0-9+.-]*:[^\s'"]+$/i.test(url)) throw new DeviceError("INVALID_ARGUMENT", "URL contains unsupported characters.");
    return this.result(await this.adb(serial, ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", `'${url}'`]));
  }

  async currentApp(serial: string) {
    const r = await this.adb(serial, ["shell", "dumpsys", "window"]);
    const out = r.stdout.toString();
    const m = out.match(/mCurrentFocus=Window\{\S+ \S+ ([\w.]+)\/([\w.$]+)\}/) ?? out.match(/mFocusedApp=.*? ([\w.]+)\/([\w.$]+)/);
    return { command: r.command, exitCode: 0, data: m ? { package: m[1], activity: m[2] } : { package: null } };
  }

  async listApps(serial: string, thirdPartyOnly: boolean) {
    const r = await this.adb(serial, ["shell", "pm", "list", "packages", ...(thirdPartyOnly ? ["-3"] : [])]);
    const apps = r.stdout.toString().split(/\r?\n/).map((l) => l.replace(/^package:/, "").trim()).filter(Boolean).sort();
    return { command: r.command, exitCode: 0, data: { count: apps.length, apps } };
  }

  async installApp(serial: string, path: string, allowDowngrade: boolean) {
    const r = await this.adb(serial, ["install", "-r", ...(allowDowngrade ? ["-d"] : []), path], { risky: true, timeoutMs: 180_000 });
    if (!r.dryRun && !/Success/.test(r.stdout.toString())) {
      throw new DeviceError("INSTALL_FAILED", r.stdout.toString().trim() || "Install failed.", "Check the APK is valid and signed; use allowDowngrade for older versions.", r.stderr);
    }
    return this.result(r);
  }

  async uninstallApp(serial: string, appId: string, keepData: boolean) {
    if (!PKG_RE.test(appId)) throw new DeviceError("INVALID_ARGUMENT", `'${appId}' is not a valid Android package name.`);
    return this.result(await this.adb(serial, ["uninstall", ...(keepData ? ["-k"] : []), appId], { risky: true }));
  }

  async pushFile(serial: string, local: string, remote: string) {
    return this.result(await this.adb(serial, ["push", local, remote], { risky: true, timeoutMs: 300_000 }));
  }

  async pullFile(serial: string, remote: string, local: string) {
    return this.result(await this.adb(serial, ["pull", remote, local], { risky: true, timeoutMs: 300_000 }), { artifacts: [local] });
  }

  async logs(serial: string, opts: { tag?: string; level: string; maxLines: number }) {
    const filter = opts.tag ? [`${opts.tag}:${opts.level}`, "*:S"] : [`*:${opts.level}`];
    if (opts.tag && !/^[\w.-]+$/.test(opts.tag)) throw new DeviceError("INVALID_ARGUMENT", "Log tag may contain only letters, digits, '.', '_' and '-'.");
    const r = await this.adb(serial, ["logcat", "-d", "-v", "time", "-t", `${opts.maxLines}`, ...filter]);
    return this.result(r);
  }

  async shell(serial: string, command: string) {
    return this.result(await this.adb(serial, ["shell", command], { risky: true }));
  }
}

function decode(s: string) {
  return s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'").replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n)).replace(/&amp;/g, "&");
}

export function parseUiXml(xml: string, onlyInteractive = true): UiNode[] {
  const nodes: UiNode[] = [];
  const nodeRe = /<node\b([^>]*?)\/?>/g;
  let m: RegExpExecArray | null;
  while ((m = nodeRe.exec(xml))) {
    const attrs: Record<string, string> = {};
    for (const a of m[1].matchAll(/([\w-]+)="([^"]*)"/g)) attrs[a[1]] = decode(a[2]);
    const b = attrs.bounds?.match(/\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]/);
    if (!b) continue;
    const bounds = [+b[1], +b[2], +b[3], +b[4]] as [number, number, number, number];
    if (bounds[2] <= bounds[0] || bounds[3] <= bounds[1]) continue;
    const clickable = attrs.clickable === "true" || attrs["long-clickable"] === "true" || attrs.checkable === "true" || attrs.scrollable === "true";
    const text = attrs.text || undefined;
    const desc = attrs["content-desc"] || undefined;
    const id = attrs["resource-id"] || undefined;
    if (onlyInteractive && !clickable && !text && !desc) continue;
    nodes.push({
      i: nodes.length,
      ...(text && { text }),
      ...(desc && { desc }),
      ...(id && { id }),
      cls: attrs.class?.split(".").pop(),
      ...(clickable && { clickable }),
      bounds,
      center: [Math.round((bounds[0] + bounds[2]) / 2), Math.round((bounds[1] + bounds[3]) / 2)],
    });
  }
  return nodes;
}

function suggestFromStderr(s: string): string {
  if (/unauthorized/i.test(s)) return "Unlock the phone and accept the 'Allow USB debugging?' prompt.";
  if (/offline/i.test(s)) return "Reconnect the cable or run 'adb kill-server && adb start-server'.";
  if (/not found|no devices/i.test(s)) return "Run list_devices; the phone may have disconnected.";
  if (/INSTALL_FAILED_VERSION_DOWNGRADE/.test(s)) return "Retry with allowDowngrade: true.";
  return "Check the device is connected, unlocked, and USB debugging is enabled.";
}
