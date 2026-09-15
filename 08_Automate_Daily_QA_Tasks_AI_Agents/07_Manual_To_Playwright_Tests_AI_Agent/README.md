# Manual to Playwright Tests — Langflow AI Agent

Paste the manual test cases a team already has written down. Get back a
Playwright spec file in TypeScript, on disk, ready to open.

![The flow open in Langflow: a Text Input node holding the manual cases feeds a Prompt Template, which feeds a Groq node running qwen3.8-27b, which feeds the Playwright Spec Writer, which reports to a Chat Output. A second edge runs from the Text Input directly to the Spec Writer, carrying the manual steps as a guard](Manual_To_Playwright_langflow_flow.png)

---

## What it does

| | |
|---|---|
| **Input** | Manual test steps, as a tester wrote them |
| **Output** | A `.spec.ts` file written into `generated/` |
| **Helpful for** | Getting manual-only coverage into an automated suite |

A manual case like this:

```
TC-01 - Sign in with valid credentials
Precondition: A registered account exists with email ada@example.com
              and password Correct-Horse-9.
1. Open the login page.
2. Enter ada@example.com in the Email field.
3. Enter Correct-Horse-9 in the Password field.
4. Click the Sign in button.
Expected: The shopper lands on the account dashboard, and the account
          menu shows the name "Ada".
```

comes back as this:

```ts
test('sign in with valid credentials', async ({ page }) => {
  // TODO: Ensure a registered account exists with email ada@example.com
  //       and password Correct-Horse-9
  await page.goto('/login');
  await page.getByLabel('Email').fill('ada@example.com');
  await page.getByLabel('Password').fill('Correct-Horse-9');
  await page.getByRole('button', { name: 'Sign in' }).click();

  await expect(page).toHaveURL(/.*dashboard.*/);
  await expect(page.getByText('Ada')).toBeVisible();
});
```

Role- and label-based locators, web-first assertions, and a `// TODO` naming what
a fixture has to provide — because "a registered account exists" is not something
a browser can arrange for itself.

---

## What is in this folder

| File | What it is |
|---|---|
| `Manual_To_Playwright_langflow_flow.json` | The flow. Import this into Langflow |
| `playwright_spec_writer.py` | The file-writer component, readable on its own |
| `test_playwright_spec_writer.py` | Its tests — 25 of them, no Langflow needed |
| `manual_test_cases.md` | Six manual cases across two features, to try it with |
| `generated/` | Where the `.spec.ts` files land |
| `plan.md` | Why it is built the way it is |

The `.py` file is a **Langflow component**, not test code — Langflow's extension
language is Python. Everything this agent *generates* is TypeScript.

---

## Before you start

1. **Langflow running**, normally at `http://127.0.0.1:7860`
2. **A Groq API key** — free from [console.groq.com](https://console.groq.com)

---

## Setup

### 1. Store your Groq key in Langflow

Looked up by name, so it is never written into the flow file.

- **Settings → Global Variables → Add New**
- Name it exactly **`GROQ_API_KEY`**, type **Credential**

### 2. Import the flow

**New Flow → Import**, then pick `Manual_To_Playwright_langflow_flow.json`.
Five nodes appear.

### 3. Point the writer at a folder

Click the **Playwright Spec Writer** node and set **Output folder** to wherever
you want the specs written. It holds an absolute path from the machine the flow
was built on, so this is the one value you must change after cloning.

```
C:/Users/you/AiTester/08_Automate_Daily_QA_Tasks_AI_Agents/07_Manual_To_Playwright_Tests_AI_Agent/generated
```

---

## Running it

Open the **Text Input** node, replace its contents with your manual cases, and
press **Run** on the **Chat Output** node.

Try it first with what is already in there — the three Login cases from
`manual_test_cases.md`. About five seconds later:

```
Wrote 1 file holding 3 tests.

Folder: .../07_Manual_To_Playwright_Tests_AI_Agent/generated

- login.spec.ts — 3 tests, 38 lines
```

Paste the Cart cases instead and you get `cart.spec.ts`. The file name comes
from the feature, so one run produces one spec file per feature.

> The entry point is the **Text Input** node, not the Playground. The Playground
> sends chat messages, and this flow reads its steps from a field — so edit the
> field and press Run.

### From the API

The caller supplies the steps, which is how you would drive it from CI:

```bash
curl -X POST "http://127.0.0.1:7860/api/v1/run/<your-flow-id>?stream=false" \
  -H "Content-Type: application/json" \
  -H "x-api-key: <your-langflow-key>" \
  -d '{
        "output_type": "chat",
        "input_type": "text",
        "input_value": "TC-01 - Sign in with valid credentials\n1. Open the login page.\n..."
      }'
```

`input_type: "text"` replaces whatever the Text Input node holds. Send
`"chat"` instead to use the steps already stored on the node.

---

## One run, one feature

Groq's free tier allows 1,000 output tokens a minute, so **Max Tokens** is 900
and a run converts three to five cases. That suits the output anyway: manual
cases arrive grouped by feature, and one spec file per feature is the layout a
Playwright suite wants.

For more at once, raise **Max Tokens** on the Groq node — or run it per feature.

---

## The guard

Give this flow no steps and it stops, rather than writing a file:

```
No manual steps reached this component, so anything generated from them
is invention. Put the cases in the input node, or wire it to the
'Manual steps (guard)' field.
```

That is deliberate, and it is why the Text Input connects to the writer as well
as to the prompt. A model handed an empty brief does not return an empty
answer — it returns fluent, well-formed, completely fictional login tests. That
is the most dangerous thing this agent could produce, because it looks exactly
like success. So the writer checks that real steps arrived before it writes
anything.

---

## Using it on your own cases

Any format works, as long as a human could follow it. Numbered steps and a line
saying what is expected is enough. The conversion is better when the manual case
names things the way the UI does — "the **Sign in** button", "the Email field" —
because those become `getByRole('button', { name: 'Sign in' })` and
`getByLabel('Email')`.

What comes out is a **draft**. Selectors are inferred from the words in your
steps, so run it, fix what does not match your markup, and keep it. That is still
far less work than writing the file from nothing.

---

## If something does not work

| What you see | What to do |
|---|---|
| `No manual steps reached this component` | The Text Input is empty, or the API call sent an empty `input_value` |
| `Only N characters of manual steps` | Too little to convert — paste the whole case, not just a title |
| `Set an output folder` | Step 3 — set **Output folder** on the writer |
| An error mentioning the Prompt Template and a `{ ... }` fragment | A literal `{` in the template is read as a variable. Double it to `{{` |
| The reply is cut off mid-test | Raise **Max Tokens**, or convert fewer cases per run |
| `Invalid API key` | The global variable must be named exactly `GROQ_API_KEY` |
| Tests that do not match your manual cases | Check the steps actually reached the node — an empty input is the usual cause |

---

## Verified

- Both entry paths — steps stored on the node, and steps supplied by the caller.
- The generated TypeScript **type-checks against the real `@playwright/test`
  types** under `strict`, not just "looks like code".
- Every literal in the manual cases — emails, passwords, expected messages —
  appears in the generated code.
- The empty-input path writes nothing.

The writer has its own tests, covering every shape a model reply arrives in and
every reply that should be refused. They need no Langflow and no network:

```bash
09_LangFlow/.venv/Scripts/python.exe test_playwright_spec_writer.py
```

```
25 passed, 0 failed
```
