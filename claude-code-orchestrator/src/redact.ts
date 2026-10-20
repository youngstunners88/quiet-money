/**
 * Removes key-like strings from text before it is logged or returned to a caller.
 * Redaction is deliberately greedy: hiding a harmless value is cheaper than leaking a key.
 */

export const REDACTED = '[REDACTED]';

interface Rule {
  pattern: RegExp;
  replace: string;
}

const RULES: Rule[] = [
  // PEM private keys (whole block when it sits in one string).
  {
    pattern: /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)/g,
    replace: REDACTED,
  },
  // Anthropic (sk-ant-...), OpenAI/OpenRouter style (sk-..., sk-proj-..., sk-or-v1-...).
  { pattern: /\bsk-[A-Za-z0-9_-]{16,}/g, replace: REDACTED },
  { pattern: /\blv_live_[A-Za-z0-9_-]{6,}/g, replace: REDACTED },
  // GitHub tokens.
  { pattern: /\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{16,}/g, replace: REDACTED },
  { pattern: /\bgithub_pat_[A-Za-z0-9_]{16,}/g, replace: REDACTED },
  // AWS access key ids.
  { pattern: /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/g, replace: REDACTED },
  // JWTs (header.payload[.signature]).
  { pattern: /\beyJ[A-Za-z0-9_-]{5,}\.eyJ[A-Za-z0-9_-]{5,}(?:\.[A-Za-z0-9_-]+)?/g, replace: REDACTED },
  // Authorization: Bearer <token>
  { pattern: /\b(Bearer)\s+[A-Za-z0-9._~+/-]{8,}=*/gi, replace: `$1 ${REDACTED}` },
  // NAME=value where NAME looks like a credential (API_KEY=..., --auth-token=..., password='...').
  {
    pattern: /\b([A-Za-z0-9_.-]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)[A-Za-z0-9_.-]*)([ \t]*=[ \t]*)("[^"\n]*"|'[^'\n]*'|[^\s"'&;,]+)/gi,
    replace: `$1$2${REDACTED}`,
  },
  // "name": "value" in JSON where the name looks like a credential.
  {
    pattern: /("[A-Za-z0-9_.-]*(?:key|token|secret|password|passwd)[A-Za-z0-9_.-]*"[ \t]*:[ \t]*)"(?:[^"\\\n]|\\.)*"/gi,
    replace: `$1"${REDACTED}"`,
  },
];

const SECRET_ENV_NAME = /(KEY|TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIAL|AUTH)/i;
const MIN_LITERAL_LENGTH = 8;

/** Values of credential-like environment variables, longest first. */
export function secretValuesFromEnv(env: Record<string, string | undefined> = process.env): string[] {
  const values = new Set<string>();
  for (const [name, value] of Object.entries(env)) {
    if (!value || !SECRET_ENV_NAME.test(name)) continue;
    const v = value.trim();
    if (v.length >= MIN_LITERAL_LENGTH) values.add(v);
  }
  return [...values].sort((a, b) => b.length - a.length);
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export type Redactor = (text: string) => string;

/** Builds a redactor that also hides the given literal values wherever they appear. */
export function createRedactor(literalSecrets: string[] = []): Redactor {
  const literals = literalSecrets.filter((s) => s.length >= MIN_LITERAL_LENGTH);
  const literalPattern =
    literals.length > 0 ? new RegExp(literals.map(escapeRegExp).join('|'), 'g') : null;

  return (text: string): string => {
    if (!text) return text;
    let out = literalPattern ? text.replace(literalPattern, REDACTED) : text;
    for (const rule of RULES) out = out.replace(rule.pattern, rule.replace);
    return out;
  };
}

let defaultRedactor: Redactor | null = null;

/** Redacts known key formats plus the values of this process's credential-like environment variables. */
export function redact(text: string): string {
  defaultRedactor ??= createRedactor(secretValuesFromEnv());
  return defaultRedactor(text);
}

/** Redacts, then caps the text at `max` characters with a visible marker. */
export function redactAndCap(text: string, max: number): string {
  const clean = redact(text);
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max)}... [truncated ${clean.length - max} chars]`;
}

const PEM_BEGIN = /-----BEGIN [A-Z ]*PRIVATE KEY-----/;
const PEM_END = /-----END [A-Z ]*PRIVATE KEY-----/;

/** Carries "inside a private key block" from one line of a stream to the next. */
export interface LineRedactState {
  inPrivateKey: boolean;
}

/**
 * Redacts one line of a line-by-line stream (stderr, raw stdout). A private key spans several lines,
 * so every line from a BEGIN ... PRIVATE KEY marker up to and including its END marker is hidden.
 */
export function redactLine(line: string, state: LineRedactState): string {
  if (state.inPrivateKey) {
    const end = PEM_END.exec(line);
    if (!end) return REDACTED;
    state.inPrivateKey = false;
    return `${REDACTED}${redact(line.slice(end.index + end[0].length))}`;
  }
  const begin = PEM_BEGIN.exec(line);
  if (begin && !PEM_END.test(line.slice(begin.index + begin[0].length))) state.inPrivateKey = true;
  return redact(line);
}
