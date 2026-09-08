# Performance Test Analyzer — n8n AI Agent

An SDET finishes a load test and drops the CSV in. Out comes a one-page
executive summary: **Pass or Fail**, what broke, at what load, and what it means
for the people who will never read a percentile table.

Exported as `Performance_Test_Analyzer_n8n_workflow.json`. The build log, with
the research and everything that only showed up against the real node source, is
in [`plan.md`](plan.md).

## The rule this agent is built around

> **Code decides Pass or Fail. The model explains it.**

A verdict is arithmetic against a threshold. Handing that to a language model
would repeat the counting mistake from
[`02_Flaky_Test_RCA_Analyzer`](../02_Flaky_Test_RCA_Analyzer) with far worse
consequences, because this output goes to stakeholders who cannot check it.

The model's job is translation — turning *"p95 = 2,271 ms against an SLO of
2,000 ms"* into a sentence a product manager can act on. In the live test it
wrote:

> *"One in fifty checkout attempts took more than 4 seconds, and more than one
> in ten of those attempts failed, meaning many shoppers would abandon their
> carts."*

That is the whole point of the agent.

## The scale problem

A one-hour JMeter run at 200 rps is roughly **720,000 rows and over 100 MB** —
past n8n's 16 MB payload limit, and far past any token budget. Two consequences
shape the build:

**The CSV arrives one of three ways**, and the workflow accepts all three:

| How | When |
|---|---|
| `csv_url` | the normal case — a link to the artefact in CI storage |
| a binary file upload | a tester with the file in their hand |
| `csv_text` inline | small runs, and how the sample is tested |

**Percentiles are computed without sorting.** The parser makes a single pass
building a latency histogram — 1 ms buckets below 10 s, 50 ms above — and reads
p50/p90/p95/p99 off the cumulative counts. One pass, constant memory. Measured
against the sample's true values, it is exact:

```
                p50        p95        p99
true value      254 ms    2271 ms    3565 ms
histogram       254 ms    2271 ms    3565 ms
```

**The model never sees a row.** A single request taking 4 seconds means nothing;
the 95th percentile taking 4 seconds is the entire story.

## The pipeline

```
Webhook            POST /perf-report  {csv_url | csv_text | file, slo{...}}
  -> Fetch CSV         (HTTP Request)  when a URL was supplied
  -> Parse CSV Stats   (Code)          histogram, statistics, verdict, breaches
  -> Performance Analyst (AI Agent + Groq + Structured Output Parser)
  -> Compose Report    (Code)          merge, and disbelieve the narrative
  -> Build HTML Report (HTML node)     the executive one-pager
  -> Send to Telegram  ->  Email Report (disabled)  ->  Respond to Caller
```

| Node | Type | Role |
|---|---|---|
| Perf Test Webhook | `webhook` | `POST /perf-report`, responds via the last node |
| Fetch CSV | `httpRequest` | Text response; a missing URL is survivable |
| Parse CSV Stats | `code` | Statistics **and the verdict** |
| Performance Analyst | `agent` | Writes the narrative, decides nothing |
| Groq Chat Model | `lmChatGroq` | `openai/gpt-oss-120b` |
| Report Schema | `outputParserStructured` | Forces the prose fields |
| Compose Report | `code` | Guard rails; renders the HTML fragments |
| Build HTML Report | `html` | `generateHtmlTemplate` |
| Send to Telegram | `telegram` | The active output |
| Email Report | `emailSend` | Built, shipped **disabled** — no SMTP credential |
| Respond to Caller | `respondToWebhook` | Returns the report and the HTML |

### Two formats, detected not declared

The parser reads the header row and works out which tool produced the file.

**JMeter** `.jtl` — `elapsed` is the latency, `success` the outcome, `label` the
endpoint. The CSV splitter is hand-rolled because JMeter's `failureMessage`
routinely contains commas and quotes, and a naive `split(',')` corrupts every
row after the first failure.

**k6** `--out csv` — shaped completely differently: one row per *metric sample*,
not per request. Only `http_req_duration` rows are requests; `http_reqs`, `vus`
and the rest are ignored, and success comes from `expected_response`.

Both normalise to one internal shape, so everything downstream is
format-agnostic.

## Pass, Fail, and the honest middle

Thresholds default sensibly and are overridable per request, because a checkout
API and a reporting export do not share SLOs:

| SLO | Default |
|---|---|
| `p95_ms` | 2000 |
| `p99_ms` | 5000 |
| `error_rate_pct` | 1.0 |
| `min_throughput_rps` | only checked when supplied |

`FAIL` on any breach. **`WARN` when a value lands within 10% of a threshold
without crossing it** — a run that squeaks through at 1,950 ms against a 2,000 ms
SLO is not a clean pass, and saying so is the difference between a report and a
rubber stamp.

## The guard rails

**1. The verdict is not the model's to give.** Every number in the report is
written from the parser's output. If the narrative implies a different verdict,
the composer overrides and records it — a `FAIL` can never be reported as `Low`
risk.

**2. No figure may appear that the parser did not produce.** The composer reads
every number out of the model's prose and checks it against the computed
statistics. Invented figures are named in `validation_notes` and the report is
flagged. This is the analogue of the quotation check in `02_`, and it matters
more here because the audience cannot verify anything.

**3. A test that did not run is not a passing test.** Zero rows, or a file that
parses to nothing, gives `NO DATA` and the words *"This is not a pass"* — never
`PASS`. An empty input that reads as a clean result is the worst failure this
tool could have.

## Trying it

`sample_jmeter.csv` is a synthetic 5,000-row JMeter run across five endpoints,
one of them deliberately awful.

```bash
curl -X POST "https://<your-n8n-host>/webhook-test/perf-report" \
  -H "Content-Type: application/json" \
  -d "{\"test_name\":\"Checkout load test\",\"csv_text\":$(node -e "console.log(JSON.stringify(require('fs').readFileSync('sample_jmeter.csv','utf8')))")}"
```

Measured result:

```
verdict   FAIL      p95 2271ms vs 2000, error rate 2.0% vs 1.0%
p99       3565ms    inside its threshold, correctly not flagged
worst     POST /api/checkout   p95 4067ms, 13.6% errors
errors    504 x53, 500 x48
cost      2,807 tokens, 2.4s
```

Send `csv_url` instead to pull a real artefact from CI, or POST the file itself.

## Setting it up

Import the JSON. Groq and Telegram both carry their credentials by id, so
nothing needs picking. Activate the workflow and it runs.

**To turn on email**, enable `Email Report`, add an SMTP credential and replace
the two placeholder addresses. It sends the same HTML as the body. The node is
disabled rather than absent because a disabled node passes its input straight
through, so switching it on needs no rewiring.

**Why HTML and not PDF.** The brief asked for a PDF and n8n has no native
HTML-to-PDF step. The report is a self-contained HTML page with a print
stylesheet, so any browser makes a PDF of it in two clicks. The two real routes
were both worse for v1: the Google Drive *download* operation converts Google
Docs to PDF, but its *upload* operation cannot convert an HTML file into one, so
that path needs a hand-built Drive API call; and an external PDF service means a
new signup and credential. Easy to add later — the HTML is already produced and
returned.

## Worth remembering

- **Never ask a model for a number you can compute.** Especially not one that
  goes in front of people who cannot check it.
- **Histograms beat sorting for percentiles.** One pass, constant memory, and
  exact to the bucket — verified against true values here.
- **Check the node's source before wiring past it.** n8n's HTML node emits only
  `{ html }` and silently discards every other field; the Telegram node after it
  would have sent an empty message with no error anywhere. Everything downstream
  references `Compose Report` by name instead.
- **A figure checker needs a unit allowance.** The first version flagged the
  model for writing "2.27 s" where the parser produced `2271` ms — punishing the
  translation it was asked to perform. Allowing the value divided by a thousand
  fixed it.
- **Write the honest middle into the verdict.** `WARN` exists so a near miss
  cannot be reported as a clean pass.
