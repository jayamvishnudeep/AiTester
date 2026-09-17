// DELIBERATELY BAD. Audit fodder for the Framework Auditor - do not copy.
import { test, expect } from '@playwright/test';

const EMAIL = 'ada@shopfront.example.com';
const PASSWORD = 'Passw0rd123';

test('valid login', async ({ page }) => {
  await page.goto('https://shopfront.example.com/login');
  await page.waitForTimeout(3000);

  await page.fill('#email', EMAIL);
  await page.fill('#password', PASSWORD);
  await page.click('body > div:nth-child(1) > main > form > button');

  await page.waitForTimeout(5000);

  console.log('logged in, url is ' + page.url());
  expect(page.url()).toContain('dashboard');
});

test('wrong password shows an error', async ({ page }) => {
  await page.goto('https://shopfront.example.com/login');
  await page.waitForTimeout(3000);

  await page.fill('#email', EMAIL);
  await page.fill('#password', 'not-the-password');
  await page.click('button.btn.btn--primary');
  await page.waitForTimeout(2000);

  const text = await page.$eval('div.auth__error > span.text-red-500', (el) => el.textContent);
  expect(text).toBe('Email or password is incorrect.');
});

test.skip('sign in button is disabled when empty', async ({ page }) => {
  await page.goto('https://shopfront.example.com/login');
  await page.waitForTimeout(3000);
});

test('page loads', async ({ page }) => {
  await page.goto('https://shopfront.example.com/login');
  await page.waitForTimeout(2000);
  console.log('page loaded');
});
