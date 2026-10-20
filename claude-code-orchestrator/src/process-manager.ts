import { spawn, type ChildProcess } from 'node:child_process';
import { randomBytes, randomUUID } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { exceedsCeiling, type OrchestratorConfig, type PermissionMode } from './config.js';
import { OrchestratorError } from './errors.js';
import { capText, fitTail, MAX_REPLY_CHARS, toJsonText } from './format.js';
import type { JsonlLogger } from './logger.js';
import { buildPermissionArgs, MODE_TOOLS, validateExtraTools, type ParsedTool } from './permissions.js';
import { redact, redactLine, type LineRedactState } from './redact.js';
import { capLine, newStreamState, parseStreamLine, type StreamState } from './stream-parser.js';

export const WORKER_STATUSES = ['starting', 'running', 'waiting_for_input', 'completed', 'failed', 'terminated'] as const;
export type WorkerStatus = (typeof WORKER_STATUSES)[number];

const ACTIVE: ReadonlySet<WorkerStatus> = new Set(['starting', 'running']);
const FINISHED: ReadonlySet<WorkerStatus> = new Set(['completed', 'failed', 'terminated']);

/** Linux caps one argv string at 128 KiB; stay well below it. */
export const MAX_PROMPT_CHARS = 100_000;
const MODEL_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:\[\]/-]{0,99}$/;
const PARTIAL_LINE_LIMIT = 1_000_000;
const STOP_TAIL_LINES = 50;
const RESULT_PREVIEW_CHARS = 2_000;
const POST_KILL_WAIT_MS = 5_000;

export interface OutputLine {
  source: 'stdout' | 'stderr';
  text: string;
  ts: number;
}

/** What the user is asked to approve before a worker that can write files or run commands starts. */
export interface ConfirmRequest {
  projectPath: string;
  mode: PermissionMode;
  tools: string[];
  label: string | null;
  model: string | null;
  prompt: string | null;
}

/** Asks the user (not the calling model); resolves true only on an explicit approval. */
export type ConfirmFn = (request: ConfirmRequest) => Promise<boolean>;

export interface StartWorkerOptions {
  projectPath: string;
  initialPrompt?: string | undefined;
  allowedTools?: string[] | undefined;
  model?: string | undefined;
  permissionMode?: PermissionMode | undefined;
  /** Fallback approval for clients that cannot ask the user themselves (no MCP elicitation), e.g. run-plan. */
  confirmWriteAccess?: boolean | undefined;
  /** When set, the user is asked through it and confirmWriteAccess is ignored. */
  confirm?: ConfirmFn | undefined;
  timeoutMinutes?: number | undefined;
  label?: string | undefined;
}

export interface SendPromptOptions {
  workerId: string;
  prompt: string;
  waitSeconds?: number | undefined;
  timeoutMinutes?: number | undefined;
}

interface Run {
  child: ChildProcess;
  startedAt: number;
  timeoutMs: number;
  stream: StreamState;
  timer: NodeJS.Timeout | null;
  killTimer: NodeJS.Timeout | null;
  timedOut: boolean;
  stopReason: string | null;
  finished: boolean;
  done: Promise<void>;
  resolveDone: () => void;
  partial: { stdout: string; stderr: string };
  costAtStart: number | null;
  /** Value of RUN_MARKER_ENV in this run's environment; every process it starts inherits it. */
  marker: string;
  stderrRedact: LineRedactState;
}

interface Worker {
  id: string;
  label: string | null;
  projectPath: string;
  permissionMode: PermissionMode;
  model: string | null;
  permissionArgs: string[];
  extras: ParsedTool[];
  status: WorkerStatus;
  reason: string | null;
  createdAt: number;
  runStartedAt: number | null;
  endedAt: number | null;
  lastActivity: number;
  pid: number | null;
  sessionId: string | null;
  costUsd: number | null;
  exitCode: number | null;
  signal: string | null;
  resultText: string | null;
  isError: boolean | null;
  numTurns: number | null;
  permissionDenials: number;
  promptsSent: number;
  timeoutMs: number;
  output: OutputLine[];
  droppedLines: number;
  run: Run | null;
}

export interface WorkerStatusView {
  worker_id: string;
  label: string | null;
  status: WorkerStatus;
  reason: string | null;
  project_path: string;
  permission_mode: PermissionMode;
  model: string | null;
  pid: number | null;
  session_id: string | null;
  started_at: string;
  ended_at: string | null;
  elapsed_ms: number;
  run_elapsed_ms: number | null;
  last_activity: string;
  cost_usd: number | null;
  exit_code: number | null;
  signal: string | null;
  prompts_sent: number;
  num_turns: number | null;
  is_error: boolean | null;
  permission_denials: number;
  timeout_ms: number;
  output_lines: number;
  can_send_prompt: boolean;
  result_preview: string | null;
}

export interface WorkerSummary {
  worker_id: string;
  label: string | null;
  project_path: string;
  status: WorkerStatus;
  reason: string | null;
  permission_mode: PermissionMode;
  model: string | null;
  started_at: string;
  ended_at: string | null;
}

export interface OutputView {
  worker_id: string;
  status: WorkerStatus;
  total_lines: number;
  returned_lines: number;
  truncated: boolean;
  output: string;
}

export interface SendPromptView {
  worker_id: string;
  status: WorkerStatus;
  reason: string | null;
  finished: boolean;
  session_id: string | null;
  response: string | null;
  is_error: boolean | null;
  turn_cost_usd: number | null;
  elapsed_ms: number;
  note: string;
}

export interface StopView {
  worker_id: string;
  status: WorkerStatus;
  reason: string | null;
  already_finished: boolean;
  exit_code: number | null;
  signal: string | null;
  cost_usd: number | null;
  last_output: string;
}

export interface ListView {
  workers: WorkerSummary[];
  running: number;
  max_concurrent: number;
  permission_ceiling: PermissionMode;
  default_timeout_ms: number;
}

const iso = (ms: number): string => new Date(ms).toISOString();

/** Marks every process of one run (Claude Code passes its environment on to the shell commands it starts). */
export const RUN_MARKER_ENV = 'CCO_RUN_ID';

/** System basics, proxy and CA settings, and Claude Code's own auth and provider settings. */
const WORKER_ENV_NAMES = new Set([
  'PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'LANG', 'LANGUAGE', 'TERM', 'COLORTERM', 'TMPDIR', 'TZ',
  'XDG_CONFIG_HOME', 'XDG_CACHE_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_RUNTIME_DIR',
  'HTTPS_PROXY', 'HTTP_PROXY', 'NO_PROXY', 'ALL_PROXY', 'https_proxy', 'http_proxy', 'no_proxy', 'all_proxy',
  'NODE_EXTRA_CA_CERTS', 'SSL_CERT_FILE', 'SSL_CERT_DIR', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE',
  'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_CUSTOM_HEADERS', 'ANTHROPIC_MODEL',
  'ANTHROPIC_SMALL_FAST_MODEL', 'ANTHROPIC_DEFAULT_OPUS_MODEL', 'ANTHROPIC_DEFAULT_SONNET_MODEL', 'ANTHROPIC_DEFAULT_HAIKU_MODEL',
  'ANTHROPIC_BEDROCK_BASE_URL', 'ANTHROPIC_VERTEX_BASE_URL', 'ANTHROPIC_VERTEX_PROJECT_ID',
  'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CONFIG_DIR', 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX',
  'CLAUDE_CODE_SKIP_BEDROCK_AUTH', 'CLAUDE_CODE_SKIP_VERTEX_AUTH',
]);
const WORKER_ENV_PREFIXES = ['LC_'];
const BEDROCK_PREFIXES = ['AWS_'];
const VERTEX_PREFIXES = ['GOOGLE_', 'CLOUD_ML_', 'VERTEX_REGION_'];
/** Variables that tie a process to the parent Claude Code session: never passed, not even through WORKER_ENV_PASS. */
const NEVER_PASS = /^(?:CLAUDECODE|CLAUDE_CODE_SESSION_ID|CLAUDE_CODE_CHILD_SESSION|CLAUDE_CODE_REMOTE.*|CLAUDE_CODE_MESSAGING_.*|.*SESSION_INGRESS.*|CCO_RUN_ID)$/;

const truthy = (value: string | undefined): boolean => value !== undefined && ['1', 'true', 'yes', 'on'].includes(value.trim().toLowerCase());

/**
 * Environment for a worker, built from an allowlist (not the server's whole environment, which holds
 * every studio key): system basics, proxy/CA settings, Claude Code's own auth and provider variables
 * (AWS_* only with CLAUDE_CODE_USE_BEDROCK, Google/Vertex ones only with CLAUDE_CODE_USE_VERTEX),
 * plus WORKER_ENV_PASS; then WORKER_ENV_STRIP removes names again.
 */
export function workerEnv(base: NodeJS.ProcessEnv, config: Pick<OrchestratorConfig, 'envPass' | 'envStrip'>): NodeJS.ProcessEnv {
  const prefixes = [...WORKER_ENV_PREFIXES];
  if (truthy(base.CLAUDE_CODE_USE_BEDROCK)) prefixes.push(...BEDROCK_PREFIXES);
  if (truthy(base.CLAUDE_CODE_USE_VERTEX)) prefixes.push(...VERTEX_PREFIXES);
  const extra = new Set(config.envPass);
  const strip = new Set(config.envStrip);
  const env: NodeJS.ProcessEnv = {};
  for (const [name, value] of Object.entries(base)) {
    if (value === undefined || NEVER_PASS.test(name) || strip.has(name)) continue;
    if (WORKER_ENV_NAMES.has(name) || extra.has(name) || prefixes.some((p) => name.startsWith(p))) env[name] = value;
  }
  return env;
}

/** Linux: (pid, process group) of every process of this user whose environment carries the run marker. */
function markedProcesses(marker: string): Array<{ pid: number; pgid: number }> {
  if (process.platform !== 'linux') return [];
  const needle = Buffer.from(`\0${RUN_MARKER_ENV}=${marker}\0`);
  let names: string[];
  try {
    names = fs.readdirSync('/proc');
  } catch {
    return [];
  }
  const found: Array<{ pid: number; pgid: number }> = [];
  for (const name of names) {
    if (!/^[0-9]+$/.test(name)) continue;
    const pid = Number(name);
    if (pid === process.pid) continue;
    try {
      // Other users' processes fail with EACCES; ones that just exited with ENOENT/ESRCH. Both are skipped.
      const environ = Buffer.concat([Buffer.from([0]), fs.readFileSync(`/proc/${name}/environ`)]);
      if (!environ.includes(needle)) continue;
      const stat = fs.readFileSync(`/proc/${name}/stat`, 'utf8');
      const pgid = Number(stat.slice(stat.lastIndexOf(')') + 2).split(' ')[2]);
      found.push({ pid, pgid: Number.isInteger(pgid) ? pgid : 0 });
    } catch {
      // gone or not ours
    }
  }
  return found;
}

let ownPgid: number | null | undefined;
function serverPgid(): number | null {
  if (ownPgid === undefined) {
    try {
      const stat = fs.readFileSync('/proc/self/stat', 'utf8');
      ownPgid = Number(stat.slice(stat.lastIndexOf(')') + 2).split(' ')[2]);
    } catch {
      ownPgid = null;
    }
  }
  return ownPgid;
}

/**
 * Signals every process that carries the run marker, and its process group. Claude Code starts Bash
 * tool commands detached (their own session and group), so signalling the worker's group alone misses them.
 */
function signalMarked(marker: string, sig: NodeJS.Signals): void {
  for (const { pid, pgid } of markedProcesses(marker)) {
    if (pgid > 1 && pgid !== serverPgid()) {
      try {
        process.kill(-pgid, sig);
      } catch {
        // ESRCH/EPERM: group gone or not ours
      }
    }
    try {
      process.kill(pid, sig);
    } catch {
      // ESRCH/EPERM
    }
  }
}

/** Resolves symlinks and checks the directory exists and sits inside the allowed roots. */
export function resolveProjectPath(input: string, allowedRoots: string[] | null): string {
  const absolute = path.resolve(input);
  let real: string;
  try {
    real = fs.realpathSync(absolute);
  } catch {
    throw new OrchestratorError(
      'PROJECT_PATH_NOT_FOUND',
      `project_path ${JSON.stringify(input)} does not exist.`,
      null,
      'Pass the absolute path of an existing project directory.',
    );
  }
  if (!fs.statSync(real).isDirectory()) {
    throw new OrchestratorError(
      'PROJECT_PATH_NOT_FOUND',
      `project_path ${JSON.stringify(input)} is not a directory.`,
      null,
      'Pass the project directory, not a file inside it.',
    );
  }
  if (allowedRoots) {
    const inside = allowedRoots.some((root) => {
      let realRoot = root;
      try {
        realRoot = fs.realpathSync(root);
      } catch {
        return false;
      }
      const rel = path.relative(realRoot, real);
      return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel));
    });
    if (!inside) {
      throw new OrchestratorError(
        'PROJECT_PATH_NOT_ALLOWED',
        `project_path ${JSON.stringify(real)} is outside WORKER_ALLOWED_ROOTS.`,
        null,
        'Use a project inside one of the allowed roots, or ask the operator to extend WORKER_ALLOWED_ROOTS.',
      );
    }
  }
  return real;
}

/** A prompt that starts with "-" would be read as a CLI flag; a leading space keeps it a prompt. */
function promptArg(prompt: string): string {
  return prompt.startsWith('-') ? ` ${prompt}` : prompt;
}

export class WorkerManager {
  private readonly workers = new Map<string, Worker>();

  constructor(
    readonly config: OrchestratorConfig,
    private readonly logger: JsonlLogger,
    private readonly baseEnv: NodeJS.ProcessEnv = process.env,
  ) {}

  runningCount(): number {
    let n = 0;
    for (const w of this.workers.values()) if (ACTIVE.has(w.status)) n += 1;
    return n;
  }

  async startWorker(opts: StartWorkerOptions): Promise<WorkerStatusView> {
    const mode = opts.permissionMode ?? 'read_only';
    const prompt = opts.initialPrompt?.trim() ? opts.initialPrompt : undefined;
    const refuse = (err: OrchestratorError): never => {
      this.logger.log({
        event: 'start_refused',
        worker_id: null,
        project_path: opts.projectPath,
        permission_mode: mode,
        model: opts.model ?? null,
        label: opts.label ?? null,
        prompt: prompt ?? null,
        error_code: err.code,
      });
      throw err;
    };

    let projectPath = '';
    let extras: ParsedTool[] = [];
    try {
      projectPath = resolveProjectPath(opts.projectPath, this.config.allowedRoots);
      if (exceedsCeiling(mode, this.config.permissionCeiling)) {
        throw new OrchestratorError(
          'PERMISSION_CEILING',
          `permission_mode ${mode} is above this server's ceiling (WORKER_PERMISSION_MODE=${this.config.permissionCeiling}).`,
          null,
          `Use permission_mode ${this.config.permissionCeiling} or lower, or have the operator raise WORKER_PERMISSION_MODE and restart the server.`,
        );
      }
      extras = validateExtraTools(mode, opts.allowedTools ?? []);
      if (opts.model !== undefined && !MODEL_PATTERN.test(opts.model)) {
        throw new OrchestratorError(
          'INVALID_INPUT',
          `model ${JSON.stringify(opts.model)} is not a valid model name or alias.`,
          null,
          'Use an alias such as "sonnet", "opus" or "haiku", or a full model id.',
        );
      }
      if (prompt !== undefined && prompt.includes('\u0000')) {
        throw new OrchestratorError('INVALID_INPUT', 'initial_prompt contains a NUL character.', null, 'Remove NUL (\\u0000) characters from the prompt.');
      }
      if (prompt !== undefined && prompt.length > MAX_PROMPT_CHARS) {
        throw new OrchestratorError(
          'INVALID_INPUT',
          `initial_prompt is ${prompt.length} characters; the limit is ${MAX_PROMPT_CHARS}.`,
          null,
          'Shorten the prompt, or write the long context to a file in the project and ask the worker to read it.',
        );
      }
      if (mode !== 'read_only') await this.confirmAccess(opts, mode, projectPath, extras, prompt ?? null);
      if (prompt !== undefined) this.assertCapacity(null);
    } catch (err) {
      if (err instanceof OrchestratorError) refuse(err);
      throw err;
    }

    const now = Date.now();
    const worker: Worker = {
      id: this.newWorkerId(),
      label: opts.label?.trim() ? opts.label.trim() : null,
      projectPath,
      permissionMode: mode,
      model: opts.model ?? null,
      permissionArgs: buildPermissionArgs(mode, extras, { restricted: this.config.restricted }),
      extras,
      status: 'waiting_for_input',
      reason: prompt === undefined ? 'no_initial_prompt' : null,
      createdAt: now,
      runStartedAt: null,
      endedAt: null,
      lastActivity: now,
      pid: null,
      sessionId: null,
      costUsd: null,
      exitCode: null,
      signal: null,
      resultText: null,
      isError: null,
      numTurns: null,
      permissionDenials: 0,
      promptsSent: 0,
      timeoutMs: this.timeoutFor(opts.timeoutMinutes),
      output: [],
      droppedLines: 0,
      run: null,
    };
    this.workers.set(worker.id, worker);
    this.logger.log({
      event: 'start',
      worker_id: worker.id,
      project_path: worker.projectPath,
      permission_mode: worker.permissionMode,
      model: worker.model,
      label: worker.label,
      prompt: prompt ?? null,
      status: prompt === undefined ? 'waiting_for_input' : 'starting',
    });

    if (prompt !== undefined) await this.launch(worker, prompt, null);
    return this.statusView(worker);
  }

  async sendPrompt(opts: SendPromptOptions): Promise<SendPromptView> {
    const worker = this.get(opts.workerId);
    const refuse = (err: OrchestratorError): never => {
      this.logger.log({
        event: 'prompt_refused',
        worker_id: worker.id,
        project_path: worker.projectPath,
        permission_mode: worker.permissionMode,
        prompt: opts.prompt,
        status: worker.status,
        error_code: err.code,
      });
      throw err;
    };

    if (ACTIVE.has(worker.status)) {
      refuse(
        new OrchestratorError(
          'WORKER_BUSY',
          `Worker ${worker.id} is still ${worker.status}; it takes one prompt at a time.`,
          worker.id,
          'Poll get_worker_status until it is completed or failed, then send the prompt again (or stop_worker first).',
        ),
      );
    }
    if (worker.status === 'terminated') {
      refuse(
        new OrchestratorError(
          'WORKER_TERMINATED',
          `Worker ${worker.id} was terminated and accepts no more prompts.`,
          worker.id,
          'Start a new worker with start_worker; include any context it needs in initial_prompt.',
        ),
      );
    }
    if (opts.prompt.includes('\u0000')) {
      refuse(
        new OrchestratorError('INVALID_INPUT', 'prompt contains a NUL character.', worker.id, 'Remove NUL (\\u0000) characters from the prompt.'),
      );
    }
    if (opts.prompt.length > MAX_PROMPT_CHARS) {
      refuse(
        new OrchestratorError(
          'INVALID_INPUT',
          `prompt is ${opts.prompt.length} characters; the limit is ${MAX_PROMPT_CHARS}.`,
          worker.id,
          'Shorten the prompt, or write the context to a file in the project and ask the worker to read it.',
        ),
      );
    }
    const firstPrompt = worker.promptsSent === 0;
    if (!firstPrompt && !worker.sessionId) {
      refuse(
        new OrchestratorError(
          'FOLLOWUP_UNSUPPORTED',
          `Worker ${worker.id} has no Claude Code session id (the CLI never reported one), so it cannot take a follow-up. ` +
            'In non-interactive mode (claude -p) each process answers exactly one prompt; follow-ups work only by resuming a recorded session with --resume.',
          worker.id,
          'Start a new worker with start_worker and put the accumulated context into initial_prompt: the earlier prompt, the useful part of get_worker_output, and this follow-up.',
        ),
      );
    }
    try {
      this.assertCapacity(worker.id);
    } catch (err) {
      if (err instanceof OrchestratorError) refuse(err);
      throw err;
    }

    if (opts.timeoutMinutes !== undefined) worker.timeoutMs = this.timeoutFor(opts.timeoutMinutes);
    this.logger.log({
      event: 'prompt',
      worker_id: worker.id,
      project_path: worker.projectPath,
      permission_mode: worker.permissionMode,
      model: worker.model,
      prompt: opts.prompt,
      status: firstPrompt ? 'starting' : 'resuming',
    });

    const started = Date.now();
    const run = await this.launch(worker, opts.prompt, firstPrompt ? null : worker.sessionId);
    const waitMs = Math.max(0, Math.round((opts.waitSeconds ?? 120) * 1000));
    const finished = run.finished || (await this.waitForRun(run, waitMs));

    let turnCost: number | null = null;
    if (finished && worker.costUsd !== null) turnCost = worker.costUsd - (run.costAtStart ?? 0);

    return {
      worker_id: worker.id,
      status: worker.status,
      reason: worker.reason,
      finished,
      session_id: worker.sessionId,
      response: finished && worker.resultText !== null ? capText(redact(worker.resultText), MAX_REPLY_CHARS - 2_000) : null,
      is_error: finished ? worker.isError : null,
      turn_cost_usd: turnCost,
      elapsed_ms: Date.now() - started,
      note: finished
        ? worker.status === 'completed'
          ? 'Turn finished. Send another prompt to continue the same session.'
          : `Turn ended with status ${worker.status}${worker.reason ? ` (${worker.reason})` : ''}; see get_worker_output.`
        : `Still running after ${Math.round(waitMs / 1000)} s; poll get_worker_status and read get_worker_output.`,
    };
  }

  getStatus(workerId: string): WorkerStatusView {
    return this.statusView(this.get(workerId));
  }

  getOutput(workerId: string, tailLines = 200): OutputView {
    const worker = this.get(workerId);
    const lines = worker.output.slice(-Math.max(1, tailLines)).map((l) => `[${l.source}] ${redact(l.text)}`);
    const view: OutputView = {
      worker_id: worker.id,
      status: worker.status,
      total_lines: worker.output.length + worker.droppedLines,
      returned_lines: lines.length,
      truncated: false,
      output: '',
    };
    const budget = MAX_REPLY_CHARS - toJsonText(view).length - 64;
    const fitted = fitTail(lines, budget, 'ask for fewer tail_lines to see the newest lines in full');
    view.output = fitted.text;
    view.returned_lines = fitted.keptLines;
    view.truncated = fitted.omittedLines > 0;
    if (lines.length === 0) view.output = '(no output yet)';
    return view;
  }

  async stopWorker(workerId: string, reason = 'stopped_by_request'): Promise<StopView> {
    const worker = this.get(workerId);
    let alreadyFinished = false;
    if (worker.run) {
      await this.terminateRun(worker, worker.run, reason);
    } else if (worker.status === 'waiting_for_input') {
      worker.status = 'terminated';
      worker.reason = reason;
      worker.endedAt = Date.now();
      worker.lastActivity = worker.endedAt;
      this.logger.log({
        event: 'termination',
        worker_id: worker.id,
        project_path: worker.projectPath,
        permission_mode: worker.permissionMode,
        status: worker.status,
        reason,
        cost_usd: worker.costUsd,
      });
      this.prune();
    } else {
      alreadyFinished = true;
    }

    const view: StopView = {
      worker_id: worker.id,
      status: worker.status,
      reason: worker.reason,
      already_finished: alreadyFinished,
      exit_code: worker.exitCode,
      signal: worker.signal,
      cost_usd: worker.costUsd,
      last_output: '',
    };
    const lines = worker.output.slice(-STOP_TAIL_LINES).map((l) => `[${l.source}] ${redact(l.text)}`);
    const budget = MAX_REPLY_CHARS - toJsonText(view).length - 64;
    view.last_output = lines.length > 0 ? fitTail(lines, budget, 'use get_worker_output for more').text : '(no output)';
    return view;
  }

  listWorkers(): ListView {
    this.prune();
    const workers = [...this.workers.values()]
      .sort((a, b) => b.createdAt - a.createdAt)
      .map<WorkerSummary>((w) => ({
        worker_id: w.id,
        label: w.label,
        project_path: w.projectPath,
        status: w.status,
        reason: w.reason,
        permission_mode: w.permissionMode,
        model: w.model,
        started_at: iso(w.createdAt),
        ended_at: w.endedAt === null ? null : iso(w.endedAt),
      }));
    return {
      workers,
      running: this.runningCount(),
      max_concurrent: this.config.maxConcurrent,
      permission_ceiling: this.config.permissionCeiling,
      default_timeout_ms: this.config.defaultTimeoutMs,
    };
  }

  /** Resolves when the worker has no live process (true) or after `timeoutMs` (false). */
  async waitForIdle(workerId: string, timeoutMs: number): Promise<boolean> {
    const worker = this.get(workerId);
    if (!worker.run) return true;
    return this.waitForRun(worker.run, timeoutMs);
  }

  /** Stops every live worker; used when the server exits. */
  async shutdown(reason = 'server_shutdown'): Promise<void> {
    const live = [...this.workers.values()].filter((w) => w.run !== null);
    await Promise.all(live.map((w) => this.terminateRun(w, w.run as Run, reason)));
  }

  // ---- internals -------------------------------------------------------------------------

  /** A mode above read_only needs the user's approval: asked through `confirm` when the client can, else confirm_write_access. */
  private async confirmAccess(
    opts: StartWorkerOptions,
    mode: PermissionMode,
    projectPath: string,
    extras: ParsedTool[],
    prompt: string | null,
  ): Promise<void> {
    const what = mode === 'full_access' ? 'write files and run shell commands' : 'write files';
    if (opts.confirm) {
      let approved = false;
      try {
        approved = await opts.confirm({
          projectPath,
          mode,
          tools: [...new Set([...MODE_TOOLS[mode], ...extras.map((t) => t.raw)])],
          label: opts.label?.trim() ? opts.label.trim() : null,
          model: opts.model ?? null,
          prompt,
        });
      } catch {
        approved = false;
      }
      if (!approved) {
        throw new OrchestratorError(
          'CONFIRMATION_REQUIRED',
          `The user did not approve a ${mode} worker (it could ${what}) in ${projectPath}.`,
          null,
          'Do not retry the same request unasked: start a read_only worker instead, or ask the user what they want to allow.',
        );
      }
      return;
    }
    if (opts.confirmWriteAccess !== true) {
      throw new OrchestratorError(
        'CONFIRMATION_REQUIRED',
        `permission_mode ${mode} lets the worker ${what}; it needs explicit user confirmation.`,
        null,
        'Ask the user to approve write access for this project, then call start_worker again with confirm_write_access: true.',
      );
    }
  }

  private get(workerId: string): Worker {
    const worker = this.workers.get(workerId);
    if (!worker) {
      throw new OrchestratorError(
        'WORKER_NOT_FOUND',
        `No worker with id ${JSON.stringify(workerId)} (it may have been pruned; the last ${this.config.retainFinished} finished workers are kept).`,
        workerId,
        'Call list_workers to see the current worker ids.',
      );
    }
    return worker;
  }

  private newWorkerId(): string {
    let id: string;
    do id = `w-${randomBytes(4).toString('hex')}`;
    while (this.workers.has(id));
    return id;
  }

  private timeoutFor(minutes: number | undefined): number {
    if (minutes === undefined) return this.config.defaultTimeoutMs;
    return Math.min(Math.max(1, Math.round(minutes * 60_000)), this.config.maxTimeoutMs);
  }

  private assertCapacity(workerId: string | null): void {
    if (this.runningCount() >= this.config.maxConcurrent) {
      throw new OrchestratorError(
        'TOO_MANY_WORKERS',
        `${this.runningCount()} workers are already running (limit ${this.config.maxConcurrent}, WORKER_MAX_CONCURRENT).`,
        workerId,
        'Wait for a worker to finish (get_worker_status) or stop one with stop_worker, then try again.',
      );
    }
  }

  private async launch(worker: Worker, prompt: string, resumeSessionId: string | null): Promise<Run> {
    const args = ['-p', promptArg(prompt), '--output-format', 'stream-json', '--verbose'];
    if (worker.model) args.push('--model', worker.model);
    if (resumeSessionId) args.push('--resume', resumeSessionId);
    else args.push('--session-id', randomUUID());
    args.push(...worker.permissionArgs);

    const marker = `${worker.id}-${randomUUID()}`;
    let child: ChildProcess;
    try {
      child = spawn(this.config.claudeBin, args, {
        cwd: worker.projectPath,
        env: { ...workerEnv(this.baseEnv, this.config), [RUN_MARKER_ENV]: marker },
        stdio: ['ignore', 'pipe', 'pipe'],
        // Own process group for the CLI. Its Bash tool commands run detached in groups of their own, so a
        // stop or timeout reaches them through the run marker in their environment (see signalMarked).
        detached: process.platform !== 'win32',
        windowsHide: true,
      });
    } catch (err) {
      throw this.spawnFailed(worker, err as Error);
    }

    let resolveDone: () => void = () => {};
    const done = new Promise<void>((resolve) => {
      resolveDone = resolve;
    });
    const now = Date.now();
    const run: Run = {
      child,
      startedAt: now,
      timeoutMs: worker.timeoutMs,
      stream: newStreamState(),
      timer: null,
      killTimer: null,
      timedOut: false,
      stopReason: null,
      finished: false,
      done,
      resolveDone,
      partial: { stdout: '', stderr: '' },
      costAtStart: worker.costUsd,
      marker,
      stderrRedact: { inPrivateKey: false },
    };

    worker.run = run;
    worker.status = 'starting';
    worker.reason = null;
    worker.runStartedAt = now;
    worker.endedAt = null;
    worker.lastActivity = now;
    worker.exitCode = null;
    worker.signal = null;
    worker.resultText = null;
    worker.isError = null;
    worker.numTurns = null;
    worker.permissionDenials = 0;
    worker.pid = null;
    worker.promptsSent += 1;

    child.stdout?.setEncoding('utf8');
    child.stderr?.setEncoding('utf8');
    child.stdout?.on('data', (chunk: string) => this.onData(worker, run, 'stdout', chunk));
    child.stderr?.on('data', (chunk: string) => this.onData(worker, run, 'stderr', chunk));
    child.on('close', (code, signal) => this.finish(worker, run, code, signal, null));

    const spawnError = await new Promise<Error | null>((resolve) => {
      child.once('spawn', () => resolve(null));
      child.once('error', (err) => resolve(err));
    });
    // Later errors (e.g. a failed kill) must not crash the server.
    child.on('error', () => {});

    if (spawnError) {
      this.finish(worker, run, null, null, `spawn_error: ${(spawnError as NodeJS.ErrnoException).code ?? spawnError.message}`);
      throw this.spawnFailed(worker, spawnError);
    }

    worker.pid = child.pid ?? null;
    if (run.finished) return run;
    run.timer = setTimeout(() => {
      run.timedOut = true;
      this.signal(run, 'SIGTERM');
      run.killTimer = setTimeout(() => this.signal(run, 'SIGKILL'), this.config.killGraceMs);
    }, run.timeoutMs);
    return run;
  }

  private spawnFailed(worker: Worker, err: Error): OrchestratorError {
    if (!worker.run) {
      // spawn() threw before a run existed: record the failure on the worker itself.
      worker.status = 'failed';
      worker.reason = `spawn_error: ${(err as NodeJS.ErrnoException).code ?? 'invalid_arguments'}`;
      worker.endedAt = Date.now();
      worker.lastActivity = worker.endedAt;
    }
    return new OrchestratorError(
      'SPAWN_FAILED',
      `Could not start the Claude Code CLI ${JSON.stringify(this.config.claudeBin)}: ${err.message}`,
      worker.id,
      'Install Claude Code (npm install -g @anthropic-ai/claude-code) or set CLAUDE_BIN to the absolute path of the claude binary, then restart the server.',
    );
  }

  private onData(worker: Worker, run: Run, source: 'stdout' | 'stderr', chunk: string): void {
    worker.lastActivity = Date.now();
    if (worker.status === 'starting') worker.status = 'running';
    let buffer = run.partial[source] + chunk;
    let newline = buffer.indexOf('\n');
    while (newline !== -1) {
      this.onLine(worker, run, source, buffer.slice(0, newline));
      buffer = buffer.slice(newline + 1);
      newline = buffer.indexOf('\n');
    }
    if (buffer.length > PARTIAL_LINE_LIMIT) {
      this.onLine(worker, run, source, buffer);
      buffer = '';
    }
    run.partial[source] = buffer;
  }

  private onLine(worker: Worker, run: Run, source: 'stdout' | 'stderr', line: string): void {
    if (source === 'stderr') {
      // Redact before capping (a cut key no longer matches), with state for multi-line key blocks.
      if (line.trim() !== '') this.push(worker, 'stderr', capLine(redactLine(line, run.stderrRedact)));
      return;
    }
    for (const rendered of parseStreamLine(line, run.stream)) this.push(worker, 'stdout', rendered);
    if (run.stream.sessionId) worker.sessionId = run.stream.sessionId;
  }

  private push(worker: Worker, source: 'stdout' | 'stderr', text: string): void {
    worker.output.push({ source, text: redact(text), ts: Date.now() });
    const max = this.config.maxOutputLines;
    if (worker.output.length > max + Math.ceil(max / 10)) {
      const drop = worker.output.length - max;
      worker.output.splice(0, drop);
      worker.droppedLines += drop;
    }
  }

  private signal(run: Run, sig: NodeJS.Signals): void {
    const pid = run.child.pid;
    if (pid === undefined) return;
    // Shell commands the worker started live in their own groups; they get the same signal.
    signalMarked(run.marker, sig);
    if (process.platform !== 'win32') {
      try {
        process.kill(-pid, sig);
        return;
      } catch {
        // Group already gone; fall through to the direct kill.
      }
    }
    try {
      run.child.kill(sig);
    } catch {
      // Already exited.
    }
  }

  private finish(worker: Worker, run: Run, code: number | null, signal: NodeJS.Signals | null, spawnError: string | null): void {
    if (run.finished) return;
    run.finished = true;
    if (run.timer) clearTimeout(run.timer);
    if (run.killTimer) clearTimeout(run.killTimer);
    for (const source of ['stdout', 'stderr'] as const) {
      if (run.partial[source]) this.onLine(worker, run, source, run.partial[source]);
      run.partial[source] = '';
    }
    // Leftover processes go with it: the worker's group, and every detached shell command it started.
    if (process.platform !== 'win32' && run.child.pid !== undefined && !spawnError) {
      try {
        process.kill(-run.child.pid, 'SIGKILL');
      } catch {
        // Nothing left.
      }
      signalMarked(run.marker, 'SIGKILL');
    }

    const s = run.stream;
    if (s.sessionId) worker.sessionId = s.sessionId;
    worker.resultText = s.resultText;
    worker.isError = s.sawResult ? s.isError : null;
    worker.numTurns = s.numTurns;
    worker.permissionDenials = s.permissionDenials;
    if (s.costUsd !== null) worker.costUsd = (worker.costUsd ?? 0) + s.costUsd;
    worker.exitCode = code;
    worker.signal = signal;
    worker.endedAt = Date.now();
    worker.lastActivity = worker.endedAt;
    worker.run = null;

    let status: WorkerStatus;
    let reason: string | null;
    if (spawnError) {
      status = 'failed';
      reason = spawnError;
    } else if (run.stopReason) {
      status = 'terminated';
      reason = run.stopReason;
    } else if (run.timedOut) {
      status = 'failed';
      reason = 'timeout';
    } else if (code === 0 && s.sawResult && !s.isError) {
      status = 'completed';
      reason = null;
    } else if (code === 0 && s.sawResult) {
      status = 'failed';
      reason = `result_error${s.subtype ? `: ${s.subtype}` : ''}`;
    } else if (code === 0) {
      status = 'failed';
      reason = 'no_result_event';
    } else if (signal) {
      status = 'failed';
      reason = `killed_by_${signal}`;
    } else {
      status = 'failed';
      reason = `exit_code_${code}`;
    }
    worker.status = status;
    worker.reason = reason;

    this.logger.log({
      event: run.stopReason || run.timedOut ? 'termination' : 'completion',
      worker_id: worker.id,
      project_path: worker.projectPath,
      permission_mode: worker.permissionMode,
      model: worker.model,
      status,
      reason,
      exit_code: code,
      cost_usd: s.costUsd,
      pid: worker.pid,
    });
    run.resolveDone();
    this.prune();
  }

  private async terminateRun(worker: Worker, run: Run, reason: string): Promise<void> {
    if (run.finished) return;
    run.stopReason = reason;
    this.signal(run, 'SIGTERM');
    if (!(await this.waitForRun(run, this.config.killGraceMs))) {
      this.signal(run, 'SIGKILL');
      if (!(await this.waitForRun(run, POST_KILL_WAIT_MS))) {
        // The process ignored SIGKILL (zombie or permission problem): record it as terminated anyway.
        this.finish(worker, run, null, 'SIGKILL', null);
      }
    }
  }

  private async waitForRun(run: Run, timeoutMs: number): Promise<boolean> {
    if (run.finished) return true;
    let timer: NodeJS.Timeout | undefined;
    const timedOut = new Promise<boolean>((resolve) => {
      timer = setTimeout(() => resolve(false), timeoutMs);
    });
    const result = await Promise.race([run.done.then(() => true), timedOut]);
    if (timer) clearTimeout(timer);
    return result;
  }

  private prune(): void {
    const finished = [...this.workers.values()]
      .filter((w) => FINISHED.has(w.status) && w.run === null)
      .sort((a, b) => (b.endedAt ?? 0) - (a.endedAt ?? 0));
    for (const w of finished.slice(this.config.retainFinished)) this.workers.delete(w.id);
  }

  private statusView(worker: Worker): WorkerStatusView {
    const now = Date.now();
    const end = worker.run ? now : (worker.endedAt ?? now);
    return {
      worker_id: worker.id,
      label: worker.label,
      status: worker.status,
      reason: worker.reason,
      project_path: worker.projectPath,
      permission_mode: worker.permissionMode,
      model: worker.model,
      pid: worker.pid,
      session_id: worker.sessionId,
      started_at: iso(worker.createdAt),
      ended_at: worker.endedAt === null ? null : iso(worker.endedAt),
      elapsed_ms: end - worker.createdAt,
      run_elapsed_ms: worker.runStartedAt === null ? null : end - worker.runStartedAt,
      last_activity: iso(worker.lastActivity),
      cost_usd: worker.costUsd,
      exit_code: worker.exitCode,
      signal: worker.signal,
      prompts_sent: worker.promptsSent,
      num_turns: worker.numTurns,
      is_error: worker.isError,
      permission_denials: worker.permissionDenials,
      timeout_ms: worker.timeoutMs,
      output_lines: worker.output.length + worker.droppedLines,
      can_send_prompt:
        !ACTIVE.has(worker.status) &&
        worker.status !== 'terminated' &&
        (worker.promptsSent === 0 || worker.sessionId !== null),
      result_preview: worker.resultText === null ? null : capText(redact(worker.resultText), RESULT_PREVIEW_CHARS),
    };
  }
}
