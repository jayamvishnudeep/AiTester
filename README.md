# AiTester

Applying AI to the work a QA engineer actually does — starting from prompt
rules on a page, through **15 working agents** that take over a daily task each,
to **RAG assistants** that answer from a team's own documents and **MCP servers**
that any AI client can call.

The repository is meant to be read in numbered order. Every folder has its own
README explaining what is in it and how to run it; this page is the map.

| | Folder | What is in it |
|---|---|---|
| 01 | [LLM Basics](01_LLM_Basics) | One file — the anti-hallucination prompt contract the rest of the repo keeps reusing |
| 02 | [Prompt Engineering](02_Prompt_Engineering) | RICE-POT taken from a one-line request through to a real Selenium framework, plus a reusable prompt library |
| 03 | [Local Test Case Generator](03_LocalTestCaseGenerator) | A Streamlit app turning a Jira ticket into test cases with a model running on your own machine |
| 04 | [JobKitAI](04_JobKitAI) | Resume tailoring against real job postings, without inventing a single fact |
| 05 | [JobTrackerAI](05_JobTrackerAI) | A browser-only Kanban job tracker — no backend, no accounts, IndexedDB only |
| 07 | [n8n Workflows](07_n8n_Workflows) | Four agents built in n8n, learning the tool |
| 08 | [Automate Daily QA Tasks](08_Automate_Daily_QA_Tasks_AI_Agents) | **15 agents** that each replace a job a tester does by hand — 6 in n8n, 9 in Langflow |
| 09 | [Langflow](09_LangFlow) | Learning Langflow — two Jira bug-triage builds and the flaky-test finder |
| 10 | [RAG](10_RAG) | Retrieval-augmented generation over QA documents — a pipeline you can watch stage by stage, naive and advanced RAG chatbots over a test-case library, and **QABuddy.ai**, a hybrid RAG assistant over a whole team's knowledge ([live demo](https://qabuddy-vishnudeep-jayam.vercel.app)) |
| 11 | [MCP](11_MCP) | **Two MCP servers** any AI client can call — Test Creator (5,000 test cases) and Test Skill Finder (100 QA skills) — and the Playwright, Selenium, GitHub, Jira, Slack and Figma servers in use |
| | [Master Classes](Master%20Classes/Playwright%20AI%20Agents) | A 34-test Playwright + TypeScript suite for a demo storefront, written by three Playwright AI agents that drove a real browser first |

There is no `06`. `Master Classes` holds course projects outside the numbered path.

## The through-line

The same lesson keeps reappearing in bigger clothes, and it is the reason to
read in order.

**A confident wrong answer is worse than no answer.** That is `01`, in one file.
In QA it is not an abstraction: an invented reproduction step sends a developer
down a path nobody took, and an invented severity wakes someone at 2 AM for a
typo. Every later folder is that rule enforced at the point it would do damage.

**Instructions belong in a file, not in a chat box.** `02` makes the case,
`07/01` is the counter-example — agents whose prompts were typed at run time and
could never be re-run to the same result — and `08` onward ships the contract
inside the exported workflow, so importing it is enough.

**Code decides the facts; the model writes the prose.** This is the pattern the
whole of `08` is built on. Counting occurrences, comparing two runs, resolving
an import graph, checking a selector resolves — these are things code does
exactly and a model does approximately. The model is handed the totals and asked
for the judgement, and told not to recompute anything.

**The interesting question is what the agent refuses to do.** Given no input, a
model does not return nothing — it returns something fluent and entirely
invented. So the agents refuse: no log, no root cause analysis; a build that
passed, no failure to explain; an element that is genuinely gone, no healed
selector; a change with wide blast radius, no clever subset.

**Retrieval decides more than the model does.** `10` starts with an app whose
two sliders, chunk size and overlap, visibly change what gets retrieved, and
ends with QABuddy measuring it: hybrid search puts the right source in the top
five for all 30 questions of its evaluation set, where semantic or keyword
search alone manages 87%. The rule from `01` comes back as the prompt every RAG
project shares — answer only from the retrieved text, cite it, and say so when
it is not there.

**A tool is only as good as an assistant's ability to call it.** `11` puts MCP
servers in front of data that stays the source of truth: a 5,000-row test-case
library and a folder of 100 skills. Every tool documents a working example
input, and inputs forgive what people actually type, because a tool that is
called wrongly is a tool nobody uses.

## Getting started

Each folder is independent and none of them need the others. Pick one, open its
README, and follow the setup there.

**What you will need, depending on where you start:**

| Folder | Needs |
|---|---|
| 01, 02, 04 | Nothing — they are documents and prompts |
| 03 | Python, Streamlit, and Ollama locally (Groq key optional as fallback) |
| 05 | Node and npm — or just open the live link |
| 07, `08/01_n8n_Agents` | An n8n instance, plus Jira / Google / Telegram credentials |
| 09, `08/02_Langflow_Agents` | Langflow at `http://127.0.0.1:7860` and a free [Groq](https://console.groq.com) API key |
| `10/RAG_Explorer` | Node 20+, plus a Groq key for the chat tab only |
| `10/01_Naive_RAG`, `10/02_Advanced_RAG` | n8n with Pinecone and OpenAI, or Langflow with Astra DB and Groq (Advanced RAG adds a Cohere key) |
| `10/RAG_QA_Buddy.Ai` | Python 3.11 and Ollama, Groq key optional — or just open the [live demo](https://qabuddy-vishnudeep-jayam.vercel.app) |
| 11 | Python 3.10+, and MCP Inspector or any MCP client (Claude Code, Claude Desktop, Cursor, VS Code) |
| Master Classes | Node 20+ and Playwright's Chromium |

**Two things are true of every Langflow and n8n folder here**, and skipping them
is the usual reason a first run fails:

1. **Credentials are global variables, never literals.** The Groq key is stored
   in Langflow as a credential named exactly `GROQ_API_KEY`. Nothing in any
   exported JSON in this repository contains a key.
2. **Paths are absolute, from the machine this was built on.** Every flow that
   reads or writes files has a path field to repoint after cloning. Each
   README's setup section lists which ones.

The Langflow agents in `08` also have component tests that run with no Langflow
and no network at all — the fastest way to see one work:

```bash
cd 08_Automate_Daily_QA_Tasks_AI_Agents/02_Langflow_Agents/09_Framework_Auditor_AI_Agent
../../../09_LangFlow/.venv/Scripts/python.exe test_framework_auditor.py
```

The MCP servers in `11` are the quickest to try by hand: install one, start it,
and connect MCP Inspector to it.

```powershell
cd 11_MCP/MCP_Creation_Vibe_Coding/TestSkill_Finder_MCP
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\tsf-mcp --transport http --port 8933    # then connect to http://127.0.0.1:8933/mcp
```

## Conventions

- **Every agent folder has a `README.md` and a `plan.md`.** The README is how to
  run it; the `plan.md` is why it is built that way, including what went wrong on
  the way. If you only read one, read the plan of an agent you find surprising.
- **Sample data is included and deliberately imperfect.** The framework auditor
  ships a framework full of real anti-patterns; the CI analyzer ships logs that
  are 90% noise. Fixtures that are all signal make an agent look better than it is.
- **Generated output is committed** under each agent's `reports/`. Those files
  are what the flow actually produced, not illustrations written by hand.
- **Numbers in a README were computed, not estimated.** Where one says 92% of a
  log was discarded, that is the figure the component printed.
- **Screenshots are of real runs, not mock-ups.** What a RAG or MCP README shows
  is what the app or tool returned; the MCP READMEs also give the exact input
  behind each one.

## Not in this repository

Secrets, API keys and tokens — none, anywhere, by design. The personal course
notes (`Notes.md`) are kept out too, along with build output, virtualenvs,
`node_modules` and runtime logs. See [`.gitignore`](.gitignore) for the full
list and the reasoning behind each entry.
