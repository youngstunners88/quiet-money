import type { PermissionMode } from './config.js';
import { OrchestratorError } from './errors.js';

/** Built-in tools each mode makes available. Nothing outside these (plus checked extras) is ever offered. */
export const MODE_TOOLS: Record<PermissionMode, readonly string[]> = {
  read_only: ['Read', 'Glob', 'Grep'],
  standard: ['Read', 'Glob', 'Grep', 'Edit', 'Write'],
  full_access: ['Read', 'Glob', 'Grep', 'Edit', 'Write', 'Bash'],
};

/** Tools explicitly denied per mode (deny rules win over allow rules in Claude Code). */
const MODE_DENY: Record<PermissionMode, readonly string[]> = {
  read_only: ['Edit', 'Write', 'NotebookEdit', 'Bash'],
  standard: ['NotebookEdit', 'Bash'],
  full_access: [],
};

// Tool name, optionally followed by one parenthesised specifier: Read, Bash(git log *), mcp__x__y.
// No parentheses or backslashes inside the specifier: Claude Code splits --allowedTools on commas and
// spaces with an on/off paren flag (not a depth counter), so "Bash(x (y) Bash z)" would come out as a
// bare "Bash" rule, and backslashes change how it finds the closing paren.
const TOOL_PATTERN = /^([A-Za-z][A-Za-z0-9_-]*)(?:\(([^\n()\\]*)\))?$/;

/** A command name or script path: literal, no wildcard, no `VAR=value` prefix. */
const COMMAND_WORD = /^[A-Za-z0-9_.\/+-]+$/;
/** An argument word with no wildcard in it. */
const LITERAL_WORD = /^[A-Za-z0-9_.\/+@=:-]+$/;
/** Commands whose job is to run another, arbitrary command: never a scope on their own. */
const LAUNCHERS = new Set([
  'sh', 'bash', 'zsh', 'dash', 'ksh', 'mksh', 'fish', 'csh', 'tcsh', 'busybox',
  'env', 'xargs', 'eval', 'exec', 'command', 'builtin', 'source', '.',
  'sudo', 'su', 'doas', 'nohup', 'timeout', 'nice', 'ionice', 'setsid', 'stdbuf', 'time', 'watch',
  'chroot', 'strace', 'script', 'parallel', 'npx', 'bunx', 'pnpx', 'uvx', 'pipx',
]);
/** Interpreters: allowed only with a script or `-m module` after them, never inline code or a wildcard. */
const INTERPRETER = /^(?:python[0-9.]*|pypy[0-9.]*|node|nodejs|perl|ruby|php|lua|luajit|deno|bun|tsx|ts-node|Rscript|osascript|pwsh|powershell)$/;
/** Tools whose subcommand starts any command or file: the word after the subcommand must be scoped too. */
const RUNNERS = new Set(['npm', 'pnpm', 'yarn', 'uv', 'poetry', 'pdm', 'hatch', 'conda', 'mamba', 'bundle']);
const RUN_SUBCOMMANDS = new Set(['run', 'exec', 'x', 'dlx']);
const INLINE_CODE_WORDS = new Set(['eval', 'repl', '-']);

/** True when a specifier pins a non-own tool to something specific (not only wildcards and separators). */
function hasLiteralScope(spec: string): boolean {
  const body = spec.replace(/^[A-Za-z]+:/, ''); // WebFetch(domain:example.com): judge what follows "domain:"
  return /^[A-Za-z0-9_.\/-]/.test(body) && body.replace(/[\s*?:\/.]/g, '').length >= 2;
}

/** Bash specifiers must start with a real command that does not itself run arbitrary commands or inline code. */
function isScopedBash(spec: string): boolean {
  // Legacy prefix syntax "npm test:*" means "npm test" followed by anything.
  const words = spec.replace(/:\*$/, ' *').trim().split(/\s+/);
  let i = 0;
  for (let hops = 0; hops < 4; hops += 1) {
    const word = words[i];
    if (word === undefined || !COMMAND_WORD.test(word) || word.startsWith('-')) return false;
    const name = word.split('/').pop() ?? '';
    if (name === '' || LAUNCHERS.has(name)) return false;
    const next = words[i + 1];
    const interpreter = INTERPRETER.test(name);
    if ((interpreter || RUNNERS.has(name)) && next !== undefined && RUN_SUBCOMMANDS.has(next)) {
      i += 2; // "uv run pytest *" is scoped by "pytest"; "uv run *" and "npm exec *" are not.
      continue;
    }
    if (!interpreter) return true;
    if (next === '-m') {
      const mod = words[i + 2];
      return mod !== undefined && LITERAL_WORD.test(mod) && !mod.startsWith('-');
    }
    return next !== undefined && LITERAL_WORD.test(next) && !next.startsWith('-') && !INLINE_CODE_WORDS.has(next);
  }
  return false;
}

/** standard mode: may a tool outside the mode's own set be added with this specifier? */
export function isScopedExtra(tool: ParsedTool): boolean {
  if (tool.specifier === null || !hasLiteralScope(tool.specifier)) return false;
  return tool.base === 'Bash' ? isScopedBash(tool.specifier) : true;
}

export interface ParsedTool {
  raw: string;
  base: string;
  specifier: string | null;
}

export function parseToolPattern(raw: string): ParsedTool | null {
  const text = raw.trim();
  if (text.length === 0 || text.length > 200 || /[,\u0000]/.test(text)) return null;
  const match = TOOL_PATTERN.exec(text);
  if (!match) return null;
  return { raw: text, base: match[1] as string, specifier: match[2] === undefined ? null : match[2].trim() };
}

/**
 * Checks caller-supplied allowed_tools against the mode and returns them normalised.
 * read_only: only Read/Glob/Grep (optionally scoped). standard: its own tools, or any other tool
 * only when scoped to a specific command/path (e.g. "Bash(python -m faceless brain *)"); see isScopedExtra.
 * full_access: anything.
 */
export function validateExtraTools(mode: PermissionMode, extras: readonly string[]): ParsedTool[] {
  const own = new Set(MODE_TOOLS[mode]);
  const parsed: ParsedTool[] = [];
  for (const raw of extras) {
    const tool = parseToolPattern(raw);
    if (!tool) {
      throw new OrchestratorError(
        'INVALID_INPUT',
        `allowed_tools entry ${JSON.stringify(raw)} is not a tool pattern like "Read" or "Bash(npm test *)" (no commas).`,
        null,
        'Pass one tool or tool pattern per array element, e.g. ["Bash(python -m pytest *)"].',
      );
    }
    if (mode === 'full_access' || own.has(tool.base)) {
      parsed.push(tool);
      continue;
    }
    if (mode === 'standard' && isScopedExtra(tool)) {
      parsed.push(tool);
      continue;
    }
    throw new OrchestratorError(
      'TOOL_NOT_PERMITTED',
      mode === 'read_only'
        ? `allowed_tools entry ${JSON.stringify(raw)} is not allowed in read_only mode (only ${MODE_TOOLS.read_only.join(', ')}).`
        : `allowed_tools entry ${JSON.stringify(raw)} would widen standard mode; other tools must be scoped to a literal command or path (no wildcard-only patterns, shells, launchers or inline-code interpreters), e.g. "${tool.base === 'Bash' ? 'Bash(npm test *)' : `${tool.base}(some/path/**)`}".`,
      null,
      mode === 'read_only'
        ? 'Drop the entry, or use permission_mode "standard" with a scoped pattern (needs confirm_write_access: true and a ceiling of standard or higher).'
        : 'Scope the pattern to the exact command, or use permission_mode "full_access" if the server ceiling allows it.',
    );
  }
  return parsed;
}

/** CLI flags that enforce a permission mode on a `claude -p` worker. */
export function buildPermissionArgs(
  mode: PermissionMode,
  extras: readonly ParsedTool[],
  options: { restricted: boolean },
): string[] {
  const allowed = [...MODE_TOOLS[mode]];
  for (const tool of extras) if (!allowed.includes(tool.raw)) allowed.push(tool.raw);

  // Tools offered to the model: the mode's own plus the base names the extras need.
  const available = [...MODE_TOOLS[mode]];
  for (const tool of extras) if (!available.includes(tool.base)) available.push(tool.base);

  const extraBases = new Set(extras.map((t) => t.base));
  const denied = MODE_DENY[mode].filter((name) => !extraBases.has(name));

  const args: string[] = [];
  if (mode !== 'read_only') args.push('--permission-mode', 'acceptEdits');
  args.push('--tools', available.join(','));
  args.push('--allowedTools', allowed.join(','));
  if (denied.length > 0) args.push('--disallowedTools', denied.join(','));
  // Nobody can answer a prompt in -p mode: anything not pre-approved is denied instead of hanging.
  args.push('--permission-prompts', 'none');
  // No MCP servers in workers: their tools would sit outside the mode's tool list.
  args.push('--strict-mcp-config');
  if (options.restricted) args.push('--restricted');
  return args;
}
