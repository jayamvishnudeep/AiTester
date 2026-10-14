---
name: rag-quality-evaluator
description: >-
  Evaluates retrieval-augmented generation (RAG) systems stage by stage. Use when a team says
  "test our RAG chatbot", "are the answers grounded in our documents", "measure retrieval
  quality", or "evaluate with RAGAS or DeepEval". Measures retrieval (recall@k, MRR, context
  precision and recall) and generation (faithfulness, answer relevancy, citation accuracy)
  separately, so a bad answer can be traced to the retriever, the chunking or the prompt.
license: MIT
metadata:
  author: AiTester
  pack: llm-evaluation
  version: 1.0.0
---

# RAG Quality Evaluator

You find out **where a RAG system goes wrong** — did it fetch the wrong passages, or write a bad
answer from the right ones?

## When to use
- A RAG assistant gives wrong, vague or uncited answers and nobody knows why.
- Chunking, embedding model, retriever or prompt changes need to be compared fairly.

## Workflow
1. **Build the eval set** — questions with the document passages that answer them (relevant
   chunk ids) and a reference answer; include questions the documents cannot answer.
2. **Evaluate retrieval on its own** — recall@k (is a relevant chunk in the top k), MRR (how high
   the first relevant chunk ranks), context precision (share of retrieved chunks that are
   relevant) and context recall (share of needed information retrieved).
3. **Evaluate generation** — faithfulness or groundedness (every claim supported by the
   retrieved context), answer relevancy (answers the question asked), citation accuracy
   (citations point at passages that support the claim), and correct refusals for unanswerable
   questions.
4. **Use tools where they help** — RAGAS, DeepEval or TruLens provide these metrics, many using an
   LLM judge; calibrate any judge-based metric against human labels.
5. **Diagnose by stage** — low recall → chunking, embeddings, hybrid search; good recall but low
   faithfulness → prompt or model; wrong citations → citation formatting or post-processing.
6. **Compare variants** on the same eval set and report per category.

## Output shape
```
## RAG Evaluation — support-assistant v3 vs v2 (60 questions)
| Metric | v2 | v3 | Note |
|--------|----|----|------|
| Recall@5 | 0.78 | 0.92 | hybrid search added |
| Faithfulness | 0.81 | 0.84 | judge agreement with humans 0.88 |
| Citation accuracy | 0.70 | 0.90 | |
| Correct refusals (8 unanswerable) | 3/8 | 7/8 | |
Weakest category: pricing questions (recall@5 0.6) → check table chunking
```

## Guardrails
- Report retrieval and generation separately; one blended score hides the cause.
- Judge-based metrics need a calibration check; say how well the judge agrees with humans.
- Keep the eval set fixed between compared variants.
