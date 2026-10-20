import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { createRedactor, REDACTED, redactAndCap, secretValuesFromEnv } from '../src/redact.js';

const redact = createRedactor([]);

// Fixtures are assembled at runtime so the source never holds a key-shaped literal (repo and push-protection scanners).
const k = (...parts: string[]): string => parts.join('');
const ALNUM = 'abcdefghijklmnopqrstuvwxyz0123456789';
const UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';

describe('redact', () => {
  const cases: Array<[string, string, string]> = [
    ['Anthropic key', k('key: sk-', 'ant-api03-', ALNUM), 'sk-ant-api03'],
    ['OpenAI-style key', k('use sk-', 'proj-', UPPER, ' now'), 'sk-proj-ABCD'],
    ['OpenRouter key', k('sk-', 'or-v1-', ALNUM), 'sk-or-v1-abcd'],
    ['lv_live key', 'token lv_live_9f8e7d6c5b4a', 'lv_live_9f8e'],
    ['GitHub personal token', k('ghp', '_', UPPER), 'ghp_ABCD'],
    ['GitHub OAuth token', k('gho', '_', UPPER), 'gho_ABCD'],
    ['GitHub fine-grained token', k('github', '_pat_11', UPPER, '_', ALNUM), 'github_pat_11'],
    ['AWS access key id', k('aws AKIA', 'IOSFODNN7ABCDEF', 'G here'), 'IOSFODNN7ABCDEFG'],
    ['JWT', k('jwt eyJ', 'hbGciOiJIUzI1NiJ9', '.eyJ', 'zdWIiOiIxMjM0NTY3ODkwIn0', '.', 'dozjgNryP4J3jVmNHl0w5N'), 'hbGciOiJIUzI1NiJ9'],
    ['Bearer header', 'Authorization: Bearer abc.def-ghi_jkl012345', 'abc.def-ghi'],
    ['NAME=value (KEY)', 'ANTHROPIC_API_KEY=plainvalue123', 'plainvalue123'],
    ['NAME=value (TOKEN, quoted)', 'export GH_TOKEN="quoted value 1"', 'quoted value 1'],
    ['NAME=value (SECRET)', 'client_secret=s3cr3t-v4lu3', 's3cr3t-v4lu3'],
    ['NAME=value (PASSWORD)', 'DB_PASSWORD=hunter2hunter2', 'hunter2hunter2'],
    ['JSON credential field', '{"api_key": "abc123def456"}', 'abc123def456'],
  ];

  for (const [name, input, secret] of cases) {
    it(`removes ${name}`, () => {
      const out = redact(input);
      assert.ok(!out.includes(secret), `${name}: ${out}`);
      assert.ok(out.includes(REDACTED), `${name}: ${out}`);
    });
  }

  it('keeps the variable name and the Bearer word', () => {
    assert.equal(redact('ANTHROPIC_API_KEY=plainvalue123'), `ANTHROPIC_API_KEY=${REDACTED}`);
    assert.equal(redact('Bearer abcdefghijklmnop'), `Bearer ${REDACTED}`);
  });

  it('leaves ordinary text alone', () => {
    const text = 'task-list ready; 3 files changed; see src/index.ts; skeleton=true; tokens used: 1200';
    assert.equal(redact(text), text);
  });

  it('is idempotent', () => {
    const once = redact(k('ANTHROPIC_API_KEY=plainvalue123 and sk-', 'ant-api03-', ALNUM));
    assert.equal(redact(once), once);
  });

  it('hides literal values of credential-like environment variables', () => {
    const env = { MY_SERVICE_TOKEN: 'weird:format/value!!', SHORT_KEY: 'abc', HOME: '/root/not-secret' };
    const values = secretValuesFromEnv(env);
    assert.deepEqual(values, ['weird:format/value!!']);
    const r = createRedactor(values);
    assert.equal(r('value is weird:format/value!! ok'), `value is ${REDACTED} ok`);
    assert.equal(r('/root/not-secret'), '/root/not-secret');
  });

  it('caps long text after redacting', () => {
    const out = redactAndCap(k('a'.repeat(50), ' sk-', 'ant-api03-', ALNUM), 20);
    assert.ok(out.startsWith('a'.repeat(20)));
    assert.match(out, /truncated/);
  });
});
