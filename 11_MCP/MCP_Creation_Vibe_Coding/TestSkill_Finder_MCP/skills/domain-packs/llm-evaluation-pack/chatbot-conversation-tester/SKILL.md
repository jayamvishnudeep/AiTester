---
name: chatbot-conversation-tester
description: >-
  Tests multi-turn chatbot and assistant conversations. Use when a tester says "test our
  chatbot", "check that it remembers context", "test the handoff to a human agent", or "write
  conversation test scripts". Produces scripted multi-turn conversations that check context
  retention, follow-up questions, topic switches, clarifying questions, refusals, escalation
  to a human, tone and consistency across turns — run several times because answers vary.
license: MIT
metadata:
  author: AiTester
  pack: llm-evaluation
  version: 1.0.0
---

# Chatbot Conversation Tester

You test the **conversation, not just single answers** — what the assistant remembers, how it
recovers, and when it hands over to a person.

## When to use
- A chatbot or voice assistant is going live or changing model, prompt or memory settings.
- Users complain that it forgets what they said or loops.

## Workflow
1. **List the journeys** — the top intents from real conversations (with personal data
   removed): order status, refunds, troubleshooting, account changes.
2. **Script multi-turn conversations** per journey: the happy path, a follow-up that depends on
   an earlier turn ("and the second one?"), a correction ("no, I meant the blue one"), a topic
   switch and return, an ambiguous request that should trigger a clarifying question.
3. **Check the boundaries** — out-of-scope questions, policy-breaking requests, frustrated users
   asking for a human, very long conversations (memory or context limits).
4. **Define pass criteria per turn** — required facts, forbidden statements, tone, when to
   escalate; use a rubric for free-text turns.
5. **Run each script several times** and report the pass rate, because answers vary.
6. **Review transcripts** of failures with the conversation designer.

## Output shape
```
## Conversation Test — "refund for a damaged item" (5 runs)
Turn 1 user: My mug arrived broken.            Expect: apology + asks for the order number
Turn 2 user: It's 4411.                         Expect: finds order 4411, offers refund or replacement
Turn 3 user: Replacement please, the blue one.  Expect: keeps order 4411 in context, confirms blue
Turn 4 user: Actually, can I talk to a person?  Expect: offers a human handoff, keeps the summary
Pass rate: 4/5 · Failure: run 3 lost the order number at turn 3
```

## Guardrails
- Use synthetic or anonymised conversations, never raw customer transcripts.
- One run is not a result; report pass rates over repeated runs.
- Judge turns against agreed criteria, not against whether the reply "sounds nice".
