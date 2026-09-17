import { type Page, type Locator } from '@playwright/test';

export class SignInPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly revealPasswordButton: Locator;
  readonly rememberMeCheckbox: Locator;
  readonly signInButton: Locator;
  readonly loginError: Locator;
  readonly signupLink: Locator;
  readonly forgotPasswordLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.revealPasswordButton = page.getByRole('button', { name: 'Show password' });
    this.rememberMeCheckbox = page.getByLabel('Keep me signed in');
    this.signInButton = page.getByRole('button', { name: 'Sign in' });
    this.loginError = page.getByRole('alert');
    this.signupLink = page.getByRole('link', { name: 'Create an account' });
    this.forgotPasswordLink = page.getByRole('link', { name: 'Forgotten your password?' });
  }

  async goto(): Promise<void> {
    await this.page.goto('/signin');
  }

  async enterEmail(email: string): Promise<void> {
    await this.emailInput.fill(email);
  }

  async enterPassword(password: string): Promise<void> {
    await this.passwordInput.fill(password);
  }

  async togglePasswordVisibility(): Promise<void> {
    await this.revealPasswordButton.click();
  }

  async toggleRememberMe(): Promise<void> {
    await this.rememberMeCheckbox.click();
  }

  async submitSignIn(): Promise<void> {
    await this.signInButton.click();
  }

  async goToSignup(): Promise<void> {
    await this.signupLink.click();
  }

  async goToForgotPassword(): Promise<void> {
    await this.forgotPasswordLink.click();
  }
}
