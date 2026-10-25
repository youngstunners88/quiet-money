#!/usr/bin/env node
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { configPath, loadConfig, ConfigSchema } from "./config.js";
import { realRunner } from "./exec.js";
import { createServer, DeviceHub, VERSION } from "./server.js";

const HELP = `open-device-mcp ${VERSION} — free, local MCP server for controlling your own phones

Usage:
  open-device-mcp serve [--dry-run] [--read-only]   Start the MCP server on stdio (what MCP clients run)
  open-device-mcp doctor                            Check adb, devices, iOS/WDA and config
  open-device-mcp list-devices                      Print connected devices as JSON
  open-device-mcp init                              Write a default config file
  open-device-mcp --version

Config: ${configPath()}  (override with OPEN_DEVICE_MCP_CONFIG)`;

async function main() {
  const [cmd = "serve", ...rest] = process.argv.slice(2);
  const overrides: Record<string, unknown> = {};
  if (rest.includes("--dry-run")) overrides.dryRun = true;
  if (rest.includes("--read-only")) overrides.mode = "read-only";

  switch (cmd) {
    case "serve": {
      const hub = new DeviceHub(loadConfig(undefined, overrides));
      const server = createServer(hub);
      await server.connect(new StdioServerTransport());
      console.error(`open-device-mcp ${VERSION} running on stdio (mode=${hub.cfg.mode}${hub.cfg.dryRun ? ", dry-run" : ""})`);
      break;
    }
    case "list-devices": {
      const hub = new DeviceHub(loadConfig(undefined, overrides));
      console.log(JSON.stringify(await hub.listDevices(), null, 2));
      break;
    }
    case "init": {
      const p = configPath();
      if (existsSync(p)) { console.log(`Config already exists at ${p}`); break; }
      mkdirSync(dirname(p), { recursive: true });
      writeFileSync(p, JSON.stringify(ConfigSchema.parse({}), null, 2));
      console.log(`Wrote default config to ${p}`);
      break;
    }
    case "doctor":
      await doctor();
      break;
    case "--version":
    case "-v":
      console.log(VERSION);
      break;
    default:
      console.log(HELP);
  }
}

async function doctor() {
  const ok = (m: string) => console.log(`  [ok]   ${m}`);
  const bad = (m: string, fix: string) => console.log(`  [fix]  ${m}\n         -> ${fix}`);
  console.log(`open-device-mcp doctor (v${VERSION})\n`);

  const major = +process.versions.node.split(".")[0];
  major >= 20 ? ok(`Node ${process.versions.node}`) : bad(`Node ${process.versions.node}`, "Install Node.js 20 or newer from nodejs.org");

  let cfg;
  try {
    cfg = loadConfig();
    ok(`Config ${existsSync(configPath()) ? configPath() : "(defaults; run 'open-device-mcp init' to customise)"}  mode=${cfg.mode}`);
  } catch (e) {
    bad(`Config invalid: ${(e as Error).message}`, `Fix or delete ${configPath()}`);
    return;
  }

  try {
    const v = await realRunner(cfg.adbPath, ["version"], { timeoutMs: 10_000 });
    ok(v.stdout.toString().split("\n")[0]);
  } catch {
    bad("adb not found", "Install Android Platform Tools (free): https://developer.android.com/tools/releases/platform-tools and add it to PATH, or set adbPath in config.");
  }

  const hub = new DeviceHub(cfg);
  const { devices, errors } = await hub.listDevices();
  for (const e of errors) bad(e, "See messages above.");
  if (!devices.length) bad("No devices found", "Android: enable Developer options > USB debugging and plug in. iPhone: see docs/IOS.md.");
  for (const d of devices) {
    const label = `${d.platform} ${d.serial} ${d.model ?? ""} ${d.osVersion ?? ""} [${d.state}]`.replace(/\s+/g, " ");
    d.authorized && d.state === "device" ? ok(label) : bad(label, d.note ?? "Device is not ready.");
  }
  if (!cfg.iosWdaUrl) console.log("  [info] iOS control disabled (iosWdaUrl not set). See docs/IOS.md to enable.");
  console.log("\nAdd to your MCP client:\n" + JSON.stringify({ mcpServers: { "open-device": { command: "open-device-mcp", args: ["serve"] } } }, null, 2));
}

main().catch((e) => {
  console.error(e instanceof Error ? e.message : e);
  process.exit(1);
});
