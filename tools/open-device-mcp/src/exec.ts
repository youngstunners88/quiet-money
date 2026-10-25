import { spawn } from "node:child_process";

export interface ExecResult {
  command: string;
  exitCode: number;
  stdout: Buffer;
  stderr: string;
  durationMs: number;
}

export interface ExecOptions {
  timeoutMs?: number;
  input?: string;
  maxBytes?: number;
}

/** A runner executes a binary with args. Injectable so tests can mock adb/WDA. */
export type Runner = (bin: string, args: string[], opts?: ExecOptions) => Promise<ExecResult>;

export function quoteForDisplay(bin: string, args: string[]): string {
  return [bin, ...args].map((a) => (/^[\w@%+=:,./-]+$/.test(a) ? a : `'${a.replace(/'/g, `'\\''`)}'`)).join(" ");
}

export const realRunner: Runner = (bin, args, opts = {}) =>
  new Promise((resolve, reject) => {
    const started = Date.now();
    const timeoutMs = opts.timeoutMs ?? 30_000;
    const maxBytes = opts.maxBytes ?? 64 * 1024 * 1024;
    const child = spawn(bin, args, { stdio: ["pipe", "pipe", "pipe"], windowsHide: true });
    const out: Buffer[] = [];
    let outLen = 0;
    let err = "";
    let killed = false;
    const timer = setTimeout(() => {
      killed = true;
      child.kill("SIGKILL");
    }, timeoutMs);
    child.stdout.on("data", (d: Buffer) => {
      outLen += d.length;
      if (outLen <= maxBytes) out.push(d);
    });
    child.stderr.on("data", (d: Buffer) => {
      if (err.length < 64_000) err += d.toString();
    });
    child.on("error", (e: NodeJS.ErrnoException) => {
      clearTimeout(timer);
      if (e.code === "ENOENT") {
        reject(new DeviceError("BINARY_NOT_FOUND", `'${bin}' was not found on PATH.`, `Install it and make sure '${bin}' is on your PATH, or set its path in the config file.`));
      } else reject(e);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (killed) {
        reject(new DeviceError("TIMEOUT", `Command timed out after ${timeoutMs} ms: ${quoteForDisplay(bin, args)}`, "Check the device is connected and unlocked, or raise timeoutMs."));
        return;
      }
      resolve({ command: quoteForDisplay(bin, args), exitCode: code ?? -1, stdout: Buffer.concat(out), stderr: err, durationMs: Date.now() - started });
    });
    if (opts.input !== undefined) child.stdin.end(opts.input);
    else child.stdin.end();
  });

export class DeviceError extends Error {
  constructor(public code: string, message: string, public suggestion?: string, public stderr?: string) {
    super(message);
  }
}
