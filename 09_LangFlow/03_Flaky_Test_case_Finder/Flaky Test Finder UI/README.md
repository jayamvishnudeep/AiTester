# Flaky Test Finder UI

A browser front end for the Flaky Test Finder flow. Point it at a folder holding
two Playwright reports, press **Compare runs**, and read which tests disagree
with themselves.

![The UI after a comparison: a banner reading "2 flaky tests", tiles for compared, flaky, broken, stable and flake rate, a run composition chart showing how each run broke down, then one card per flaky test showing its attempts in run 1 and run 2 as coloured squares, a separate section for the two tests that failed in both runs, and the agent's recommendations at the bottom](Flaky_Test_Finder_UI.png)

Above: 2 flaky tests found out of 100 compared, in about five seconds.

---

## Before you start

Two things must already be true:

1. **The flow is set up in Langflow.** Follow the [parent folder's
   README](../README.md) first — it covers importing the flow, storing your Groq
   key and pointing it at a results folder.
2. **Langflow is running**, normally at `http://127.0.0.1:7860`.

Without those the page opens but has nothing to talk to.

---

## Setup

### 1. Open the page

Double-click **`index.html`**.

That is the whole install — no `npm install`, no build step, no server.

### 2. Add your Langflow API key

Open the **Connection** panel. You need one value:

- In Langflow, go to **Settings → API Keys → Add New**
- Copy the key — it is shown only once
- Paste it into **Langflow API key**

Check the other two while you are there:

| Field | What it should be |
|---|---|
| **Base URL** | Where Langflow is running — `http://127.0.0.1:7860` |
| **Flow ID** | The long id in Langflow's address bar when your flow is open |

Your Flow ID is the part after `/flow/`:

```
http://127.0.0.1:7860/flow/90a3ee19-9e17-42ac-82ef-073d6120b4fc
                           └──────────── this ────────────┘
```

All of it is saved in your browser, so you do this once.

### 3. Check the connection

The pill in the top right should read **"Langflow connected"** with a green dot.
A red dot means Langflow is not running or the Base URL is wrong.

---

## Using it

Put the path to a folder holding **`result1.json`** and **`result2.json`** in the
**Results folder** box, then press **Compare runs** (or hit Enter). Leave the box
empty to use whatever folder the flow itself is pointed at.

Give it about five seconds.

### What comes back

| | |
|---|---|
| **The verdict** | How many tests are flaky, out of how many compared |
| **Tiles** | Compared, flaky, broken, stable, and the flake rate |
| **Run composition** | How each run broke down into passed, retried and failed |
| **Flaky tests** | One card each, with attempts and the error |
| **Not flaky — actually broken** | Failed in both runs, so they need fixing rather than quarantining |
| **Recommendations** | The agent's write-up, with the model and token count |

### Reading the attempt squares

Playwright records every attempt it makes at a test. Each card shows them as
squares — green passed, red failed — for both runs:

```
catalog/search.spec.ts
Search › shows type-ahead suggestions after three characters
RUN 1  ✗ ✗   →   RUN 2  ✓
```

Failed twice, then passed on the next run. That is flake.

```
checkout/payment.spec.ts
Payment › declines an expired card with a field-level error
RUN 1  ✗ ✗   →   RUN 2  ✗ ✗
```

Failed every time it was asked. That is a defect, and it sits in its own section
so it does not get quarantined by mistake.

### History

Every comparison is kept under **History**, newest first, and survives closing
the browser. Click a row to bring that result back on screen. **Clear history**
empties the list.

### Light and dark

The button beside the connection pill switches themes. Left alone, the page
follows whatever your system is set to.

---

## Changing the defaults

If you always use the same Langflow, edit the block near the top of the script
inside `index.html` (around line 425) and you can leave the Connection panel
closed:

```js
const DEFAULTS = {
  baseUrl: "http://127.0.0.1:7860",
  flowId:  "90a3ee19-9e17-42ac-82ef-073d6120b4fc",
  apiKey:  "",
  folder:  "…/03_Flaky_Test_case_Finder/results",
};
```

- **`flowId`** — your own flow's id
- **`folder`** — the results folder you use most
- **`apiKey`** — leave blank. Keys belong in the browser, not in a file you might
  commit

---

## How it is built

One HTML file: React 18 with `htm` and `marked`, loaded from a CDN. No build step
and no runtime JSX transform, which is why it opens instantly.

It calls the flow like this:

```
POST {baseUrl}/api/v1/run/{flowId}?stream=false
     x-api-key: <your Langflow key>

{
  "output_type": "debug",
  "input_type":  "chat",
  "input_value": "<your results folder>"
}
```

`output_type` is **`debug`** rather than `chat` for a reason. A plain chat run
returns only the agent's prose, and prose is a poor thing to build a dashboard
on — the wording shifts from run to run. `debug` also returns the comparator's
own report, and **every number on screen is parsed from that**, never from the
model's reply. The write-up at the bottom is presented as what it is: a
recommendation, not the source of the counts.

Nothing leaves your machine except that call to your own Langflow.

---

## If something does not work

| What you see | What to do |
|---|---|
| Red dot, "Langflow unreachable" | Start Langflow, or fix the Base URL |
| "No Langflow API key" | Open **Connection** and paste your key |
| `HTTP 403 — Invalid or missing API key` | The key is wrong, or has a stray space or quote |
| `HTTP 404` | The Flow ID is wrong |
| `no readable results folder` | The path does not exist. Check it, or clear the box to use the flow's default |
| `Run 1: no file at …` | The folder needs files named exactly `result1.json` and `result2.json` |
| "returned no comparison" | The flow is missing its Flaky Test Comparator node |
| Blank page | You are offline — the page loads React from a CDN |
