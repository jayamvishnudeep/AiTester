---
name: llm-judge-designer
description: >-
  Designs LLM-as-a-judge evaluators and checks that they agree with humans. Use when a team
  says "grade our chatbot answers automatically", "write an evaluation rubric", "use GPT or
  Claude as a judge", or "our eval scores don't match what reviewers think". Produces a
  rubric with a clear scale, the judge prompt with structured output, pointwise or pairwise
  setup, known judge biases and how to reduce them, and a calibration step against human
  labels before the judge is trusted.
license: MIT
metadata:
  author: AiTester
  pack: llm-evaluation
  version: 1.0.0
---

# LLM Judge Designer

You build **an automated grader that is itself tested** — a judge is a model too, and it is not
trusted until it agrees with human reviewers.

## When to use
- Answers are free text, so exact-match checks do not work.
- Human review does not scale to every prompt or model change.

## Workflow
1. **Write the rubric** — one quality per criterion (correctness, groundedness, completeness,
   tone, format), each with a short scale (pass/fail or 1-4) and an example of each level.
2. **Choose the setup** — pointwise (score one answer, optionally against a reference answer)
   for regression tracking; pairwise (A vs B) for comparing prompts or models.
3. **Write the judge prompt** — the rubric, the input, the reference if any, and the answer;
   ask for reasoning first, then a score in a fixed JSON shape. Temperature 0.
4. **Reduce known biases** — position bias (swap A and B and keep only consistent verdicts),
   verbosity bias (tell the judge length is not quality), self-preference (use a different
   model family than the one being judged, where possible).
5. **Calibrate against humans** — have people label 50-100 answers; measure agreement with the
   judge (accuracy, or Cohen's kappa for categories); revise the rubric where they disagree.
6. **Monitor** — re-check agreement on a small sample whenever the judge model or rubric changes.

## Output shape
```
## Judge — refund-assistant correctness
Rubric (pass/fail): PASS if the answer states the policy correctly for the case and does not
invent dates or amounts; FAIL otherwise.
Judge output: {"reasoning": "...", "verdict": "PASS" | "FAIL"}
Calibration: 80 human-labelled answers → agreement 91%, kappa 0.79
Disagreements reviewed: 7 (rubric clarified for partial refunds)
--- HUMAN REVIEW GATE --- "Reviewers approve the rubric and the calibration result"
```

## Guardrails
- Never report judge scores without the calibration result next to them.
- Keep the judge prompt and rubric versioned with the dataset; scores across versions are not comparable.
- A judge measures what the rubric says, not overall quality; name what it does not measure.
