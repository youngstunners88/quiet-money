import fs from 'node:fs';
import path from 'node:path';
import { redact, redactAndCap } from './redact.js';

export type LogEventName =
  | 'start'
  | 'start_refused'
  | 'prompt'
  | 'prompt_refused'
  | 'completion'
  | 'termination';

export interface LogEntry {
  event: LogEventName;
  worker_id: string | null;
  project_path?: string | null;
  permission_mode?: string | null;
  model?: string | null;
  label?: string | null;
  prompt?: string | null;
  status?: string | null;
  reason?: string | null;
  error_code?: string | null;
  exit_code?: number | null;
  cost_usd?: number | null;
  pid?: number | null;
}

export const LOG_PROMPT_MAX_CHARS = 2000;

/**
 * Append-only JSONL audit log. Every string is redacted and prompts are capped.
 * The worker environment is never passed here, so it can never be logged.
 */
export class JsonlLogger {
  readonly file: string;
  private warned = false;

  constructor(logDir: string, fileName = 'orchestrator.jsonl') {
    this.file = path.join(logDir, fileName);
  }

  log(entry: LogEntry): void {
    const record: Record<string, unknown> = { ts: new Date().toISOString() };
    for (const [key, value] of Object.entries(entry)) {
      if (value === undefined) continue;
      if (typeof value === 'string') {
        record[key] = key === 'prompt' ? redactAndCap(value, LOG_PROMPT_MAX_CHARS) : redact(value);
      } else {
        record[key] = value;
      }
    }
    try {
      fs.mkdirSync(path.dirname(this.file), { recursive: true });
      fs.appendFileSync(this.file, `${JSON.stringify(record)}\n`, { encoding: 'utf8', mode: 0o600 });
    } catch (err) {
      // Logging must never take the server down; report once on stderr (stdout carries MCP traffic).
      if (!this.warned) {
        this.warned = true;
        process.stderr.write(`claude-code-orchestrator: cannot write ${this.file}: ${(err as Error).message}\n`);
      }
    }
  }
}
