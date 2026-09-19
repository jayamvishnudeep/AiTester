import { test, expect } from '@playwright/test';
import { LoginPage } from '@pages/LoginPage';

test('signs in with valid credentials', async ({ page }) => {
  const login = new LoginPage(page);
  await login.seedUser('ada@shopfront.example.com');
  await page.goto('/login');
  await login.signIn('ada@shopfront.example.com', 'correct-horse');
  await expect(page.getByRole('heading', { name: 'Your account' })).toBeVisible();
});
