// DELIBERATELY BAD. Audit fodder for the Framework Auditor - do not copy.
import { test, expect } from '@playwright/test';

test('pay with a saved card', async ({ page }) => {
  await page.goto('https://shopfront.example.com/cart');
  await page.waitForTimeout(4000);

  await page.click('xpath=/html/body/div[1]/main/section[3]/button');
  await page.waitForTimeout(4000);

  await page.click('//*[@id="root"]/div/div[2]/div[1]/label[1]/input');
  await page.click('button.btn.btn--primary');
  await page.waitForTimeout(8000);

  expect(await page.content()).toContain('Order confirmed');
});

test.fixme('expired card is rejected', async ({ page }) => {
  await page.goto('https://shopfront.example.com/checkout');
  await page.waitForTimeout(4000);
  await page.click('button.btn.btn--primary');
  await page.waitForTimeout(3000);
  const err = await page.$eval('div.checkout__error', (el) => el.textContent);
  expect(err).toBe('Card expired. Use a different card.');
});
