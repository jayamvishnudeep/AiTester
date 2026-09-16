// DELIBERATELY BAD. No retries, one worker, no trace, no baseURL.
import { PlaywrightTestConfig } from '@playwright/test';

const config: PlaywrightTestConfig = {
  testDir: './tests',
  timeout: 120000,
  workers: 1,
  retries: 0,
  use: {
    headless: false,
    screenshot: 'off',
    video: 'off',
  },
};

export default config;
