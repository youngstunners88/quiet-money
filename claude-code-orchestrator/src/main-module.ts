import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

/** True when the module with this import.meta.url is the script node was started with. */
export function isMainModule(metaUrl: string): boolean {
  const entry = process.argv[1];
  if (!entry) return false;
  try {
    return pathToFileURL(fs.realpathSync(entry)).href === metaUrl;
  } catch {
    return false;
  }
}
