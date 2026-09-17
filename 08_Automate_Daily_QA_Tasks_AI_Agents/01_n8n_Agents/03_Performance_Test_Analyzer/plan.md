# Plan — Performance Test Analyzer (n8n AI Agent)

An SDET finishes a load test and drops the CSV in. Out comes a one-page
executive summary: **Pass or Fail**, what broke, at what load, and what it means
for the people who will not read a percentile table.

Status: **built and tested against the live Groq API.** Forty-four assertions
pass, including a real model call. Not yet imported into n8n Cloud.

## The brief

| | |
|---|---|
| Audience | SDET |
| Problem | Raw load test data is hard to interpret |
| Input | JMeter / k6 CSV reports |
| Output | Executive Performance Summary PDF |
| Helpful for | Explaining performance risk to non-technical stakeholders |
| Given shape | Webhook → Code (parse CSV stats) → AI Agent (performance analyst) → HTML node (format report) → Email + Telegram |

## How this differs from the first two agents

`01_Screenshot_To_Bug_Reporter` reads one artefact. `02_Flaky_Test_RCA_Analyzer`
reads several and finds what they share. This one reads **millions of rows and
must not show the model any of them.**

That sounds like the same budgeting problem as `02_`, and it is not. There the
job was choosing *which* lines to forward. Here no line matters on its own — a
single request taking 4 seconds is meaningless; the 95th percentile taking 4
seconds is the entire story. **The model must never see the data, only the
statistics computed from it.**

Which leads to the design rule this agent is built around:

> **Code decides Pass or Fail. The model explains it.**

A verdict is arithmetic against a threshold. Handing that to a language model
would be the `02_` counting mistake with far worse consequences, because this
output goes to stakeholders who cannot check it. The model's job is translation:
turning "p95 = 4,210 ms against an SLO of 2,000 ms" into a sentence a product
manager can act on.

## The scale problem

A JMeter `.jtl` from a one-hour test at 200 rps is about **720,000 rows and
100+ MB**. Two consequences:

**It cannot arrive in the webhook body.** n8n's default payload limit is 16 MB.
So the CSV has to arrive one of three ways, and the workflow should accept all
three:

| How | When |
|---|---|
| `csv_url` | the normal case — a link to the artefact in CI storage |
| binary file upload | a tester dragging a file into a form or `curl -F` |
| `csv_text` inline | small runs, and the way the sample is tested |

**Percentiles cannot be computed by sorting.** Sorting 720,000 latencies in a
Code node is slow and memory-hungry. Instead the parser makes a **single pass
building a latency histogram** — 1 ms buckets to 10 s, then coarser overflow
buckets — and reads p50/p90/p95/p99 off the cumulative counts. Exact to the
bucket width, constant memory, one pass. That is how the "millions of data
points" in the brief actually get handled.

## Parsing two different formats

The parser detects the format from the header row rather than being told.

**JMeter** (`.jtl` CSV, default fields):

```
timeStamp,elapsed,label,responseCode,responseMessage,threadName,dataType,
success,failureMessage,bytes,sentBytes,grpThreads,allThreads,URL,Latency,
IdleTime,Connect
```

The columns that matter: `elapsed` (ms), `success` (true/false), `label`
(the sampler name, which becomes the per-endpoint breakdown), `timeStamp`
(for throughput and the run window), `responseCode`.

**k6** (`--out csv`):

```
metric_name,timestamp,metric_value,check,error,error_code,expected_response,
group,method,name,proto,scenario,service,status,subproto,tls_version,url,extra_tags
```

Shaped completely differently — one row per *metric sample*, not per request. So
`http_req_duration` rows carry the latencies, `expected_response` and `status`
carry success, and `name` is the endpoint. The parser normalises both into one
internal shape so everything downstream is format-agnostic.

## What the parser computes

All in code, all handed to the model as fact:

```
total_requests, failed_requests, error_rate
p50, p90, p95, p99, min, max, mean          (from the histogram)
throughput_rps, duration_seconds, start/end
per_endpoint[]  — label, count, error_rate, p95, worst offender first
error_breakdown[] — response code / message, count
verdict          — PASS | FAIL | WARN, computed against the SLOs
breaches[]       — which SLO, threshold, actual, by how much
```

### The SLOs

Defaults, overridable per request in the webhook body, because a checkout API
and a reporting export do not share thresholds:

| SLO | Default | Why |
|---|---|---|
| `p95_ms` | 2000 | the usual "feels slow" boundary for a web action |
| `p99_ms` | 5000 | the tail users actually complain about |
| `error_rate_pct` | 1.0 | above this, something is genuinely broken |
| `min_throughput_rps` | not set | only checked when supplied |

`FAIL` if any hard threshold is breached. `WARN` if a value lands within 10% of
a threshold without crossing it — a run that squeaks through at 1,950 ms is not
a clean pass, and saying so is the difference between a report and a rubber
stamp.

## The pipeline

```
Webhook               POST /perf-report  {csv_url | csv_text | binary, slo{...}}
  -> Fetch CSV        (HTTP Request)   when a URL was supplied
  -> Parse CSV Stats  (Code)           histogram, stats, verdict, breaches
  -> Performance Analyst (AI Agent + Groq + Structured Output Parser)
  -> Compose Report   (Code)           merge, validate, guard rails
  -> Build Report     (HTML node)      the executive one-pager
  -> [ PDF step — see open question 1 ]
  -> Send to Telegram + Email
  -> Respond to Caller
```

## What the model is asked for

Deliberately **not** the numbers, and **not** the verdict:

```
headline               one sentence a non-technical reader understands
business_impact        what this means for users, in plain language
risk_level             Low | Moderate | High | Critical
key_findings[]         3-5 bullets, each citing a computed figure
worst_offender_note    why that endpoint stands out
recommended_actions[]  concrete, ordered by impact
caveats                what this test does not prove
```

Every field is prose. The figures are injected from the parser, and the guard
rails below stop the model contradicting them.

## The guard rails

**1. The verdict is not the model's to give.** `verdict`, `p95` and every other
number are computed in code and written into the report directly. If the model's
narrative claims a different verdict, the composer overrides it and records the
correction.

**2. No number may appear in the narrative that the parser did not produce.**
The composer extracts numeric tokens from the model's prose and checks each one
against the computed stats. An invented "response times improved by 30%" is the
same class of failure as the fabricated log quotation in `02_`, and worse here,
because the audience cannot check it.

**3. A test that did not run is not a passing test.** Zero rows, zero requests,
or a CSV that parses to nothing must produce `verdict: NO DATA`, never `PASS`.
This is the analogue of `02_`'s "one failure is not a pattern" — the failure
mode where an empty input looks like a clean result.

Plus the standing rule from `01_LLM_Basics`: anything undeterminable is stated,
not guessed.

## What was found by building it

**The HTML node throws away everything except the HTML.** Read from
`packages/nodes-base/nodes/Html/Html.node.ts`, `generateHtmlTemplate` returns
`{ html }` and nothing else — the item's other fields are gone. Anything after
it that needs the report data has to reference `Compose Report` by name. This
would have failed silently: the Telegram node would have sent an empty message
with no error anywhere.

**The Google Drive PDF route is half-supported, which settled the PDF question.**
The Drive *download* operation does convert Google Docs to `application/pdf` —
confirmed in `download.operation.ts`. But the Drive *upload* operation has no
"convert to Google format" option; it uploads the file with its original
mimeType, so an HTML file stays an HTML file and never becomes convertible.
Forcing the conversion needs a hand-built call to the Drive API with
`mimeType: application/vnd.google-apps.document`. That is why HTML-only was the
right call for v1 rather than a shortcut.

**There is no way to send mail from this account.** A sweep of every credential
referenced across every workflow in the repo returns Google Docs, Drive and
Sheets, Groq, Jira, LinkedIn, OpenAI, Telegram and a Header Auth — and nothing
that can send email.

**The figure checker needed a unit allowance.** Guard rail 2 compares numbers in
the model's prose against the computed statistics, and the first version failed
its own live test: the parser produces `2271` ms and the model — correctly, and
as instructed — writes "2.27 s". Any honest translation of milliseconds into
seconds looked like a fabrication. The allowed set now includes the value
divided by a thousand, which is the difference between a checker that catches
invented figures and one that punishes good writing.

## Test result

Both Code nodes are executed with mocked n8n globals and one real Groq call is
made with the real system message. **Forty-four assertions, all passing.**

The histogram approach was the thing most worth verifying, and it is exact:

```
                p50        p95        p99
true value      254 ms    2271 ms    3565 ms
histogram       254 ms    2271 ms    3565 ms
```

Against `sample_jmeter.csv` — 5,000 rows, five endpoints, one deliberately
awful:

```
verdict   FAIL      (p95 2271ms vs 2000, error rate 2.0% vs 1.0%)
p99       3565ms    inside its 5000ms threshold, correctly not flagged
worst     POST /api/checkout   p95 4067ms, 13.6% errors
errors    504 x53, 500 x48
```

The same file with a looser SLO returns `PASS`, and with a 2400 ms threshold
returns `WARN` rather than a clean pass — the near-miss band working.

The k6 path is tested separately on a fixture containing `http_reqs`,
`http_req_duration` and `vus` rows, confirming only the duration rows are
counted as requests and the rest are ignored.

**The live model call** cost 2,807 tokens in 2.4 seconds and produced:

> *"One in fifty checkout attempts took more than 4 seconds, and more than one
> in ten of those attempts failed, meaning many shoppers would abandon their
> carts."*

which is the translation this agent exists to do. Every figure in its prose
passed verification against the computed statistics.

The guard rails were tested by attacking them: a model narrative claiming `Low`
risk on a failing run is raised to `High`; prose containing "improved by 37%"
and "8400 users" is flagged with both figures named; an empty CSV produces
`NO DATA` with the words "This is not a pass" rather than a clean result.

## Deliverables

```
03_Performance_Test_Analyzer/
├── plan.md
├── Performance_Test_Analyzer_n8n_workflow.json
├── sample_jmeter.csv
└── README.md
```

## Decisions taken

Both open questions were answered before building.

**1. HTML, not PDF, in v1.** The report is a self-contained HTML one-pager with
a print stylesheet, so a browser makes a PDF of it in two clicks. Neither PDF
route earned its cost yet: the Drive conversion needs a hand-built API call
because the upload node cannot convert, and an external PDF service means a new
signup and credential for a document nobody has asked to archive. The HTML is
returned by the webhook and forms the email body, so nothing is lost.

**2. Telegram now, Email disabled.** Same pattern as `02_`. Telegram carries the
credential already proven by the daily LinkedIn workflow and runs today; the
Email node is built, wired and shipped **disabled** with placeholder addresses,
because there is no SMTP credential to attach.

They sit **in a line**, not on parallel branches:

```
Compose Report -> Build HTML Report -> Send to Telegram -> Email Report (disabled) -> Respond
```

A disabled node passes its input through, so enabling email later is one toggle
and two addresses. Both messengers are `onError: continueRegularOutput` so a
delivery failure cannot lose the analysis — the webhook still returns the full
report and the HTML.

## Deliberately not in v1

- **No trend comparison against previous runs.** Every report analyses one run.
  Storing results in Sheets to say "p95 is up 40% since last week" is the
  obvious v2 and needs somewhere to keep history.
- **No raw data in the output.** The report is the summary; the CSV stays where
  it was.
- **No threshold learning.** SLOs are supplied or defaulted, never inferred from
  the data — a threshold derived from the run it is judging proves nothing.
