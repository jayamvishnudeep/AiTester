import type { Page } from '@playwright/test';
import { request } from '../utils/api';

export class LoginPage {
  constructor(private readonly page: Page) {}

  async signIn(email: string, password: string): Promise<void> {
    await this.page.getByLabel('Email').fill(email);
    await this.page.getByLabel('Password').fill(password);
    await this.page.getByRole('button', { name: 'Sign in' }).click();
  }

  async seedUser(email: string): Promise<void> {
    await request('/test/seed-user', { method: 'POST', body: email });
  }
}
