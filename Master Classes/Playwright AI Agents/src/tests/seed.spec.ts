import { test } from '@playwright/test';

test('seed', async ({ page }) => {
  await page.goto('https://app.thetestingacademy.com/playwright/ttacart/');
});
