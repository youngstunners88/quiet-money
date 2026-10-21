/**
 * Turns `claude -p --output-format stream-json --verbose` lines into short human-readable lines
 * and collects the facts the orchestrator needs (session id, result, cost).
 * Lines that are not JSON objects are kept verbatim; nothing here throws on bad input.
 * Text is redacted whole before it is split or shortened, so a multi-line key or a key that
 * straddles a cut cannot leak in pieces.
 */
import { redact, redactLine } from './redact.js';

export const MAX_LINE_CHARS = 4000;
const TOOL_INPUT_MAX = 200;
const TOOL_ERROR_MAX = 300;

export interface StreamState {
  sessionId: string | null;
  model: string | null;
  sawResult: boolean;
  resultText: string | null;
  isError: boolean | null;
  subtype: string | null;
  costUsd: number | null;
  numTurns: number | null;
  permissionDenials: number;
  malformedLines: number;
  /** Raw (non-JSON) stdout lines are inside a private key block. */
  inPrivateKey: boolean;
}

export function newStreamState(): StreamState {
  return {
    sessionId: null,
    model: null,
    sawResult: false,
    resultText: null,
    isError: null,
    subtype: null,
    costUsd: null,
    numTurns: null,
    permissionDenials: 0,
    malformedLines: 0,
    inPrivateKey: false,
  };
}

type Json = Record<string, unknown>;

function isObject(value: unknown): value is Json {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function str(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function oneLine(text: string, max: number): string {
  const flat = text.replace(/\s+/g, ' ').trim();
  return flat.length > max ? `${flat.slice(0, max)}...` : flat;
}

export function capLine(text: string): string {
  return text.length > MAX_LINE_CHARS ? `${text.slice(0, MAX_LINE_CHARS)}... [line truncated, ${text.length - MAX_LINE_CHARS} chars]` : text;
}

/** "prefix: first line" followed by indented continuation lines (redacted as a whole first). */
function block(prefix: string, text: string): string[] {
  const lines = redact(text).replace(/\r\n/g, '\n').split('\n');
  while (lines.length > 0 && (lines[lines.length - 1] as string).trim() === '') lines.pop();
  if (lines.length === 0) return [];
  return lines.map((line, i) => capLine(i === 0 ? `${prefix}: ${line}` : `  ${line}`));
}

const INPUT_KEYS = ['command', 'file_path', 'pattern', 'glob', 'path', 'url', 'query', 'description'];

function summariseToolInput(input: unknown): string {
  if (!isObject(input)) return input === undefined ? '' : oneLine(redact(JSON.stringify(input) ?? ''), TOOL_INPUT_MAX);
  const parts: string[] = [];
  for (const key of INPUT_KEYS) {
    const value = input[key];
    if (typeof value === 'string' && value.length > 0) parts.push(`${key}=${JSON.stringify(value)}`);
    if (parts.length === 2) break;
  }
  const text = parts.length > 0 ? parts.join(' ') : JSON.stringify(input);
  return oneLine(redact(text), TOOL_INPUT_MAX);
}

function toolResultText(content: unknown): string {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content
      .map((part) => (isObject(part) && typeof part.text === 'string' ? part.text : ''))
      .join(' ');
  }
  return '';
}

function renderAssistant(event: Json): string[] {
  const message = isObject(event.message) ? event.message : null;
  if (!message) return [];
  const content = message.content;
  if (typeof content === 'string') return block('assistant', content);
  if (!Array.isArray(content)) return [];
  const out: string[] = [];
  for (const part of content) {
    if (!isObject(part)) continue;
    if (part.type === 'text' && typeof part.text === 'string') out.push(...block('assistant', part.text));
    else if (part.type === 'tool_use') {
      const name = str(part.name) ?? 'unknown';
      const input = summariseToolInput(part.input);
      out.push(capLine(input ? `tool: ${name} ${input}` : `tool: ${name}`));
    }
  }
  return out;
}

function renderUser(event: Json): string[] {
  const message = isObject(event.message) ? event.message : null;
  if (!message || !Array.isArray(message.content)) return [];
  const out: string[] = [];
  for (const part of message.content) {
    if (isObject(part) && part.type === 'tool_result' && part.is_error === true) {
      out.push(`tool_error: ${oneLine(redact(toolResultText(part.content)), TOOL_ERROR_MAX)}`);
    }
  }
  return out;
}

function renderResult(event: Json, state: StreamState): string[] {
  state.sawResult = true;
  state.resultText = str(event.result);
  state.isError = event.is_error === true;
  state.subtype = str(event.subtype);
  if (typeof event.total_cost_usd === 'number') state.costUsd = event.total_cost_usd;
  if (typeof event.num_turns === 'number') state.numTurns = event.num_turns;
  if (Array.isArray(event.permission_denials)) state.permissionDenials = event.permission_denials.length;
  const sid = str(event.session_id);
  if (sid) state.sessionId = sid;

  const out = state.resultText ? block('result', state.resultText) : [];
  const meta = [
    `subtype=${state.subtype ?? 'unknown'}`,
    `is_error=${state.isError}`,
    `turns=${state.numTurns ?? '?'}`,
    `cost_usd=${state.costUsd ?? '?'}`,
  ];
  if (state.permissionDenials > 0) meta.push(`permission_denials=${state.permissionDenials}`);
  out.push(`result_meta: ${meta.join(' ')}`);
  return out;
}

/** Parses one stdout line, updates `state`, and returns the lines to show for it. */
export function parseStreamLine(rawLine: string, state: StreamState): string[] {
  const line = rawLine.replace(/\r$/, '');
  if (line.trim() === '') return [];

  let event: unknown;
  try {
    event = JSON.parse(line);
  } catch {
    state.malformedLines += 1;
    return [capLine(redactLine(line, state))];
  }
  if (!isObject(event)) {
    state.malformedLines += 1;
    return [capLine(redactLine(line, state))];
  }
  // A JSON event is never part of a key block (base64 lines cannot form an object).
  state.inPrivateKey = false;

  const sid = str(event.session_id);
  switch (event.type) {
    case 'system':
      if (event.subtype === 'init') {
        if (sid) state.sessionId = sid;
        state.model = str(event.model);
        const tools = Array.isArray(event.tools) ? event.tools.filter((t) => typeof t === 'string').join(', ') : '?';
        return [
          capLine(
            redact(
              `system: session ${sid ?? '?'} started (model ${state.model ?? '?'}, permission mode ${str(event.permissionMode) ?? '?'}, tools: ${tools || 'none'})`,
            ),
          ),
        ];
      }
      return [];
    case 'assistant':
      return renderAssistant(event);
    case 'user':
      return renderUser(event);
    case 'result':
      return renderResult(event, state);
    default:
      // stream_event, rate_limit_event and other bookkeeping events carry nothing for a human.
      return [];
  }
}
