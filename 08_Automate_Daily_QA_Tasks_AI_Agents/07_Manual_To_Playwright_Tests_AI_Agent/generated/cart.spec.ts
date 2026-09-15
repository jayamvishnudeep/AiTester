import { test, expect } from '@playwright/test';

test.describe('Cart', () => {
  test('add a single item to the cart', async ({ page }) => {
    // TODO: Ensure the product "Linen Apron" is in stock via fixture
    await page.goto('/products/linen-apron');
    await page.getByRole('button', { name: 'Add to cart' }).click();
    await page.getByRole('link', { name: 'Cart' }).click();

    const cartLine = page.getByRole('listitem').filter({ hasText: 'Linen Apron' });
    await expect(cartLine).toBeVisible();
    await expect(cartLine.getByText('1')).toBeVisible();
    await expect(page.getByRole('status').getByText('1')).toBeVisible();
  });

  test('change the quantity from the cart', async ({ page }) => {
    // TODO: Ensure the cart already holds one "Linen Apron" via fixture
    await page.goto('/cart');

    const cartLine = page.getByRole('listitem').filter({ hasText: 'Linen Apron' });
    const plusButton = cartLine.getByRole('button', { name: '+' });
    await plusButton.click();
    await plusButton.click();

    await expect(cartLine.getByText('3')).toBeVisible();
    // Note: Exact line total assertion depends on unit price, assuming standard display
    await expect(page.getByRole('status').getByText('3')).toBeVisible();
  });

  test('remove the last item and see the empty state', async ({ page }) => {
    // TODO: Ensure the cart holds exactly one line via fixture
    await page.goto('/cart');

    const cartLine = page.getByRole('listitem').first();
    await cartLine.getByRole('button', { name: 'Remove' }).click();

    await expect(page.getByText('Your cart is empty')).toBeVisible();
    await expect(page.getByRole('status')).not.toBeVisible();
    await expect(page.getByRole('button', { name: 'Checkout' })).not.toBeVisible();
  });
});
