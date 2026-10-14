# TestCreator MCP (TC MCP): plan

Status: Phases 1-3 are built in this folder, [TestCase_Creator_MCP](./) (2026-10-14): 20 tools, 3 resources,
3 prompts and 64 tests. It runs locally at `http://127.0.0.1:8932/mcp`. Phase 4, a shared hosted server, is next.
The decisions in section 11 were taken as recommended. The data numbers below come from profiling
[data/vwo_5000_test_cases.csv](data/vwo_5000_test_cases.csv) on 2026-10-13, and the FastMCP details from its docs
for version 4.1.0.

## 1. Goal

From [objective.md](objective.md): turn the 5,000 VWO test cases into MCP tools that any QA engineer or developer
can use from Claude Code, Claude Desktop, Cursor, VS Code or MCP Inspector, so they can:

- get test cases **by priority**;
- get test cases **by module**;
- apply **maximum and minimum limits** (section 3);
- get the **top test cases to execute for a module**;
- later, **create** new test cases in the same format, which is the "creator" part.

It is built with [FastMCP](https://gofastmcp.com) 4.1 (Python). Teammates first run it on their own machine,
and later connect to one hosted server.

**Done when** a teammate installs it with one command, asks "top 10 Funnels tests to run for this release",
and gets a ranked list with a reason for each pick in under a second. Every tool must also be covered by tests.

## 2. What the data looks like

| | |
|---|---|
| Rows | 5,000 test cases, keys `VWO-1001` to `VWO-6000` (consecutive, unique) |
| Columns (14) | Issue Type, Issue Key, Summary, Description, Priority, Component, Labels, Test Type, Preconditions, Steps, Expected Result, Browser, Device, Status |
| Empty cells | None |
| Modules (`Component`) | 17, with 265-333 cases each |
| Features | 72, 4-6 per module, named in every description ("the *step drop-off* in the *Funnels* module") |
| Priority | Highest 396 · High 1,546 · Medium 2,198 · Low 860 |
| Test Type | Functional 1,516 · Negative 810 · UI/UX 515 · API 415 · Boundary 406 · Regression 379 · Security 368 · Accessibility 321 · Performance 270 |
| Status | Ready 2,234 · Automated 1,594 · Draft 757 · Deprecated 415 |
| Browser | Safari 19 · Firefox 141 · Chrome 148 · Edge 148 (1,192-1,308 each) |
| Device | desktop · mobile (Android) · mobile (iOS) · tablet (1,214-1,266 each) |
| Steps | Exactly 4 per case, joined with ` \| ` |
| Size | 3.7 MB |

These findings shape the design:

1. **Small enough to keep in memory.** Loading takes well under a second, and any query is a scan of 5,000 rows
   that finishes in milliseconds. No database is needed.
2. **The feature column comes for free.** Every description follows "the *feature* in the *module* module", so
   each case gets a `feature` field (for example Funnels: funnel builder, step drop-off, segment comparison,
   conversion rate). Tools can filter by feature as well as by module.
3. **Priority is an ordered scale**: Low < Medium < High < Highest (no "Lowest" level). That allows ranges such
   as "High or above".
4. **"Runnable" means Ready or Automated** (3,828 cases). Deprecated cases are never suggested for execution;
   Draft cases only when asked for.
5. **The same test idea repeats across environments.** There are 1,520 distinct summaries, and only 1,244
   distinct test ideas once the interchangeable verbs (verify, check, validate, ensure, confirm) are ignored.
   Most rows are one idea on another browser or device. The variants also disagree on priority: 1,075 of
   the 1,235 repeated summaries have more than one priority. So a "top N" list must pick one row per idea
   (the best variant) and list the other environments, or it fills up with near-copies.
6. **60 rows are exact copies** of another row, apart from the key.
7. **Labels are unreliable.** The A/B Testing module label is just `a`, the SDK one is `sdk`, and 379 rows
   carry `regression` twice. Module filters use `Component`; labels stay free-text tags.

## 3. What "maximum and minimum limitations" means here

The objective can be read three ways, and the tools support all three. Please confirm (section 11).

| Reading | How the tools handle it |
|---|---|
| How many results: "at most 20, then the next 20" | `limit` (1-100, default 20) and `offset`. Every list reply says how many matched in total, how many were returned, and where the next page starts |
| A priority range: "High and above", "Medium or lower" | `min_priority` and `max_priority` |
| Quotas per module in a suite: "at least 2 and at most 5 per module, 40 in total" | `min_per_module`, `max_per_module` and `max_total` in the suite builders |

A time budget ("tests that fit in 2 hours") is not possible yet, because the CSV has no duration column. We
could add estimated minutes per test type if you want it.

## 4. Tools

How every tool behaves:

- Names are `snake_case` verbs. Tools that only read are marked read-only, so clients run them without
  asking for confirmation.
- Inputs are forgiving. Module, priority and the other fields match regardless of case and accept common
  aliases ("ab testing" → A/B Testing, "P1" → Highest). An unknown value returns an error that suggests the
  closest valid values.
- Lists come back compact by default: key, summary, module, feature, priority, test type, status, browser
  and device, about 50 tokens per case. `detail="full"` adds the description, preconditions, the 4 steps as
  a list, and the expected result, about 250 tokens per case.

### Phase 1: MVP, read-only (10 tools)

| # | Tool | Answers | Main inputs |
|---|---|---|---|
| 1 | `get_catalog_overview` | "What's in here?" Totals and counts by every field | none |
| 2 | `list_modules` | The 17 modules with their features, case counts, priority split and automation share | none |
| 3 | `list_field_values` | The allowed values of a field, with counts, so filters are valid | `field` |
| 4 | `get_test_cases` | One or more cases by key, in full | `issue_keys` (1-50) |
| 5 | `get_test_cases_by_priority` | **Objective:** cases of a priority or a priority range | `priority` or `min_priority`/`max_priority`, `module`, `limit`, `offset` |
| 6 | `get_test_cases_by_module` | **Objective:** cases of a module, optionally one feature | `module`, `feature`, `min_priority`, `limit`, `offset` |
| 7 | `filter_test_cases` | Any combination of filters | `module`, `feature`, `min_priority`/`max_priority`, `test_type`, `status`, `browser`, `device`, `label`, `include_deprecated`, `sort_by`, `limit`, `offset`, `detail` |
| 8 | `count_test_cases` | Counts only, grouped ("High Funnels tests per browser") | the same filters, `group_by` |
| 9 | `search_test_cases` | Keyword search over summary, description, steps and expected result | `query`, filters, `limit` |
| 10 | `get_top_test_cases` | **Objective:** the top N to execute for a module, ranked, with a reason each (section 6) | `module`, `limit` (1-50, default 10), `min_priority`, `execution` (any / manual / automated), `one_per_idea` (default true) |

### Phase 2: planning and quality (5 tools)

| # | Tool | Answers | Main inputs |
|---|---|---|---|
| 11 | `build_smoke_suite` | The top N per module, across modules | `modules`, `per_module` (1-10, default 2), `max_total` |
| 12 | `build_regression_suite` | A suite within a budget that guarantees coverage. It reports what did not fit | `modules`, `max_total`, `min_per_module`, `max_per_module`, `min_priority`, `test_types`, `cover_browsers`, `cover_devices` |
| 13 | `get_coverage_matrix` | A grid of counts for two fields (module × test type, browser × device), highlighting empty cells | `rows`, `columns`, filters, `only_gaps` |
| 14 | `find_duplicate_test_cases` | The 60 exact copies, and the same idea repeated across environments | `module`, `mode` (exact / same_idea) |
| 15 | `get_automation_candidates` | Ready, high-priority, automatable cases that are not Automated yet, plus each module's automation share | `module`, `limit` |

### Phase 3: authoring, the "creator" part (5 tools)

| # | Tool | Answers | Main inputs |
|---|---|---|---|
| 16 | `get_test_case_template` | The house format for a module, feature and test type, with 2-3 similar existing cases as examples | `module`, `feature`, `test_type` |
| 17 | `validate_test_case` | Checks a draft: allowed values, exactly 4 steps, the `[Module] Type: action` summary pattern, near-duplicates of existing cases | the draft case |
| 18 | `create_test_case` | Validates the draft, gives it the next key (`VWO-6001`, ...) and appends it to `data/new_test_cases.csv`. The master CSV is never edited | the draft case |
| 19 | `create_environment_variants` | Copies a case to other browser and device pairs, the way the existing data does | `issue_key`, `browsers`, `devices` |
| 20 | `export_test_cases` | Cases as Jira/Xray import CSV, Markdown or Gherkin (Given the preconditions, When the steps, Then the expected result) | `issue_keys` or filters, `format` |

**The server never calls an LLM.** The client's model (Claude or any other) writes the text of a new test
case. The server supplies the template and examples, validates the result, and stores it. That keeps the
server deterministic and free to run, and it needs no API keys to share.

Twenty tools is near the upper end of what a model chooses between reliably. Tags group them (read, plan,
write), so a profile can expose fewer: `TC_MCP_PROFILE=readonly` hides the two tools that write
(`create_test_case`, `create_environment_variants`). Tools 5 and 6
overlap tool 7 on purpose, because the objective names them; we can drop them if you prefer fewer tools.

## 5. Resources and prompts

Resources (data a client can attach without calling a tool):

| URI | Content |
|---|---|
| `tc://schema` | Every field, its allowed values and formats |
| `tc://modules` | The modules and their features |
| `tc://test-cases/{issue_key}` | One test case. In Claude Code, users can @-mention a case this way |

Prompts (ready-made instructions that a user picks from the client's menu):

| Prompt | What it does |
|---|---|
| `release_run_plan(module, count)` | Calls `get_top_test_cases` and writes a short run plan with owners left blank |
| `coverage_review(module)` | Coverage matrix, gaps and automation candidates, summarised for a QA lead (Phase 2) |
| `write_test_cases(module, feature, count)` | Template → draft → validate → create, in the house format (Phase 3) |

## 6. How the "top test cases to execute" are chosen

1. **Eligible cases** are Ready or Automated. `execution="manual"` keeps only Ready cases, and
   `execution="automated"` only Automated ones. Draft cases count only with `include_drafts`, and Deprecated
   cases never do.
2. **Score** = priority points (Highest 100, High 70, Medium 40, Low 10) + test type points (Security 12,
   Functional 10, Regression 10, API 8, Negative 8, Boundary 6, Performance 6, Accessibility 4, UI/UX 4). A
   tie goes to the lower key. The weights live in `ranking.yaml` (shipped inside the package), so a QA lead can tune them without
   touching code.
3. **One per test idea.** Rows with the same module, test type and check (the leading verb ignored) collapse
   into the best-scoring row. The other environments are listed as "also runnable on".
4. **Every pick explains itself**, for example "Highest · Security · Automated · best of 5 runnable variants".

On the real data this gives every module 59-85 runnable test ideas, 8-22 of them with a Highest-priority
variant, so a top 10 can always be filled. Funnels, top 5:

| Key | Score | Priority | Type | Status | Test idea | Other runnable rows |
|---|---|---|---|---|---|---|
| VWO-3821 | 112 | Highest | Security | Automated | check authorization for funnel builder | 0 |
| VWO-1628 | 110 | Highest | Regression | Ready | re-verify funnel builder | 4 |
| VWO-2084 | 110 | Highest | Functional | Automated | verify step drop-off | 15 |
| VWO-2453 | 110 | Highest | Functional | Ready | ensure segment comparison | 18 |
| VWO-5007 | 110 | Highest | Regression | Automated | regression-check conversion rate | 5 |

Without the one-per-idea rule, VWO-2453 would be followed by VWO-2633 ("confirm segment comparison") and
VWO-3173 ("verify segment comparison"): the same test three times.

## 7. Architecture

**Stack:** Python 3.11, `fastmcp>=4.1,<5` ([PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp)), Pydantic
models for inputs and outputs, and the standard library for CSV and search. Nothing else is needed for
Phases 1-3.

Points about FastMCP 4 that matter here. Most tutorials still show 2.x, and 4 changed things:

- Tools are plain Python functions with `@mcp.tool`. Typed parameters with `Annotated` + `Field(ge=1, le=100)`
  become the input schema, so the client cannot even send `limit=0` or `limit=500`. `Literal` and `Enum`
  types show the allowed values to the model.
- Typed return values (Pydantic models) become structured output with an output schema. Bad input raises
  `ToolError`, whose message reaches the user.
- Tools carry read-only annotations and tags. `mcp.enable(...)` and `mcp.disable(...)` switch tools on and
  off by name or tag, which is how the profiles in section 4 work.
- Version 4 defaults to the newer sessionless protocol. The server can no longer call back into the client
  in the middle of a request (no `ctx.sample` or default `ctx.elicit`). We don't need either. Protocol
  fields are now `snake_case`, and the HTTP client is `httpx2`.
- `fastmcp dev inspector server.py` opens the server in MCP Inspector. `fastmcp run server.py --transport http`
  serves it at `http://127.0.0.1:8000/mcp`.

**Components:**

```text
TestCase_Creator_MCP/              (built)
├── pyproject.toml                 package "test-creator-mcp", command "tc-mcp"
├── server.py                      entry file for `fastmcp dev inspector` and `fastmcp install`
├── src/test_creator_mcp/
│   ├── server.py                  FastMCP app: registers the tools, resources and prompts
│   ├── __main__.py                the tc-mcp command (stdio, or --transport http)
│   ├── settings.py                the TC_MCP_* environment variables
│   ├── ranking.yaml               the weights from section 6
│   ├── catalog.py                 loads and validates the CSV, derives feature and idea, builds lookups, reloads when the file changes
│   ├── models.py                  the TestCase model, allowed values, aliases
│   ├── query.py                   filters, priority ranges, paging, counts, coverage matrix
│   ├── ranking.py                 scoring, one-per-idea, smoke and regression suites
│   ├── search.py                  keyword search (BM25)
│   └── authoring.py               template, validation, create, variants, export (Phase 3)
├── tests/
└── README.md                      install and run guide
```

**Settings** (environment variables): `TC_MCP_CSV` (the test case file, defaulting to `data/vwo_5000_test_cases.csv`),
`TC_MCP_NEW_CASES` (where Phase 3 writes), `TC_MCP_PROFILE` (`readonly` or `full`) and `TC_MCP_MAX_LIMIT`
(default 100). The CSV is re-read when its timestamp changes, so replacing the file needs no restart.

## 8. Sharing with QA and developers

| | A. Everyone runs their own copy (Phase 1) | B. One shared server (Phase 4) |
|---|---|---|
| How | A GitHub repository with the CSV bundled; each client starts the server on the user's machine (stdio) | `fastmcp run --transport http` on a small VM or droplet, or on [Prefect Horizon](https://www.prefect.io/horizon) |
| Setup for a teammate | One command (below) | Add a URL and a token |
| Data | Each copy has its own CSV | One source of truth |
| Access control | None needed | A team token for a pilot (`JWTVerifier`); GitHub login for the team (`GitHubProvider`) |
| Needed when | Reading and planning | Teammates create test cases (Phase 3) and must all see them |

**Recommendation:** start with A, and move to B when Phase 3 writes need to be shared. B can reuse whatever we
pick for QABuddy's cloud deployment (AWS, DigitalOcean, GCP or Azure).

How a teammate would add it (A), once the repository exists:

```bash
# Claude Code
claude mcp add test-creator -- uvx --from git+https://github.com/jayamvishnudeep/test-creator-mcp tc-mcp

# From a clone, for Claude Code, Claude Desktop or Cursor
fastmcp install claude-code src/test_creator_mcp/server.py --name test-creator
```

Other clients (Claude Desktop, Cursor, VS Code) take the same command as an `mcpServers` JSON entry, which
`fastmcp install mcp-json` prints. With B the entry is the URL plus an `Authorization: Bearer <token>`
header. In both cases the server also gets a **"Test Creator" card in MCP Inspector**, which is where it is
checked and screenshotted.

## 9. Testing

- **Tool tests:** pytest with FastMCP's in-memory client (`Client(transport=mcp)`, pytest-asyncio in auto
  mode). These call the real tools through MCP, with no network.
- **Golden numbers** from section 2 become assertions: 5,000 cases, 396 Highest, 3,828 runnable, 72 features,
  1,244 test ideas, 60 exact copies.
- **Boundaries:** every limit at its edges (`limit` 0 and 101 rejected by the schema, 1 and 100 accepted), each
  priority range, paging totals, and unknown values returning suggestions.
- **Ranking:** a fixed snapshot of the Funnels top 10, and a check that VWO-2453, VWO-2633 and VWO-3173 collapse
  into one pick.
- **Mutation check:** break the code in 10 or more plausible ways (an off-by-one limit, a Deprecated case let
  through, a reversed priority order) and confirm a test fails for each. This is the house rule from the
  Langflow agents and QABuddy.
- **By hand:** `fastmcp dev inspector`, the Inspector card, and a set of prompts in Claude Code ("top 10
  Funnels tests", "how many High Security tests are there on Safari?").
- **Speed:** every tool answers in under 50 ms on the 5,000 cases.

## 10. Phases

| Phase | Scope | Size |
|---|---|---|
| 0 | Agree this plan (section 11) | now |
| 1 | MVP: tools 1-10, the three resources, `release_run_plan`, tests, README, Inspector card, Claude Code install | about a day |
| 2 | Planning and quality: tools 11-15, `coverage_review` | half a day to a day |
| 3 | Authoring: tools 16-20, `write_test_cases`, the new-cases file | about a day |
| 4 | Sharing: a standalone repository, the HTTP server with auth, hosting | half a day, plus the hosting choice |

Later ideas, not planned: an interactive test picker or coverage heatmap shown inside the chat ([FastMCP
Apps](https://gofastmcp.com/apps/overview)); pushing new cases to Jira through the Jira MCP; pass/fail history
per run, to spot flaky tests; semantic search, if keyword search is not enough.

## 11. Decisions needed

On 2026-10-14 the build went ahead with every recommendation below; any of them can still be changed.

| # | Question | Recommendation |
|---|---|---|
| 1 | Which meaning of "maximum and minimum limitations" do you want (section 3)? | All three |
| 2 | Are the ranking weights in section 6 right? Should "top to execute" default to manual (Ready) or any? | These weights; `execution="any"` |
| 3 | Should top lists collapse the same idea across browsers and devices? | Yes for top lists and suites; plain filters show every row |
| 4 | Should the CSV be cleaned (60 exact copies, broken labels), or left as is? | Leave the source untouched; handle it in code and report it with tool 14 |
| 5 | Is authoring (Phase 3) in scope, and where do new cases go? | Yes, into a separate `new_test_cases.csv`; Jira later |
| 6 | Local first (A), then shared (B)? Public or private repository? | A first. Public or private is your call |
| 7 | Priority aliases: P1 = Highest, P2 = High, P3 = Medium, P4 = Low? | Yes |
| 8 | Names: server "Test Creator", package `test-creator-mcp`, command `tc-mcp`? | Yes |

## 12. Risks

| Risk | Mitigation |
|---|---|
| Twenty tools confuse the model's tool choice | Clear names, a 10-tool MVP, tags and the `readonly` profile |
| Large replies fill the model's context | A compact default view, `limit` capped at 100, and a counts-only tool |
| Teammates' copies of the data drift apart | The shared server (B) once the data changes often or Phase 3 writes start |
| FastMCP majors move fast (2 → 3 → 4 in about 18 months) | Pin `<5`; the in-memory tests catch API changes on upgrade |
| The data looks generated (the same idea gets a different priority per environment) | Ranking takes the best variant, and the weights are configurable. Re-check the rules when real data arrives |
