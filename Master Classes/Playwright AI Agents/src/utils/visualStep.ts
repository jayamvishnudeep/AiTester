// spec: specs/ttacart-e2e-order-plan.md
//
// test.step with an optional screenshot attached, so the HTML report reads as a
// timeline of what the flow looked like at each stage rather than a flat list of
// actions.

import { type Page, test } from '@playwright/test';
import { envFlag } from '../config/env';

/**
 * Run a named step and attach a screenshot of the page at its end.
 *
 * Screenshots are off by default and enabled with VISUAL_STEPS=1. They are a
 * reporting aid, never a source of assertions — nothing in this suite branches
 * on an image, and a screenshot that fails to capture must not fail a test, so
 * the attach is wrapped.
 */
export async function visualStep<T>(
  page: Page,
  title: string,
  body: () => Promise<T>,
): Promise<T> {
  return test.step(title, async () => {
    const result = await body();
    if (envFlag('VISUAL_STEPS')) {
      try {
        await test.info().attach(title, {
          body: await page.screenshot(),
          contentType: 'image/png',
        });
      } catch {
        // A failed attachment is a reporting problem, not a test result.
      }
    }
    return result;
  });
}

/** A step with no screenshot, for grouping only. */
export async function step<T>(title: string, body: () => Promise<T>): Promise<T> {
  return test.step(title, body);
}
