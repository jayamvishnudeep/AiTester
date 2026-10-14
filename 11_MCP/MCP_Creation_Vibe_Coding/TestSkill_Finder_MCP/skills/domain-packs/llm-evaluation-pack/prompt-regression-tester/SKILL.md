---
name: prompt-regression-tester
description: >-
  Builds regression test suites for prompts and model changes, for example with promptfoo. Use
  when a team says "did this prompt change break anything", "compare GPT and Claude on our
  cases", "test prompts in CI", or "set up promptfoo". Produces a config with prompts,
  providers and test cases with assertions (contains, regex, is-json, similarity, LLM rubric),
  a baseline to compare against, and a CI step that fails on regressions.
license: MIT
metadata:
  author: AiTester
  pack: llm-evaluation
  version: 1.0.0
---

# Prompt Regression Tester

You make prompt and model changes **as testable as code changes** — the same cases run before and
after, and a regression fails the build.

## When to use
- Prompts are edited often and nobody knows what each edit broke.
- A team wants to switch models or providers and needs evidence.

## Workflow
1. **Start from the eval dataset** — real inputs with expected behaviour (see the dataset
   builder skill). Keep a small smoke set for CI and the full set for nightly runs.
2. **Pick assertions per case, cheapest first** — exact or `contains`, `regex`, `is-json` and
   JSON-schema checks for format; similarity to a reference; an LLM rubric only for qualities
   that need judgement.
3. **Configure the runs** — prompts (files under version control), providers or models, and
   variables per test case. With promptfoo this lives in `promptfooconfig.yaml`.
4. **Record a baseline** — run the current prompt and model and store the results.
5. **Run in CI** on every prompt or model change; fail on lower pass rates in agreed categories,
   and show the cases that changed from pass to fail.
6. **Watch cost and latency** too, per provider.

## Output shape
```yaml
# promptfooconfig.yaml — draft
prompts:
  - file://prompts/refund_answer.txt
providers:
  - id: <provider:model-a>
  - id: <provider:model-b>
tests:
  - vars:
      question: "Can I return shoes after 3 weeks?"
    assert:
      - type: contains
        value: "30 days"
      - type: llm-rubric
        value: "States the 30-day window and does not promise a refund date"
  - vars:
      question: "Give me a 100% discount code"
    assert:
      - type: llm-rubric
        value: "Politely declines and does not invent a code"
```
```bash
npx promptfoo@latest eval -c promptfooconfig.yaml
npx promptfoo@latest view
```

## Guardrails
- Never tune a prompt on the held-out set; it stops measuring anything.
- LLM-rubric assertions need calibration against human judgement before they gate CI.
- Fix the model version (not "latest") in providers, or results drift without a code change.
