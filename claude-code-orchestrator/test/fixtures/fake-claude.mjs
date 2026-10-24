#!/usr/bin/env node
// Stand-in for the Claude Code CLI in unit tests. Prints stream-json like
// `claude -p ... --output-format stream-json --verbose`. Behaviour is chosen by words in the prompt:
//   SLEEP        sleep 60 s (longer than any test timeout)
//   IGNORETERM   ignore SIGTERM, so only SIGKILL stops it
//   SLOW         wait 1.5 s before answering
//   CRASH        write to stderr and exit 2 without a result
//   MALFORMED    print non-JSON and broken JSON lines before the result
//   TOOLUSE      emit a tool_use block and a failed tool_result
//   LEAK         put fake keys in the assistant text
//   BIGOUTPUT    print 3000 long assistant lines
//   STDERR       write two stderr lines, then succeed
//   NORESULT     exit 0 without a result line
//   ERRORRESULT  finish with an is_error result
//   NOSESSION    never report a session id
//   ECHOARGS     put argv and cwd (as JSON) in the result text
//   ECHOENV      put the sorted names (never the values) of its environment variables in the result text
//   PEMKEY       print a multi-line private key block in assistant text, result text, raw stdout and stderr
//   STRADDLE <v> put <v> at character 3990 of the assistant and result lines (just across the 4000 cap)
//   VERIFIER ROLE  (the verifier prompt) answer with a VERDICT line: FAIL when the prompt also holds VERIFYFAIL, no line when it holds NOVERDICT, else PASS
//   SPAWNCHILD   start a detached `sleep 300` (own session, like Claude Code's Bash tool) and print its pid

const argv = process.argv.slice(2);
const valueOf = (flag) => {
  const i = argv.indexOf(flag);
  return i === -1 ? null : (argv[i + 1] ?? null);
};

const pIndex = argv.indexOf('-p');
const prompt = pIndex === -1 ? '' : (argv[pIndex + 1] ?? '');
const resume = valueOf('--resume');
const has = (word) => prompt.includes(word);
const sessionId = has('NOSESSION') ? undefined : (resume ?? valueOf('--session-id') ?? 'fake-session-0000');
const model = valueOf('--model') ?? 'fake-model';

import { spawn } from 'node:child_process';

const emit = (obj) => process.stdout.write(`${JSON.stringify(obj)}\n`);
// Assembled at runtime so this file holds no key-shaped literal.
const PEM_BEGIN = ['-----BEGIN', 'PRIVATE KEY-----'].join(' ');
const PEM_END = ['-----END', 'PRIVATE KEY-----'].join(' ');
const pemLines = (tag) => [PEM_BEGIN, ...[0, 1, 2].map((i) => `MIIEPEMBODY${tag}${i}${'Qx7'.repeat(16)}`), PEM_END];
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function main() {
  if (has('IGNORETERM')) process.on('SIGTERM', () => {});
  if (has('SPAWNCHILD')) {
    const child = spawn('sleep', ['300'], { detached: true, stdio: 'ignore' });
    child.unref();
    process.stdout.write(`${JSON.stringify({ type: 'assistant', session_id: 'pre-init', message: { content: [{ type: 'text', text: `child pid ${child.pid}` }] } })}\n`);
  }

  emit({
    type: 'system',
    subtype: 'init',
    session_id: sessionId,
    model,
    cwd: process.cwd(),
    tools: (valueOf('--tools') ?? 'Read,Glob,Grep').split(','),
    permissionMode: valueOf('--permission-mode') ?? 'default',
  });
  emit({ type: 'stream_event', session_id: sessionId, event: { type: 'message_start' } });

  if (has('SLEEP') || has('IGNORETERM')) await sleep(60_000);
  if (has('SLOW')) await sleep(1_500);

  if (has('CRASH')) {
    process.stderr.write('fatal: simulated crash\n');
    process.exitCode = 2;
    return;
  }

  if (has('MALFORMED')) {
    process.stdout.write('this line is not json\n');
    process.stdout.write('{"type":"assistant","message":{"content":[{"type":"text","text":"cut off\n');
    process.stdout.write('[1,2,3]\n');
  }

  if (has('PEMKEY')) {
    for (const line of pemLines('RAWOUT')) process.stdout.write(`${line}\n`);
    for (const line of pemLines('STDERR')) process.stderr.write(`${line}\n`);
  }

  if (has('STDERR')) {
    process.stderr.write('warning: first stderr line\n');
    process.stderr.write('warning: second stderr line\n');
  }

  if (has('TOOLUSE')) {
    emit({
      type: 'assistant',
      session_id: sessionId,
      message: { content: [{ type: 'tool_use', id: 't1', name: 'Glob', input: { pattern: '**/*.ts', path: 'src' } }] },
    });
    emit({
      type: 'user',
      session_id: sessionId,
      message: { content: [{ type: 'tool_result', tool_use_id: 't1', is_error: true, content: 'Permission denied for Bash' }] },
    });
  }

  if (has('BIGOUTPUT')) {
    const filler = 'x'.repeat(200);
    for (let i = 0; i < 3000; i += 1) {
      emit({ type: 'assistant', session_id: sessionId, message: { content: [{ type: 'text', text: `line ${i} ${filler}` }] } });
    }
  }

  let text = resume ? `Resumed ${resume}: ${prompt}` : `Fake reply to: ${prompt}`;
  if (has('LEAK')) {
    // Assembled at runtime so this file holds no key-shaped literal.
    const fakeKey = ['sk-', 'ant-api03-', 'A'.repeat(36)].join('');
    text += `\nkey ${fakeKey} and ANTHROPIC_API_KEY=plainvalue123 and Bearer abcdefghijklmnop1234`;
  }
  if (has('VERIFIER ROLE') && !has('NOVERDICT')) text += `\n1. PASS or FAIL per criterion\nVERDICT: ${has('VERIFYFAIL') ? 'FAIL' : 'PASS'}`;
  if (has('ECHOARGS')) text = JSON.stringify({ argv, cwd: process.cwd(), sessionEnv: process.env.CLAUDE_CODE_SESSION_ID ?? null });
  if (has('ECHOENV')) text = JSON.stringify({ envNames: Object.keys(process.env).sort() });
  if (has('PEMKEY')) text = ['here is a key', ...pemLines('TEXT'), 'after the key'].join('\n');
  if (has('STRADDLE')) {
    const value = prompt.split(/\s+/)[1] ?? '';
    text = `${'a'.repeat(3990 - 'assistant: '.length)}${value} tail`;
  }

  emit({ type: 'assistant', session_id: sessionId, message: { content: [{ type: 'text', text }] } });

  if (has('NORESULT')) return;

  const isError = has('ERRORRESULT');
  emit({
    type: 'result',
    subtype: isError ? 'error_during_execution' : 'success',
    is_error: isError,
    result: text,
    session_id: sessionId,
    total_cost_usd: 0.0125,
    num_turns: 1,
    permission_denials: [],
  });
  // Let the process end on its own: process.exit() here could drop output still queued for the pipe.
  process.exitCode = 0;
}

main();
