// Flat config, ESLint 9.
//
// Type-aware rules are scoped to src/**/*.ts on purpose. They need a TypeScript
// program, and this config file is not in one — applying them repo-wide makes
// ESLint fail to load rather than fail to lint, which looks like a broken setup.

import tseslint from 'typescript-eslint';
import playwright from 'eslint-plugin-playwright';

export default tseslint.config(
  {
    ignores: [
      'node_modules/**',
      'playwright-report/**',
      'test-results/**',
      'specs/**',
      '*.mjs',
    ],
  },

  {
    files: ['src/**/*.ts', 'playwright.config.ts'],
    extends: [...tseslint.configs.recommendedTypeChecked],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // The expensive Playwright bug, and the reason type-aware linting earns its
      // setup cost: a forgotten await on an action or an expect means the test
      // races the page and passes for the wrong reason. Nothing else catches it.
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/await-thenable': 'error',
      '@typescript-eslint/require-await': 'error',

      eqeqeq: ['error', 'always'],
      'prefer-const': 'error',
      'no-console': 'off', // the logger writes to the console on purpose

      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },

  {
    files: ['src/tests/**/*.spec.ts'],
    extends: [playwright.configs['flat/recommended']],
    rules: {
      // Conditionals in a test usually hide a second scenario. A warning rather
      // than an error: nothing currently trips it, but the pinned-bug tests are
      // the kind of test that legitimately inspects observed state.
      'playwright/no-conditional-in-test': 'warn',
      'playwright/no-skipped-test': 'warn',

      // Kept as an error, but taught about this project's assertion helpers.
      //
      // Page objects own the page-identity and shell assertions - expectLoaded,
      // expectError, expectCartBadgeAbsent and friends - so a spec can assert
      // without a literal `expect(` on the line. Without this the rule reports
      // nine tests as assertion-free when every one of them asserts.
      //
      // Listed exactly, not as a glob. The rule compares identifiers with `===`
      // for string entries, so `expect*` matches nothing — and it walks a member
      // expression down to its property, so `cartPage.expectEmpty()` is seen as
      // the bare name `expectEmpty`.
      //
      // Naming them individually is the better failure mode anyway: a new page
      // object helper is not silently trusted as an assertion. It has to be added
      // here, which is a prompt to check that it really does assert something.
      'playwright/expect-expect': [
        'error',
        {
          assertFunctionNames: [
            'expect',
            'expectAtUrl',
            'expectBlockedByNativeValidation',
            'expectCartBadgeAbsent',
            'expectCartBadgeCount',
            'expectConfirmationHeader',
            'expectDefaultSort',
            'expectEmpty',
            'expectError',
            'expectErrorBannerAbsent',
            'expectFieldsEmpty',
            'expectFirstItem',
            'expectLoaded',
            'expectNoError',
            'expectOrderConfirmed',
            'expectPaymentAndShipping',
            'expectSingleLineItem',
            'expectTotals',
          ],
        },
      ],
      // page.evaluate appears once, deliberately, for storage teardown; the
      // fixture comment explains why. Not worth a blanket ban.
      'playwright/no-eval': 'off',
    },
  },

  {
    // The generator agent's seed file. It navigates and asserts nothing, by
    // design - its only job is to give generator_setup_page a starting point.
    files: ['src/tests/seed.spec.ts'],
    rules: { 'playwright/expect-expect': 'off' },
  },
);
