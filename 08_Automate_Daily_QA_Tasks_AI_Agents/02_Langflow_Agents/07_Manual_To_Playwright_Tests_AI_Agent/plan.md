# Plan — Manual to Playwright Tests (Langflow AI Agent)

An SDET pastes the manual test cases a team already has written down, and gets
back a Playwright spec file in TypeScript, on disk, ready to open.

Status: **built and verified against the live Groq API.** Both entry paths run
end to end, the generated TypeScript type-checks against `@playwright/test`, and
every fact in the manual cases survives into the generated code.

## The brief

| | |
|---|---|
| Audience | SDET |
| Problem | Manual coverage not automated yet |
| Input | Manual test steps |
| Output | Playwright script draft |
| Helpful for | Accelerating the transition from manual to automated testing |
| Given shape | Text Input → Prompt Template → LLM → Code Output → File Writer |

## Why Langflow rather than n8n

Folders 01–06 are n8n workflows. This one is Langflow, and the File Writer step
is the reason. n8n Cloud runs on someone else's machine, so "write a
`.spec.ts` file" can only ever mean "send you a download". Langflow runs on
yours, so the last node writes a real file into a real folder — which is the
whole point of the agent. The implementation guide for this agent says Langflow
for the same reason.

## The rule this one is built on

Every agent in this folder draws a line between what code decides and what the
model decides. Here it is:

> **The model writes the code. Code decides what the file is called, where it
> goes, and what counts as code at all.**

A model asked for a test file returns a test file wrapped in things that are not
a test file: a fenced block, a "Here you go:", occasionally a closing paragraph
explaining what it just wrote. None of that compiles. Asking the model to *also*
be disciplined about packaging is asking it to be reliable at the one thing it is
worst at, when a regular expression is perfect at it.

So the last node does the mechanical work:

- finds the code inside fences, or takes the body as it stands
- drops leading chatter that is plainly prose, not code
- reads a `// file: name.spec.ts` marker to name the file, and writes one file
  per marker when the model emits several
- reduces whatever the marker says to a bare file name, so a model that writes
  `// file: ../../etc/passwd` gets `passwd.spec.ts` inside the output folder
- counts the `test(` calls it wrote, without counting the `test.describe(`
  wrapper as a test

The model never touches the filesystem, and nothing it says can change where a
file lands.

## The failure this agent has to avoid

A converter that invents is worse than no converter. If the manual case says the
password is `Correct-Horse-9` and the expected error is
*"Email or password is incorrect."*, then a generated test asserting
*"Invalid credentials"* against `password123` is not a draft — it is a test that
fails on first run for a reason that has nothing to do with the product, and an
SDET who hits that twice stops trusting the tool.

The prompt therefore forbids invention explicitly, and the check that matters is
not "did it produce code" but **"is every literal from the manual case present in
the output"** — the email, the password, the exact expected message, the
assertion the Expected line implies. That is asserted on rather than eyeballed.

The corollary is that an empty input must never look like a successful run.
Passing the flow no steps produces plausible, well-formed, entirely fictional
login tests — the most dangerous possible output, because it looks right.

## What the model is actually good at here

Everything a schema cannot imply, which is most of this problem:

- **Naming.** "Sign in with valid credentials" becomes
  `test('sign in with valid credentials')`, and the feature becomes the
  `describe` title and the file name.
- **Locators.** "the Email field" becomes `getByLabel('Email')`, "the **Sign in**
  button" becomes `getByRole('button', { name: 'Sign in' })`. Role- and
  label-based locators are required by the prompt; CSS and XPath are forbidden,
  because a generated CSS selector is a guess that will not survive a redesign.
- **Assertions.** An Expected line in English becomes one or more web-first
  assertions. "The Sign in button is disabled" becomes `toBeDisabled()`, not a
  visibility check.
- **Admitting what it cannot do.** A precondition like "a registered account
  exists" cannot be set up from a browser, so the prompt asks for a `// TODO`
  naming what the fixture must provide rather than a fabricated sign-up flow.

## The token ceiling

Groq's free tier allows 1,000 output tokens a minute, so `max_tokens` is 900 and
one run converts one feature's worth of cases — three to five. That is not much
of a limitation in practice: manual test cases arrive grouped by feature anyway,
and one spec file per feature is the layout a Playwright suite wants.

## Pipeline

```
Text Input          the manual cases, as written
  -> Prompt Template   the conversion rules + {manual_steps}
  -> Groq              qwen/qwen3.8-27b, max_tokens 900, temperature 0.1
  -> Spec Writer       strips prose, names the file, writes .spec.ts
  -> Chat Output       what was written, and how many tests
```

Temperature is 0.1 rather than 0 because the task has genuine naming choices in
it, but the conversion itself should not wander between runs.

## Verified

- Both entry paths: the steps stored on the Text Input node, and steps supplied
  by the caller in the API request.
- Fidelity: every literal from the manual cases appears in the generated code.
- The generated TypeScript type-checks against the real `@playwright/test`
  types, not just "looks like code".
- The writer has 25 tests of its own, run without Langflow or a network. They
  cover every shape a reply arrives in — bare code, one fence, prose before or
  after the fence, several back-to-back fences, markers in both comment styles,
  extra text on a marker line — and every reply that must be refused.

That last point is the one worth keeping. The interesting cases are not the
tidy replies; they are a reply of three fenced blocks with no marker, a closing
paragraph after the final fence, and a `/* file: x.spec.ts */` marker whose `*/`
must not end up in the TypeScript. Each of those silently produces a broken or
incomplete file if the extraction is even slightly wrong, and none of them is
visible from a green "it ran" in the canvas — which is why they are tests rather
than a thing to check by eye.
