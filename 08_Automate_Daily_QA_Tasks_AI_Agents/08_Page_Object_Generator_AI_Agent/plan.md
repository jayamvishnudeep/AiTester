# Plan — Page Object Generator (Langflow AI Agent)

An SDET pastes the HTML of a page they are about to automate, and gets back a
Playwright Page Object class in TypeScript, on disk, named after the class it
contains.

Status: **built and verified against the live Groq API.** Both sample pages
convert, the generated TypeScript type-checks against `@playwright/test`, and
every locator in the output traces back to an element that is really in the HTML.

## The brief

| | |
|---|---|
| Audience | Automation / SDET |
| Problem | Writing POM boilerplate is tedious |
| Input | HTML / DOM snapshot |
| Output | Page Object class file |
| Helpful for | Setting up new page automation quickly |
| Given shape | Text Input (HTML) → Prompt Template (POM pattern + language) → LLM → Code Output |

The given shape stops at Code Output. This one adds a writer after it, for the
same reason agent 07 does: a class you have to copy out of a chat window by hand
is most of the tedium the agent was supposed to remove.

## The rule this one is built on

> **The model writes the class. Code decides what the file is called.**

A Page Object file is named after the class inside it — `LoginPage.ts` holds
`class LoginPage`. Ask a model to produce both the class and a file name and it
will occasionally disagree with itself, naming the file `Login.ts` while writing
`class SignInPage`. That is a small thing that quietly breaks an import.

So the class wins. The writer reads the class name out of the code it is about to
write and names the file from that; a `// file:` marker is only a fallback for a
reply that somehow contains no class at all. It is the one naming rule that
cannot be wrong, because it is derived from the thing being named.

This showed up immediately on the sample: given a page whose heading reads
"Sign in", the model wrote `class SignInPage`, and the file came out
`SignInPage.ts` rather than the `LoginPage.ts` the source file name might have
suggested. The class and the file agree, which is what matters.

## The failure this agent has to avoid

Inventing elements.

A Page Object is a promise that these locators exist on that page. A generated
class that includes a `rememberMeCheckbox` the page does not have is worse than
no class: it compiles, it reads well, and it fails at run time with a timeout
that looks like a flaky test rather than a fabrication.

So the prompt forbids invention explicitly, and the check that matters is not
"did it produce a class" but **"does every locator in the class correspond to
something in the HTML"**. That is asserted mechanically: pull every string out of
`getByLabel`, `getByText`, `getByTestId` and `getByRole(..., { name })`, and
require each one to appear in the source snapshot. Eighteen locator strings
across the two sample pages, all traced.

The guard follows from the same reasoning. Run the flow with no HTML and the
model does not say "you gave me no HTML" — it writes a plausible sign-in page
from nothing at all. The writer therefore refuses unless real markup arrived,
and "real" means long enough to be a snapshot and containing a tag.

## What the model is good at here

Everything that is a judgement rather than a lookup:

- **Naming.** `<input id="email">` with a matching label becomes `emailInput`,
  and a `<button type="button" aria-label="Show password">` becomes
  `revealPasswordButton`. Naming is most of what makes a Page Object readable and
  it is the part that cannot be derived from the markup alone.
- **Choosing a locator.** The sample pages carry `data-testid` on nearly
  everything, and the prompt asks for it to be used only where nothing better
  exists. The model consistently preferred `getByLabel('Email')` and
  `getByRole('button', { name: 'Sign in' })`, which is the right call — a test id
  is a fallback, not a first choice.
- **Grouping actions.** Four fields and a button become `enterAddress`,
  `selectCard`, `applyPromoCode` and `pay` — methods named after what a user is
  doing, not after the widget they are doing it with.

## The token ceiling

Groq's free tier allows 1,000 output tokens a minute, so `max_tokens` is 900 and
one run converts one page. A page with more than a couple of dozen elements will
need the ceiling raised, or the snapshot trimmed to the section being automated —
which is usually the right thing to paste anyway.

## Pipeline

```
Text Input       the DOM snapshot
  -> Prompt Template   the POM rules + {html}
  -> Groq              qwen/qwen3.8-27b, max_tokens 900, temperature 0.1
  -> Page Object Writer  strips prose, names from the class, writes .ts
  -> Chat Output       what was written, with its locators and methods
```

The Text Input also runs straight to the writer, which is what lets it refuse an
empty page without asking the model first.

## Verified

- Both sample pages convert, from the node and from the API.
- The generated TypeScript type-checks against the real `@playwright/test` types
  under `strict`.
- All 18 locator strings across the two classes appear in the source HTML.
- The empty-input path writes nothing.
- The writer has 24 tests of its own, covering every shape a reply arrives in,
  how the file gets its name, and the replies that must be refused.
