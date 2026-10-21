import assert from 'node:assert/strict';
import path from 'node:path';
import { describe, it } from 'node:test';
import { OrchestratorClient } from '../src/client.js';
import { PACKAGE_ROOT, tempDir } from './helpers.js';

// Starts a REAL read-only Claude Code worker (costs a few cents). Run with: RUN_INTEGRATION=1 npm test
// INTEGRATION_MODEL picks the model (default haiku, the cheapest); CLAUDE_BIN picks the CLI.
const enabled = process.env.RUN_INTEGRATION === '1';

describe('integration: real Claude Code worker', () => {
  const options = { timeout: 8 * 60_000, skip: enabled ? false : 'set RUN_INTEGRATION=1 to run' };
  it('lists the files of this repository and explains its structure (read_only)', options, async () => {
    const env: NodeJS.ProcessEnv = { ...process.env, ORCHESTRATOR_LOG_DIR: tempDir('integration-logs') };
    const client = await OrchestratorClient.connect({ serverEntry: path.join(PACKAGE_ROOT, 'dist', 'index.js'), env });
    try {
      const listed = await client.listWorkers();
      assert.ok(listed.ok);

      const started = await client.startWorker({
        project_path: PACKAGE_ROOT,
        initial_prompt: 'List the files in this repository and explain the project structure',
        model: process.env.INTEGRATION_MODEL ?? 'haiku',
        timeout_minutes: 6,
        label: 'integration',
      });
      assert.ok(started.ok, JSON.stringify(started));
      const id = started.ok ? started.data.worker_id : '';
      assert.equal(started.ok && started.data.permission_mode, 'read_only');

      let status = 'starting';
      const deadline = Date.now() + 7 * 60_000;
      while (['starting', 'running'].includes(status) && Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 3_000));
        const st = await client.getWorkerStatus(id);
        status = st.ok ? st.data.status : 'error';
      }
      const final = await client.getWorkerStatus(id);
      const output = await client.getWorkerOutput(id, 400);
      assert.ok(final.ok && output.ok);
      if (final.ok && output.ok) {
        process.stderr.write(
          `integration worker ${id}: ${final.data.status} ${final.data.reason ?? ''} cost_usd=${final.data.cost_usd} ` +
            `turns=${final.data.num_turns} denials=${final.data.permission_denials}\n`,
        );
        assert.equal(final.data.status, 'completed', output.data.output.slice(-3000));
        assert.ok(final.data.session_id);
        assert.ok((final.data.result_preview ?? '').length > 50);
        assert.match(output.data.output, /\[stdout\] system: session /);
        assert.match(output.data.output, /\[stdout\] tool: (Glob|Read|Grep)/);
        assert.match(output.data.output, /\[stdout\] result: /);
        assert.match(final.data.result_preview ?? '', /src|package\.json|README/);
      }
    } finally {
      await client.close();
    }
  });
});
