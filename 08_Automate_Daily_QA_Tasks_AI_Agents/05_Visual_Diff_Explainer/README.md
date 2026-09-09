# Visual Diff Explainer — n8n AI Agent

A UI QA has two screenshots, before and after, and can tell something is wrong
without being able to say what. The explainer reads both and describes the
change in plain English — then puts it on the Jira ticket where the developer
will read it.

Exported as `Visual_Diff_Explainer_n8n_workflow.json`. The build log, including
the model comparison that changed the design, is in [`plan.md`](plan.md).

> **Read [what it cannot see](#what-it-cannot-see) before trusting it.** It
> catches text and structural changes reliably and misses small colour shifts
> and a few pixels of spacing. That limit is measured, not assumed.

## The failure mode

**A vision model asked "what changed?" will always find something.**

Show it two identical screenshots and you get a confident paragraph about
spacing, shade and alignment. Nothing in the output looks wrong. A QA files a
bug against a change that never happened, and a developer spends a morning
looking for it.

> **"Nothing changed" has to be an answer — and one that code can verify.**

Whether two files are byte-identical is not a judgement call, so the workflow
settles it before spending a model call. Identical bytes short-circuit the whole
run to `No Difference`, and even on the normal path any difference reported
against identical files is discarded. That is the one part of a visual
comparison that is genuinely computable without an image library.

## What is measured and what is asked

n8n's Code node has no image processing, so there is no pixel diff to be had.
What can be read from the raw bytes is stated as fact:

| Fact | How |
|---|---|
| Are the files identical? | Exact buffer comparison |
| Canvas dimensions | PNG `IHDR` header, or the JPEG `SOF` marker |
| Did the canvas resize? | Comparing those |
| File size delta | Byte length |

A canvas resize matters on its own: if the after image is a different size then
everything in it has moved, and "the button shifted left" is describing the
screenshot rather than the bug. When that happens the run says so and confidence
drops.

Everything else — colour, wording, missing elements — is the model's, under the
guard rails below.

## The pipeline

```
Webhook              POST /visual-diff  { before, after, context, issue_key }
  -> Extract Before / After Image  (Extract From File)  binary -> base64
  -> Inspect Images     (Code)  facts, and the vision request
  -> Are They Identical? (IF)   identical bytes skip the model entirely
        |                    \
        |                     -> Compare Screenshots (Groq vision, both images, one call)
        |                     -> Explain The Diff    (AI Agent + Structured Output Parser)
        \--------------------> Validate Findings     (Code)  guard rails
  -> Comment on Jira  ->  Send to Telegram  ->  Respond to Caller
```

| Node | Type | Role |
|---|---|---|
| Visual Diff Webhook | `webhook` | `POST /visual-diff` |
| Extract Before / After Image | `extractFromFile` | Binary to base64 - reading it directly does not work |
| Inspect Images | `code` | Measures the files, builds the vision request |
| Are They Identical? | `if` | The short-circuit |
| Compare Screenshots | `httpRequest` | Groq `qwen3.8-27b`, both images in one call |
| Explain The Diff | `agent` | Structures the description for a developer |
| Groq Chat Model | `lmChatGroq` | `gpt-oss-120b`, text only |
| Diff Schema | `outputParserStructured` | Forces the finding shape |
| Validate Findings | `code` | Guard rails; builds both message bodies |
| Comment on Jira | `jira` | `issueComment:add`, when an `issue_key` was sent |
| Send to Telegram | `telegram` | Always fires |
| Respond to Caller | `respondToWebhook` | Full report as JSON |

**Why seeing and explaining are separate nodes.** The brief splits them, and
there is a hard reason to: Groq rejects JSON mode when an image is attached, so
the vision call cannot return structured output. It returns prose; a second,
text-only agent turns that into the schema. Splitting them also means the
explanation step can carry guard rails without fighting the vision model's
formatting.

## Choosing the model — the part that surprised me

`01_Screenshot_To_Bug_Reporter` uses Groq's `qwen3.6-27b`, so reusing it here
looked obvious. Run side by side on the same before/after pair:

| Model | Subtle pair<br>(case change, colour shift, 4px spacing) | Obvious pair<br>(banner added, button recoloured and relabelled) |
|---|---|---|
| `qwen/qwen3.6-27b` | **"The two screenshots are identical."** | found all three |
| `qwen/qwen3.8-27b` | **found `Sign in` → `Sign In`** | found all three |

qwen3.6 takes five images to qwen3.8's three, which is what decided it for
`01_`. A comparison needs two, and catching the subtle case is the entire point
here — so this agent uses **qwen3.8-27b**.

The lesson generalises: the right model for one job in a family is not
automatically right for the next one, and only a controlled comparison shows it.

## What it cannot see

Three changes were made to the sample pair on purpose. The tool found one:

| Change | Detected |
|---|---|
| Button label `Sign in` → `Sign In` | **yes**, quoted exactly |
| Button colour `#3452d4` → `#4a63d8` | no — reported "no visible changes to colors" |
| Field spacing 18px → 14px | no — reported "no visible changes to layout, spacing" |

So this **explains** visual differences; it does not **detect** all of them. For
sub-perceptual drift a pixel-diff tool is the right instrument, and this agent is
what you point at the pair once something has been flagged — by a human, a
snapshot test, or that diff tool.

Saying so is the point. A tool whose limits are documented is usable; one that
quietly misses things is not.

## The guard rails

**1. Identical files can never produce differences.** Enforced twice — once by
skipping the model, once by discarding anything reported anyway.

**2. Every difference must be localised.** A finding needs a region or element,
and a before/after pair. "The layout feels different" is the absence of a defect
report, and it is dropped and counted.

**3. The canvas size is a fact.** Read from the file headers; the model is told
and may not contradict it. A resize lowers confidence automatically.

**4. "No Difference" is a first-class answer**, in the prompt and in the schema.
An explainer that never says "nothing changed" cannot be trusted when it says
something did.

## Trying it

`sample_before.png` and `sample_after.png` are a login card rendered twice.

```bash
curl -X POST "https://<your-n8n-host>/webhook-test/visual-diff" \
  -F "before=@sample_before.png" \
  -F "after=@sample_after.png" \
  -F "context=Login card after a styling change" \
  -F "issue_key=KAN-42"
```

Or send `before_base64` / `after_base64`, or `before_url` / `after_url` as JSON.
Note that URLs skip the identical-file check, since the bytes never reach the
workflow — the report says so when that happens.

Measured on the real pair: **4,066 tokens, 1.4s**, and the description came back

> *"Sign In Button — Change: the button text capitalization has changed.
> Before: 'Sign in'. After: 'Sign In'."*

## Setting it up

Import the JSON. Groq, Jira and Telegram all carry their credentials by id, so
nothing needs picking. A request without an `issue_key` is normal — the Jira
node fails soft and the explanation still reaches Telegram and the caller.

**One comparison per minute.** Groq's vision tier caps output at 1,000 tokens a
minute and counts the requested ceiling rather than what is used, so the request
asks for 800. Ask for more and it is rejected before the model runs.

## Worth remembering

- **Compute what is computable.** Whether two files are identical is a fact, and
  a fact beats a confident opinion every time.
- **Don't inherit a model choice across jobs.** qwen3.6 was right for `01_` and
  is wrong here, and nothing but a side-by-side probe would have shown it.
- **A test can pass green while the thing it tests is broken.** The first
  assertion here matched the words "Sign in" and "text" inside a sentence saying
  the images were *identical* — so it passed while the agent failed its whole
  purpose. Assert on the conclusion, not on vocabulary that appears either way.
- **Document the detection floor.** A tool that says what it cannot do is more
  useful than one that appears to do everything.
- **A mock that is more convenient than reality tests the mock.** Every harness
  case fed binary as inline base64, because that is easy. n8n can hold binary on
  the filesystem instead, where `item.binary[key].data` is empty — so the first
  live run read two empty buffers, found them equal, and reported two different
  screenshots as *"byte-identical. Nothing changed."* with High confidence.
  Thirty-four assertions had passed over it. Binary now goes through **Extract
  From File** nodes, and an image under 100 bytes is an error rather than a
  verdict.
