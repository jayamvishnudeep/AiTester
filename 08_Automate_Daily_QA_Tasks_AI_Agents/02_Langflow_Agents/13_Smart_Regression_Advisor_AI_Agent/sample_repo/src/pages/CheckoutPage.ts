import type { Page } from '@playwright/test';
import { formatPrice, addTax } from '@utils/money';
import { request } from '../utils/api';

export class CheckoutPage {
  constructor(private readonly page: Page) {}

  async expectedTotal(netPennies: number): Promise<string> {
    return formatPrice(addTax(netPennies, 20));
  }

  async placeOrder(): Promise<void> {
    await this.page.getByTestId('place-order').click();
  }

  async clearBasket(): Promise<void> {
    await request('/test/clear-basket', { method: 'POST' });
  }
}
