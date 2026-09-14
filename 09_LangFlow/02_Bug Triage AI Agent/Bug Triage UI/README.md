# Bug Triage UI

A browser front end for the Bug Triage flow. Type a Jira ticket number, press
**Run**, and read the triage — severity, priority and what to do about it.

![The UI after running KAN-11: a gradient header with Triaged and Blockers counters, a large ticket input beside a gradient Run button, a history row showing KAN-11 as S0 Blocker, and the triage reply below in a card whose header band is tinted red for the blocker severity](Bug_Triage_UI.png)

Above: **KAN-11** triaged as **S0 - Blocker / P0 - Immediate** in under five
seconds. Severity drives the colour, so a blocker looks like one at a glance.

---

## Before you start

Two things must already be true:

1. **The flow is set up in Langflow.** Follow the [parent folder's
   README](../README.md) first — it covers importing the flow, adding your Groq
   key and pointing it at your Jira.
2. **Langflow is running**, normally at `http://127.0.0.1:7860`.

If you skip these, the page opens but has nothing to talk to.

---

## Setup

### 1. Open the page

Double-click **`index.html`**.

That is the entire install — no `npm install`, no build step, no server. It
opens straight in your browser.

### 2. Add your Langflow API key

The **Connection** panel is open the first time. You need one value:

- In Langflow, go to **Settings → API Keys → Add New**
- Copy the key (it is shown only once)
- Paste it into **Langflow API key**

Check the other two while you are there:

| Field | What it should be |
|---|---|
| **Base URL** | Where Langflow is running — `http://127.0.0.1:7860` |
| **Flow ID** | The long id in Langflow's address bar when your flow is open |

Your Flow ID is the part after `/flow/`:

```
http://127.0.0.1:7860/flow/1d4f1d82-9619-4dab-9825-eada514790f2
                           └──────────── this ────────────┘
```

All three are saved in your browser, so you only do this once.

### 3. Check the connection

The pill in the top right should read **"Langflow connected"** with a green dot.
If it is red, Langflow is not running or the Base URL is wrong — fix that before
going on.

---

## Using it

**Type a ticket number and press Run** (or hit Enter). `KAN-11`, `KAN-9` —
whatever exists in your Jira project. Give it about five seconds.

The buttons under the box marked **Try** just fill in a number for you, so you
can test without typing.

### What comes back

| | |
|---|---|
| **Severity / Priority** | Pulled out as coloured badges — red for blockers, amber for major, green for minor |
| **The triage** | Formatted properly, not raw text |
| **Metrics** | Which model ran, tokens used, how long it took |

### History

Every run is listed under **History**, newest first, with its verdict and when it
ran. It survives closing the browser.

- **Click a row** to put that ticket number back in the box and jump to its reply
- **Clear history** empties the list

The counters in the header — **Triaged** and **Blockers** — update as you go.

---

## Changing the defaults

If you always use the same Langflow, set your own defaults near the top of the
script inside `index.html` (around line 405) and you can skip the Connection
panel entirely:

```js
const DEFAULTS = {
  baseUrl: "http://127.0.0.1:7860",
  flowId:  "1d4f1d82-9619-4dab-9825-eada514790f2",
  apiKey:  "",
};
const SUGGESTED = ["KAN-11", "KAN-9", "KAN-13", "KAN-8", "KAN-12"];
```

- **`flowId`** — set it to your own flow's id
- **`SUGGESTED`** — the **Try** buttons; put your own common tickets here
- **`apiKey`** — leave it blank. Keys belong in the browser, not in a file you
  might commit

Two values below that are worth leaving alone unless you know why you are
changing them:

- **`input_type: "chat"`** in the request — the flow reads the ticket number
  from a Chat Input, and any other value drops it
- **`MAX_TOKENS = 900`** — Groq's free tier allows 1000 output tokens a minute
  and rejects a request that asks for more

---

## If something does not work

| What you see | What to do |
|---|---|
| Red dot, "Langflow unreachable" | Start Langflow, or fix the Base URL |
| "Add a Langflow API key…" | Open **Connection** and paste your key |
| `HTTP 403 — Invalid or missing API key` | The key is wrong, or has a stray space or quote |
| `HTTP 404 — Flow identifier … not found` | The Flow ID is wrong |
| A warning that the reply is Jira's error | That ticket number does not exist in your project |
| The reply stops mid-sentence | Shorten the brief in the flow's prompt |
| Blank page | You are offline — the page loads React from a CDN |

---

## How it is built

One HTML file: React 18 with `htm` and `marked`, loaded from a CDN. No build
step and no runtime JSX transform, which is why it opens instantly.

It calls the same endpoint as the Postman collection in the parent folder:

```
POST {baseUrl}/api/v1/run/{flowId}?stream=false
     x-api-key: <your Langflow key>

{
  "output_type": "chat",
  "input_type":  "chat",
  "input_value": "KAN-11",
  "tweaks": { "ext:groq:GroqModel@official-KES2M": { "max_tokens": 900 } }
}
```

Nothing leaves your machine except that call to your own Langflow, and the
requests it makes to your Jira and to Groq.
