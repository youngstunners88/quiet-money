import { describe, it, expect, beforeEach } from "vitest";
import { mkdtempSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { loadConfig } from "../src/config.js";
import { createServer, DeviceHub } from "../src/server.js";
import { parseUiXml } from "../src/backends/android.js";
import { flattenWda } from "../src/backends/ios.js";
import { Safety } from "../src/safety.js";

const here = dirname(fileURLToPath(import.meta.url));
const FAKE_ADB = join(here, "fake-adb.mjs");

function setup(overrides: Record<string, unknown> = {}) {
  const dir = mkdtempSync(join(tmpdir(), "odm-"));
  const log = join(dir, "adb-calls.jsonl");
  process.env.FAKE_ADB_LOG = log;
  const cfg = loadConfig(join(dir, "missing.json"), {
    adbPath: FAKE_ADB,
    artifactsDir: join(dir, "artifacts"),
    pathAllowlist: [dir],
    auditLog: join(dir, "audit.jsonl"),
    ...overrides,
  } as any);
  return { dir, log, cfg, hub: new DeviceHub(cfg) };
}

async function connect(hub: DeviceHub) {
  const [a, b] = InMemoryTransport.createLinkedPair();
  await createServer(hub).connect(a);
  const client = new Client({ name: "test", version: "0" });
  await client.connect(b);
  return client;
}

const body = (r: any) => JSON.parse(r.content[0].text);
const calls = (log: string) => (existsSync(log) ? readFileSync(log, "utf8").trim().split("\n").map((l) => JSON.parse(l)) : []);

describe("MCP tools against a simulated Android phone", () => {
  let ctx: ReturnType<typeof setup>;
  let client: Client;
  beforeEach(async () => {
    ctx = setup();
    client = await connect(ctx.hub);
  });

  it("exposes the full tool surface", async () => {
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual([
      "adb_shell", "current_app", "get_ui_tree", "install_app", "launch_app", "list_apps", "list_devices",
      "open_url", "press_key", "pull_file", "push_file", "read_logs", "screenshot", "select_device", "swipe", "tap", "type_text", "uninstall_app",
    ]);
  });

  it("lists devices with model and OS version", async () => {
    const r = body(await client.callTool({ name: "list_devices", arguments: {} }));
    expect(r.ok).toBe(true);
    expect(r.data.devices[0]).toMatchObject({ serial: "FAKE123", platform: "android", authorized: true, model: "Pixel 7", osVersion: "Android 14", transport: "usb" });
  });

  it("runs the first end-to-end slice: select -> screenshot -> ui tree -> tap", async () => {
    expect(body(await client.callTool({ name: "select_device", arguments: { serial: "FAKE123" } })).ok).toBe(true);

    const shot: any = await client.callTool({ name: "screenshot", arguments: {} });
    const s = body(shot);
    expect(s.data).toMatchObject({ width: 108, height: 240 });
    expect(existsSync(s.artifacts[0])).toBe(true);
    expect(shot.content[1]).toMatchObject({ type: "image", mimeType: "image/png" });

    const ui = body(await client.callTool({ name: "get_ui_tree", arguments: {} }));
    expect(ui.data.nodes.map((n: any) => n.text ?? n.desc)).toEqual(["Search settings", "Network & internet", "Navigate up"]);

    const [cx, cy] = ui.data.nodes[0].center;
    const tap = body(await client.callTool({ name: "tap", arguments: { x: cx, y: cy } }));
    expect(tap.ok).toBe(true);
    expect(calls(ctx.log).at(-1)).toEqual(["-s", "FAKE123", "shell", "input", "tap", "540", "250"]);
  });

  it("auto-selects the only connected device", async () => {
    const r = body(await client.callTool({ name: "press_key", arguments: { key: "HOME" } }));
    expect(r.deviceSerial).toBe("FAKE123");
    expect(calls(ctx.log).at(-1)).toEqual(["-s", "FAKE123", "shell", "input", "keyevent", "3"]);
  });

  it("long-presses with a zero-distance swipe", async () => {
    await client.callTool({ name: "tap", arguments: { x: 10, y: 20, durationMs: 800 } });
    expect(calls(ctx.log).at(-1)).toEqual(["-s", "FAKE123", "shell", "input", "swipe", "10", "20", "10", "20", "800"]);
  });

  it("escapes typed text for the device shell", async () => {
    await client.callTool({ name: "type_text", arguments: { text: "it's 100% ok" } });
    expect(calls(ctx.log).at(-1)).toEqual(["-s", "FAKE123", "shell", `input text 'it'\\''s%s100\\%%sok'`]);
    const audit = readFileSync(join(ctx.dir, "audit.jsonl"), "utf8");
    expect(audit).not.toContain("100%"); // typed text is never written to the audit log
  });

  it("reports the foreground app", async () => {
    const r = body(await client.callTool({ name: "current_app", arguments: {} }));
    expect(r.data).toEqual({ package: "com.android.settings", activity: "com.android.settings.Settings" });
  });

  it("rejects invalid package names before touching adb", async () => {
    const r: any = await client.callTool({ name: "launch_app", arguments: { appId: "com.x; reboot" } });
    expect(r.isError).toBe(true);
    expect(body(r).error.code).toBe("INVALID_ARGUMENT");
  });

  it("requires confirmation for installs, then installs from an allowed folder", async () => {
    const apk = join(ctx.dir, "app.apk");
    writeFileSync(apk, "x");
    const denied: any = await client.callTool({ name: "install_app", arguments: { apkPath: apk } });
    expect(body(denied).error.code).toBe("CONFIRMATION_REQUIRED");
    const ok = body(await client.callTool({ name: "install_app", arguments: { apkPath: apk, confirmed: true } }));
    expect(ok.ok).toBe(true);
  });

  it("refuses local paths outside the allowlist", async () => {
    const r: any = await client.callTool({ name: "install_app", arguments: { apkPath: "/etc/passwd.apk", confirmed: true } });
    expect(body(r).error.code).toBe("PATH_NOT_ALLOWED");
  });

  it("blocks dangerous shell commands and allows safe ones", async () => {
    for (const command of ["rm -rf /sdcard", "reboot", "getprop | sh", "su -c id"]) {
      const r: any = await client.callTool({ name: "adb_shell", arguments: { command } });
      expect(r.isError, command).toBe(true);
    }
    const ok = body(await client.callTool({ name: "adb_shell", arguments: { command: "wm size" } }));
    expect(ok.stdoutPreview).toContain("1080x2400");
  });
});

describe("modes", () => {
  it("read-only mode blocks actions but allows observation", async () => {
    const { hub } = setup({ mode: "read-only" });
    const client = await connect(hub);
    expect(body(await client.callTool({ name: "list_devices", arguments: {} })).ok).toBe(true);
    const r: any = await client.callTool({ name: "tap", arguments: { x: 1, y: 1 } });
    expect(body(r).error.code).toBe("READ_ONLY");
  });

  it("dry-run returns the command without running it", async () => {
    const ctx = setup({ dryRun: true });
    const client = await connect(ctx.hub);
    const apk = join(ctx.dir, "a.apk");
    writeFileSync(apk, "x");
    const r = body(await client.callTool({ name: "install_app", arguments: { apkPath: apk, confirmed: true } }));
    expect(r.command).toContain("install -r");
    expect(r.warnings).toContain("dry-run: command was not executed");
    expect(calls(ctx.log).some((c: string[]) => c.includes("install"))).toBe(false);
  });

  it("device allowlist blocks other phones", async () => {
    const { hub } = setup({ deviceAllowlist: ["OTHER"] });
    const client = await connect(hub);
    const r: any = await client.callTool({ name: "tap", arguments: { deviceSerial: "FAKE123", x: 1, y: 1 } });
    expect(body(r).error.code).toBe("DEVICE_NOT_ALLOWED");
  });
});

describe("parsers", () => {
  it("parses uiautomator XML, skipping empty/zero-size nodes", () => {
    const nodes = parseUiXml(readFileSync(join(here, "fixtures/ui.xml"), "utf8"));
    expect(nodes).toHaveLength(3);
    expect(nodes[2]).toMatchObject({ desc: "Navigate up", clickable: true, center: [70, 130] });
  });

  it("flattens a WebDriverAgent source tree", () => {
    const tree = { type: "XCUIElementTypeApplication", rect: { x: 0, y: 0, width: 390, height: 844 }, children: [
      { type: "XCUIElementTypeButton", label: "Settings", name: "settings", isEnabled: true, rect: { x: 10, y: 20, width: 100, height: 40 } },
      { type: "XCUIElementTypeOther", rect: { x: 0, y: 0, width: 10, height: 10 } },
    ] };
    const nodes = flattenWda(tree);
    expect(nodes).toEqual([{ i: 0, text: "Settings", id: "settings", cls: "Button", clickable: true, bounds: [10, 20, 110, 60], center: [60, 40] }]);
  });

  it("shell allowlist rejects anything not explicitly allowed", () => {
    const s = new Safety(loadConfig("/nonexistent.json"));
    expect(() => s.checkShell("pm list packages -3")).not.toThrow();
    expect(() => s.checkShell("pm uninstall com.x")).toThrow();
  });
});

describe("iOS via a mocked WebDriverAgent", () => {
  it("lists, screenshots and taps in points", async () => {
    const png = readFileSync(join(here, "fixtures/screen.png")).toString("base64");
    const seen: string[] = [];
    const fakeFetch = (async (url: string, init: any) => {
      const path = url.replace("http://wda", "");
      seen.push(`${init.method} ${path}`);
      const value =
        path === "/status" ? { ready: true, os: { version: "18.1" }, device: "iphone" } :
        path === "/screenshot" ? png :
        path === "/wda/screen" ? { scale: 3 } :
        path === "/session" ? { sessionId: "S1" } : null;
      return new Response(JSON.stringify(path === "/session" ? { sessionId: "S1", value } : { value }), { status: 200 });
    }) as any;
    const cfg = loadConfig("/nonexistent.json", { iosWdaUrl: "http://wda", adbPath: FAKE_ADB, ideviceIdPath: "/nonexistent", auditLog: "" } as any);
    const hub = new DeviceHub(cfg, undefined, fakeFetch);
    const client = await connect(hub);
    const list = body(await client.callTool({ name: "list_devices", arguments: {} }));
    expect(list.data.devices.map((d: any) => d.serial)).toEqual(["FAKE123", "ios-wda"]);
    const shot = body(await client.callTool({ name: "screenshot", arguments: { deviceSerial: "ios-wda", saveToDisk: false } }));
    expect(shot.data).toMatchObject({ scale: 3, coordinateSpace: "points", pointsWidth: 36 });
    expect(body(await client.callTool({ name: "tap", arguments: { deviceSerial: "ios-wda", x: 5, y: 5 } })).ok).toBe(true);
    expect(seen).toContain("POST /session/S1/actions");
    const back: any = await client.callTool({ name: "press_key", arguments: { deviceSerial: "ios-wda", key: "BACK" } });
    expect(body(back).error.code).toBe("UNSUPPORTED");
  });
});

describe("real stdio process", () => {
  it("serves MCP over stdio using the built CLI", async () => {
    const dir = mkdtempSync(join(tmpdir(), "odm-stdio-"));
    const cfgFile = join(dir, "config.json");
    writeFileSync(cfgFile, JSON.stringify({ adbPath: FAKE_ADB, auditLog: "", artifactsDir: dir }));
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [join(here, "../dist/cli.js"), "serve"],
      env: { ...process.env, OPEN_DEVICE_MCP_CONFIG: cfgFile } as Record<string, string>,
    });
    const client = new Client({ name: "stdio-test", version: "0" });
    await client.connect(transport);
    const r = body(await client.callTool({ name: "list_devices", arguments: {} }));
    expect(r.data.devices[0].serial).toBe("FAKE123");
    await client.close();
  }, 20_000);
});
