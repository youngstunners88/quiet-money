import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { describe, it } from 'node:test';
import { loadConfig } from '../src/config.js';
import { MAX_REPLY_CHARS, toJsonText } from '../src/format.js';
import { workerEnv } from '../src/process-manager.js';
import { expectCode, harness, tempDir } from './helpers.js';

// Assembled at runtime so the source holds no key-shaped literal.
const FAKE_KEY = ['sk-', 'ant-api03-', 'PLANTED'.repeat(4), '0123'].join('');
// A credential-like variable of the server: its literal value is redacted wherever it shows up.
// Set before the first redact() call, which builds the redactor from process.env.
const STRADDLE_SECRET = ['qv7Rt2Lm9X', 'c4Wz8Np3Hs6K'].join('');
process.env.ADV_SERVICE_TOKEN = STRADDLE_SECRET;

const sleepMs = (ms: number): Promise<void> => new Promise((r) => setTimeout(r, ms));

/** Linux: is this pid a live (non-zombie) process? */
function alive(pid: number): boolean {
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    return stat.slice(stat.lastIndexOf(')') + 2).split(' ')[0] !== 'Z';
  } catch {
    return false;
  }
}

async function waitFor(check: () => boolean, ms: number): Promise<boolean> {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    if (check()) return true;
    await sleepMs(50);
  }
  return check();
}

describe('worker lifecycle', () => {
  it('starts a worker and completes with a session id and result', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'hello', label: 'first' });
    assert.match(started.worker_id, /^w-[0-9a-f]{8}$/);
    assert.ok(['starting', 'running'].includes(started.status));
    assert.equal(typeof started.pid, 'number');
    assert.equal(started.permission_mode, 'read_only');

    assert.equal(await h.manager.waitForIdle(started.worker_id, 10_000), true);
    const st = h.manager.getStatus(started.worker_id);
    assert.equal(st.status, 'completed');
    assert.equal(st.reason, null);
    assert.equal(st.exit_code, 0);
    assert.match(st.session_id ?? '', /^[0-9a-f-]{36}$/);
    assert.equal(st.result_preview, 'Fake reply to: hello');
    assert.equal(st.cost_usd, 0.0125);
    assert.ok(st.elapsed_ms >= 0);
    assert.ok(!Number.isNaN(Date.parse(st.last_activity)));
    assert.equal(st.can_send_prompt, true);

    const list = h.manager.listWorkers();
    assert.equal(list.workers.length, 1);
    const w = list.workers[0];
    assert.equal(w?.worker_id, started.worker_id);
    assert.equal(w?.project_path, h.projectDir);
    assert.equal(w?.status, 'completed');
    assert.equal(w?.label, 'first');
    assert.equal(w?.permission_mode, 'read_only');
    assert.ok(w?.started_at);
  });

  it('runs the worker in the real project path with read_only flags and no inherited session id', async () => {
    const h = harness({}, {}, { ...process.env, CLAUDE_CODE_SESSION_ID: 'parent-session' });
    const link = path.join(tempDir('links'), 'project-link');
    fs.symlinkSync(h.projectDir, link);
    const started = await h.manager.startWorker({ projectPath: link, initialPrompt: 'ECHOARGS', model: 'haiku' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const st = h.manager.getStatus(started.worker_id);
    assert.equal(st.project_path, h.projectDir);
    const echoed = JSON.parse(st.result_preview ?? '{}') as { argv: string[]; cwd: string; sessionEnv: string | null };
    assert.equal(echoed.cwd, h.projectDir);
    assert.equal(echoed.sessionEnv, null);
    const a = echoed.argv;
    assert.equal(a[0], '-p');
    assert.equal(a[1], 'ECHOARGS');
    assert.deepEqual(a.slice(2, 5), ['--output-format', 'stream-json', '--verbose']);
    assert.equal(a[a.indexOf('--model') + 1], 'haiku');
    assert.ok(a.includes('--session-id'));
    assert.equal(a[a.indexOf('--allowedTools') + 1], 'Read,Glob,Grep');
    assert.equal(a[a.indexOf('--disallowedTools') + 1], 'Edit,Write,NotebookEdit,Bash');
    assert.ok(!a.includes('--add-dir'));
    assert.ok(!a.includes('--dangerously-skip-permissions'));
    assert.ok(!a.includes('bypassPermissions'));
  });

  it('keeps a prompt that starts with a dash from being read as a flag', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: '--help me ECHOARGS' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const echoed = JSON.parse(h.manager.getStatus(started.worker_id).result_preview ?? '{}') as { argv: string[] };
    assert.equal(echoed.argv[1], ' --help me ECHOARGS');
  });

  it('creates a waiting worker without an initial prompt and starts it on send_prompt', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir });
    assert.equal(started.status, 'waiting_for_input');
    assert.equal(started.pid, null);
    const reply = await h.manager.sendPrompt({ workerId: started.worker_id, prompt: 'first task', waitSeconds: 10 });
    assert.equal(reply.finished, true);
    assert.equal(reply.status, 'completed');
    assert.equal(reply.response, 'Fake reply to: first task');
  });
});

describe('output capture', () => {
  it('labels stdout and stderr lines and renders stream-json', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'TOOLUSE STDERR' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const out = h.manager.getOutput(started.worker_id);
    const lines = out.output.split('\n');
    assert.ok(lines.every((l) => l.startsWith('[stdout] ') || l.startsWith('[stderr] ')), out.output);
    assert.ok(lines.some((l) => l.startsWith('[stdout] system: session ')));
    assert.ok(lines.includes('[stdout] tool: Glob pattern="**/*.ts" path="src"'));
    assert.ok(lines.includes('[stdout] tool_error: Permission denied for Bash'));
    assert.ok(lines.includes('[stderr] warning: first stderr line'));
    assert.ok(lines.some((l) => l.startsWith('[stdout] result: Fake reply to: TOOLUSE STDERR')));
    assert.equal(out.truncated, false);
  });

  it('honours tail_lines', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'TOOLUSE' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const out = h.manager.getOutput(started.worker_id, 2);
    assert.equal(out.returned_lines, 2);
    assert.match(out.output, /result_meta:/);
  });

  it('truncates very long output and marks the cut', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'BIGOUTPUT' });
    await h.manager.waitForIdle(started.worker_id, 20_000);
    const out = h.manager.getOutput(started.worker_id, 2000);
    assert.equal(out.truncated, true);
    assert.ok(out.returned_lines < 2000);
    assert.ok(out.total_lines > 3000);
    assert.match(out.output.split('\n')[0] as string, /^\[truncated: \d+ earlier line\(s\) omitted/);
    assert.ok(toJsonText(out).length <= MAX_REPLY_CHARS, `reply is ${toJsonText(out).length} chars`);
    assert.match(out.output, /result_meta:/);
  });

  it('keeps malformed output as raw text and still completes', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'MALFORMED' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    assert.equal(h.manager.getStatus(started.worker_id).status, 'completed');
    const out = h.manager.getOutput(started.worker_id).output;
    assert.match(out, /\[stdout\] this line is not json/);
    assert.match(out, /\[stdout\] \[1,2,3\]/);
  });

  it('redacts keys in returned output', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'LEAK' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const out = h.manager.getOutput(started.worker_id).output;
    assert.ok(!out.includes('sk-ant-api03-AAAA'));
    assert.ok(!out.includes('plainvalue123'));
    assert.ok(!out.includes('abcdefghijklmnop1234'));
    assert.match(out, /\[REDACTED\]/);
    assert.ok(!(h.manager.getStatus(started.worker_id).result_preview ?? '').includes('plainvalue123'));
  });
});

describe('failures and timeouts', () => {
  it('fails a worker that runs past its timeout', async () => {
    const h = harness({ defaultTimeoutMs: 400 });
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'SLEEP' });
    assert.equal(await h.manager.waitForIdle(started.worker_id, 10_000), true);
    const st = h.manager.getStatus(started.worker_id);
    assert.equal(st.status, 'failed');
    assert.equal(st.reason, 'timeout');
    assert.equal(st.signal, 'SIGTERM');
    const log = h.readLog();
    assert.ok(log.some((e) => e.event === 'termination' && e.reason === 'timeout' && e.worker_id === started.worker_id));
  });

  it('escalates to SIGKILL when the worker ignores SIGTERM', async () => {
    const h = harness({ defaultTimeoutMs: 300, killGraceMs: 300 });
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'IGNORETERM' });
    assert.equal(await h.manager.waitForIdle(started.worker_id, 10_000), true);
    const st = h.manager.getStatus(started.worker_id);
    assert.equal(st.status, 'failed');
    assert.equal(st.reason, 'timeout');
    assert.equal(st.signal, 'SIGKILL');
  });

  it('caps a caller timeout at WORKER_MAX_TIMEOUT_MS', async () => {
    const h = harness({ maxTimeoutMs: 500 });
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'SLEEP', timeoutMinutes: 60 });
    assert.equal(started.timeout_ms, 500);
    await h.manager.waitForIdle(started.worker_id, 10_000);
    assert.equal(h.manager.getStatus(started.worker_id).reason, 'timeout');
  });

  it('reports a crash with its exit code and stderr', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'CRASH' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const st = h.manager.getStatus(started.worker_id);
    assert.equal(st.status, 'failed');
    assert.equal(st.reason, 'exit_code_2');
    assert.equal(st.exit_code, 2);
    assert.match(h.manager.getOutput(started.worker_id).output, /\[stderr\] fatal: simulated crash/);
  });

  it('fails when the CLI exits without a result or with an error result', async () => {
    const h = harness();
    const a = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'NORESULT' });
    const b = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'ERRORRESULT' });
    await h.manager.waitForIdle(a.worker_id, 10_000);
    await h.manager.waitForIdle(b.worker_id, 10_000);
    assert.equal(h.manager.getStatus(a.worker_id).reason, 'no_result_event');
    assert.equal(h.manager.getStatus(b.worker_id).status, 'failed');
    assert.equal(h.manager.getStatus(b.worker_id).reason, 'result_error: error_during_execution');
  });

  it('returns SPAWN_FAILED when the CLI cannot be started', async () => {
    const h = harness({ claudeBin: '/nonexistent/claude-binary' });
    const err = await expectCode(() => h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'x' }), 'SPAWN_FAILED');
    assert.ok(err.workerId);
    assert.match(err.suggestedFix, /CLAUDE_BIN/);
    const st = h.manager.getStatus(err.workerId as string);
    assert.equal(st.status, 'failed');
    assert.match(st.reason ?? '', /^spawn_error/);
  });
});

describe('invalid inputs', () => {
  it('rejects a project path that does not exist or is a file', async () => {
    const h = harness();
    await expectCode(() => h.manager.startWorker({ projectPath: '/definitely/not/here', initialPrompt: 'x' }), 'PROJECT_PATH_NOT_FOUND');
    await expectCode(
      () => h.manager.startWorker({ projectPath: path.join(h.projectDir, 'README.md'), initialPrompt: 'x' }),
      'PROJECT_PATH_NOT_FOUND',
    );
  });

  it('rejects a project path outside WORKER_ALLOWED_ROOTS, including through a symlink', async () => {
    const allowed = tempDir('allowed');
    const h = harness({ allowedRoots: [allowed] });
    await expectCode(() => h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'x' }), 'PROJECT_PATH_NOT_ALLOWED');
    const sneaky = path.join(allowed, 'escape');
    fs.symlinkSync(h.projectDir, sneaky);
    await expectCode(() => h.manager.startWorker({ projectPath: sneaky, initialPrompt: 'x' }), 'PROJECT_PATH_NOT_ALLOWED');
    const inside = path.join(allowed, 'proj');
    fs.mkdirSync(inside);
    const ok = await h.manager.startWorker({ projectPath: inside });
    assert.equal(ok.status, 'waiting_for_input');
  });

  it('refuses a mode above the ceiling', async () => {
    const h = harness();
    const err = await expectCode(
      () => h.manager.startWorker({ projectPath: h.projectDir, permissionMode: 'standard', confirmWriteAccess: true }),
      'PERMISSION_CEILING',
    );
    assert.match(err.suggestedFix, /WORKER_PERMISSION_MODE/);
  });

  it('requires explicit confirmation for write access', async () => {
    const h = harness({ permissionCeiling: 'full_access' });
    await expectCode(() => h.manager.startWorker({ projectPath: h.projectDir, permissionMode: 'standard' }), 'CONFIRMATION_REQUIRED');
    await expectCode(
      () => h.manager.startWorker({ projectPath: h.projectDir, permissionMode: 'full_access', confirmWriteAccess: false }),
      'CONFIRMATION_REQUIRED',
    );
    const ok = await h.manager.startWorker({
      projectPath: h.projectDir,
      permissionMode: 'standard',
      confirmWriteAccess: true,
      initialPrompt: 'ECHOARGS',
    });
    await h.manager.waitForIdle(ok.worker_id, 10_000);
    const argv = (JSON.parse(h.manager.getStatus(ok.worker_id).result_preview ?? '{}') as { argv: string[] }).argv;
    assert.equal(argv[argv.indexOf('--permission-mode') + 1], 'acceptEdits');
    assert.equal(argv[argv.indexOf('--allowedTools') + 1], 'Read,Glob,Grep,Edit,Write');
  });

  it('refuses tools that would widen read_only and bad model names', async () => {
    const h = harness();
    await expectCode(
      () => h.manager.startWorker({ projectPath: h.projectDir, allowedTools: ['Bash(rm -rf *)'] }),
      'TOOL_NOT_PERMITTED',
    );
    await expectCode(() => h.manager.startWorker({ projectPath: h.projectDir, model: '--dangerously-skip-permissions' }), 'INVALID_INPUT');
  });

  it('rejects NUL characters before they reach spawn()', async () => {
    const h = harness();
    await expectCode(() => h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'a\u0000b' }), 'INVALID_INPUT');
    await expectCode(() => h.manager.startWorker({ projectPath: h.projectDir, allowedTools: ['Read(a\u0000)'] }), 'INVALID_INPUT');
    const waiting = await h.manager.startWorker({ projectPath: h.projectDir });
    await expectCode(() => h.manager.sendPrompt({ workerId: waiting.worker_id, prompt: 'x\u0000' }), 'INVALID_INPUT');
    assert.equal(h.manager.getStatus(waiting.worker_id).status, 'waiting_for_input');
  });

  it('limits concurrent workers', async () => {
    const h = harness({ maxConcurrent: 2 });
    const a = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'SLEEP' });
    const b = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'SLEEP' });
    await expectCode(() => h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'x' }), 'TOO_MANY_WORKERS');
    assert.equal(h.manager.listWorkers().running, 2);
    await h.manager.stopWorker(a.worker_id);
    const c = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'x' });
    await h.manager.waitForIdle(c.worker_id, 10_000);
    await h.manager.shutdown();
    assert.equal(h.manager.getStatus(b.worker_id).status, 'terminated');
  });

  it('returns WORKER_NOT_FOUND for unknown worker ids', async () => {
    const h = harness();
    assert.throws(() => h.manager.getStatus('w-nope'), { code: 'WORKER_NOT_FOUND' });
    assert.throws(() => h.manager.getOutput('w-nope'), { code: 'WORKER_NOT_FOUND' });
    await expectCode(() => h.manager.stopWorker('w-nope'), 'WORKER_NOT_FOUND');
    await expectCode(() => h.manager.sendPrompt({ workerId: 'w-nope', prompt: 'x' }), 'WORKER_NOT_FOUND');
  });
});

describe('send_prompt', () => {
  it('refuses while the worker is busy', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'SLOW' });
    const err = await expectCode(() => h.manager.sendPrompt({ workerId: started.worker_id, prompt: 'next' }), 'WORKER_BUSY');
    assert.equal(err.workerId, started.worker_id);
    await h.manager.waitForIdle(started.worker_id, 10_000);
  });

  it('resumes the recorded session for a follow-up', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'first' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const sessionId = h.manager.getStatus(started.worker_id).session_id as string;
    const reply = await h.manager.sendPrompt({ workerId: started.worker_id, prompt: 'second', waitSeconds: 10 });
    assert.equal(reply.worker_id, started.worker_id);
    assert.equal(reply.finished, true);
    assert.equal(reply.status, 'completed');
    assert.equal(reply.session_id, sessionId);
    assert.equal(reply.response, `Resumed ${sessionId}: second`);
    assert.equal(reply.turn_cost_usd, 0.0125);
    const st = h.manager.getStatus(started.worker_id);
    assert.equal(st.prompts_sent, 2);
    assert.equal(st.cost_usd, 0.025);
  });

  it('returns running when the reply takes longer than wait_seconds', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'first' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const reply = await h.manager.sendPrompt({ workerId: started.worker_id, prompt: 'SLOW', waitSeconds: 0.2 });
    assert.equal(reply.finished, false);
    assert.equal(reply.response, null);
    assert.ok(['starting', 'running'].includes(reply.status));
    await h.manager.waitForIdle(started.worker_id, 10_000);
    assert.equal(h.manager.getStatus(started.worker_id).status, 'completed');
  });

  it('explains that a follow-up is impossible without a session id', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'NOSESSION' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const err = await expectCode(
      () => h.manager.sendPrompt({ workerId: started.worker_id, prompt: 'more' }),
      'FOLLOWUP_UNSUPPORTED',
    );
    assert.match(err.message, /non-interactive/);
    assert.match(err.suggestedFix, /initial_prompt/);
  });

  it('refuses prompts to a terminated worker', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir });
    await h.manager.stopWorker(started.worker_id);
    await expectCode(() => h.manager.sendPrompt({ workerId: started.worker_id, prompt: 'x' }), 'WORKER_TERMINATED');
  });
});

describe('stop_worker', () => {
  it('terminates a running worker and returns its last output', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'SLEEP' });
    await new Promise((r) => setTimeout(r, 300));
    const stopped = await h.manager.stopWorker(started.worker_id);
    assert.equal(stopped.status, 'terminated');
    assert.equal(stopped.reason, 'stopped_by_request');
    assert.equal(stopped.already_finished, false);
    assert.match(stopped.last_output, /\[stdout\] system: session/);
    assert.equal(h.manager.listWorkers().running, 0);
    assert.ok(h.readLog().some((e) => e.event === 'termination' && e.worker_id === started.worker_id));
  });

  it('leaves a completed worker as it is', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'done' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const stopped = await h.manager.stopWorker(started.worker_id);
    assert.equal(stopped.status, 'completed');
    assert.equal(stopped.already_finished, true);
  });
});

describe('list_workers retention', () => {
  it('keeps only the newest finished workers', async () => {
    const h = harness({ retainFinished: 2 });
    const ids: string[] = [];
    for (let i = 0; i < 4; i += 1) {
      const s = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: `n${i}` });
      await h.manager.waitForIdle(s.worker_id, 10_000);
      ids.push(s.worker_id);
    }
    const listed = h.manager.listWorkers().workers.map((w) => w.worker_id);
    assert.deepEqual(listed.sort(), ids.slice(2).sort());
  });
});

describe('audit log', () => {
  it('logs start, prompt, completion and termination without secrets', async () => {
    const h = harness();
    const started = await h.manager.startWorker({
      projectPath: h.projectDir,
      initialPrompt: `use ANTHROPIC_API_KEY=${FAKE_KEY} and token ${FAKE_KEY}`,
      label: 'audit',
    });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    await h.manager.sendPrompt({ workerId: started.worker_id, prompt: `again Bearer ${FAKE_KEY}`, waitSeconds: 10 });
    const sleeper = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'SLEEP' });
    await h.manager.stopWorker(sleeper.worker_id);
    await expectCode(() => h.manager.startWorker({ projectPath: '/nope', initialPrompt: FAKE_KEY }), 'PROJECT_PATH_NOT_FOUND');

    const raw = fs.readFileSync(h.logFile, 'utf8');
    assert.ok(!raw.includes('PLANTED'), 'planted key reached the log');
    const events = h.readLog();
    const kinds = events.map((e) => e.event);
    for (const kind of ['start', 'prompt', 'completion', 'termination', 'start_refused']) assert.ok(kinds.includes(kind), kind);
    const start = events.find((e) => e.event === 'start' && e.worker_id === started.worker_id);
    assert.equal(start?.project_path, h.projectDir);
    assert.equal(start?.permission_mode, 'read_only');
    assert.match(String(start?.prompt), /\[REDACTED\]/);
    for (const e of events) {
      assert.ok(typeof e.ts === 'string');
      assert.ok(!('env' in e));
    }
    const completion = events.find((e) => e.event === 'completion');
    assert.equal(completion?.cost_usd, 0.0125);
  });

  it('caps logged prompts at 2000 characters', async () => {
    const h = harness();
    await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'y'.repeat(5000) }).then((s) =>
      h.manager.waitForIdle(s.worker_id, 10_000),
    );
    const start = h.readLog().find((e) => e.event === 'start');
    assert.ok(String(start?.prompt).length < 2100);
  });
});

describe('worker environment', () => {
  const base: NodeJS.ProcessEnv = {
    PATH: process.env.PATH,
    HOME: '/home/someone',
    LANG: 'C.UTF-8',
    LC_ALL: 'C.UTF-8',
    HTTPS_PROXY: 'http://proxy.local:3128',
    NODE_EXTRA_CA_CERTS: '/etc/ca.pem',
    ANTHROPIC_API_KEY: 'anthropic-test-value',
    CLAUDE_CODE_OAUTH_TOKEN: 'oauth-test-value',
    FOO_API_KEY: 'planted-foo-value',
    GITHUB_TOKEN: 'planted-gh-value',
    AWS_ACCESS_KEY_ID: 'planted-aws-id',
    AWS_SECRET_ACCESS_KEY: 'planted-aws-secret',
    CLOUDFLARE_API_TOKEN: 'planted-cf-value',
    CLAUDECODE: '1',
    CLAUDE_CODE_SESSION_ID: 'parent-session',
    CLAUDE_CODE_CHILD_SESSION: '1',
    CLAUDE_CODE_MESSAGING_SOCKET: '/tmp/parent.sock',
    CLAUDE_CODE_MESSAGING_TOKEN: 'parent-messaging',
    CLAUDE_CODE_REMOTE: 'true',
    CLAUDE_CODE_REMOTE_SESSION_ID: 'parent-remote',
    SESSION_INGRESS_URL: 'https://ingress.local',
    CLAUDE_SESSION_INGRESS_TOKEN_FILE: '/run/ingress-token',
    OPERATOR_EXTRA: 'opted-in',
  };

  it('builds the worker environment from an allowlist', () => {
    const env = workerEnv(base, loadConfig({}));
    for (const name of ['PATH', 'HOME', 'LANG', 'LC_ALL', 'HTTPS_PROXY', 'NODE_EXTRA_CA_CERTS', 'ANTHROPIC_API_KEY', 'CLAUDE_CODE_OAUTH_TOKEN']) {
      assert.equal(env[name], base[name], name);
    }
    for (const name of Object.keys(base).filter((n) => !(n in env))) assert.equal(env[name], undefined);
    for (const name of [
      'FOO_API_KEY', 'GITHUB_TOKEN', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'CLOUDFLARE_API_TOKEN', 'CLAUDECODE',
      'CLAUDE_CODE_SESSION_ID', 'CLAUDE_CODE_CHILD_SESSION', 'CLAUDE_CODE_MESSAGING_SOCKET', 'CLAUDE_CODE_MESSAGING_TOKEN',
      'CLAUDE_CODE_REMOTE', 'CLAUDE_CODE_REMOTE_SESSION_ID', 'SESSION_INGRESS_URL', 'CLAUDE_SESSION_INGRESS_TOKEN_FILE', 'OPERATOR_EXTRA',
    ]) {
      assert.ok(!(name in env), name);
    }
  });

  it('passes AWS or Google credentials only when Claude Code is set to use Bedrock or Vertex', () => {
    const bedrock = workerEnv({ ...base, CLAUDE_CODE_USE_BEDROCK: '1' }, loadConfig({}));
    assert.equal(bedrock.AWS_SECRET_ACCESS_KEY, 'planted-aws-secret');
    assert.equal(bedrock.CLAUDE_CODE_USE_BEDROCK, '1');
    const vertex = workerEnv({ ...base, CLAUDE_CODE_USE_VERTEX: '1', GOOGLE_APPLICATION_CREDENTIALS: '/k.json', CLOUD_ML_REGION: 'us-east5' }, loadConfig({}));
    assert.equal(vertex.GOOGLE_APPLICATION_CREDENTIALS, '/k.json');
    assert.equal(vertex.CLOUD_ML_REGION, 'us-east5');
    assert.ok(!('AWS_SECRET_ACCESS_KEY' in vertex));
    const off = workerEnv({ ...base, CLAUDE_CODE_USE_BEDROCK: '0' }, loadConfig({}));
    assert.ok(!('AWS_SECRET_ACCESS_KEY' in off));
  });

  it('adds WORKER_ENV_PASS names but never the parent-session ones, and WORKER_ENV_STRIP still wins', () => {
    const config = loadConfig({
      WORKER_ENV_PASS: 'OPERATOR_EXTRA, CLAUDE_CODE_REMOTE_SESSION_ID,CLAUDE_CODE_MESSAGING_TOKEN,SESSION_INGRESS_URL,CLAUDECODE',
      WORKER_ENV_STRIP: 'ANTHROPIC_API_KEY',
    });
    const env = workerEnv(base, config);
    assert.equal(env.OPERATOR_EXTRA, 'opted-in');
    for (const name of ['CLAUDE_CODE_REMOTE_SESSION_ID', 'CLAUDE_CODE_MESSAGING_TOKEN', 'SESSION_INGRESS_URL', 'CLAUDECODE', 'ANTHROPIC_API_KEY']) {
      assert.ok(!(name in env), name);
    }
  });

  it('a real worker sees neither the server keys nor the parent session variables', async () => {
    const h = harness({}, { WORKER_ENV_PASS: 'OPERATOR_EXTRA' }, base);
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'ECHOENV' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const st = h.manager.getStatus(started.worker_id);
    assert.equal(st.status, 'completed', h.manager.getOutput(started.worker_id).output);
    const names = (JSON.parse(st.result_preview ?? '{}') as { envNames: string[] }).envNames;
    assert.ok(names.includes('PATH'));
    assert.ok(names.includes('ANTHROPIC_API_KEY'));
    assert.ok(names.includes('OPERATOR_EXTRA'));
    for (const name of ['FOO_API_KEY', 'GITHUB_TOKEN', 'AWS_SECRET_ACCESS_KEY', 'CLAUDE_CODE_MESSAGING_TOKEN', 'CLAUDE_CODE_REMOTE_SESSION_ID', 'SESSION_INGRESS_URL', 'CLAUDECODE', 'CLAUDE_CODE_SESSION_ID']) {
      assert.ok(!names.includes(name), `${name} reached the worker`);
    }
  });
});

describe('redaction of multi-line and cut secrets', () => {
  it('hides every line of a private key block in assistant text, result text, raw stdout and stderr', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'PEMKEY' });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const out = h.manager.getOutput(started.worker_id, 2000).output;
    assert.ok(!out.includes('PEMBODY'), out);
    assert.match(out, /\[REDACTED\]/);
    assert.match(out, /after the key/);
    assert.match(out, /\[stdout\] result_meta:/);
    const stopped = await h.manager.stopWorker(started.worker_id);
    assert.ok(!stopped.last_output.includes('PEMBODY'), stopped.last_output);
    assert.ok(!(h.manager.getStatus(started.worker_id).result_preview ?? '').includes('PEMBODY'));
  });

  it('redacts before cutting a long line, so no part of a secret survives the 4000-character cap', async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: `STRADDLE ${STRADDLE_SECRET}` });
    await h.manager.waitForIdle(started.worker_id, 10_000);
    const out = h.manager.getOutput(started.worker_id, 2000).output;
    assert.match(out, /line truncated/);
    assert.ok(!out.includes(STRADDLE_SECRET.slice(0, 6)), 'a prefix of the secret survived the cap');
  });
});

describe('shell commands a worker started', () => {
  const linux = process.platform === 'linux';

  async function childPid(h: ReturnType<typeof harness>, workerId: string): Promise<number> {
    let pid = 0;
    await waitFor(() => {
      const m = /child pid (\d+)/.exec(h.manager.getOutput(workerId).output);
      if (m) pid = Number(m[1]);
      return pid > 0;
    }, 10_000);
    assert.ok(pid > 0, 'the fake CLI never reported its child');
    return pid;
  }

  it('stop_worker also ends detached children when the CLI ignores SIGTERM', { skip: !linux && 'needs /proc' }, async () => {
    const h = harness({ killGraceMs: 300 });
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'SPAWNCHILD IGNORETERM' });
    const pid = await childPid(h, started.worker_id);
    try {
      assert.ok(alive(pid));
      const stopped = await h.manager.stopWorker(started.worker_id);
      assert.equal(stopped.status, 'terminated');
      assert.ok(await waitFor(() => !alive(pid), 3_000), `child ${pid} outlived stop_worker`);
    } finally {
      try {
        process.kill(pid, 'SIGKILL');
      } catch {
        // already gone
      }
    }
  });

  it('ends detached children left behind when the CLI exits on its own', { skip: !linux && 'needs /proc' }, async () => {
    const h = harness();
    const started = await h.manager.startWorker({ projectPath: h.projectDir, initialPrompt: 'SPAWNCHILD' });
    const pid = await childPid(h, started.worker_id);
    try {
      await h.manager.waitForIdle(started.worker_id, 10_000);
      assert.equal(h.manager.getStatus(started.worker_id).status, 'completed');
      assert.ok(await waitFor(() => !alive(pid), 3_000), `child ${pid} outlived the worker`);
    } finally {
      try {
        process.kill(pid, 'SIGKILL');
      } catch {
        // already gone
      }
    }
  });
});
