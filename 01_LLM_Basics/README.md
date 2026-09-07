# LLM Basics

One file, and it is the most reused idea in this repository.

`ANTI-HALLUCINATION.rules.md` is a prompt contract that forces a model to work
only from evidence you gave it, and to say so plainly when the evidence runs out.

## What it says

**Scope.** The model may use only what was explicitly provided — PRD, API docs,
logs, screenshots, test data, user input. Nothing else.

**The six rules.** Never invent features, APIs, error codes, UI elements or
behaviour. Never assume "typical" system behaviour. When information is missing,
answer `Insufficient information to determine.` Every assertion must be
traceable to the input. Anything inferred must be labelled
`Inference (low confidence)`. Output must be deterministic and repeatable.

**A four-step process**, not just a list of prohibitions:

1. Extract the verifiable facts from the input.
2. List what is unknown or missing.
3. Generate output *only* from step 1.
4. Self-check for hallucinations and contradictions.

**A fixed output shape** — Verified Facts, Missing / Unknown Information,
Generated Output, Self-Validation Check — so the gaps are a visible section of
the answer rather than something you have to notice is absent.

And the closing line, which is the whole idea in one sentence:

> If you cannot complete a step, stop and report why.

## Why it matters to everything else here

Almost every later folder is this rule wearing different clothes. When you come
back to this repo, this is the thread to follow:

| Where | How the same rule appears |
|---|---|
| `02_Promt_Engineering` | `VWO_Login_Test_Plan.md` is written in this exact output format, opening with **Verified Facts** |
| `03_LocalTestCaseGenerator` | The QA template says *"Use ONLY the provided requirements… if information is missing, state Not specified"* |
| `07_.../02_BugTriage` | `Not Applicable` — a Story or Task is never forced into a defect classification |
| `08_.../01_Screenshot_To_Bug_Reporter` | Steps to reproduce are never invented from an image; the field reads `Not Provided - tester to complete` and confidence drops to Low |

The reason it keeps coming back is that in QA a confident wrong answer is worse
than no answer. An invented reproduction step sends a developer down a path
nobody took; an invented severity wakes someone at 2 AM for a typo.

## Using it

Paste the file as a system prompt, then supply your evidence below it. It works
unchanged with any model. The output format is the part people drop first and
the part worth keeping — without a **Missing / Unknown Information** section,
nothing forces the model to admit what it did not have.
