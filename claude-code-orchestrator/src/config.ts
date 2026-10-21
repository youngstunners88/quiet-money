import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const PERMISSION_MODES = ['read_only', 'standard', 'full_access'] as const;
export type PermissionMode = (typeof PERMISSION_MODES)[number];

const MODE_RANK: Record<PermissionMode, number> = { read_only: 0, standard: 1, full_access: 2 };

/** True when `mode` is wider than `ceiling`. */
export function exceedsCeiling(mode: PermissionMode, ceiling: PermissionMode): boolean {
  return MODE_RANK[mode] > MODE_RANK[ceiling];
}

export function isPermissionMode(value: unknown): value is PermissionMode {
  return typeof value === 'string' && (PERMISSION_MODES as readonly string[]).includes(value);
}

export interface OrchestratorConfig {
  /** Claude Code CLI used for workers (CLAUDE_BIN). */
  claudeBin: string;
  /** Widest permission mode any worker may get (WORKER_PERMISSION_MODE). */
  permissionCeiling: PermissionMode;
  /** Maximum workers with a live process (WORKER_MAX_CONCURRENT). */
  maxConcurrent: number;
  /** Default time limit per worker task (WORKER_TIMEOUT_MS). */
  defaultTimeoutMs: number;
  /** Upper bound for a caller-supplied timeout (WORKER_MAX_TIMEOUT_MS). */
  maxTimeoutMs: number;
  /** Wait between SIGTERM and SIGKILL (WORKER_KILL_GRACE_MS). */
  killGraceMs: number;
  /** When set, project paths must sit inside one of these real paths (WORKER_ALLOWED_ROOTS). */
  allowedRoots: string[] | null;
  /** Directory holding orchestrator.jsonl (ORCHESTRATOR_LOG_DIR). */
  logDir: string;
  /** Finished workers kept for list_workers (WORKER_RETAIN_FINISHED). */
  retainFinished: number;
  /** Output lines kept per worker (WORKER_MAX_OUTPUT_LINES). */
  maxOutputLines: number;
  /** Pass --restricted to workers: ignores settings files and confines file tools to the project (WORKER_RESTRICTED). */
  restricted: boolean;
  /** Extra variable names passed to workers on top of the built-in allowlist (WORKER_ENV_PASS). */
  envPass: string[];
  /** Environment variables removed from the worker environment (defaults + WORKER_ENV_STRIP). */
  envStrip: string[];
  /** Problems found while reading the environment; reported on stderr at start-up. */
  warnings: string[];
}

/** Root of this package (dist/src/config.js -> package root). */
export const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');

/**
 * Variables that bind a nested Claude Code process to its parent's session.
 * Inheriting CLAUDE_CODE_SESSION_ID makes every worker reuse the parent's session id.
 */
export const DEFAULT_ENV_STRIP = ['CLAUDE_CODE_SESSION_ID', 'CLAUDE_CODE_INCLUDE_PARTIAL_MESSAGES'];

type Env = Record<string, string | undefined>;

function readInt(env: Env, name: string, fallback: number, min: number, warnings: string[]): number {
  const raw = env[name];
  if (raw === undefined || raw.trim() === '') return fallback;
  const value = Number(raw);
  if (!Number.isFinite(value) || !Number.isInteger(value) || value < min) {
    warnings.push(`${name}=${JSON.stringify(raw)} is not an integer >= ${min}; using ${fallback}`);
    return fallback;
  }
  return value;
}

function readBool(env: Env, name: string, fallback: boolean, warnings: string[]): boolean {
  const raw = env[name];
  if (raw === undefined || raw.trim() === '') return fallback;
  const v = raw.trim().toLowerCase();
  if (['1', 'true', 'yes', 'on'].includes(v)) return true;
  if (['0', 'false', 'no', 'off'].includes(v)) return false;
  warnings.push(`${name}=${JSON.stringify(raw)} is not a boolean; using ${fallback}`);
  return fallback;
}

export function loadConfig(env: Env = process.env): OrchestratorConfig {
  const warnings: string[] = [];

  let permissionCeiling: PermissionMode = 'read_only';
  const rawMode = env.WORKER_PERMISSION_MODE?.trim();
  if (rawMode) {
    if (isPermissionMode(rawMode)) permissionCeiling = rawMode;
    else warnings.push(`WORKER_PERMISSION_MODE=${JSON.stringify(rawMode)} is not one of ${PERMISSION_MODES.join(', ')}; using read_only`);
  }

  const defaultTimeoutMs = readInt(env, 'WORKER_TIMEOUT_MS', 600_000, 1, warnings);
  let maxTimeoutMs = readInt(env, 'WORKER_MAX_TIMEOUT_MS', 7_200_000, 1, warnings);
  if (maxTimeoutMs < defaultTimeoutMs) {
    warnings.push(`WORKER_MAX_TIMEOUT_MS is below WORKER_TIMEOUT_MS; raising it to ${defaultTimeoutMs}`);
    maxTimeoutMs = defaultTimeoutMs;
  }

  const roots = (env.WORKER_ALLOWED_ROOTS ?? '')
    .split(':')
    .map((r) => r.trim())
    .filter((r) => r.length > 0)
    .map((r) => path.resolve(r));

  const names = (raw: string | undefined): string[] =>
    (raw ?? '')
      .split(',')
      .map((n) => n.trim())
      .filter((n) => n.length > 0);
  const extraStrip = names(env.WORKER_ENV_STRIP);

  return {
    claudeBin: env.CLAUDE_BIN?.trim() || 'claude',
    permissionCeiling,
    maxConcurrent: readInt(env, 'WORKER_MAX_CONCURRENT', 3, 1, warnings),
    defaultTimeoutMs,
    maxTimeoutMs,
    killGraceMs: readInt(env, 'WORKER_KILL_GRACE_MS', 5_000, 0, warnings),
    allowedRoots: roots.length > 0 ? roots : null,
    logDir: path.resolve(env.ORCHESTRATOR_LOG_DIR?.trim() || path.join(PACKAGE_ROOT, 'logs')),
    retainFinished: readInt(env, 'WORKER_RETAIN_FINISHED', 50, 1, warnings),
    maxOutputLines: readInt(env, 'WORKER_MAX_OUTPUT_LINES', 5_000, 100, warnings),
    restricted: readBool(env, 'WORKER_RESTRICTED', true, warnings),
    envPass: [...new Set(names(env.WORKER_ENV_PASS))],
    envStrip: [...new Set([...DEFAULT_ENV_STRIP, ...extraStrip])],
    warnings,
  };
}
