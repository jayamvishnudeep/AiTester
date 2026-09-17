import { test, expect } from '@playwright/test';

test.describe('Checkout', () => {
  test('pay with a saved card', async ({ page }) => {
    // TODO: Fixture must sign in as ada@example.com, add "Linen Apron" to cart, and ensure card ending 4242 is saved
    await page.goto('/cart');
    await page.getByRole('button', { name: 'Checkout' }).click();
    await page.getByText('4242').click();
    await page.getByRole('button', { name: 'Pay £24.00' }).click();
    
    await expect(page.getByRole('heading', { name: 'Order confirmed' })).toBeVisible();
    const orderNumberLocator = page.getByText(/SF-\d{6}/);
    await expect(orderNumberLocator).toBeVisible();
  });

  test('reject an expired card', async ({ page }) => {
    // TODO: Fixture must sign in and navigate to payment step with card expiring 01/24 saved
    await page.goto('/checkout/payment');
    await page.getByText('01/24').click();
    await page.getByRole('button', { name: 'Pay £24.00' }).click();
    
    await expect(page.getByText('Card expired. Use a different card.')).toBeVisible();
    await expect(page).toHaveURL(/.*payment.*/);
    await expect(page.getByText(/SF-\d{6}/)).not.toBeVisible();
  });

  test('require a delivery address before paying', async ({ page }) => {
    // TODO: Fixture must sign in with no saved address and add one item to cart
    await page.goto('/cart');
    await page.getByRole('button', { name: 'Checkout' }).click();
    
    await expect(page.getByRole('button', { name: 'Pay' })).toBeDisabled();
    await expect(page.getByText('Add a delivery address to continue.')).toBeVisible();
  });

  test('apply a promotion code', async ({ page }) => {
    // TODO: Fixture must add "Linen Apron" to cart
    await page.goto('/cart');
    await page.getByRole('button', { name: 'Checkout' }).click();
    await page.getByLabel('Promotion code').fill('APRON10');
    await page.getByRole('button', { name: 'Apply' }).click();
    
    await expect(page.getByText('-£2.40')).toBeVisible();
    await expect(page.getByText('£21.60')).toBeVisible();
  });
});
