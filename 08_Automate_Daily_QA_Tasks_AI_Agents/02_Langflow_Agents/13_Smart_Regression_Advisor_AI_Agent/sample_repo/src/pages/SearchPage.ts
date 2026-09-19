import type { Page } from '@playwright/test';
import { request } from '../utils/api';

export class SearchPage {
  constructor(private readonly page: Page) {}

  async search(term: string): Promise<void> {
    await this.page.getByRole('searchbox').fill(term);
    await this.page.keyboard.press('Enter');
  }

  async reindex(): Promise<void> {
    await request('/test/reindex', { method: 'POST' });
  }
}
