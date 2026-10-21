// Writes dist/index.js and dist/run-plan.js so the documented commands
// (`node dist/index.js`, `node dist/run-plan.js`) work; the compiled code lives in dist/src/.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'dist');
const shims = {
  'index.js': './src/index.js',
  'run-plan.js': './src/run-plan.js',
};
for (const [name, target] of Object.entries(shims)) {
  const file = path.join(dist, name);
  fs.writeFileSync(file, `#!/usr/bin/env node\nimport { runCli } from '${target}';\nrunCli();\n`);
  fs.chmodSync(file, 0o755);
}
