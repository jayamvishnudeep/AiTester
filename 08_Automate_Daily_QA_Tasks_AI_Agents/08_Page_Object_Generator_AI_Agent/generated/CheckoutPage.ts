import { type Page, type Locator } from '@playwright/test';

export class CheckoutPage {
  readonly page: Page;

  readonly addressLine1: Locator;
  readonly postcode: Locator;
  readonly findAddressButton: Locator;
  readonly addressRequiredNotice: Locator;

  readonly visaCard: Locator;
  readonly mastercardCard: Locator;
  readonly cardError: Locator;

  readonly promoCode: Locator;
  readonly applyPromoButton: Locator;

  readonly subtotal: Locator;
  readonly discount: Locator;
  readonly total: Locator;

  readonly payButton: Locator;

  constructor(page: Page) {
    this.page = page;

    this.addressLine1 = page.getByLabel('Address line 1');
    this.postcode = page.getByLabel('Postcode');
    this.findAddressButton = page.getByRole('button', { name: 'Find address' });
    this.addressRequiredNotice = page.getByTestId('address-required');

    this.visaCard = page.getByRole('radio', { name: 'Visa ending 4242 — expires 09/29' });
    this.mastercardCard = page.getByRole('radio', { name: 'Mastercard ending 1881 — expires 01/24' });
    this.cardError = page.getByRole('alert');

    this.promoCode = page.getByLabel('Promotion code');
    this.applyPromoButton = page.getByRole('button', { name: 'Apply' });

    this.subtotal = page.getByTestId('subtotal');
    this.discount = page.getByTestId('discount');
    this.total = page.getByTestId('total');

    this.payButton = page.getByRole('button', { name: /Pay £/ });
  }

  async goto(): Promise<void> {
    await this.page.goto('/checkout');
  }

  async enterAddress(line1: string, postcode: string): Promise<void> {
    await this.addressLine1.fill(line1);
    await this.postcode.fill(postcode);
  }

  async lookupPostcode(): Promise<void> {
    await this.findAddressButton.click();
  }

  async selectCard(cardName: 'Visa ending 4242 — expires 09/29' | 'Mastercard ending 1881 — expires 01/24'): Promise<void> {
    const card = cardName === 'Visa ending 4242 — expires 09/29' ? this.visaCard : this.mastercardCard;
    await card.check();
  }

  async applyPromoCode(code: string): Promise<void> {
    await this.promoCode.fill(code);
    await this.applyPromoButton.click();
  }

  async pay(): Promise<void> {
    await this.payButton.click();
  }
}
