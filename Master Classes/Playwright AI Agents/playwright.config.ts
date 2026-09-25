// spec: specs/ttacart-e2e-order-plan.md
//
// @config/env is imported FIRST, before anything else, and that ordering is the
// point. Imports are hoisted, so a module that reads process.env at import time
// can run before dotenv has loaded — the value comes back undefined rather than
// wrong, which is the hardest kind of configuration bug to see. Importing the
// config module here guarantees the environment is loaded before any spec,
// fixture or page object is evaluated.

import { defineConfig, devices } from '@playwright/test';
import './src/config/env';
import { envFlag, envOr } from './src/config/env';

const isCI = envFlag('CI');

export default defineConfig({
  testDir: './src/tests',
  fullyParallel: true,
  forbidOnly: isCI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined,
  timeout: 60_000,
  expect: { timeout: 10_000 },

  reporter: isCI
    ? [['list'], ['html', { open: 'never' }], ['github']]
    : [['list'], ['html', { open: 'never' }]],

  use: {
    // Set for tooling that expects it, but every spec navigates by ABSOLUTE URL
    // — the plan names full URLs, and resolving them through a baseURL would put
    // a second source of truth in the way of where the app actually lives.
    baseURL: envOr(
      'BASE_URL',
      'https://app.thetestingacademy.com/playwright/ttacart/',
    ),
    viewport: { width: 1920, height: 1080 },
    actionTimeout: Number(envOr('ELEMENT_TIMEOUT_MS', '10000')),
    navigationTimeout: 30_000,
    trace: isCI ? 'on-first-retry' : 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
