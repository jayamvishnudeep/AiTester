import { test, expect } from '@playwright/test';
import { CheckoutPage } from '@pages/CheckoutPage';
import { formatPrice } from '../src/utils/money';

test('shows the order total including tax', async ({ page }) => {
  const checkout = new CheckoutPage(page);
  await checkout.clearBasket();
  await page.goto('/checkout');
  await expect(page.getByTestId('order-total')).toHaveText(await checkout.expectedTotal(10375));
});

test('formats a bare price', async () => {
  expect(formatPrice(1250)).toBe('£12.50');
});
