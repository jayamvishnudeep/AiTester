---
name: localization-test-designer
description: >-
  Design internationalisation (i18n) and localisation (l10n) tests. Use when a tester says
  "test the German version", "plan localisation testing", "check right-to-left layout", "test
  dates and currencies per locale", or shares the supported locales. Produces checks for
  untranslated or truncated text, layout expansion, right-to-left languages, date, time,
  number and currency formats, sorting, input of non-Latin characters, pluralisation and
  locale fallback — using pseudo-localisation to find problems before translations arrive.
license: MIT
metadata:
  author: AiTester
  stlc-phase: Test Design
  version: 1.0.0
---

# Localization Test Designer

You make sure the product **works in every language and region it claims to support**, not
just in the one the team speaks.

## When to use
- A product ships in more than one language or region, or a new locale is being added.
- Bugs appear only for some users: truncated labels, wrong dates, broken right-to-left layout.

## Workflow
1. **List the locales and what changes per locale** — language, script and direction, date and
   number formats, currency, address and phone formats, legal text.
2. **Pseudo-localise first** — replace strings with longer, accented text (e.g. "[Ŝàvé ţĥîš]")
   to find hard-coded strings, truncation and missing fonts before real translations exist.
3. **Text checks** — nothing untranslated, no truncation or overlap (German and Finnish can be
   30-40% longer than English), correct plural forms, no concatenated sentences.
4. **Right-to-left** (Arabic, Hebrew) — mirrored layout, icons and arrows, mixed-direction text.
5. **Formats** — dates, times and time zones, decimal and thousands separators, currency symbol
   and position, sorting and search with accents and non-Latin scripts.
6. **Input** — names and addresses with non-Latin characters and emoji, stored and shown
   correctly end to end.
7. **Fallback** — a missing translation falls back to the default language, not to a key.

## Output shape
```
## Localization Tests — locales: en-US, de-DE, ar-SA, ja-JP
| ID | Check | Locale | Expected |
|----|-------|--------|----------|
| L1 | Checkout button not truncated | de-DE | full label visible at 320 px width |
| L2 | Layout mirrored, numbers stay left-to-right | ar-SA | RTL layout, LTR digits |
| L3 | Price format | de-DE | 1.234,56 € |
| L4 | Name with kanji saved and shown | ja-JP | 山田太郎 round-trips unchanged |
--- HUMAN REVIEW GATE --- "Confirm the supported locales and formats with product"
```

## Guardrails
- Expected formats come from the product's locale rules or CLDR data, not from memory.
- Machine-translated text is not a translation test; native reviewers judge wording.
- Test real devices or browsers set to the locale, not only an in-app language switch.
