// spec: specs/ttacart-e2e-order-plan.md
//
// The single entry point for .env loading. Every other module reads the
// environment THROUGH this one, never from process.env directly.
//
// The ordering matters and is the reason this file exists. Imports are hoisted,
// so a spec that reads process.env at module scope can run before dotenv has
// loaded anything — the value is silently undefined rather than wrong, which is
// the hardest kind of bug to see. Loading here, at first import of the config
// module, means anything that imports a typed reader below is guaranteed to get
// a loaded environment.

import * as dotenv from 'dotenv';

dotenv.config();

/**
 * Read a required variable, failing loudly if it is missing.
 *
 * Preferred over `process.env.X ?? ''` everywhere: an empty-string fallback
 * turns a configuration mistake into a test failure somewhere else entirely —
 * a login that fails against a blank username, reported as an auth bug.
 */
export function requireEnv(name: string): string {
  const value = process.env[name];
  if (value === undefined || value === '') {
    throw new Error(
      `Missing required environment variable ${name}. ` +
        `Copy .env.example to .env and fill it in.`,
    );
  }
  return value;
}

/** Read an optional variable, falling back to a default. */
export function envOr(name: string, fallback: string): string {
  const value = process.env[name];
  return value === undefined || value === '' ? fallback : value;
}

/**
 * Assert a set of variables is present without reading them.
 *
 * Used by the fixture layer so a misconfigured .env fails once, up front, with
 * every missing name listed — rather than one at a time as each test reaches
 * the line that needed it.
 */
export function assertEnv(...names: string[]): void {
  const missing = names.filter(
    (n) => process.env[n] === undefined || process.env[n] === '',
  );
  if (missing.length > 0) {
    throw new Error(
      `Missing required environment variable(s): ${missing.join(', ')}. ` +
        `Copy .env.example to .env and fill it in.`,
    );
  }
}

/** Read a boolean flag. Anything other than "1"/"true" is false. */
export function envFlag(name: string): boolean {
  const value = (process.env[name] ?? '').toLowerCase();
  return value === '1' || value === 'true';
}
