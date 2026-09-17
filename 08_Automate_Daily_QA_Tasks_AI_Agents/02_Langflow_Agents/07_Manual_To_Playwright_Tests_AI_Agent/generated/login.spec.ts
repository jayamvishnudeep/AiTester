import { test, expect } from '@playwright/test';

test.describe('Login', () => {
  test('sign in with valid credentials', async ({ page }) => {
    // TODO: Fixture must ensure a registered account exists with email ada@example.com and password Correct-Horse-9.
    await page.goto('/login');
    await page.getByLabel('Email').fill('ada@example.com');
    await page.getByLabel('Password').fill('Correct-Horse-9');
    await page.getByRole('button', { name: 'Sign in' }).click();
    
    // Assert landing on account dashboard
    await expect(page).toHaveURL(/.*dashboard.*/);
    // Assert account menu shows the name "Ada"
    await expect(page.getByText('Ada')).toBeVisible();
  });

  test('reject a wrong password', async ({ page }) => {
    // TODO: Fixture must ensure the account ada@example.com exists.
    await page.goto('/login');
    await page.getByLabel('Email').fill('ada@example.com');
    await page.getByLabel('Password').fill('not-the-password');
    await page.getByRole('button', { name: 'Sign in' }).click();
    
    // Assert error message
    await expect(page.getByText('Email or password is incorrect.')).toBeVisible();
    // Assert shopper stays on login page
    await expect(page).toHaveURL(/.*login.*/);
    // Assert Password field is cleared
    await expect(page.getByLabel('Password')).toHaveValue('');
  });

  test('require both fields before submitting', async ({ page }) => {
    await page.goto('/login');
    // Fields are empty by default, no need to fill them
    
    // Assert Sign in button is disabled
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeDisabled();
  });
});
