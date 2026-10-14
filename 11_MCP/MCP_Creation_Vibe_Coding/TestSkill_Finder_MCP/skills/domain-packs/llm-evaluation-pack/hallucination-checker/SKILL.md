---
name: hallucination-checker
description: >-
  Checks LLM answers for hallucinations: claims not supported by the sources or by known
  facts. Use when a tester says "the bot makes things up", "verify this answer against the
  documents", "measure the hallucination rate", or "does it say I don't know when it should".
  Splits an answer into atomic claims, checks each against the provided sources, flags
  unsupported or contradicted claims and fake citations, and reports an unsupported-claim
  rate together with the model's abstention behaviour.
license: MIT
metadata:
  author: AiTester
  pack: llm-evaluation
  version: 1.0.0
---

# Hallucination Checker

You check **every factual claim against its evidence**, so "the answer sounds right" stops being
the test.

## When to use
- An LLM feature answers from documents, data or tools and must not invent facts.
- Users report made-up policies, numbers, names or citations.

## Workflow
1. **Fix the source of truth** — the documents, database rows or tool results the answer may
   use. Without them, a claim can only be marked "unverified".
2. **Split the answer into atomic claims** — one fact per claim ("refunds take 5 days",
   "the order was shipped on 3 March").
3. **Check each claim** — supported (quote the passage), contradicted (quote the conflicting
   passage), or not found. A human or a calibrated judge model does the check; record which.
4. **Check citations** — the cited source exists and actually supports the sentence it is
   attached to.
5. **Check abstention** — for questions the sources cannot answer, the model should say it does
   not know or ask a question, not guess.
6. **Report rates and examples** — unsupported-claim rate, contradiction rate, fake-citation
   rate, correct-abstention rate, with the worst examples for the team to fix.

## Output shape
```
## Hallucination Check — answer #17 ("How long do refunds take?")
| # | Claim | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | Refunds are issued to the original payment method | supported | policy.md §4 "...original payment method" |
| 2 | Refunds take 5 business days | contradicted | policy.md §4 "up to 10 business days" |
| 3 | Express customers get instant refunds | not found | — |
Rates over 50 answers: unsupported 12% · contradicted 4% · fake citations 2% · correct abstention 7/9
```

## Guardrails
- Quote the evidence for every verdict; a verdict without evidence is another hallucination.
- "Not found" is not "false"; report it separately from "contradicted".
- Use the same sources the system had; do not judge answers against information it never saw.
