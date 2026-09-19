import { test, expect } from '@playwright/test';
import { SearchPage } from '@pages/SearchPage';

test('returns matching products', async ({ page }) => {
  const search = new SearchPage(page);
  await search.reindex();
  await page.goto('/');
  await search.search('keyboard');
  await expect(page.getByRole('list', { name: 'Results' })).toBeVisible();
});
