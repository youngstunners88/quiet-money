#!/usr/bin/env node
// A tiny stand-in for the real adb binary so the full MCP server can be tested without a phone.
import { readFileSync, appendFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const here = dirname(fileURLToPath(import.meta.url));
let args = process.argv.slice(2);
if (process.env.FAKE_ADB_LOG) appendFileSync(process.env.FAKE_ADB_LOG, JSON.stringify(args) + "\n");
if (args[0] === "-s") args = args.slice(2);
const cmd = args.join(" ");
const out = (s) => process.stdout.write(s);
if (cmd === "version") out("Android Debug Bridge version 1.0.41\n");
else if (cmd === "devices -l") out("List of devices attached\nFAKE123          device usb:1-1 product:panther model:Pixel_7 device:panther transport_id:1\n\n");
else if (cmd === "shell getprop ro.build.version.release") out("14\n");
else if (cmd === "exec-out screencap -p") process.stdout.write(readFileSync(join(here, "fixtures/screen.png")));
else if (cmd.startsWith("shell uiautomator dump")) out("UI hierchary dumped to: /sdcard/.open-device-mcp-ui.xml\n");
else if (cmd.startsWith("exec-out cat")) out(readFileSync(join(here, "fixtures/ui.xml")));
else if (cmd.startsWith("shell input")) out("");
else if (cmd.startsWith("shell dumpsys window")) out("  mCurrentFocus=Window{abc u0 com.android.settings/com.android.settings.Settings}\n");
else if (cmd.startsWith("shell monkey")) out("Events injected: 1\n");
else if (cmd.startsWith("shell pm list packages")) out("package:com.example.b\npackage:com.example.a\n");
else if (cmd.startsWith("install")) out("Performing Streamed Install\nSuccess\n");
else if (cmd.startsWith("shell wm size")) out("Physical size: 1080x2400\n");
else { process.stderr.write(`fake-adb: unknown command ${cmd}\n`); process.exit(1); }
