import { redact } from './redact.js';

export type ErrorCode =
  | 'INVALID_INPUT'
  | 'UNKNOWN_TOOL'
  | 'PROJECT_PATH_NOT_FOUND'
  | 'PROJECT_PATH_NOT_ALLOWED'
  | 'PERMISSION_CEILING'
  | 'CONFIRMATION_REQUIRED'
  | 'TOOL_NOT_PERMITTED'
  | 'TOO_MANY_WORKERS'
  | 'WORKER_NOT_FOUND'
  | 'WORKER_BUSY'
  | 'WORKER_TERMINATED'
  | 'FOLLOWUP_UNSUPPORTED'
  | 'SPAWN_FAILED'
  | 'INTERNAL_ERROR';

/** The JSON body of every tool error. */
export interface ToolErrorPayload {
  error_code: ErrorCode;
  message: string;
  worker_id: string | null;
  suggested_fix: string;
}

export class OrchestratorError extends Error {
  constructor(
    readonly code: ErrorCode,
    message: string,
    readonly workerId: string | null = null,
    readonly suggestedFix = '',
  ) {
    super(message);
    this.name = 'OrchestratorError';
  }

  toPayload(): ToolErrorPayload {
    return {
      error_code: this.code,
      message: redact(this.message),
      worker_id: this.workerId,
      suggested_fix: redact(this.suggestedFix),
    };
  }
}

/** Converts anything thrown into a payload without leaking stack traces or environment. */
export function toErrorPayload(err: unknown, workerId: string | null = null): ToolErrorPayload {
  if (err instanceof OrchestratorError) return err.toPayload();
  const message = err instanceof Error ? err.message : String(err);
  return {
    error_code: 'INTERNAL_ERROR',
    message: redact(message),
    worker_id: workerId,
    suggested_fix: 'Check logs/orchestrator.jsonl and the server stderr; retry, or restart the MCP server if it persists.',
  };
}
