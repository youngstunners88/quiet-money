import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { MAX_LINE_CHARS, newStreamState, parseStreamLine } from '../src/stream-parser.js';

// A credential-like variable of this process; set before the first redact() call builds the redactor.
const SECRET = ['zx81Kq0Pw', 'Lm4Rt7Vy2Nb5'].join('');
process.env.PARSER_TEST_TOKEN = SECRET;
const PEM = [['-----BEGIN', 'RSA PRIVATE KEY-----'].join(' '), 'MIIEbodyLINEone', 'bodyLINEtwo==', ['-----END', 'RSA PRIVATE KEY-----'].join(' ')];

describe('stream-json parser', () => {
  it('reads init, assistant text, tool use and result', () => {
    const s = newStreamState();
    const init = parseStreamLine(
      JSON.stringify({ type: 'system', subtype: 'init', session_id: 'abc', model: 'm', tools: ['Read'], permissionMode: 'default' }),
      s,
    );
    assert.equal(s.sessionId, 'abc');
    assert.match(init[0] as string, /^system: session abc started/);

    const text = parseStreamLine(
      JSON.stringify({ type: 'assistant', message: { content: [{ type: 'text', text: 'one\ntwo\n' }] } }),
      s,
    );
    assert.deepEqual(text, ['assistant: one', '  two']);

    const tool = parseStreamLine(
      JSON.stringify({
        type: 'assistant',
        message: { content: [{ type: 'tool_use', name: 'Read', input: { file_path: '/p/README.md' } }] },
      }),
      s,
    );
    assert.deepEqual(tool, ['tool: Read file_path="/p/README.md"']);

    const result = parseStreamLine(
      JSON.stringify({
        type: 'result',
        subtype: 'success',
        is_error: false,
        result: 'done',
        session_id: 'abc',
        total_cost_usd: 0.5,
        num_turns: 3,
        permission_denials: [{}],
      }),
      s,
    );
    assert.equal(result[0], 'result: done');
    assert.match(result[1] as string, /^result_meta: subtype=success is_error=false turns=3 cost_usd=0.5 permission_denials=1/);
    assert.equal(s.sawResult, true);
    assert.equal(s.costUsd, 0.5);
    assert.equal(s.resultText, 'done');
  });

  it('keeps malformed lines as raw text and never throws', () => {
    const s = newStreamState();
    assert.deepEqual(parseStreamLine('not json at all', s), ['not json at all']);
    assert.deepEqual(parseStreamLine('{"type":"assistant","message":', s), ['{"type":"assistant","message":']);
    assert.deepEqual(parseStreamLine('[1,2]', s), ['[1,2]']);
    assert.deepEqual(parseStreamLine('{"type":"assistant","message":{"content":42}}', s), []);
    assert.deepEqual(parseStreamLine('', s), []);
    assert.equal(s.malformedLines, 3);
  });

  it('skips bookkeeping events and shows tool errors', () => {
    const s = newStreamState();
    assert.deepEqual(parseStreamLine(JSON.stringify({ type: 'stream_event', event: {} }), s), []);
    const err = parseStreamLine(
      JSON.stringify({ type: 'user', message: { content: [{ type: 'tool_result', is_error: true, content: 'denied' }] } }),
      s,
    );
    assert.deepEqual(err, ['tool_error: denied']);
  });

  it('caps very long lines', () => {
    const s = newStreamState();
    const [line] = parseStreamLine('z'.repeat(MAX_LINE_CHARS * 2), s);
    assert.ok((line as string).length < MAX_LINE_CHARS + 100);
    assert.match(line as string, /line truncated/);
  });

  it('redacts a private key block before splitting text into lines', () => {
    const s = newStreamState();
    const text = ['before', ...PEM, 'after'].join('\n');
    const assistant = parseStreamLine(JSON.stringify({ type: 'assistant', message: { content: [{ type: 'text', text }] } }), s);
    const result = parseStreamLine(JSON.stringify({ type: 'result', subtype: 'success', is_error: false, result: text }), s);
    const all = [...assistant, ...result].join('\n');
    assert.ok(!all.includes('bodyLINE'), all);
    assert.match(all, /assistant: before/);
    assert.match(all, /after/);
  });

  it('redacts every raw (non-JSON) line between BEGIN and END', () => {
    const s = newStreamState();
    const out = [...PEM, 'plain line after'].flatMap((line) => parseStreamLine(line, s));
    assert.ok(!out.join('\n').includes('bodyLINE'), out.join('\n'));
    assert.equal(out[out.length - 1], 'plain line after');
    assert.equal(s.inPrivateKey, false);
  });

  it('redacts before shortening tool input, tool errors and long lines', () => {
    const s = newStreamState();
    const command = `${'c'.repeat(185)}${SECRET}`;
    const tool = parseStreamLine(JSON.stringify({ type: 'assistant', message: { content: [{ type: 'tool_use', name: 'Bash', input: { command } }] } }), s);
    assert.ok(!tool.join('').includes(SECRET.slice(0, 4)), tool.join(''));
    const err = parseStreamLine(
      JSON.stringify({ type: 'user', message: { content: [{ type: 'tool_result', is_error: true, content: `${'e'.repeat(295)}${SECRET}` }] } }),
      s,
    );
    assert.ok(!err.join('').includes(SECRET.slice(0, 4)), err.join(''));
    const raw = parseStreamLine(`${'r'.repeat(MAX_LINE_CHARS - 5)}${SECRET}`, s);
    assert.ok(!raw.join('').includes(SECRET.slice(0, 4)), 'raw line kept a prefix of the secret');
  });
});

