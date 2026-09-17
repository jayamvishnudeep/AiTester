// DELIBERATELY BAD. Audit fodder for the Framework Auditor - do not copy.
import { test, expect, type Page } from '@playwright/test';

// Shared across every test in this file, so none of them can run in parallel.
let sharedPage: Page;

test.beforeAll(async ({ browser }) => {
  sharedPage = await browser.newPage();
  await sharedPage.goto('https://shopfront.example.com/account');
  await sharedPage.waitForLoadState('networkidle');
});

test('shows the profile details', async () => {
  // the sleep that survives a lint rule banning waitForTimeout
  await new Promise((resolve) => setTimeout(resolve, 2000));

  // no await - this assertion can never fail
  expect(sharedPage.getByRole('heading', { name: 'Your account' })).toBeVisible();
});

test('updates the display name', async () => {
  await sharedPage.fill('#displayName', 'Ada L.');
  await sharedPage.click('button.btn--primary');
  await expect(sharedPage.getByText('Saved')).toBeVisible({ timeout: 120000 });
});

test('waits for the orders list', async () => {
  await sharedPage.goto('https://shopfront.example.com/account/orders');
  while (!(await sharedPage.getByTestId('orders-table').isVisible())) {
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  // await expect(sharedPage.getByRole('row')).toHaveCount(5);
});
