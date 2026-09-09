# Plan — Visual Diff Explainer (n8n AI Agent)

A UI QA has two screenshots — before and after — and can tell something is
wrong without being able to say what. The explainer reads both and describes the
change in plain English a developer can act on.

Status: **built and tested against the live Groq API.** Thirty-four assertions
pass, including live vision calls. Not yet imported into n8n Cloud. Read
[the detection floor](#the-detection-floor) before trusting it on fine changes.

## The brief

| | |
|---|---|
| Audience | UI QA |
| Problem | Hard to see subtle visual bugs |
| Input | Before / after screenshots |
| Output | Natural language explanation of the diff |
| Helpful for | Communicating visual bugs to developers clearly |
| Given shape | Webhook → OpenAI Vision node (compare images) → AI Agent (explain diff) → Slack / Jira comment |

## The failure mode

Every agent in this folder has one, and this one's is the most seductive:

**A vision model asked "what changed?" will always find something.**

Ask it to compare two identical screenshots and it will produce a confident
paragraph about spacing, shade and alignment. Nothing in the output looks wrong.
A UI QA then files a bug against a change that never happened, and a developer
spends a morning looking for it.

So the rule this agent is built on:

> **"Nothing changed" has to be an answer the agent can give — and one that code
> can verify.**

Two screenshots that are byte-identical are not a judgement call. The engine
hashes both before spending a model call, and when they match it reports
**No Difference** without asking. That is a fact the model cannot override, and
it is the only part of a visual comparison that is genuinely computable without
an image library.

## What can be computed, and what cannot

n8n's Code node has no image processing available, so there is no pixel diff to
be had. What *is* computable from the raw bytes, and therefore stated as fact
rather than asked for:

| Fact | How |
|---|---|
| Are the images identical? | An exact buffer comparison — both files are in the node at once, so no hash is needed |
| Dimensions of each | Parsed from the PNG `IHDR` header, or JPEG `SOF` markers |
| Did the canvas resize? | Comparing those dimensions |
| File size delta | Byte length |
| Format, and whether they match | Magic bytes |

A dimension change is worth stating on its own: if the "after" is a different
size, every position in it has moved, and a model describing that as "the button
shifted left" is describing an artefact of the capture rather than a bug.

Everything else — colour, spacing, wording, missing elements — is the model's
job, and the guard rails below constrain how it may report them.

## The pipeline

```
Webhook               POST /visual-diff  { before, after, context, issue_key }
  -> Inspect Images     (Code)   hash, dimensions, format; decide if there is anything to do
  -> Anything Changed?  (IF)     identical bytes short-circuit the whole run
  -> Compare Screenshots (vision, both images in one call)
  -> Explain The Diff   (AI Agent + Structured Output Parser)
  -> Validate Findings  (Code)   guard rails
  -> Comment on Jira  ->  Send to Telegram  ->  Respond to Caller
```

The two-node split between *seeing* and *explaining* is the brief's, and it is
right: the vision call describes what is on the two images, and the agent turns
that into something a developer can act on. Keeping them apart also means the
explanation step can be given a schema and guard rails without fighting the
vision model's own formatting.

## The images

Accepted three ways, as with the earlier agents:

| How | When |
|---|---|
| `before_url` / `after_url` | screenshots already in CI storage |
| binary upload as `before` and `after` | a tester with two files |
| base64 in the body | scripted callers |

Both images go into a **single** call as two `image_url` content parts, before
first and after second, and the prompt says which is which. That matters: a
model shown one image at a time cannot compare them, it can only describe each.

Supplying URLs instead of files is cheaper — nothing is uploaded — but it costs
the identical-file check and the dimension facts, since the bytes never reach
the workflow. The report says so rather than quietly dropping the guarantee.

## What the model is asked to produce

```
verdict            Difference Found | No Difference | Cannot Compare
summary            one sentence a developer can read in a standup
differences[]      { region, element, change_type, before_state, after_state, severity }
likely_cause       only when the evidence supports one, otherwise Unable to Determine
developer_note     what to look at, phrased for whoever will fix it
questions[]        what a screenshot cannot answer
confidence         High | Medium | Low
```

`change_type` is a closed vocabulary, so the output can be grouped and counted:
`Colour`, `Spacing or Alignment`, `Text or Wording`, `Missing Element`,
`Added Element`, `Size or Scale`, `State or Styling`, `Image or Icon`,
`Layout Reflow`, `Unable to Determine`.

`severity` reuses the S0–S4 scale from `07_.../02_BugTriage`, so a visual bug
raised here can be triaged there without translation.

## The guard rails

**1. Identical images can never produce differences.** Checked in code before
the model is called, and enforced again after it.

**2. Every difference must be localised.** A finding needs a `region` and either
an `element` or a concrete `before_state`/`after_state` pair. "The layout feels
different" is not a defect report; it is the absence of one. Unlocalised
findings are dropped and counted.

**3. The canvas size is a fact, not an observation.** Dimensions come from the
file headers. If they differ, that is reported as a capture difference, and the
run is marked so that position-based findings are read with suspicion.

**4. "No Difference" is a first-class answer.** The prompt says so explicitly and
the schema allows an empty `differences` array. An explainer that never returns
"nothing changed" cannot be trusted when it says something did.

## Decisions taken

**1. Groq vision, not OpenAI.** Free, and already proven on this account. The
costs were known going in from `01_Screenshot_To_Bug_Reporter`: n8n's Groq
chat-model node cannot take a binary image, so the vision call is a hand-built
HTTP Request; JSON mode is rejected alongside an image, which is why the
structured output comes from a second, text-only agent step rather than from the
vision call itself. That split is the brief's shape anyway.

**2. Jira comment plus Telegram.** When the request carries an `issue_key` the
explanation is added to that ticket; Telegram always fires, so a request without
a key still reaches someone. The Jira node is `onError: continueRegularOutput`,
because a missing key is a normal case rather than a failure.

## What was found by building it

**The vision tier's output cap is 1,000 tokens a minute, and asking for more is
rejected outright.** The first live call requested 1,200 and came back
`Request too large ... on output tokens per minute (OTPM): Limit 1000,
Requested 1200` — before the model ran at all, because Groq counts the ceiling
as requested rather than used. `01_Screenshot_To_Bug_Reporter` documents this
exact limit and I still walked into it. Set to 800, which also means **roughly
one comparison per minute**.

**The model choice from `01_` is wrong for this job, and only a controlled probe
showed it.** Both agents use Groq vision, so reusing qwen3.6 looked obvious.
Run side by side on the same before/after pair:

| Model | Subtle pair (case change, colour shift, 4px spacing) | Obvious pair (banner added, button recoloured and relabelled) |
|---|---|---|
| `qwen/qwen3.6-27b` | **"The two screenshots are identical."** | found all three changes |
| `qwen/qwen3.8-27b` | **found the `Sign in` → `Sign In` change** | found all three changes |

qwen3.6 accepts five images against qwen3.8's three, and that is what decided it
for `01_`. A comparison only ever needs two, and catching the subtle case is the
entire purpose here — so this agent uses **qwen3.8-27b**.

**A test can pass green while the thing it tests is broken.** The first
assertion for "it finds the button label change" was
`/sign\s*in/i.test(desc) && /(capital|Sign In|wording|text|label)/i.test(desc)`.
The model had answered *"The two screenshots are identical... the 'Sign in'
button shows no differences in text, color, or style"* — which contains both
patterns, so the check passed while the agent was failing its core job. An
assertion that matches words appearing in a sentence asserting the opposite is
worse than no assertion, because it reports confidence. It now tests that the
description does **not** claim the pair is identical.

## The detection floor

Worth knowing before trusting this on fine work. On the sample pair, three
changes were made deliberately:

| Change | Detected by qwen3.8 |
|---|---|
| Button label `Sign in` → `Sign In` | **yes**, quoted exactly |
| Button colour `#3452d4` → `#4a63d8` | **no** — reported "no visible changes to colors" |
| Field spacing 18px → 14px | **no** — reported "no visible changes to layout, spacing" |

So the tool catches text and structural changes well and **misses small colour
shifts and a few pixels of spacing**. Given the brief is "hard to see subtle
visual bugs", that limit belongs in the README rather than buried here: this
explains changes, it does not detect every one. A pixel-diff tool remains the
right instrument for finding sub-perceptual drift; this one is for explaining
what a human or a diff tool has already flagged.

## Test result

Both Code nodes are executed with mocked n8n globals and two real vision calls
are made with the real prompt. **Thirty-four assertions, all passing.**

```
Inspect Images   PNG 760x520 read from the header; JPEG dimensions from the SOF
                 marker; byte-identical pair detected; canvas change detected;
                 URLs accepted with the identical check reported unavailable;
                 a non-image and a request with no images both refused

live vision      3,844 + 222 = 4,066 tokens, 1.4s
                 "Sign In Button - Change: the button text capitalization has
                  changed. Before: 'Sign in'. After: 'Sign In'."

same image twice NO VISIBLE DIFFERENCE, unprompted - and the code short-circuits
                 that case before the model is called anyway
```

The guard rails were tested by attacking them: a model reporting two differences
against byte-identical files has both discarded and the verdict forced to
`No Difference`; a difference with no region, element or before/after state is
dropped; invented `change_type` and `severity` values are clamped; a canvas size
change lowers confidence and is noted; and the validator produces a complete
report with no model output at all, which is the short-circuit path.

## Deliverables

```
05_Visual_Diff_Explainer/
├── plan.md
├── Visual_Diff_Explainer_n8n_workflow.json
├── sample_before.png
├── sample_after.png
└── README.md
```

## Deliberately not in v1

- **No pixel diffing or highlighted overlay.** The Code node has no image
  library, so an annotated image would need an external service.
- **No baseline management.** The caller supplies both images; storing approved
  baselines and detecting drift over time is a different tool.
- **No batch comparison.** One pair per call, because two images is already the
  interesting case and a set of twenty is a different interface.
