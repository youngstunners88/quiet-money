import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { describe, it } from 'node:test';
import { parseArgs } from '../src/run-plan.js';
import { FAKE_CLAUDE, PACKAGE_ROOT, tempDir } from './helpers.js';

function runPlan(plan: unknown): { status: number | null; stdout: string; out: string } {
  const dir = tempDir('plan');
  fs.mkdirSync(path.join(dir, 'proj'));
  const planFile = path.join(dir, 'plan.json');
  fs.writeFileSync(planFile, JSON.stringify(plan));
  const out = path.join(dir, 'out');
  const res = spawnSync(process.execPath, [path.join(PACKAGE_ROOT, 'dist', 'run-plan.js'), planFile, '--out', out, '--poll-seconds', '0.2'], {
    env: { ...process.env, CLAUDE_BIN: FAKE_CLAUDE, ORCHESTRATOR_LOG_DIR: path.join(dir, 'logs'), WORKER_KILL_GRACE_MS: '200' },
    encoding: 'utf8',
    timeout: 60_000,
  });
  return { status: res.status, stdout: res.stdout, out };
}

describe('run-plan CLI', () => {
  it('parses its arguments', () => {
    const o = parseArgs(['plan.json', '--out', 'x', '--poll-seconds', '2']);
    assert.equal(path.basename(o.planFile), 'plan.json');
    assert.equal(path.basename(o.outDir), 'x');
    assert.equal(o.pollSeconds, 2);
    assert.throws(() => parseArgs([]), /usage/);
    assert.throws(() => parseArgs(['p.json', '--poll-seconds', '0']), /positive/);
  });

  it('runs every worker through one server, writes logs and a summary, exits 0 when all complete', () => {
    const { status, stdout, out } = runPlan({
      workers: [
        { label: 'alpha', project_path: 'proj', prompt: 'first job' },
        { label: 'beta', project_path: 'proj', prompt: 'second job', model: 'haiku' },
        { label: 'gamma', project_path: 'proj', prompt: 'third job' },
        { label: 'delta', project_path: 'proj', prompt: 'fourth job (queued behind the limit of 3)' },
      ],
    });
    assert.equal(status, 0, stdout);
    assert.match(stdout, /^list_workers:/);
    const summary = JSON.parse(fs.readFileSync(path.join(out, 'summary.json'), 'utf8')) as {
      all_completed: boolean;
      workers: Array<{ label: string; status: string; log_file: string }>;
    };
    assert.equal(summary.all_completed, true);
    assert.deepEqual(summary.workers.map((w) => w.status), ['completed', 'completed', 'completed', 'completed']);
    const alphaLog = fs.readFileSync(path.join(out, 'alpha.log'), 'utf8');
    assert.match(alphaLog, /\[stdout\] result: Fake reply to: first job/);
  });

  it('exits 1 when a worker fails or cannot start', () => {
    const { status, out } = runPlan({
      workers: [
        { label: 'ok', project_path: 'proj', prompt: 'fine' },
        { label: 'boom', project_path: 'proj', prompt: 'CRASH' },
        { label: 'nope', project_path: 'proj', prompt: 'x', permission_mode: 'full_access', confirm_write_access: true },
      ],
    });
    assert.equal(status, 1);
    const summary = JSON.parse(fs.readFileSync(path.join(out, 'summary.json'), 'utf8')) as {
      all_completed: boolean;
      workers: Array<{ label: string; status: string; reason: string | null; start_error: { error_code: string } | null }>;
    };
    assert.equal(summary.all_completed, false);
    const byLabel = Object.fromEntries(summary.workers.map((w) => [w.label, w]));
    assert.equal(byLabel.ok?.status, 'completed');
    assert.equal(byLabel.boom?.status, 'failed');
    assert.equal(byLabel.boom?.reason, 'exit_code_2');
    assert.equal(byLabel.nope?.status, 'start_failed');
    assert.equal(byLabel.nope?.start_error?.error_code, 'PERMISSION_CEILING');
    assert.match(fs.readFileSync(path.join(out, 'boom.log'), 'utf8'), /\[stderr\] fatal: simulated crash/);
  });

  it('on Ctrl-C stops the running workers, keeps every log and marks the stopped worker terminated', { skip: process.platform === 'win32' && 'needs process groups' }, async () => {
    const dir = tempDir('plan-int');
    fs.mkdirSync(path.join(dir, 'proj'));
    const planFile = path.join(dir, 'plan.json');
    fs.writeFileSync(
      planFile,
      JSON.stringify({ workers: [{ label: 'quick', project_path: 'proj', prompt: 'first job' }, { label: 'slow', project_path: 'proj', prompt: 'SLEEP' }] }),
    );
    const out = path.join(dir, 'out');
    // Own process group, like a terminal's foreground job: SIGINT to the group reaches run-plan and its server.
    const child = spawn(process.execPath, [path.join(PACKAGE_ROOT, 'dist', 'run-plan.js'), planFile, '--out', out, '--poll-seconds', '0.2'], {
      env: { ...process.env, CLAUDE_BIN: FAKE_CLAUDE, ORCHESTRATOR_LOG_DIR: path.join(dir, 'logs'), WORKER_KILL_GRACE_MS: '200' },
      stdio: ['ignore', 'pipe', 'pipe'],
      detached: true,
    });
    let stdout = '';
    child.stdout.setEncoding('utf8');
    child.stdout.on('data', (chunk: string) => {
      stdout += chunk;
    });
    child.stderr.resume();
    const exited = new Promise<number | null>((resolve) => child.on('close', (code) => resolve(code)));
    const deadline = Date.now() + 20_000;
    while (!(/quick: \S+ -> completed/.test(stdout) && /started slow/.test(stdout)) && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 50));
    }
    assert.match(stdout, /quick: \S+ -> completed/);
    process.kill(-(child.pid as number), 'SIGINT');
    const timer = setTimeout(() => process.kill(-(child.pid as number), 'SIGKILL'), 30_000);
    const code = await exited;
    clearTimeout(timer);

    assert.equal(code, 1, stdout);
    const summary = JSON.parse(fs.readFileSync(path.join(out, 'summary.json'), 'utf8')) as {
      interrupted: boolean;
      error: string | null;
      workers: Array<{ label: string; status: string; log_file: string | null }>;
    };
    assert.equal(summary.interrupted, true);
    assert.equal(summary.error, null, stdout);
    const byLabel = Object.fromEntries(summary.workers.map((w) => [w.label, w]));
    assert.equal(byLabel.quick?.status, 'completed');
    assert.equal(byLabel.slow?.status, 'terminated');
    assert.ok(byLabel.quick?.log_file && fs.existsSync(byLabel.quick.log_file), 'quick.log missing');
    assert.match(fs.readFileSync(path.join(out, 'quick.log'), 'utf8'), /Fake reply to: first job/);
    assert.ok(byLabel.slow?.log_file && fs.existsSync(byLabel.slow.log_file), 'slow.log missing');
  });
});

