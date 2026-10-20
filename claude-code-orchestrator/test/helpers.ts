import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadConfig, type OrchestratorConfig } from '../src/config.js';
import { JsonlLogger } from '../src/logger.js';
import { WorkerManager } from '../src/process-manager.js';

/** dist/test/helpers.js -> package root */
export const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const FAKE_CLAUDE = path.join(PACKAGE_ROOT, 'test', 'fixtures', 'fake-claude.mjs');
fs.chmodSync(FAKE_CLAUDE, 0o755);

export function tempDir(prefix: string): string {
  return fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), `cco-${prefix}-`)));
}

export interface Harness {
  manager: WorkerManager;
  config: OrchestratorConfig;
  logFile: string;
  projectDir: string;
  readLog: () => Array<Record<string, unknown>>;
}

export function harness(
  overrides: Partial<OrchestratorConfig> = {},
  env: Record<string, string> = {},
  baseEnv: NodeJS.ProcessEnv = process.env,
): Harness {
  const logDir = tempDir('logs');
  const projectDir = tempDir('project');
  fs.writeFileSync(path.join(projectDir, 'README.md'), '# sample project\n');
  const config: OrchestratorConfig = {
    ...loadConfig({ CLAUDE_BIN: FAKE_CLAUDE, ORCHESTRATOR_LOG_DIR: logDir, WORKER_KILL_GRACE_MS: '200', ...env }),
    ...overrides,
  };
  const logger = new JsonlLogger(config.logDir);
  const manager = new WorkerManager(config, logger, baseEnv);
  return {
    manager,
    config,
    logFile: logger.file,
    projectDir,
    readLog: () =>
      fs.existsSync(logger.file)
        ? fs
            .readFileSync(logger.file, 'utf8')
            .split('\n')
            .filter((l) => l.trim() !== '')
            .map((l) => JSON.parse(l) as Record<string, unknown>)
        : [],
  };
}

/** Runs `fn`, expecting it to throw an OrchestratorError with `code`; returns the error. */
export async function expectCode(fn: () => unknown, code: string): Promise<{ code: string; workerId: string | null; suggestedFix: string; message: string }> {
  try {
    await fn();
  } catch (err) {
    const e = err as { code?: string; workerId?: string | null; suggestedFix?: string; message: string };
    if (e.code !== code) throw new Error(`expected ${code}, got ${e.code ?? 'no code'}: ${e.message}`);
    return { code: e.code, workerId: e.workerId ?? null, suggestedFix: e.suggestedFix ?? '', message: e.message };
  }
  throw new Error(`expected error ${code}, but nothing was thrown`);
}
