import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { ElicitRequestSchema, type ElicitResult } from '@modelcontextprotocol/sdk/types.js';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { after, before, describe, it } from 'node:test';
import { OrchestratorClient } from '../src/client.js';
import { createServer } from '../src/tools.js';
import { FAKE_CLAUDE, harness, PACKAGE_ROOT, tempDir, type Harness } from './helpers.js';

interface TextResult {
  isError?: boolean;
  content: Array<{ type: string; text?: string }>;
}

describe('MCP tools (in-memory transport)', () => {
  let h: Harness;
  let client: Client;

  before(async () => {
    h = harness();
    const server = createServer(h.manager);
    const [clientSide, serverSide] = InMemoryTransport.createLinkedPair();
    await server.connect(serverSide);
    client = new Client({ name: 'test', version: '0.0.0' });
    await client.connect(clientSide);
  });

  after(async () => {
    await h.manager.shutdown();
    await client.close();
  });

  async function call(name: string, args: Record<string, unknown>): Promise<{ isError: boolean; body: Record<string, unknown> }> {
    const res = (await client.callTool({ name, arguments: args })) as TextResult;
    assert.equal(res.content[0]?.type, 'text');
    return { isError: res.isError === true, body: JSON.parse(res.content[0]?.text ?? '{}') as Record<string, unknown> };
  }

  it('lists the six tools with JSON schemas', async () => {
    const { tools } = await client.listTools();
    assert.deepEqual(
      tools.map((t) => t.name).sort(),
      ['get_worker_output', 'get_worker_status', 'list_workers', 'send_prompt', 'start_worker', 'stop_worker'],
    );
    const start = tools.find((t) => t.name === 'start_worker');
    assert.equal(start?.inputSchema.type, 'object');
    assert.deepEqual(start?.inputSchema.required, ['project_path']);
    const props = start?.inputSchema.properties as Record<string, { enum?: string[] }>;
    assert.deepEqual(props.permission_mode?.enum, ['read_only', 'standard', 'full_access']);
    const output = tools.find((t) => t.name === 'get_worker_output');
    const tail = (output?.inputSchema.properties as Record<string, { default?: number; maximum?: number }>).tail_lines;
    assert.equal(tail?.default, 200);
    assert.equal(tail?.maximum, 2000);
  });

  it('returns structured JSON errors for invalid input', async () => {
    const bad = await call('start_worker', { project_path: h.projectDir, permission_mode: 'root' });
    assert.equal(bad.isError, true);
    assert.deepEqual(Object.keys(bad.body).sort(), ['error_code', 'message', 'suggested_fix', 'worker_id']);
    assert.equal(bad.body.error_code, 'INVALID_INPUT');
    assert.match(String(bad.body.message), /permission_mode/);

    const missing = await call('start_worker', {});
    assert.equal(missing.body.error_code, 'INVALID_INPUT');

    const extra = await call('get_worker_status', { worker_id: 'w-1', verbose: true });
    assert.equal(extra.body.error_code, 'INVALID_INPUT');
    assert.equal(extra.body.worker_id, 'w-1');

    const tail = await call('get_worker_output', { worker_id: 'w-1', tail_lines: 5000 });
    assert.equal(tail.body.error_code, 'INVALID_INPUT');

    const unknown = await call('get_worker_status', { worker_id: 'w-unknown' });
    assert.equal(unknown.body.error_code, 'WORKER_NOT_FOUND');
    assert.equal(unknown.body.worker_id, 'w-unknown');
    assert.ok(String(unknown.body.suggested_fix).length > 0);

    const path404 = await call('start_worker', { project_path: '/no/such/dir' });
    assert.equal(path404.body.error_code, 'PROJECT_PATH_NOT_FOUND');

    const confirm = await call('start_worker', { project_path: h.projectDir, permission_mode: 'standard' });
    assert.equal(confirm.body.error_code, 'PERMISSION_CEILING');

    const tool = await call('no_such_tool', {});
    assert.equal(tool.body.error_code, 'UNKNOWN_TOOL');
  });

  it('runs a worker end to end through the tools', async () => {
    const started = await call('start_worker', { project_path: h.projectDir, initial_prompt: 'hello there', label: 'mcp' });
    assert.equal(started.isError, false);
    const id = String(started.body.worker_id);
    await h.manager.waitForIdle(id, 10_000);

    const status = await call('get_worker_status', { worker_id: id });
    assert.equal(status.body.status, 'completed');
    for (const key of ['elapsed_ms', 'last_activity', 'pid', 'session_id', 'cost_usd', 'exit_code', 'reason']) {
      assert.ok(key in status.body, key);
    }

    const output = await call('get_worker_output', { worker_id: id });
    assert.match(String(output.body.output), /\[stdout\] result: Fake reply to: hello there/);

    const follow = await call('send_prompt', { worker_id: id, prompt: 'and again', wait_seconds: 10 });
    assert.equal(follow.body.status, 'completed');
    assert.match(String(follow.body.response), /^Resumed /);

    const listed = await call('list_workers', {});
    const workers = listed.body.workers as Array<Record<string, unknown>>;
    assert.ok(workers.some((w) => w.worker_id === id && w.label === 'mcp'));
    assert.equal(listed.body.max_concurrent, 3);
    assert.equal(listed.body.permission_ceiling, 'read_only');

    const stopped = await call('stop_worker', { worker_id: id });
    assert.equal(stopped.body.already_finished, true);
  });
});

describe('start_worker asks the user before write access (MCP elicitation)', () => {
  async function connect(h: Harness, answers: ElicitResult[] | null): Promise<{ client: Client; asked: string[] }> {
    const server = createServer(h.manager);
    const [clientSide, serverSide] = InMemoryTransport.createLinkedPair();
    await server.connect(serverSide);
    const asked: string[] = [];
    const client = new Client({ name: 'test', version: '0.0.0' }, answers ? { capabilities: { elicitation: {} } } : {});
    if (answers) {
      client.setRequestHandler(ElicitRequestSchema, async (request) => {
        asked.push(request.params.message);
        return answers.shift() ?? { action: 'cancel' };
      });
    }
    await client.connect(clientSide);
    return { client, asked };
  }

  async function start(client: Client, args: Record<string, unknown>): Promise<{ isError: boolean; body: Record<string, unknown> }> {
    const res = (await client.callTool({ name: 'start_worker', arguments: args })) as TextResult;
    return { isError: res.isError === true, body: JSON.parse(res.content[0]?.text ?? '{}') as Record<string, unknown> };
  }

  it('starts a writing worker only when the user accepts, whatever confirm_write_access says', async () => {
    const h = harness({ permissionCeiling: 'standard' });
    const { client, asked } = await connect(h, [
      { action: 'decline' },
      { action: 'accept', content: { approve: false } },
      { action: 'cancel' },
      { action: 'accept', content: { approve: true } },
    ]);
    try {
      const request = { project_path: h.projectDir, permission_mode: 'standard', confirm_write_access: true, initial_prompt: 'ECHOARGS', allowed_tools: ['Bash(npm test *)'] };
      for (let i = 0; i < 3; i += 1) {
        const refused = await start(client, request);
        assert.equal(refused.isError, true);
        assert.equal(refused.body.error_code, 'CONFIRMATION_REQUIRED');
      }
      assert.equal(h.readLog().filter((e) => e.event === 'start_refused' && e.error_code === 'CONFIRMATION_REQUIRED').length, 3);
      assert.equal(h.manager.listWorkers().workers.length, 0);

      const { confirm_write_access: _ignored, ...withoutFlag } = request;
      const ok = await start(client, withoutFlag);
      assert.equal(ok.isError, false, JSON.stringify(ok.body));
      assert.equal(ok.body.permission_mode, 'standard');
      await h.manager.waitForIdle(String(ok.body.worker_id), 10_000);

      assert.equal(asked.length, 4);
      assert.match(asked[0] as string, /standard/);
      assert.ok((asked[0] as string).includes(h.projectDir));
      assert.match(asked[0] as string, /Bash\(npm test \*\)/);

      const readOnly = await start(client, { project_path: h.projectDir, initial_prompt: 'hello' });
      assert.equal(readOnly.isError, false);
      assert.equal(asked.length, 4, 'read_only must not ask');
    } finally {
      await h.manager.shutdown();
      await client.close();
    }
  });

  it('falls back to confirm_write_access for clients without elicitation', async () => {
    const h = harness({ permissionCeiling: 'standard' });
    const { client } = await connect(h, null);
    try {
      const refused = await start(client, { project_path: h.projectDir, permission_mode: 'standard' });
      assert.equal(refused.body.error_code, 'CONFIRMATION_REQUIRED');
      const ok = await start(client, { project_path: h.projectDir, permission_mode: 'standard', confirm_write_access: true });
      assert.equal(ok.isError, false, JSON.stringify(ok.body));
      assert.equal(ok.body.status, 'waiting_for_input');
    } finally {
      await h.manager.shutdown();
      await client.close();
    }
  });
});

describe('stdio server and client library', () => {
  it('builds the documented entry points', () => {
    for (const file of ['dist/index.js', 'dist/run-plan.js', 'dist/src/index.js']) {
      assert.ok(fs.existsSync(path.join(PACKAGE_ROOT, file)), file);
    }
  });

  it('serves the tools over stdio and runs a worker', async () => {
    const logDir = tempDir('stdio-logs');
    const project = tempDir('stdio-project');
    const client = await OrchestratorClient.connect({
      serverEntry: path.join(PACKAGE_ROOT, 'dist', 'index.js'),
      env: { ...process.env, CLAUDE_BIN: FAKE_CLAUDE, ORCHESTRATOR_LOG_DIR: logDir, WORKER_KILL_GRACE_MS: '200' },
      stderr: 'ignore',
    });
    try {
      assert.equal((await client.listToolNames()).length, 6);
      const listed = await client.listWorkers();
      assert.ok(listed.ok);
      assert.deepEqual(listed.ok && listed.data.workers, []);

      const started = await client.startWorker({ project_path: project, initial_prompt: 'over stdio' });
      assert.ok(started.ok, JSON.stringify(started));
      const id = started.ok ? started.data.worker_id : '';
      let status = '';
      for (let i = 0; i < 100 && status !== 'completed'; i += 1) {
        const st = await client.getWorkerStatus(id);
        status = st.ok ? st.data.status : 'error';
        if (status !== 'completed') await new Promise((r) => setTimeout(r, 100));
      }
      assert.equal(status, 'completed');
      const out = await client.getWorkerOutput(id, 50);
      assert.ok(out.ok && out.data.output.includes('Fake reply to: over stdio'));

      const err = await client.stopWorker('w-missing');
      assert.equal(err.ok, false);
      assert.equal(!err.ok && err.error.error_code, 'WORKER_NOT_FOUND');
    } finally {
      await client.close();
    }
    assert.ok(fs.existsSync(path.join(logDir, 'orchestrator.jsonl')));
  });
});
