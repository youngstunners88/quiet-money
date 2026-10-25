import { appendFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, resolve, sep } from "node:path";
import type { Config } from "./config.js";
import { DeviceError } from "./exec.js";

export type Risk = "read" | "act" | "destructive";

export class Safety {
  constructor(private cfg: Config) {}

  checkDevice(serial: string) {
    if (this.cfg.deviceAllowlist.length && !this.cfg.deviceAllowlist.includes(serial)) {
      throw new DeviceError("DEVICE_NOT_ALLOWED", `Device ${serial} is not in deviceAllowlist.`, "Add it to deviceAllowlist in your config file.");
    }
  }

  checkRisk(tool: string, risk: Risk, confirmed: boolean | undefined) {
    if (this.cfg.mode === "read-only" && risk !== "read") {
      throw new DeviceError("READ_ONLY", `'${tool}' is blocked because the server is in read-only mode.`, "Set mode to 'confirm-destructive' or 'open' in config.");
    }
    if (this.cfg.mode === "confirm-destructive" && risk === "destructive" && confirmed !== true) {
      throw new DeviceError("CONFIRMATION_REQUIRED", `'${tool}' changes the device or files. Ask the user, then call again with confirmed: true.`, "Get explicit user approval, then retry with confirmed: true.");
    }
  }

  /** Ensures a local path is inside one of the allowed directories. */
  checkLocalPath(p: string): string {
    const abs = resolve(p);
    const ok = this.cfg.pathAllowlist.some((root) => abs === root || abs.startsWith(root.endsWith(sep) ? root : root + sep));
    if (!ok) {
      throw new DeviceError("PATH_NOT_ALLOWED", `Local path ${abs} is outside pathAllowlist.`, `Use a path under: ${this.cfg.pathAllowlist.join(", ")}`);
    }
    return abs;
  }

  /** Device-side paths: block system partitions; allow /sdcard, /storage, /data/local/tmp. */
  checkDevicePath(p: string): string {
    if (p.includes("..")) throw new DeviceError("PATH_NOT_ALLOWED", "Device paths may not contain '..'.");
    if (!/^(\/sdcard|\/storage|\/data\/local\/tmp)(\/|$)/.test(p)) {
      throw new DeviceError("PATH_NOT_ALLOWED", `Device path ${p} is not allowed.`, "Use a path under /sdcard, /storage, or /data/local/tmp.");
    }
    return p;
  }

  checkShell(command: string) {
    const c = command.trim();
    for (const d of this.cfg.shellDeny) if (new RegExp(d).test(c)) throw new DeviceError("SHELL_DENIED", `Shell command blocked by deny rule /${d}/.`, "Use a dedicated tool instead, or adjust shellDeny in config.");
    if (!this.cfg.shellAllow.some((a) => new RegExp(a).test(c))) {
      throw new DeviceError("SHELL_NOT_ALLOWLISTED", "Shell command does not match any shellAllow pattern.", "Add a regex to shellAllow in config if you trust this command.");
    }
  }

  audit(entry: Record<string, unknown>) {
    if (!this.cfg.auditLog) return;
    try {
      mkdirSync(dirname(this.cfg.auditLog), { recursive: true });
      appendFileSync(this.cfg.auditLog, JSON.stringify({ ts: new Date().toISOString(), ...entry }) + "\n");
    } catch {
      /* audit must never break the tool call */
    }
  }

  static digest(s: string | Buffer): string {
    return createHash("sha256").update(s).digest("hex").slice(0, 16);
  }
}
