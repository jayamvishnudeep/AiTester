// spec: specs/ttacart-e2e-order-plan.md §1.2
//
// A thin wrapper over Playwright's Locator that adds scoped logging and a
// configurable default timeout, so page objects declare intent and the trace
// records what was attempted.
//
// It wraps rather than replaces: `.locator` is public, so anything the wrapper
// does not cover uses the real Locator API directly instead of waiting for a
// method to be added here. Assertions are NOT wrapped — those stay as
// web-first expect(locator) calls in the specs, where the claim is visible.

import { type Locator, type Page } from '@playwright/test';
import { createLogger, type Logger } from './logger';
import { envOr } from '../config/env';

const DEFAULT_TIMEOUT = Number(envOr('ELEMENT_TIMEOUT_MS', '10000'));

export class UtilElementLocator {
  readonly locator: Locator;
  private readonly log: Logger;
  private readonly description: string;
  private readonly timeout: number;

  constructor(
    locator: Locator,
    description: string,
    log: Logger,
    timeout: number = DEFAULT_TIMEOUT,
  ) {
    this.locator = locator;
    this.description = description;
    this.log = log;
    this.timeout = timeout;
  }

  async click(): Promise<void> {
    this.log.debug(`click ${this.description}`);
    await this.locator.click({ timeout: this.timeout });
  }

  async fill(value: string): Promise<void> {
    // Values can be whitespace or empty on purpose — those are the negative
    // cases. Quote them in the log so "   " is distinguishable from "".
    this.log.debug(`fill ${this.description} with "${value}"`);
    await this.locator.fill(value, { timeout: this.timeout });
  }

  async selectOption(value: string): Promise<void> {
    this.log.debug(`select "${value}" in ${this.description}`);
    await this.locator.selectOption(value, { timeout: this.timeout });
  }

  async textContent(): Promise<string> {
    return (await this.locator.textContent({ timeout: this.timeout })) ?? '';
  }

  async isVisible(): Promise<boolean> {
    return this.locator.isVisible();
  }

  async count(): Promise<number> {
    return this.locator.count();
  }

  /** Narrow to the nth match — the products grid has six of several elements. */
  nth(index: number): UtilElementLocator {
    return new UtilElementLocator(
      this.locator.nth(index),
      `${this.description}[${index}]`,
      this.log,
      this.timeout,
    );
  }

  first(): UtilElementLocator {
    return this.nth(0);
  }
}

/**
 * Build an element factory bound to a page and a scope.
 *
 * Page objects hold this as `el`, so a locator declaration reads as
 * `this.el('#user-name', 'username field')` and carries its own description
 * into the log.
 */
export function elementFactory(page: Page, scope: string) {
  const log = createLogger(scope);
  return (selector: string, description: string): UtilElementLocator =>
    new UtilElementLocator(page.locator(selector), description, log);
}
