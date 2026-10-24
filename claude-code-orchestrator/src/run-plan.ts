#!/usr/bin/env node
/**
 * Runs a plan of workers through ONE orchestrator server (workers live inside that server process):
 *   node dist/run-plan.js plan.json --out <dir> [--poll-seconds 15]
 * Exit code 0 only when every worker completed and every lane with done_when was verified PASS by an independent read-only worker.
 */
import { spawnSync } from 'node:child_process';
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
  /** Checkable acceptance criteria. A write lane that has them is checked by an independent read-only verifier after it finishes. */
  done_when: z.array(z.string().min(1).max(500)).min(1).max(12).optional(),
}).refine((e) => !e.done_when || (e.permission_mode !== undefined && e.permission_mode !== 'read_only'), {
  message: 'done_when needs a write lane (permission_mode other than read_only): the verifier judges the diff, and a read-only lane produces none',
  path: ['done_when'],
});
const PlanSchema = z.strictObject({ workers: z.array(PlanEntrySchema).min(1) });

export type PlanEntry = z.infer<typeof PlanEntrySchema>;
export type Plan = z.infer<typeof PlanSchema>;

const TERMINAL = new Set(['completed', 'failed', 'terminated']);

export type Verified = 'pass' | 'fail' | 'unverified' | 'not_required';

interface Verification {
  state: Verified;
  evidence: string | null;
  workerId: string | null;
  logFile: string | null;
}

interface Slot {
  index: number;
  entry: PlanEntry;
  name: string;
  workerId: string | null;
  status: string;
  last: WorkerStatusView | null;
  startError: ToolErrorPayload | null;
  logFile: string | null;
  verification: Verification;
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

const DIFF_LIMIT = 60_000;

/** What the lane changed, as the verifier will see it: tracked changes against HEAD plus the names of untracked files. Never the builder's own account. */
export function captureDiff(projectPath: string): string {
  const git = (args: string[]): string => {
    const r = spawnSync('git', ['-C', projectPath, ...args], { encoding: 'utf8', timeout: 30_000, maxBuffer: 16 * 1024 * 1024 });
    return r.status === 0 ? r.stdout : `(git ${args[0]} failed: ${(r.stderr || r.error?.message || 'no output').toString().slice(0, 200)})\n`;
  };
  const untracked = git(['ls-files', '--others', '--exclude-standard']).trim();
  const diff = git(['diff', 'HEAD']);
  const text = `${diff}${untracked ? `\n# untracked files (contents not shown; read them if a criterion needs it)\n${untracked}\n` : ''}`;
  return text.length > DIFF_LIMIT ? `${text.slice(0, DIFF_LIMIT)}\n# diff truncated at ${DIFF_LIMIT} characters\n` : text || '(no changes were made to the project)\n';
}

/** The verifier sees only the contract (the task and its criteria) and the diff. It is never given the builder's summary or result. */
export function verifierPrompt(entry: PlanEntry, diff: string): string {
  const criteria = (entry.done_when ?? []).map((c, i) => `${i + 1}. ${c}`).join('\n');
  return [
    'VERIFIER ROLE. You are an independent, adversarial reviewer. You have read-only access to the project. Another worker was given the TASK below and says it is finished;',
    'you have not been told what it claims. Your job is to find out whether each acceptance criterion is actually true, by reading the diff and, where needed, the files themselves.',
    'Treat a criterion as failed unless you can point to evidence for it. Do not fix anything. Other lanes may have edited the same tree: judge only the criteria.',
    '',
    '# TASK GIVEN TO THE WORKER',
    entry.prompt,
    '',
    '# ACCEPTANCE CRITERIA (every one must hold)',
    criteria,
    '',
    '# DIFF OF WHAT CHANGED (git diff HEAD, plus untracked file names)',
    diff,
    '',
    '# HOW TO ANSWER',
    'For each criterion write one line: its number, PASS or FAIL, and the evidence (a file and line, a quoted diff line, or the missing thing).',
    'Then end your answer with one final line that is exactly "VERDICT: PASS" (every criterion passed) or exactly "VERDICT: FAIL" (any criterion failed or could not be shown).',
  ].join('\n');
}

/** The last "VERDICT: PASS|FAIL" in the verifier's output, or null when it gave none (which counts as unverified, never as a pass). */
export function parseVerdict(output: string): 'pass' | 'fail' | null {
  // the verdict must stand alone on its own line, so the instruction text quoted in an echo of the prompt never counts
  const all = [...output.matchAll(/(?:^|\n)(?:\[\w+\]\s*)?(?:(?:assistant|result):\s*)?VERDICT:[ \t]*(PASS|FAIL)[ \t]*(?=\r?\n|$)/g)];
  const last = all[all.length - 1];
  return last ? (last[1] === 'PASS' ? 'pass' : 'fail') : null;
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
    verification: { state: 'not_required', evidence: null, workerId: null, logFile: null },
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

    // Done is a claim; Verified is a state. Each finished write lane that carries done_when gets a fresh read-only worker that sees only the contract and the diff.
    if (!fatal && !interrupted) {
      const verifyLane = async (s: Slot): Promise<void> => {
        const entry = s.entry;
        if (!entry.done_when || s.status !== 'completed') return;
        s.verification.state = 'unverified';
        const prompt = verifierPrompt(entry, captureDiff(entry.project_path));
        let started = await client.startWorker({ project_path: entry.project_path, initial_prompt: prompt, label: `verify-${s.name}`.slice(0, 80), permission_mode: 'read_only', ...(entry.model ? { model: entry.model } : {}) });
        for (let tries = 0; !started.ok && started.error.error_code === 'TOO_MANY_WORKERS' && tries < 240; tries += 1) {
          await sleep(options.pollSeconds * 1000);
          started = await client.startWorker({ project_path: entry.project_path, initial_prompt: prompt, label: `verify-${s.name}`.slice(0, 80), permission_mode: 'read_only', ...(entry.model ? { model: entry.model } : {}) });
        }
        if (!started.ok) {
          s.verification.evidence = `verifier could not start: ${started.error.error_code}: ${started.error.message}`;
          return;
        }
        const id = started.data.worker_id;
        s.verification.workerId = id;
        let status = started.data.status;
        while (!TERMINAL.has(status)) {
          await sleep(options.pollSeconds * 1000);
          const st = await client.getWorkerStatus(id);
          if (st.ok) status = st.data.status;
        }
        const out = await client.getWorkerOutput(id, 2000);
        const text = out.ok ? out.data.output : "";
        const file = path.join(options.outDir, `verify-${s.name}.log`);
        fs.writeFileSync(file, `# verifier for ${s.name} (${status})\n\n${text}\n`);
        s.verification.logFile = file;
        const verdict = status === 'completed' ? parseVerdict(text) : null;
        s.verification.state = verdict ?? 'unverified';
        s.verification.evidence = verdict ? `see ${path.basename(file)}` : `the verifier ended ${status} without a VERDICT line`;
        say(`verify ${s.name}: ${s.verification.state}`);
      };
      try {
        await Promise.all(slots.map(verifyLane));
      } catch (err) {
        fatal = err instanceof Error ? err.message : String(err);
        say(`run-plan: lost the orchestrator server while verifying: ${fatal}`);
      }
    }

    const allCompleted = !fatal && slots.every((s) => s.status === 'completed');
    const allVerified = allCompleted && slots.every((s) => s.verification.state === 'pass' || s.verification.state === 'not_required');
    const summary = {
      plan_file: options.planFile,
      started_at: startedAt,
      finished_at: new Date().toISOString(),
      all_completed: allCompleted,
      all_verified: allVerified,
      interrupted,
      error: fatal,
      workers: slots.map((s) => ({
        label: s.entry.label ?? s.name,
        worker_id: s.workerId,
        project_path: s.entry.project_path,
        permission_mode: s.entry.permission_mode ?? 'read_only',
        status: s.status,
        claimed_done: s.status === 'completed',
        verified: s.verification.state,
        verification_evidence: s.verification.evidence,
        verifier_log: s.verification.logFile,
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
    for (const w of summary.workers) say(`  ${w.label}: ${w.status}${w.verified !== 'not_required' ? ` verified=${w.verified}` : ''}${w.reason ? ` (${w.reason})` : ''} cost_usd=${w.cost_usd ?? '?'}`);
    return allVerified ? 0 : 1;
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
