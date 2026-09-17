# Plan — Screenshot to Bug Reporter (n8n AI Agent)

A tester uploads a screenshot of a bug, optionally pastes the error logs, and
gets a filed Jira bug back with a title, steps, expected vs actual, and the
visual detail written out — without typing any of it.

Status: **built, run end to end, and filed KAN-9 through the real form.**
`Screenshot_To_Bug_Reporter_n8n_workflow.json` is ready to import. The Jira
create step has not been fired at the real project yet — see the end of this
file.

## Decisions already made

| | |
|---|---|
| Instance | n8n Cloud (`jayamvishnudeep.app.n8n.cloud`) |
| Vision model | Groq `qwen/qwen3.6-27b` |
| Input | n8n **Form Trigger** (upload page), not a raw webhook |
| Output | Jira issue in **KAN** ("Bug-Tracking"), created directly |

The Jira target is the same project the BugTriage agent reads from. Worth being
precise about what that means: BugTriage's Jira node runs a plain `getAll` with
no project filter, and what came back was KAN-1 to KAN-7 in "Bug-Tracking" — so
KAN is the project the credential resolves to, rather than one BugTriage names
explicitly.

**Checked against the live Jira, and the concern was justified: KAN has no `Bug`
issue type.** `createmeta` returns only:

| id | name |
|---|---|
| 10001 | Epic |
| 10002 | Subtask |
| 10003 | Task |
| 10004 | Story |

So the planned fallback is now the actual behaviour — issues are filed as
**Task** (`10003`) in project **KAN** (`10000`), carrying a `bug` label so they
can still be found as bugs. Both ids are hardcoded in the workflow, so nothing
needs picking from a dropdown on import.

Adding a real `Bug` type to the project in Jira and switching `issueType` to its
id would be the cleaner end state.

## Model research

### Why Groq, and which model

Groq's [vision docs](https://console.groq.com/docs/vision) list exactly two
image-capable models right now:

| Model | Images per request |
|---|---|
| `qwen/qwen3.6-27b` | up to 5 |
| `qwen/qwen3.8-27b` | up to 3 |

Neither is marked preview or deprecated. **Going with `qwen/qwen3.6-27b`** — same
capability, and the higher image limit leaves room to accept a "before and after"
pair later without changing models.

**Verified against the live account**, not just the docs. `GET /openai/v1/models`
returns 14 models, and those two Qwen entries are the only vision-capable ones.
Llama 4 Scout and Maverick — which every pricing blog still names as Groq's
vision option — are **not on this account at all**. The docs were right and the
blogs were stale, which matters in a repo that has already had one Groq model
deprecated out from under it.

### Cost and the limit that actually bites

Measured on a real 314 KB screenshot through the finished workflow:

```
prompt_tokens      1529   (image + instructions + tester notes)
completion_tokens   379
total_tokens       1908   per bug report
round trip          1.5s
```

**Cost: $0.** That is inside the free tier and there is no reason to pay for a
vision model here.

The binding constraint is not price and not requests-per-day. It is
**output tokens per minute: 1,000** on the free `on_demand` tier. This was hit
during testing:

```
rate_limit_exceeded ... on output tokens per minute (OTPM):
Limit 1000, Used 436, Requested 715
```

Two things follow, both of which shaped the build:

1. Groq counts `max_completion_tokens` as **requested**, not as used. Setting a
   generous ceiling burns the quota whether or not the tokens are produced, so
   the workflow sets it to 800 rather than leaving it open.
2. At 800 requested per call, the practical ceiling is **about one report per
   minute**. Fine for a tester filing bugs by hand; not fine for a batch. A
   second submission inside the same minute returns 429.

The published "30 requests/minute, 14,400 requests/day" figures are real but
irrelevant — OTPM runs out first.

Limits are per organisation and shared across models, so heavy Groq use
elsewhere in this repo eats the same pool.

### The catch

n8n's built-in Groq node is a **chat-model sub-node** for AI Agents. It is not
built to accept a binary image, so this cannot be an Agent + Groq node the way
the BugTriage and RCA agents were built.

The working path is an **HTTP Request node** posting to Groq's OpenAI-compatible
endpoint with the image inlined as a base64 data URI. Two extra nodes compared
with OpenAI's native "Analyze Image" operation, and free instead of metered.

This is the same shape as the Hugging Face image call in
`07_n8n_Workflows/04_Daily_LinkedIn_post_telegram_approval` — an HTTP Request
node with a Header Auth credential — so the pattern is already proven in this
repo.

## The pipeline

```
Form Trigger  (screenshot + optional logs + context)
   -> Extract From File   (binary -> base64 string)
   -> Build Request       (Code: assemble the messages payload)
   -> HTTP Request        (POST Groq chat/completions, qwen3.6-27b)
   -> Parse Bug Report    (Code: parse + validate the JSON, fill gaps)
   -> Create Issue        (Jira: project, Task + bug label, ADF description)
   -> Carry Screenshot    (Code: re-attach the binary the pipeline dropped)
   -> Attach Screenshot   (Jira: upload the original image to the new issue)
   -> Build Result Page   (Code: render the confirmation page as HTML)
   -> Form Ending         (serve that page to the tester)
```

Ten nodes. Node-by-node notes:

**Form Trigger.** Fields:

| Field | Type | Required |
|---|---|---|
| Screenshot | File (`image/*`) | yes |
| What were you doing? | Textarea | no |
| Error logs / console output | Textarea | no |
| Environment | Dropdown — Production / Staging / QA / Local | yes |
| Your name | Text | no |

The two optional text fields matter more than they look. They are the only
source of anything the screenshot cannot show, and they are what keeps the model
from guessing (see the guard rail below).

**Extract From File.** Operation "Move File to Base64 String". Produces the
string the HTTP node inlines as `data:image/png;base64,...`.

**Build Request (Code).** Assembles the `messages` array and injects the tester's
notes into the instruction text. A Code node rather than raw expressions because
the payload is a nested array of content parts, which is painful to express
inline.

**HTTP Request.** `POST https://api.groq.com/openai/v1/chat/completions`,
Header Auth credential carrying `Authorization: Bearer gsk_...`, body:

```json
{
  "model": "qwen/qwen3.6-27b",
  "messages": [{ "role": "user", "content": [
      { "type": "text",      "text": "<instructions + tester notes>" },
      { "type": "image_url", "image_url": { "url": "data:image/png;base64,..." } }
  ]}],
  "response_format": { "type": "json_object" },
  "temperature": 0.2
}
```

Two things to verify at build time rather than assume: that `response_format`
JSON mode is accepted **alongside** an image on this model, and whether a
`system` message can coexist with image content. Groq has historically restricted
both on vision models. If either is rejected, the fallback is instructions in the
user message (already the plan) and parsing the JSON defensively in the next node
(also already the plan), so neither breaks the design.

**Parse Bug Report (Code).** The model returns JSON as a *string* inside
`choices[0].message.content`, so it needs parsing, then validating against the
schema below, then defaulting anything missing to `Not Provided`. Never let a
malformed response reach Jira.

**Create Issue.** Jira node. Description built as ADF.

**Attach Screenshot.** The whole point is the visual, so the image should live on
the ticket, not just be described. Uses the issue key from the previous node.

**Build Result Page (Code).** Renders the whole confirmation page as one HTML
string. See "The pages the tester sees" below.

**Form Ending.** `Show Text` with `{{ $json.html }}`, which serves that page
verbatim rather than n8n's default success screen.

## What the model is asked to produce

```
summary                one-line title, no "bug:" prefix
environment            echoed from the form
visible_symptom        what is actually wrong on screen
visual_details         layout, overlap, truncation, colour, alignment,
                       broken image, cut-off text, misaligned control
error_text_on_screen   any error message legible in the image (OCR)
affected_screen        the page or component, if identifiable
steps_to_reproduce     array; see the guard rail below
expected_result
actual_result
severity               S0-S4
priority               P0-P4
category               reuses the taxonomy from 02_BugTriage
confidence             High / Medium / Low
missing_information    semicolon-separated
```

Severity, priority and category deliberately reuse the vocabularies already
written for `02_BugTriage_n8n_AI_Agent`, so a bug filed by this agent can be
triaged by that one without translation.

## The guard rail that matters

**A screenshot cannot show how someone got there.** The obvious failure mode is a
vision model cheerfully inventing:

```
1. Navigate to the login page
2. Enter valid credentials
3. Click Login
```

...none of which it can possibly know. Steps invented like this are worse than no
steps, because they look authoritative and send a developer down a path the
tester never took.

So the prompt will state: derive steps **only** from what is visible in the image
plus what the tester typed in "What were you doing?". If that is not enough,
emit a single entry reading `Not Provided — tester to complete` and drop
`confidence` to Low. Same rule for the error text: transcribe what is legible,
never paraphrase or complete a truncated message.

This is the same discipline as the `Not Applicable` guard in the BugTriage
prompt, which is the rule that made that agent's output trustworthy.

## What was found by building it

Three things only showed up against the live API, and all three changed the
workflow:

**JSON mode cannot be combined with an image.** Sending
`response_format: {"type":"json_object"}` alongside image content returns
`400 json_validate_failed` with an empty `failed_generation`. Removed. The JSON
contract is now held by the prompt plus defensive parsing, which is why the
parser salvages the first `{...}` block and defaults every field rather than
trusting the model.

**Reasoning tokens ate the entire output budget.** qwen3.6 is a thinking model.
Left on, it spent all 900 completion tokens reasoning and the JSON came back
truncated mid-object — `parseFailed: true`, and a ticket full of "Not Provided".
Setting `reasoning_effort: 'none'` took the same screenshot from **900 tokens and
unparseable** to **128 tokens and clean JSON**. This is the single most important
line in the request payload.

**KAN has no Bug issue type**, so bugs file as Task with a `bug` label.

## Test result

The two Code nodes were executed with mocked n8n globals against the real Groq
API, using an actual screenshot from this repo — so what was tested is the code
that ships, not a paraphrase of it.

Output on a screenshot of a failing n8n run:

- Read the on-screen error verbatim: `This is an item, but it's empty.`
- Spotted the contradiction a human would: the node "shows a blue checkmark and
  Success in 139ms" while its output panel is empty.
- Rated it `S2 - Major` / `P1 - Current Sprint`, `Functional Logic`, confidence
  `Medium`, and explained why severity and priority differ.
- Listed genuinely useful `missing_information` — whether the Jira query is
  valid, whether empty is expected for the dataset.
- **Left steps to reproduce as `Not Provided - tester to complete`.** The guard
  held; it did not invent navigation it could not know.

If anything, the guard is slightly too strict — the tester's note was arguably
enough for a two-step repro and it still declined. That errs in the safe
direction, so it stays as is for now.

## The pages the tester sees

Both pages were rebuilt after the first live run. The default n8n form and its
"success" screen work, but they look like plumbing, and a tester who is asked to
trust an automated bug report should not be handed a page that looks automated.

What n8n actually allows, checked against the docs rather than assumed:

| | |
|---|---|
| Form Trigger | `customCss` option — a full stylesheet, no markup control |
| Form Ending | `Show Text` — arbitrary HTML, `<style>` and `<script>` included |
| Both | `appendAttribution: false` removes the n8n footer |

So the form is restyled but n8n-shaped, while the result page is entirely ours.

### One design across both

IBM Plex Sans with IBM Plex Mono — Plex was drawn for technical documentation,
and the mono carries the ticket key and the severity codes.

Both pages are **committed dark**, not theme-following: ground `#0b0e17`,
card `#151b2b`, accent `#5c7cfa`, with semantic colour kept separate from the
accent so severity still means something — `#3ecf8e` good, `#f0b429` warning,
`#ff6b6b` critical. Because the design commits to one world, every colour is
painted explicitly rather than inherited, and the result page declares
`color-scheme: dark` so form controls and scrollbars follow.

The result page is laid out as a **filed record**, not a success modal — the
ticket key as a monospace masthead, severity encoded as a stripe down the left
edge as well as in colour, triage values in a label/value grid. A centred green
tick would have said "form submitted"; a defect report is a record, so it reads
like one. The form card carries the same accent rail down its left edge, so the
two pages are visibly one product.

The page shows the Jira key, a link straight to the issue, whether the
screenshot attached, severity / priority / category / confidence, and the
environment. Two pieces of behaviour are worth naming:

- **Low confidence raises a callout** listing what the model could not tell,
  taken from `missingInformation`. That field is the honest half of the report,
  so it is surfaced rather than buried in the ticket description.
- **"Report another bug"** is built from `window.location.origin` plus the form
  path, so it works on any n8n host without a hardcoded URL. Same reasoning as
  the browse URL, which is derived from the Jira `self` link.

### Styling n8n's form: variables, not guesses

The first attempt at the form styled it with attribute-substring selectors —
`[class*="card"]`, `[class*="input"]`, `[class*="file"]` — on the theory that
they would survive a class rename. They did something worse than break: they
matched the wrong elements and the form came out visibly buggy.

| Selector | What it actually hit |
|---|---|
| `[class*="input"]` | `.inputs-wrapper`, drawing a border around every field at once |
| `[class*="file"]` | `.file-input-wrapper`, which wraps the **label** as well as the control |
| `[class*="required"]` | `label.form-required` — the label itself, so every required label turned red |

The submit button also stayed n8n salmon, because the override set
`--color-primary`, which the form template does not read.

The fix was to stop guessing and read n8n's own two files:
`packages/nodes-base/nodes/Form/cssVariables.ts` for the variable list, and
`packages/cli/templates/form-trigger.handlebars` for the markup. That settled
three things worth writing down:

- The button colour is `--color-submit-btn-bg`, defaulting to `#ff6d5a`.
- `--color-input-bg` **is read by the template but is not in n8n's defaults**.
  Without setting it, every field keeps a white background on a dark page.
- `.form-group` and `.form-label` have no default rules at all, so field
  spacing is whatever the browser does unless it is set deliberately.

The stylesheet now drives colour entirely through documented variables, and
the handful of structural rules target real class names.

### The bug that only showed up in the generated HTML

The closing `</script>` tag was written with a doubled backslash in the node
source, so the page shipped a literal `<\/script>` — a script block that never
closed, and everything after it swallowed. One backslash is what evaluates to a
plain closing tag. It is invisible in the node editor and obvious in the output,
which is the argument for checking the rendered HTML rather than the code that
writes it.

## Why the screenshot never attached

Every ticket filed came back marked "Screenshot not attached", including the
ones where the upload plainly worked. The cause is a property of n8n rather
than of Jira: **binary data does not survive a Code or HTTP node.**

`Build Groq Request` returns plain JSON, so the file is gone from that point
on. The HTTP node returns Groq's response, `Parse Bug Report` returns its own
object, and the Jira node returns the created issue. By the time
`Attach Screenshot to Issue` runs, its `binaryPropertyName` of `Screenshot`
matches nothing at all.

It failed quietly because the node is deliberately set to
`onError: continueRegularOutput` with `alwaysOutputData` — losing the image
should never lose the ticket. So the attach failed, an empty item came out,
and the result page correctly reported what it saw.

The fix is a Code node, `Carry Screenshot Forward`, sitting between the create
and the attach. It reads the binary back off the form trigger and re-emits it
alongside the created issue:

```js
const created = $input.first().json;
const form = $('Bug Report Form').first();
const bin = form.binary || {};
const key = Object.keys(bin)[0];
if (!key) throw new Error('No binary on the form submission');
return [{ json: created, binary: { Screenshot: bin[key] } }];
```

Two details are deliberate. It takes `Object.keys(bin)[0]` rather than assuming
the property is called `Screenshot` — the form names it after the field label,
which a rename would change — and then republishes it under the fixed key the
attach node reads, so the two can never drift apart. And it throws when there
is no file, because a missing screenshot at that point is a real fault, not a
state to paper over.

### How the page was checked

Both Code nodes are executed with mocked n8n globals and their output asserted
— so what is checked is the code that ships. Thirty-three assertions in all,
and they pass.

`Carry Screenshot Forward` is checked for passing the Jira key through, for
re-attaching under the fixed key, for still working when the form names the
binary property something else, and for throwing rather than continuing when
no file is present. The attach node's `binaryPropertyName` is asserted against
the key the Code node writes, so the two cannot drift apart silently.

`Build Result Page` is rendered in three states: S1 / low confidence with three
missing items and the screenshot attached, S3 / high confidence with it not
attached, and one where the tester's text is `<script>alert(1)</script>` — that
last one asserts the summary comes back escaped and the page still contains
exactly one script block. The rest covers the closing script tag, the derived
browse URL, the severity stripe, the callout appearing only below High
confidence, the dark ground being painted explicitly with no light tokens left
behind, and no n8n branding anywhere.

## Still to do

1. **Re-import and file one bug.** The pipeline is proven live through KAN-12:
   the form, the Groq call, the Jira create and the custom result page all work
   on n8n Cloud. What has never yet succeeded is the attachment, so the thing to
   watch on the next run is the pill reading **Screenshot attached** rather than
   not. Also unproven: the dark styling, and whether n8n Cloud reaches Google
   Fonts — the type falls back to system faces if it cannot, which degrades
   rather than breaks.
2. Consider adding a real `Bug` issue type to KAN.

### On import

All three credentialled nodes now carry their credential by id, so an import
resolves without anything being picked from a dropdown: the two Jira nodes use
`Jira SW Cloud account`, and the Groq node uses n8n's built-in `groqApi`
credential type (`Groq account 2`) rather than the generic header auth it was
first built with.

## Deliberately not in v1

- **No approval gate.** The point of the tool is filing a bug in seconds. If one
  is wanted later, it goes in as a Telegram `sendAndWait` **plus an IF node on
  the result** — the gate has to actually branch, or it is decoration.
- **No duplicate detection.** Worth adding later as a JQL search on the summary
  before creating.
- **No multi-image support**, though the model allows five, so before/after pairs
  are a natural v2.
