// spec: specs/ttacart-e2e-order-plan.md
//
// Structured, scope-tagged logging.
//
// Deliberately dependency-free rather than Winston-backed. The interface is the
// part the call sites depend on — `log.info(...)` with a scope tag — and a
// transport layer for a 34-test UI suite that writes only to the console would be
// weight without a reader. If this grows file or JSON transports, swap the
// implementation here and no page object changes.

import { envFlag, envOr } from '../config/env';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const LEVEL_ORDER: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

/** LOG_LEVEL in .env; defaults to info. DEBUG=1 forces debug. */
function activeLevel(): LogLevel {
  if (envFlag('DEBUG')) return 'debug';
  const configured = envOr('LOG_LEVEL', 'info').toLowerCase();
  return (configured in LEVEL_ORDER ? configured : 'info') as LogLevel;
}

export interface Logger {
  debug(message: string): void;
  info(message: string): void;
  warn(message: string): void;
  error(message: string): void;
  /** A child logger whose scope is appended to this one's. */
  child(scope: string): Logger;
}

function emit(scope: string, level: LogLevel, message: string): void {
  if (LEVEL_ORDER[level] < LEVEL_ORDER[activeLevel()]) return;
  const line = `[${level.toUpperCase()}] [${scope}] ${message}`;
  if (level === 'error') console.error(line);
  else if (level === 'warn') console.warn(line);
  else console.log(line);
}

/**
 * A logger tagged with a scope — normally the page object's class name, so a
 * trace reads as which page produced which action rather than a flat stream.
 */
export function createLogger(scope: string): Logger {
  return {
    debug: (m) => emit(scope, 'debug', m),
    info: (m) => emit(scope, 'info', m),
    warn: (m) => emit(scope, 'warn', m),
    error: (m) => emit(scope, 'error', m),
    child: (childScope) => createLogger(`${scope}:${childScope}`),
  };
}
