/** Upper bound for any single tool reply, so a chatty worker cannot flood the orchestrator's context. */
export const MAX_REPLY_CHARS = 20_000;

/** The one JSON formatting used for every tool reply (sizes are computed with it). */
export function toJsonText(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export interface FittedText {
  text: string;
  keptLines: number;
  omittedLines: number;
}

/**
 * Joins the newest lines that fit in `budget` characters once JSON-escaped.
 * When lines are dropped, a marker line saying so is put first.
 */
export function fitTail(lines: readonly string[], budget: number, hint: string): FittedText {
  const escapedLength = (s: string): number => JSON.stringify(s).length - 2;
  const markerReserve = 220;
  const total = lines.reduce((n, l) => n + escapedLength(l) + 2, 0);
  if (total <= budget) return { text: lines.join('\n'), keptLines: lines.length, omittedLines: 0 };

  const room = Math.max(0, budget - markerReserve);
  const kept: string[] = [];
  let used = 0;
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const line = lines[i] as string;
    const cost = escapedLength(line) + 2;
    if (used + cost > room) {
      if (kept.length === 0) {
        // A single oversized line: keep its end.
        const tailChars = Math.max(0, Math.floor(room / 2) - 40);
        kept.unshift(`...${line.slice(-tailChars)}`);
      }
      break;
    }
    kept.unshift(line);
    used += cost;
  }
  const omitted = lines.length - kept.length;
  const marker = `[truncated: ${omitted} earlier line(s) omitted to stay under ${MAX_REPLY_CHARS} characters; ${hint}]`;
  return { text: [marker, ...kept].join('\n'), keptLines: kept.length, omittedLines: omitted };
}

/** Caps a free-text field with a visible marker. */
export function capText(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max)}\n[truncated: ${text.length - max} more characters]` : text;
}
