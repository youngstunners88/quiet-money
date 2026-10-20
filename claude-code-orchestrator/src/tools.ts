import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type CallToolResult,
  type Tool,
  type ToolAnnotations,
} from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import { PERMISSION_MODES } from './config.js';
import { OrchestratorError, toErrorPayload, type ToolErrorPayload } from './errors.js';
import { toJsonText } from './format.js';
import { MAX_PROMPT_CHARS, type ConfirmFn, type ConfirmRequest, type WorkerManager } from './process-manager.js';
import { redactAndCap } from './redact.js';

export const SERVER_NAME = 'claude-code-orchestrator';
export const SERVER_VERSION = '0.1.0';

export interface ToolContext {
  manager: WorkerManager;
  /**
   * Asks the user directly (MCP elicitation) whether a worker may write files or run commands.
   * Undefined when the client cannot ask; then confirm_write_access is the fallback.
   */
  confirm?: ConfirmFn | undefined;
}

/** How long the user has to answer an approval question. */
export const CONFIRM_TIMEOUT_MS = 10 * 60_000;

/** A tool as the server sees it: metadata plus a runner that validates its own input. */
export interface RegisteredTool {
  name: string;
  title: string;
  description: string;
  inputSchema: z.ZodType;
  annotations?: ToolAnnotations;
  run: (rawArgs: unknown, ctx: ToolContext) => Promise<unknown>;
}

/**
 * Declares a tool. New tools (code review, test runs, multi-worker delegation) are one more
 * defineTool(...) entry in TOOLS; validation and structured errors come for free.
 */
export function defineTool<S extends z.ZodType>(def: {
  name: string;
  title: string;
  description: string;
  inputSchema: S;
  annotations?: ToolAnnotations;
  handler: (args: z.output<S>, ctx: ToolContext) => unknown;
}): RegisteredTool {
  return {
    name: def.name,
    title: def.title,
    description: def.description,
    inputSchema: def.inputSchema,
    ...(def.annotations ? { annotations: def.annotations } : {}),
    run: async (rawArgs, ctx) => {
      const parsed = def.inputSchema.safeParse(rawArgs ?? {});
      if (!parsed.success) {
        const workerId = workerIdOf(rawArgs);
        throw new OrchestratorError(
          'INVALID_INPUT',
          `Invalid arguments for ${def.name}: ${z.prettifyError(parsed.error).replace(/\n/g, '; ')}`,
          workerId,
          'Fix the listed fields and call the tool again; see the tool input schema for allowed values.',
        );
      }
      return await def.handler(parsed.data, ctx);
    },
  };
}

function workerIdOf(rawArgs: unknown): string | null {
  if (typeof rawArgs === 'object' && rawArgs !== null && 'worker_id' in rawArgs) {
    const id = (rawArgs as { worker_id: unknown }).worker_id;
    if (typeof id === 'string') return id;
  }
  return null;
}

const workerId = z.string().min(1).max(64).describe('Worker id returned by start_worker or list_workers.');

export const TOOLS: RegisteredTool[] = [
  defineTool({
    name: 'start_worker',
    title: 'Start a Claude Code worker',
    description:
      'Spawn a Claude Code worker (claude -p, non-interactive) in project_path and return its worker_id and status. ' +
      'Default permission_mode is read_only (Read/Glob/Grep, no writes, no shell). standard adds Edit/Write; full_access adds Bash. ' +
      'Any mode above read_only is capped by the server ceiling WORKER_PERMISSION_MODE and needs the user\'s approval: the server asks the user ' +
      'itself when the client supports MCP elicitation (a decline returns CONFIRMATION_REQUIRED); otherwise it needs confirm_write_access: true, ' +
      'which you may only set after the user explicitly approved write access. Without initial_prompt the worker waits for send_prompt. ' +
      'At most 3 workers run at once by default; each task times out after 10 minutes unless timeout_minutes says otherwise.',
    inputSchema: z.strictObject({
      project_path: z
        .string()
        .min(1)
        .describe('Absolute path of an existing project directory; the worker runs there and its file tools stay inside it.'),
      initial_prompt: z
        .string()
        .max(MAX_PROMPT_CHARS)
        .optional()
        .describe('The first task. Without it the worker is created in waiting_for_input and send_prompt starts it.'),
      allowed_tools: z
        .array(z.string().min(1).max(200))
        .max(50)
        .optional()
        .describe(
          'Extra Claude Code tool patterns, one per element, e.g. "Bash(python -m pytest *)". read_only accepts only Read/Glob/Grep patterns; standard accepts its own tools or scoped patterns of others.',
        ),
      model: z.string().min(1).max(100).optional().describe('Model alias or id, e.g. "sonnet", "opus", "haiku".'),
      permission_mode: z
        .enum(PERMISSION_MODES)
        .optional()
        .describe('read_only (default), standard (adds Edit/Write) or full_access (adds Bash). Capped by the server ceiling.'),
      confirm_write_access: z
        .boolean()
        .optional()
        .describe(
          'Only for clients without MCP elicitation: required true for standard and full_access, and only after the user explicitly approved it. Ignored when the server can ask the user itself.',
        ),
      timeout_minutes: z
        .number()
        .positive()
        .max(1440)
        .optional()
        .describe('Time limit for this task in minutes (default 10; capped by WORKER_MAX_TIMEOUT_MS).'),
      label: z.string().max(80).optional().describe('Short label for humans, shown in list_workers.'),
    }),
    handler: (args, ctx) =>
      ctx.manager.startWorker({
        projectPath: args.project_path,
        initialPrompt: args.initial_prompt,
        allowedTools: args.allowed_tools,
        model: args.model,
        permissionMode: args.permission_mode,
        confirmWriteAccess: args.confirm_write_access,
        confirm: ctx.confirm,
        timeoutMinutes: args.timeout_minutes,
        label: args.label,
      }),
  }),

  defineTool({
    name: 'send_prompt',
    title: 'Send a follow-up prompt to a worker',
    description:
      'Give a worker its next prompt. Claude Code -p answers one prompt per process, so a follow-up resumes the recorded session ' +
      '(claude -p --resume <session_id>) with the same permissions. Waits up to wait_seconds for the reply and returns the response text and status; ' +
      'if it is still running, poll get_worker_status. Errors: WORKER_BUSY while a turn runs, FOLLOWUP_UNSUPPORTED when no session id was recorded.',
    inputSchema: z.strictObject({
      worker_id: workerId,
      prompt: z.string().min(1).max(MAX_PROMPT_CHARS).describe('The follow-up prompt.'),
      wait_seconds: z
        .number()
        .min(0)
        .max(600)
        .default(120)
        .describe('How long to wait for the reply before returning with status running (default 120, max 600).'),
      timeout_minutes: z.number().positive().max(1440).optional().describe('Time limit for this turn in minutes.'),
    }),
    handler: (args, { manager }) =>
      manager.sendPrompt({
        workerId: args.worker_id,
        prompt: args.prompt,
        waitSeconds: args.wait_seconds,
        timeoutMinutes: args.timeout_minutes,
      }),
  }),

  defineTool({
    name: 'get_worker_status',
    title: 'Get worker status',
    description:
      'Status of a worker: starting, running, waiting_for_input, completed, failed or terminated, with reason, elapsed_ms, last_activity, pid, session_id, cost_usd, exit_code and a preview of the final result.',
    inputSchema: z.strictObject({ worker_id: workerId }),
    annotations: { readOnlyHint: true, idempotentHint: true },
    handler: (args, { manager }) => manager.getStatus(args.worker_id),
  }),

  defineTool({
    name: 'get_worker_output',
    title: 'Get worker output',
    description:
      'The most recent output lines of a worker, each labelled [stdout] or [stderr]. stdout is rendered from Claude Code stream-json ' +
      '("assistant: ...", "tool: <name> <input>", "result: ..."). Replies are capped at 20000 characters; older lines are dropped first and the cut is marked.',
    inputSchema: z.strictObject({
      worker_id: workerId,
      tail_lines: z.number().int().min(1).max(2000).default(200).describe('How many of the newest lines to return (default 200, max 2000).'),
    }),
    annotations: { readOnlyHint: true, idempotentHint: true },
    handler: (args, { manager }) => manager.getOutput(args.worker_id, args.tail_lines),
  }),

  defineTool({
    name: 'stop_worker',
    title: 'Stop a worker',
    description:
      'Gracefully stop a worker: SIGTERM to its process group, SIGKILL after 5 s if needed. Returns the final status (terminated) and the last 50 output lines. ' +
      'A worker that already completed or failed is left as it is.',
    inputSchema: z.strictObject({ worker_id: workerId }),
    annotations: { destructiveHint: true, idempotentHint: true },
    handler: (args, { manager }) => manager.stopWorker(args.worker_id),
  }),

  defineTool({
    name: 'list_workers',
    title: 'List workers',
    description:
      'All running workers and the most recent finished ones (last 50) with worker_id, label, project_path, status, permission_mode and started_at, plus the server limits.',
    inputSchema: z.strictObject({}),
    annotations: { readOnlyHint: true, idempotentHint: true },
    handler: (_args, { manager }) => manager.listWorkers(),
  }),
];

export const SERVER_INSTRUCTIONS =
  'Runs Claude Code workers (claude -p) in local project folders. Typical flow: list_workers, start_worker with a project_path and ' +
  'initial_prompt, poll get_worker_status until completed/failed, read get_worker_output, then send_prompt for follow-ups or stop_worker. ' +
  'Workers are read_only unless the server ceiling allows more and the user approves it (asked directly through elicitation when the client supports it, else confirm_write_access). ' +
  'Every tool error is JSON with error_code, message, worker_id and suggested_fix.';

function listing(tool: RegisteredTool): Tool {
  const schema = z.toJSONSchema(tool.inputSchema, { io: 'input' }) as Record<string, unknown>;
  delete schema.$schema;
  return {
    name: tool.name,
    title: tool.title,
    description: tool.description,
    inputSchema: schema as Tool['inputSchema'],
    ...(tool.annotations ? { annotations: tool.annotations } : {}),
  };
}

const CONFIRM_SCHEMA = {
  type: 'object' as const,
  properties: {
    approve: {
      type: 'boolean' as const,
      title: 'Approve this worker',
      description: 'Yes lets this Claude Code worker start with the access described above.',
    },
  },
  required: ['approve'],
};

/** An empty elicitation capability means form mode (MCP 2025-06-18); newer clients list `form` explicitly. */
function supportsFormElicitation(capability: unknown): boolean {
  if (typeof capability !== 'object' || capability === null) return false;
  const c = capability as Record<string, unknown>;
  return Object.keys(c).length === 0 || (typeof c.form === 'object' && c.form !== null);
}

export function confirmMessage(r: ConfirmRequest): string {
  const access = r.mode === 'full_access' ? 'write files and run any shell command' : 'write files';
  const lines = [
    `Allow a ${r.mode} Claude Code worker to ${access} in ${r.projectPath}?`,
    `Tools: ${r.tools.join(', ')}`,
  ];
  if (r.label) lines.push(`Label: ${r.label}`);
  if (r.model) lines.push(`Model: ${r.model}`);
  if (r.prompt) lines.push(`Task: ${redactAndCap(r.prompt, 500)}`);
  return lines.join('\n');
}

export function okResult(payload: unknown): CallToolResult {
  return { content: [{ type: 'text', text: toJsonText(payload) }] };
}

export function errorResult(payload: ToolErrorPayload): CallToolResult {
  return { content: [{ type: 'text', text: toJsonText(payload) }], isError: true };
}

/**
 * Builds the MCP server. The low-level Server is used (rather than McpServer.registerTool) because
 * McpServer answers schema failures with plain text, and every error here must be the JSON payload.
 */
export function createServer(manager: WorkerManager, tools: RegisteredTool[] = TOOLS): Server {
  const server = new Server(
    { name: SERVER_NAME, version: SERVER_VERSION },
    { capabilities: { tools: {} }, instructions: SERVER_INSTRUCTIONS },
  );
  const byName = new Map(tools.map((t) => [t.name, t]));
  const listings = tools.map(listing);

  const askUser: ConfirmFn = async (request) => {
    const result = await server.elicitInput(
      { mode: 'form', message: confirmMessage(request), requestedSchema: CONFIRM_SCHEMA },
      { timeout: CONFIRM_TIMEOUT_MS },
    );
    return result.action === 'accept' && result.content?.approve === true;
  };
  const ctx: ToolContext = {
    manager,
    // Client capabilities are only known after initialize, so this is decided per call.
    get confirm(): ConfirmFn | undefined {
      return supportsFormElicitation(server.getClientCapabilities()?.elicitation) ? askUser : undefined;
    },
  };

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: listings }));
  server.setRequestHandler(CallToolRequestSchema, async (request): Promise<CallToolResult> => {
    const rawArgs: unknown = request.params.arguments ?? {};
    const tool = byName.get(request.params.name);
    if (!tool) {
      return errorResult({
        error_code: 'UNKNOWN_TOOL',
        message: `Unknown tool ${JSON.stringify(request.params.name)}.`,
        worker_id: workerIdOf(rawArgs),
        suggested_fix: `Use one of: ${tools.map((t) => t.name).join(', ')}.`,
      });
    }
    try {
      return okResult(await tool.run(rawArgs, ctx));
    } catch (err) {
      return errorResult(toErrorPayload(err, workerIdOf(rawArgs)));
    }
  });
  return server;
}
