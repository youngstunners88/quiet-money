import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { exceedsCeiling, loadConfig } from '../src/config.js';
import { buildPermissionArgs, MODE_TOOLS, parseToolPattern, validateExtraTools } from '../src/permissions.js';
import type { PermissionMode } from '../src/config.js';

function flag(args: string[], name: string): string | null {
  const i = args.indexOf(name);
  return i === -1 ? null : (args[i + 1] ?? null);
}

describe('permission modes', () => {
  it('read_only allows only Read/Glob/Grep and denies writes and shell', () => {
    const args = buildPermissionArgs('read_only', [], { restricted: true });
    assert.equal(flag(args, '--allowedTools'), 'Read,Glob,Grep');
    assert.equal(flag(args, '--disallowedTools'), 'Edit,Write,NotebookEdit,Bash');
    assert.equal(flag(args, '--tools'), 'Read,Glob,Grep');
    assert.equal(flag(args, '--permission-mode'), null);
    assert.equal(flag(args, '--permission-prompts'), 'none');
    assert.ok(args.includes('--strict-mcp-config'));
    assert.ok(args.includes('--restricted'));
    assert.ok(!args.some((a) => /bypassPermissions|dangerously/.test(a)));
  });

  it('standard adds Edit/Write with acceptEdits and scoped extras', () => {
    const extras = validateExtraTools('standard', ['Bash(python -m faceless brain *)']);
    const args = buildPermissionArgs('standard', extras, { restricted: true });
    assert.equal(flag(args, '--permission-mode'), 'acceptEdits');
    assert.equal(flag(args, '--allowedTools'), 'Read,Glob,Grep,Edit,Write,Bash(python -m faceless brain *)');
    assert.equal(flag(args, '--tools'), 'Read,Glob,Grep,Edit,Write,Bash');
    assert.equal(flag(args, '--disallowedTools'), 'NotebookEdit');
  });

  it('standard without extras keeps Bash denied', () => {
    const args = buildPermissionArgs('standard', [], { restricted: false });
    assert.equal(flag(args, '--disallowedTools'), 'NotebookEdit,Bash');
    assert.ok(!args.includes('--restricted'));
  });

  it('full_access adds Bash', () => {
    const args = buildPermissionArgs('full_access', [], { restricted: true });
    assert.equal(flag(args, '--allowedTools'), 'Read,Glob,Grep,Edit,Write,Bash');
    assert.equal(flag(args, '--disallowedTools'), null);
    assert.equal(flag(args, '--permission-mode'), 'acceptEdits');
  });

  it('refuses extras that would widen a mode', () => {
    assert.throws(() => validateExtraTools('read_only', ['Bash(ls)']), { code: 'TOOL_NOT_PERMITTED' });
    assert.throws(() => validateExtraTools('read_only', ['Write']), { code: 'TOOL_NOT_PERMITTED' });
    assert.throws(() => validateExtraTools('standard', ['Bash']), { code: 'TOOL_NOT_PERMITTED' });
    assert.throws(() => validateExtraTools('standard', ['Bash(*)']), { code: 'TOOL_NOT_PERMITTED' });
    assert.throws(() => validateExtraTools('standard', ['WebFetch']), { code: 'TOOL_NOT_PERMITTED' });
    assert.throws(() => validateExtraTools('read_only', ['Read,Bash']), { code: 'INVALID_INPUT' });
    assert.throws(() => validateExtraTools('read_only', ['--dangerously-skip-permissions']), { code: 'INVALID_INPUT' });
  });

  it('accepts extras inside a mode', () => {
    assert.equal(validateExtraTools('read_only', ['Read(src/**)']).length, 1);
    assert.equal(validateExtraTools('standard', ['Bash(npm test *)', 'Edit']).length, 2);
    assert.equal(validateExtraTools('full_access', ['WebFetch']).length, 1);
  });

  it('parses tool patterns', () => {
    assert.deepEqual(parseToolPattern('Bash(git log *)'), { raw: 'Bash(git log *)', base: 'Bash', specifier: 'git log *' });
    assert.deepEqual(parseToolPattern('Read'), { raw: 'Read', base: 'Read', specifier: null });
    assert.equal(parseToolPattern('bad pattern'), null);
  });

  it('refuses nested parentheses and backslashes in any mode (Claude Code would split them into extra rules)', () => {
    for (const mode of ['read_only', 'standard', 'full_access'] as const) {
      assert.throws(() => validateExtraTools(mode, ['Bash(x (y) Bash z)']), { code: 'INVALID_INPUT' }, mode);
      assert.throws(() => validateExtraTools(mode, ['Read(x (y) Bash z)']), { code: 'INVALID_INPUT' }, mode);
      assert.throws(() => validateExtraTools(mode, ['Edit(a\\) Bash']), { code: 'INVALID_INPUT' }, mode);
    }
    assert.throws(() => validateExtraTools('standard', ['Bash(npm test *)', 'Edit(x (y) Bash z)']), { code: 'INVALID_INPUT' });
  });

  it('refuses wildcard-only, launcher and inline-code Bash patterns in standard mode', () => {
    const refused = [
      'Bash(***)', 'Bash(* * *)', 'Bash(*/*)', 'Bash(?*)', 'Bash(:*)', 'Bash(./*)', 'Bash(.)', 'Bash(/)', 'Bash(* npm)',
      'Bash(sh -c *)', 'Bash(bash *)', 'Bash(env *)', 'Bash(/usr/bin/env *)', 'Bash(xargs *)', 'Bash(sudo npm test)',
      'Bash(eval *)', 'Bash(exec *)', 'Bash(nohup *)', 'Bash(timeout 5 *)', 'Bash(nice *)', 'Bash(npx *)', 'Bash(bunx *)',
      'Bash(python *)', 'Bash(python)', 'Bash(python -c *)', 'Bash(python3 -m *)', 'Bash(python3.12 -I -c *)', 'Bash(python:*)',
      'Bash(node *)', 'Bash(node -e *)', 'Bash(perl -e *)', 'Bash(ruby -e *)', 'Bash(deno eval *)', 'Bash(deno run *)',
      'Bash(uv run *)', 'Bash(npm exec *)', 'Bash(npm run *)', 'Bash(pnpm dlx *)', 'Bash(FOO=1 *)', 'Bash(-x *)',
      'WebFetch(*)', 'WebFetch(domain:*)', 'WebFetch(domain:*.com)', 'NotebookEdit(**)', 'NotebookEdit(/**)', 'mcp__x__y(*)',
    ];
    for (const entry of refused) {
      assert.throws(() => validateExtraTools('standard', [entry]), { code: 'TOOL_NOT_PERMITTED' }, entry);
    }
  });

  it('accepts Bash and other tools scoped to a literal command or path in standard mode', () => {
    const accepted = [
      'Bash(npm test *)', 'Bash(npm test:*)', 'Bash(npm run test *)', 'Bash(python -m faceless brain *)', 'Bash(python -m pytest *)',
      'Bash(git log *)', 'Bash(uv run pytest *)', 'Bash(node scripts/check.js)', 'Bash(./scripts/test.sh *)',
      'WebFetch(domain:example.com)', 'NotebookEdit(notebooks/**)',
    ];
    for (const entry of accepted) assert.equal(validateExtraTools('standard', [entry]).length, 1, entry);
  });

  it('never lets a validated entry turn into a wider rule once Claude Code splits the flags', () => {
    // Port of Claude Code's --allowedTools/--tools splitter (2.1.x): commas and spaces separate rules
    // unless inside parentheses, tracked with an on/off flag rather than a depth counter.
    const splitRules = (value: string): string[] => {
      const out: string[] = [];
      let cur = '';
      let inParen = false;
      for (const ch of value) {
        if (ch === '(') {
          inParen = true;
          cur += ch;
        } else if (ch === ')') {
          inParen = false;
          cur += ch;
        } else if (ch === ',') {
          if (inParen) cur += ch;
          else {
            if (cur.trim()) out.push(cur.trim());
            cur = '';
          }
        } else if (ch === ' ') {
          if (inParen) cur += ch;
          else if (cur.trim()) {
            out.push(cur.trim());
            cur = '';
          }
        } else if (cur || ch.trim()) cur += ch;
      }
      if (cur.trim()) out.push(cur.trim());
      return out;
    };

    const fixed = [
      'Bash(x (y) Bash z)', 'Edit(x (y) Bash z)', 'Bash(npm test *)', 'Bash(***)', 'Bash(a) Bash', 'Read(a)(b)', 'Bash(a\\) Bash(b)',
      'Read(src/**)', 'Bash(git log *)', 'WebFetch(domain:example.com)', 'Bash( npm test )', 'Read(()', 'Read())',
    ];
    // Deterministic fuzz over the characters that matter to the splitter.
    const alphabet = ['Bash', 'Edit', 'Read', '(', ')', ' ', '*', 'x', ',', '\\', ':', 'npm', '-'];
    let seed = 7;
    const rand = (n: number): number => {
      seed = (seed * 1103515245 + 12345) % 2147483648;
      return seed % n;
    };
    const fuzz: string[] = [];
    for (let i = 0; i < 3000; i += 1) {
      let t = '';
      const len = 1 + rand(9);
      for (let j = 0; j < len; j += 1) t += alphabet[rand(alphabet.length)];
      fuzz.push(t);
    }

    let checked = 0;
    for (const mode of ['read_only', 'standard'] as PermissionMode[]) {
      for (const entry of [...fixed, ...fuzz]) {
        let extras;
        try {
          extras = validateExtraTools(mode, [entry]);
        } catch {
          continue;
        }
        checked += 1;
        const args = buildPermissionArgs(mode, extras, { restricted: true });
        const allowed = splitRules(flag(args, '--allowedTools') ?? '');
        const expected = new Set<string>([...MODE_TOOLS[mode], ...extras.map((t) => t.raw)]);
        assert.equal(allowed.length, expected.size, `${mode} ${JSON.stringify(entry)} -> ${JSON.stringify(allowed)}`);
        for (const rule of allowed) {
          assert.ok(expected.has(rule), `${mode} ${JSON.stringify(entry)} produced rule ${JSON.stringify(rule)}`);
          if (!rule.includes('(')) assert.ok(MODE_TOOLS[mode].includes(rule), `${mode} ${JSON.stringify(entry)} produced bare ${rule}`);
        }
        const offered = splitRules(flag(args, '--tools') ?? '');
        const bases = new Set<string>([...MODE_TOOLS[mode], ...extras.map((t) => t.base)]);
        assert.deepEqual(new Set(offered), bases, `${mode} ${JSON.stringify(entry)} --tools`);
      }
    }
    assert.ok(checked > 20, `only ${checked} entries validated`);
  });

  it('orders modes for the ceiling', () => {
    assert.equal(exceedsCeiling('standard', 'read_only'), true);
    assert.equal(exceedsCeiling('full_access', 'standard'), true);
    assert.equal(exceedsCeiling('read_only', 'read_only'), false);
    assert.equal(exceedsCeiling('standard', 'full_access'), false);
  });
});

describe('config', () => {
  it('defaults to read_only, 3 workers, 10 minutes', () => {
    const c = loadConfig({});
    assert.equal(c.permissionCeiling, 'read_only');
    assert.equal(c.maxConcurrent, 3);
    assert.equal(c.defaultTimeoutMs, 600_000);
    assert.equal(c.claudeBin, 'claude');
    assert.equal(c.restricted, true);
    assert.ok(c.envStrip.includes('CLAUDE_CODE_SESSION_ID'));
    assert.match(c.logDir, /logs$/);
  });

  it('falls back to read_only on an unknown mode and reports it', () => {
    const c = loadConfig({ WORKER_PERMISSION_MODE: 'root', WORKER_MAX_CONCURRENT: 'many' });
    assert.equal(c.permissionCeiling, 'read_only');
    assert.equal(c.maxConcurrent, 3);
    assert.equal(c.warnings.length, 2);
  });

  it('reads the allowed roots and the ceiling', () => {
    const c = loadConfig({ WORKER_PERMISSION_MODE: 'full_access', WORKER_ALLOWED_ROOTS: '/a:/b/c' });
    assert.equal(c.permissionCeiling, 'full_access');
    assert.deepEqual(c.allowedRoots, ['/a', '/b/c']);
  });
});
