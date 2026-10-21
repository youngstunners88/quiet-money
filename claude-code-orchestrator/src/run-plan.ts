#!/usr/bin/env node
/**
 * Runs a plan of workers through ONE orchestrator server (workers live inside that server process):
 *   node dist/run-plan.js plan.json --out <dir> [--poll-seconds 15]
 * Exit code 0 only when every worker completed.
 */
import fs from 'node:fs';
import path from 'node:path';
import { z } from 'zod';
import { OrchestratorClient, type StartWorkerArgs } from './client.js';
import { PERMISSION_MODES } from './config.js';
import type { ToolErrorPayload } from './errors.js';
import { isMainModule } from './main-module.js';
import type { WorkerStatusView } from './process-manager.js';

const PlanEntrySchema = z.strictObject({
  label: z.string().min(1).max(80).optional(),
  project_path: z.string().min(1),
  prompt: z.string().min(1),
  permission_mode: z.enum(PERMISSION_MODES).optional(),
  confirm_write_access: z.boolean().optional(),
  allowed_tools: z.array(z.string().min(1)).optional(),
  model: z.string().min(1).optional(),
  timeout_minutes: z.number().positive().optional(),
});
const PlanSchema = z.strictObject({ workers: z.array(PlanEntrySchema).min(1) });

export type PlanEntry = z.infer<typeof PlanEntrySchema>;
export type Plan = z.infer<typeof PlanSchema>;

const TERMINAL = new Set(['completed', 'failed', 'terminated']);

interface Slot {
  index: number;
  entry: PlanEntry;
  name: string;
  workerId: string | null;
  status: string;
  last: WorkerStatusView | null;
  startError: ToolErrorPayload | null;
  logFile: string | null;
}

export interface CliOptions {
  planFile: string;
  outDir: string;
  pollSeconds: number;
}

const USAGE = 'usage: node dist/run-plan.js <plan.json> --out <dir> [--poll-seconds 15]';

export function parseArgs(argv: string[]): CliOptions {
  let planFile: string | null = null;
  let outDir: string | null = null;
  let pollSeconds = 15;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i] as string;
    if (arg === '--out') outDir = argv[++i] ?? null;
    else if (arg === '--poll-seconds') pollSeconds = Number(argv[++i]);
    else if (arg === '-h' || arg === '--help') throw new Error(USAGE);
    else if (!arg.startsWith('-') && planFile === null) planFile = arg;
    else throw new Error(`unexpected argument ${JSON.stringify(arg)}\n${USAGE}`);
  }
  if (!planFile) throw new Error(USAGE);
  if (!Number.isFinite(pollSeconds) || pollSeconds <= 0) throw new Error('--poll-seconds must be a positive number');
  const stamp = new Date().toISOString().replace(/[:.]/g, '-');
  return {
    planFile: path.resolve(planFile),
    outDir: path.resolve(outDir ?? path.join('orchestrator-runs', stamp)),
    pollSeconds,
  };
}

export function loadPlan(planFile: string): Plan {
  const plan = PlanSchema.parse(JSON.parse(fs.readFileSync(planFile, 'utf8')));
  // Relative project paths are read against the plan file, not the shell's current directory.
  const base = path.dirname(planFile);
  for (const entry of plan.workers) entry.project_path = path.resolve(base, entry.project_path);
  return plan;
}

function safeName(text: string): string {
  return text.replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 80) || 'worker';
}

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));
const say = (text: string): void => {
  process.stdout.write(`${text}\n`);
};

export async function runPlan(options: CliOptions): Promise<number> {
  const plan = loadPlan(options.planFile);
  fs.mkdirSync(options.outDir, { recursive: true });
  const startedAt = new Date().toISOString();

  // Ctrl-C reaches the server too (same process group); it leaves the stopping to us so no output is lost.
  const client = await OrchestratorClient.connect({ parentHandlesSigint: true });
  const slots: Slot[] = plan.workers.map((entry, index) => ({
    index,
    entry,
    name: safeName(entry.label ?? `worker-${index + 1}`),
    workerId: null,
    status: 'pending',
    last: null,
    startError: null,
    logFile: null,
  }));

  let interrupted = false;
  const onSignal = (): void => {
    interrupted = true;
  };
  process.on('SIGINT', onSignal);
  process.on('SIGTERM', onSignal);

  try {
    const listed = await client.listWorkers();
    say('list_workers:');
    say(JSON.stringify(listed.ok ? listed.data : listed.error, null, 2));
    const maxConcurrent = listed.ok ? listed.data.max_concurrent : 3;

    const isDone = (s: Slot): boolean => s.status === 'start_failed' || TERMINAL.has(s.status);

    // Each worker's log is written as soon as it finishes, so a later failure cannot lose finished output.
    const used = new Set<string>();
    const writeLog = async (s: Slot): Promise<void> => {
      if (!s.workerId || s.logFile) return;
      let base = s.name;
      if (used.has(base)) base = `${base}-${s.workerId}`;
      used.add(base);
      const [output, status] = await Promise.all([client.getWorkerOutput(s.workerId, 2000), client.getWorkerStatus(s.workerId)]);
      if (status.ok) {
        s.last = status.data;
        if (s.status !== 'start_failed') s.status = status.data.status;
      }
      const header = status.ok ? JSON.stringify(status.data, null, 2) : JSON.stringify(status.error, null, 2);
      const body = output.ok ? output.data.output : `output unavailable: ${output.error.message}`;
      const file = path.join(options.outDir, `${base}.log`);
      fs.writeFileSync(file, `# status\n${header}\n\n# output (newest ${output.ok ? output.data.returned_lines : 0} lines)\n${body}\n`);
      s.logFile = file;
    };
    const startPending = async (): Promise<void> => {
      const running = slots.filter((s) => s.workerId && !isDone(s)).length;
      const pending = slots.filter((s) => s.status === 'pending').slice(0, Math.max(0, maxConcurrent - running));
      await Promise.all(
        pending.map(async (slot) => {
          const e = slot.entry;
          const args: StartWorkerArgs = { project_path: e.project_path, initial_prompt: e.prompt, label: e.label ?? slot.name };
          if (e.permission_mode) args.permission_mode = e.permission_mode;
          if (e.confirm_write_access !== undefined) args.confirm_write_access = e.confirm_write_access;
          if (e.allowed_tools) args.allowed_tools = e.allowed_tools;
          if (e.model) args.model = e.model;
          if (e.timeout_minutes !== undefined) args.timeout_minutes = e.timeout_minutes;
          const started = await client.startWorker(args);
          if (started.ok) {
            slot.workerId = started.data.worker_id;
            slot.status = started.data.status;
            slot.last = started.data;
            say(`started ${slot.name}: ${slot.workerId} (${slot.status}, ${e.permission_mode ?? 'read_only'})`);
          } else if (started.error.error_code === 'TOO_MANY_WORKERS') {
            say(`queued ${slot.name}: no free worker slot yet`);
          } else {
            slot.status = 'start_failed';
            slot.startError = started.error;
            if (started.error.worker_id) slot.workerId = started.error.worker_id;
            say(`could not start ${slot.name}: ${started.error.error_code}: ${started.error.message}`);
          }
        }),
      );
    };

    // If the server goes away (Ctrl-C reaches it too, and it stops its workers), still write what is known.
    let fatal: string | null = null;
    try {
      await startPending();
      while (!slots.every(isDone)) {
        if (interrupted) {
          say('interrupted: stopping running workers');
          for (const s of slots) {
            if (s.workerId && !isDone(s)) {
              const stopped = await client.stopWorker(s.workerId);
              if (stopped.ok) s.status = stopped.data.status;
              await writeLog(s);
            }
            if (s.status === 'pending') s.status = 'not_started';
          }
          break;
        }
        await sleep(options.pollSeconds * 1000);
        for (const s of slots) {
          if (!s.workerId || isDone(s)) continue;
          const st = await client.getWorkerStatus(s.workerId);
          if (!st.ok) continue;
          if (st.data.status !== s.status) say(`${s.name}: ${s.status} -> ${st.data.status}${st.data.reason ? ` (${st.data.reason})` : ''}`);
          s.status = st.data.status;
          s.last = st.data;
          if (isDone(s)) await writeLog(s);
        }
        await startPending();
      }
      // Workers that never reached the poll (e.g. a start that failed after a worker id was assigned).
      for (const s of slots) await writeLog(s);
    } catch (err) {
      fatal = err instanceof Error ? err.message : String(err);
      say(`run-plan: lost the orchestrator server: ${fatal}`);
    }

    const allCompleted = !fatal && slots.every((s) => s.status === 'completed');
    const summary = {
      plan_file: options.planFile,
      started_at: startedAt,
      finished_at: new Date().toISOString(),
      all_completed: allCompleted,
      interrupted,
      error: fatal,
      workers: slots.map((s) => ({
        label: s.entry.label ?? s.name,
        worker_id: s.workerId,
        project_path: s.entry.project_path,
        permission_mode: s.entry.permission_mode ?? 'read_only',
        status: s.status,
        reason: s.last?.reason ?? null,
        session_id: s.last?.session_id ?? null,
        cost_usd: s.last?.cost_usd ?? null,
        exit_code: s.last?.exit_code ?? null,
        elapsed_ms: s.last?.elapsed_ms ?? null,
        result_preview: s.last?.result_preview ?? null,
        start_error: s.startError,
        log_file: s.logFile,
      })),
    };
    fs.writeFileSync(path.join(options.outDir, 'summary.json'), `${JSON.stringify(summary, null, 2)}\n`);
    say(`summary: ${path.join(options.outDir, 'summary.json')}`);
    for (const w of summary.workers) say(`  ${w.label}: ${w.status}${w.reason ? ` (${w.reason})` : ''} cost_usd=${w.cost_usd ?? '?'}`);
    return allCompleted ? 0 : 1;
  } finally {
    process.off('SIGINT', onSignal);
    process.off('SIGTERM', onSignal);
    await client.close().catch(() => {});
  }
}

export function runCli(argv: string[] = process.argv.slice(2)): void {
  let options: CliOptions;
  try {
    options = parseArgs(argv);
  } catch (err) {
    process.stderr.write(`${(err as Error).message}\n`);
    process.exit(2);
  }
  runPlan(options).then(
    (code) => process.exit(code),
    (err: unknown) => {
      process.stderr.write(`run-plan: ${err instanceof Error ? err.message : String(err)}\n`);
      process.exit(1);
    },
  );
}

if (isMainModule(import.meta.url)) runCli();
