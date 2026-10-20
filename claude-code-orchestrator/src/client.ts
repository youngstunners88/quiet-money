import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { fileURLToPath } from 'node:url';
import type { PermissionMode } from './config.js';
import type { ToolErrorPayload } from './errors.js';
import type { ListView, OutputView, SendPromptView, StopView, WorkerStatusView } from './process-manager.js';
import { SERVER_VERSION } from './tools.js';

export interface ConnectOptions {
  /** Server entry script; defaults to the built dist/src/index.js next to this file. */
  serverEntry?: string;
  /** Environment for the server (and so for its workers). Defaults to this process's environment. */
  env?: NodeJS.ProcessEnv;
  cwd?: string;
  /** What to do with the server's stderr (default: inherit). */
  stderr?: 'inherit' | 'pipe' | 'ignore';
  /**
   * The caller handles Ctrl-C itself: the server then ignores SIGINT (which a terminal sends to the whole
   * foreground process group) and keeps serving until the caller has stopped the workers and closed it.
   */
  parentHandlesSigint?: boolean;
}

/** Same name as PARENT_HANDLES_SIGINT_ENV in index.ts (not imported, so the client does not load the server). */
const PARENT_HANDLES_SIGINT_ENV = 'ORCHESTRATOR_PARENT_HANDLES_SIGINT';

export type ToolOutcome<T> = { ok: true; data: T } | { ok: false; error: ToolErrorPayload };

export interface StartWorkerArgs {
  project_path: string;
  initial_prompt?: string;
  allowed_tools?: string[];
  model?: string;
  permission_mode?: PermissionMode;
  confirm_write_access?: boolean;
  timeout_minutes?: number;
  label?: string;
}

export interface SendPromptArgs {
  worker_id: string;
  prompt: string;
  wait_seconds?: number;
  timeout_minutes?: number;
}

/** Long enough for send_prompt's maximum wait (600 s) plus slack. */
const CALL_TIMEOUT_MS = 15 * 60_000;

function stringEnv(env: NodeJS.ProcessEnv): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(env)) if (typeof value === 'string') out[key] = value;
  return out;
}

function isErrorPayload(value: unknown): value is ToolErrorPayload {
  return typeof value === 'object' && value !== null && 'error_code' in value && 'message' in value;
}

/** Small typed client for the orchestrator server over stdio (used by run-plan and the tests). */
export class OrchestratorClient {
  private constructor(
    private readonly client: Client,
    private readonly transport: StdioClientTransport,
  ) {}

  static async connect(options: ConnectOptions = {}): Promise<OrchestratorClient> {
    const entry = options.serverEntry ?? fileURLToPath(new URL('./index.js', import.meta.url));
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [entry],
      // Pass the full environment: the SDK default keeps only a safe subset, and workers need Claude Code's auth variables.
      env: {
        ...stringEnv(options.env ?? process.env),
        ...(options.parentHandlesSigint ? { [PARENT_HANDLES_SIGINT_ENV]: '1' } : {}),
      },
      stderr: options.stderr ?? 'inherit',
      ...(options.cwd ? { cwd: options.cwd } : {}),
    });
    const client = new Client({ name: 'claude-code-orchestrator-client', version: SERVER_VERSION });
    await client.connect(transport);
    return new OrchestratorClient(client, transport);
  }

  get serverPid(): number | null {
    return this.transport.pid;
  }

  async listToolNames(): Promise<string[]> {
    const result = await this.client.listTools();
    return result.tools.map((t) => t.name);
  }

  async call<T>(name: string, args: Record<string, unknown> = {}): Promise<ToolOutcome<T>> {
    const result = await this.client.callTool({ name, arguments: args }, undefined, { timeout: CALL_TIMEOUT_MS });
    const content = Array.isArray(result.content) ? result.content : [];
    const first = content.find((c): c is { type: 'text'; text: string } => c?.type === 'text');
    const text = first?.text ?? '';
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = undefined;
    }
    if (result.isError) {
      return {
        ok: false,
        error: isErrorPayload(parsed)
          ? parsed
          : { error_code: 'INTERNAL_ERROR', message: text, worker_id: null, suggested_fix: '' },
      };
    }
    if (parsed === undefined) {
      return {
        ok: false,
        error: { error_code: 'INTERNAL_ERROR', message: `Reply was not JSON: ${text.slice(0, 200)}`, worker_id: null, suggested_fix: '' },
      };
    }
    return { ok: true, data: parsed as T };
  }

  listWorkers(): Promise<ToolOutcome<ListView>> {
    return this.call<ListView>('list_workers');
  }

  startWorker(args: StartWorkerArgs): Promise<ToolOutcome<WorkerStatusView>> {
    return this.call<WorkerStatusView>('start_worker', { ...args });
  }

  sendPrompt(args: SendPromptArgs): Promise<ToolOutcome<SendPromptView>> {
    return this.call<SendPromptView>('send_prompt', { ...args });
  }

  getWorkerStatus(workerId: string): Promise<ToolOutcome<WorkerStatusView>> {
    return this.call<WorkerStatusView>('get_worker_status', { worker_id: workerId });
  }

  getWorkerOutput(workerId: string, tailLines = 200): Promise<ToolOutcome<OutputView>> {
    return this.call<OutputView>('get_worker_output', { worker_id: workerId, tail_lines: tailLines });
  }

  stopWorker(workerId: string): Promise<ToolOutcome<StopView>> {
    return this.call<StopView>('stop_worker', { worker_id: workerId });
  }

  async close(): Promise<void> {
    await this.client.close();
  }
}
