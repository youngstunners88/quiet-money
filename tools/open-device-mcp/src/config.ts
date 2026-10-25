import { readFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { z } from "zod";

export const ConfigSchema = z.object({
  /** Path to the adb binary. */
  adbPath: z.string().default("adb"),
  /** Base URL of a running WebDriverAgent for iOS control (e.g. http://127.0.0.1:8100). Empty disables iOS. */
  iosWdaUrl: z.string().default(""),
  /** Path to idevice_id (libimobiledevice) used to list iOS devices. Optional. */
  ideviceIdPath: z.string().default("idevice_id"),
  /** "confirm-destructive" requires confirmed:true for risky tools. "open" skips that. "read-only" blocks all actions. */
  mode: z.enum(["confirm-destructive", "open", "read-only"]).default("confirm-destructive"),
  /** If true, risky commands are returned but never executed. */
  dryRun: z.boolean().default(false),
  /** If non-empty, only these device serials/UDIDs may be used. */
  deviceAllowlist: z.array(z.string()).default([]),
  /** Local directories that push/pull/install/screenshot may read from or write to. */
  pathAllowlist: z.array(z.string()).default([join(homedir(), "open-device-mcp")]),
  /** Where screenshots and pulled files go by default. */
  artifactsDir: z.string().default(join(homedir(), "open-device-mcp", "artifacts")),
  /** Append-only JSONL audit log. Empty disables. */
  auditLog: z.string().default(join(homedir(), "open-device-mcp", "audit.jsonl")),
  /** Regexes. A shell command must match at least one allow pattern and no deny pattern. */
  shellAllow: z.array(z.string()).default([
    "^getprop( [\\w.]+)?$",
    "^dumpsys (battery|window|activity activities|display|meminfo [\\w.]+)$",
    "^pm list packages( -[3sfd])*$",
    "^wm (size|density)$",
    "^settings get (system|secure|global) [\\w.]+$",
    "^ls( -[la]+)? /sdcard(/[\\w./ -]*)?$",
    "^cat /sdcard/[\\w./-]+$",
    "^am start(-activity)? .+$",
    "^am force-stop [\\w.]+$",
    "^input .+$",
  ]),
  shellDeny: z.array(z.string()).default([
    "rm\\s+-[a-z]*r",
    "\\breboot\\b",
    "\\bfastboot\\b",
    "\\bflash",
    "\\bsu\\b",
    "\\bdd\\b",
    "\\bmkfs",
    "\\bformat\\b",
    "[;&|`$<>]",
  ]),
  commandTimeoutMs: z.number().int().positive().default(30_000),
  maxOutputChars: z.number().int().positive().default(8_000),
});

export type Config = z.infer<typeof ConfigSchema>;

export function configPath(): string {
  return process.env.OPEN_DEVICE_MCP_CONFIG ?? join(homedir(), "open-device-mcp", "config.json");
}

export function loadConfig(path = configPath(), overrides: Partial<Config> = {}): Config {
  let raw: unknown = {};
  if (existsSync(path)) {
    try {
      raw = JSON.parse(readFileSync(path, "utf8"));
    } catch (e) {
      throw new Error(`Config file ${path} is not valid JSON: ${(e as Error).message}`);
    }
  }
  const cfg = ConfigSchema.parse({ ...(raw as object), ...overrides });
  cfg.pathAllowlist = cfg.pathAllowlist.map((p) => resolve(p));
  cfg.artifactsDir = resolve(cfg.artifactsDir);
  return cfg;
}
