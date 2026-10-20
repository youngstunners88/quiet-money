#!/usr/bin/env node
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import fs from 'node:fs';
import path from 'node:path';
import { loadConfig, PACKAGE_ROOT } from './config.js';
import { JsonlLogger } from './logger.js';
import { isMainModule } from './main-module.js';
import { WorkerManager } from './process-manager.js';
import { createServer, SERVER_NAME } from './tools.js';

/** Set to 1 by a parent that handles Ctrl-C itself (see OrchestratorClient.connect). */
export const PARENT_HANDLES_SIGINT_ENV = 'ORCHESTRATOR_PARENT_HANDLES_SIGINT';

/** Starts the MCP server on stdio. stdout carries protocol messages only; diagnostics go to stderr. */
export async function main(): Promise<void> {
  loadDotEnv();
  const config = loadConfig();
  for (const warning of config.warnings) process.stderr.write(`${SERVER_NAME}: ${warning}\n`);

  const manager = new WorkerManager(config, new JsonlLogger(config.logDir));
  const server = createServer(manager);

  let closing = false;
  const shutdown = async (): Promise<void> => {
    if (closing) return;
    closing = true;
    await manager.shutdown('server_shutdown');
    await server.close().catch(() => {});
    process.exit(0);
  };
  // A terminal's Ctrl-C reaches every process of the foreground group. When the parent (run-plan) handles
  // it, the parent stops the workers and collects their output first, then closes stdin, which ends us.
  if (process.env[PARENT_HANDLES_SIGINT_ENV] === '1') process.on('SIGINT', () => {});
  else process.on('SIGINT', () => void shutdown());
  process.on('SIGTERM', () => void shutdown());
  process.stdin.on('end', () => void shutdown());
  server.onclose = () => void shutdown();

  await server.connect(new StdioServerTransport());
  process.stderr.write(
    `${SERVER_NAME}: ready (ceiling ${config.permissionCeiling}, max ${config.maxConcurrent} workers, ` +
      `timeout ${config.defaultTimeoutMs} ms, log ${config.logDir})\n`,
  );
}

/** Reads <package root>/.env when present (Node 20.12+); variables already set in the environment win. */
function loadDotEnv(): void {
  const file = path.join(PACKAGE_ROOT, '.env');
  if (!fs.existsSync(file)) return;
  const loader = (process as { loadEnvFile?: (path: string) => void }).loadEnvFile;
  if (typeof loader !== 'function') {
    process.stderr.write(`${SERVER_NAME}: ${file} ignored (needs Node 20.12+); pass settings as environment variables\n`);
    return;
  }
  loader.call(process, file);
}

export function runCli(): void {
  main().catch((err: unknown) => {
    process.stderr.write(`${SERVER_NAME}: fatal: ${err instanceof Error ? err.message : String(err)}\n`);
    process.exit(1);
  });
}

if (isMainModule(import.meta.url)) runCli();
