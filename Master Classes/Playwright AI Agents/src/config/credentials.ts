// spec: specs/ttacart-e2e-order-plan.md §1
//
// Every account this suite uses, read through @config/env so a missing value
// fails with the variable's name rather than as a blank login.

import { envOr, requireEnv } from './env';

/** The application root. Absolute on purpose — this suite does not use baseURL. */
export const APP_URL = envOr(
  'BASE_URL',
  'https://app.thetestingacademy.com/playwright/ttacart/',
);

/**
 * The standard user, from .env.
 *
 * The TTA_ prefix is load-bearing, not tidiness. Windows defines USERNAME as a
 * system environment variable, and dotenv will not overwrite a variable that is
 * already set — so a .env containing `USERNAME=` is read, ignored, and the
 * Windows account name is submitted to the login form instead. dotenv considers
 * declining to overwrite correct behaviour and says nothing, so the failure
 * surfaces as an auth error against a username nobody configured, which sends
 * you looking at the application rather than at the loader.
 */
export const standardUser = {
  get username(): string {
    return requireEnv('TTA_USERNAME');
  },
  get password(): string {
    return requireEnv('TTA_PASSWORD');
  },
};

/**
 * The other accepted accounts. All six documented usernames share the standard
 * password; their verified behavioural differences are in plan §5.
 *
 * Only the locked-out user earns a scenario of its own. performance_glitch_user
 * merely delays login by about four seconds, and visual_user is functionally
 * identical to the standard user apart from an 8px transform on the cart link —
 * a visual-regression fixture, not a functional-failure case.
 */
export const accounts = {
  lockedOut: 'locked_out_user',
  unknown: 'nonexistent_user',
  /** The standard username in the wrong case. Matching is case-sensitive. */
  wrongCase: 'Standard_User',
} as const;
