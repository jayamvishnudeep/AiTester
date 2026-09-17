# Screenshot to Bug Reporter — n8n AI Agent

A tester uploads a screenshot of a bug, optionally pastes the error logs, and
gets a filed Jira ticket back — title, symptom, visual detail, expected versus
actual, severity, priority and category — without typing any of it.

**Live form:** <https://jayamvishnudeep.app.n8n.cloud/form/report-bug>

> The workflow is published, but at the time of writing that URL answers `401`
> with `WWW-Authenticate: Basic realm="Enter credentials"`, so visitors get a
> browser password prompt. The Form Trigger's **Authentication** is set to Basic
> Auth on the live copy. Set it to **None** and publish again to make the link
> genuinely public. The setting is not in the exported JSON, which defaults to
> none.

Exported as `Screenshot_To_Bug_Reporter_n8n_workflow.json`. The full build log,
including the model research and the things that only showed up against the live
API, is in [`plan.md`](plan.md).

## The form

![The bug submission form](Screenshot%20Bug%20Form.png)

Five fields, two of which do the heavy lifting:

| Field | Type | Required |
|---|---|---|
| Screenshot | File (`.png .jpg .jpeg .webp`) | yes |
| Environment | Dropdown — Production / Staging / QA / Local | yes |
| What were you doing | Textarea | no |
| Error logs or console output | Textarea | no |
| Your name | Text | no |

The two optional boxes matter more than they look. They are the only source of
anything a screenshot cannot show, and they are what stops the model guessing.

## What the tester gets back

![The confirmation page showing KAN-13 with the screenshot attached](Form%20Submisssion%20Success%20with%20Jira%20Ticket%20number%20visible.png)

Not n8n's default "form submitted" screen — a custom page built by a Code node
and served through the Form Ending's `Show Text` option. It is laid out as a
**filed record** rather than a success modal: the ticket key as a monospace
masthead, severity as a stripe down the left edge as well as in colour, and the
triage values in a label/value grid.

Two behaviours worth naming:

- **Below High confidence it raises a callout** listing what the model could not
  determine. That list is the honest half of the report, so it is surfaced
  rather than buried in the ticket description.
- **"Report another bug"** is built from `window.location.origin` plus the form
  path, so it works on any n8n host without a hardcoded URL — same reasoning as
  the Jira browse link, which is derived from the API `self` link.

## What lands in Jira

![The Jira ticket created automatically](Jira%20ticket%20created%20automatically.png)

Filed into **KAN** ("Bug-Tracking") as a **Task** carrying the labels `bug`,
`screenshot-reported` and `ai-drafted`, with the original screenshot attached.

It files as Task rather than Bug because `createmeta` on this project returns
only Epic, Subtask, Task and Story — **KAN has no `Bug` issue type**. Adding one
and pointing `issueType` at its id would be the cleaner end state.

Note what the Steps to Reproduce field says: `Not Provided - tester to complete`.
That is the guard rail working, and it is the most important thing in the whole
agent — see below.

## The pipeline

![The workflow on the n8n canvas](n8n%20Workflow%20for%20Screenshot%20to%20Bug%20Creation.png)

| Node | Type | Role |
|---|---|---|
| Bug Report Form | `formTrigger` | Upload page, custom CSS, no n8n branding |
| Screenshot to Base64 | `extractFromFile` | Binary → base64 string |
| Build Groq Request | `code` | Assembles the vision payload and the prompt |
| Analyze Screenshot (Groq) | `httpRequest` | POST to Groq, `qwen/qwen3.6-27b` |
| Parse Bug Report | `code` | Parses, validates, defaults every field |
| Create Jira Bug | `jira` | Creates the issue |
| Carry Screenshot Forward | `code` | Re-attaches the binary the pipeline dropped |
| Attach Screenshot to Issue | `jira` | Uploads the image to the new issue |
| Build Result Page | `code` | Renders the confirmation page as HTML |
| Show Result to Tester | `form` | Serves that page |

A full run takes about **30 seconds**, most of it the Groq call and Jira.

## The guard rail that matters

**A screenshot cannot show how someone got there.** The obvious failure mode is
a vision model cheerfully inventing "1. Navigate to the login page, 2. Enter
valid credentials, 3. Click Login" — none of which it can possibly know.

Invented steps are worse than no steps, because they look authoritative and send
a developer down a path the tester never took. So the prompt states: derive
steps **only** from what is visible in the image plus what the tester typed. If
that is not enough, emit `Not Provided - tester to complete` and drop confidence
to Low. Same rule for error text — transcribe what is legible, never paraphrase
or complete a truncated message.

## Why the screenshot used to come back unattached

Worth knowing if you build anything similar: **binary data does not survive a
Code or HTTP node in n8n.** `Build Groq Request` returns plain JSON, so the file
is gone from that point on, and by the time the Jira attachment node ran its
`binaryPropertyName` matched nothing. It failed silently because the node is set
to `onError: continueRegularOutput` — losing the image should never lose the
ticket.

`Carry Screenshot Forward` fixes it by reading the binary back off the form
trigger and re-emitting it alongside the created issue:

```js
const created = $input.first().json;
const form = $('Bug Report Form').first();
const bin = form.binary || {};
const key = Object.keys(bin)[0];
if (!key) throw new Error('No binary on the form submission');
return [{ json: created, binary: { Screenshot: bin[key] } }];
```

It reads `Object.keys(bin)[0]` rather than assuming the property is called
`Screenshot` — the form names it after the field label, so renaming the field
would break a hardcoded name — then republishes it under the fixed key the
attach node reads.

## Styling an n8n form

The form and the result page are both dark, driven from one palette: ground
`#0b0e17`, card `#151b2b`, accent `#5c7cfa`, with semantic colour kept separate
from the accent so severity still means something.

The form is styled through the Form Trigger's **Custom CSS** option. Three
things are worth knowing before writing any, all of them learned the hard way:

- Colour goes through n8n's own variables, listed in
  `packages/nodes-base/nodes/Form/cssVariables.ts`. The submit button is
  `--color-submit-btn-bg`, defaulting to salmon `#ff6d5a` — setting
  `--color-primary` does nothing.
- **`--color-input-bg` is read by the template but is not in n8n's defaults.**
  Without setting it, every field keeps a white background on a dark page.
- Target real class names from
  `packages/cli/templates/form-trigger.handlebars` — `.card`, `.form-group`,
  `.form-input`, `.select-input`, `.file-input-wrapper`, `#submit-btn`. Guessing
  with `[class*="..."]` selectors matches the wrong elements: `[class*="input"]`
  hits `.inputs-wrapper` and boxes in every field at once, and anything matching
  "required" hits `label.form-required` — the label itself — turning every
  required label red.

`.form-group` and `.form-label` have no default rules at all, so field spacing
is browser default until you set it.

## Setting it up

Import the JSON into n8n. All three credentialled nodes carry their credential
by id, so nothing needs picking from a dropdown:

| Credential | Used by |
|---|---|
| Groq (`groqApi`) | Analyze Screenshot (Groq) |
| Jira SW Cloud (`jiraSoftwareCloudApi`) | Create Jira Bug, Attach Screenshot to Issue |

Then change two values to your own, since the export carries the ones from this
account:

- the **project** and **issueType** ids on Create Jira Bug — `10000` / `10003`
  here, meaning KAN and Task
- the **path** on the Form Trigger — `report-bug`, which is what makes the
  production URL `/form/report-bug`

## Notes and limits

- **Groq's free tier is capped on output tokens per minute (1,000)**, and it
  counts `max_completion_tokens` as *requested*, not used. At the 800 set here
  the practical ceiling is about **one report per minute**; a second submission
  inside the same minute returns 429. Requests-per-day never runs out first.
- **`reasoning_effort: 'none'` is load-bearing.** qwen3.6 is a thinking model;
  left on, it spends the whole completion budget reasoning and the JSON comes
  back truncated mid-object. The same screenshot went from 900 tokens and
  unparseable to 128 tokens and clean JSON with it off.
- **JSON mode cannot be combined with an image** on this model — sending
  `response_format: {"type":"json_object"}` alongside image content returns
  `400 json_validate_failed`. The JSON contract is held by the prompt plus
  defensive parsing instead.
- The instance is on an **n8n Cloud trial**, so the production URL stops
  answering when the trial lapses.
- No approval gate and no duplicate detection in v1. The model accepts up to
  five images, so before/after pairs are a natural v2.
