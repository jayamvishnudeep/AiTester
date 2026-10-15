# LLM evaluation pack

A domain pack: 7 skills that plug into the STLC phases. Each folder holds a `SKILL.md`: a short header plus the instructions an AI assistant follows.

| Skill | What it does | From |
|---|---|---|
| [chatbot-conversation-tester](chatbot-conversation-tester/SKILL.md) | Tests multi-turn chatbot and assistant conversations. | added here |
| [hallucination-checker](hallucination-checker/SKILL.md) | Checks LLM answers for hallucinations: claims not supported by the sources or by known facts. | added here |
| [llm-eval-dataset-builder](llm-eval-dataset-builder/SKILL.md) | Builds evaluation datasets (golden sets) for LLM applications. | added here |
| [llm-judge-designer](llm-judge-designer/SKILL.md) | Designs LLM-as-a-judge evaluators and checks that they agree with humans. | added here |
| [prompt-injection-tester](prompt-injection-tester/SKILL.md) | Plans authorized red-team tests for your own LLM application against prompt injection and related risks from the OWASP Top 10 for LLM Applications. | added here |
| [prompt-regression-tester](prompt-regression-tester/SKILL.md) | Builds regression test suites for prompts and model changes, for example with promptfoo. | added here |
| [rag-quality-evaluator](rag-quality-evaluator/SKILL.md) | Evaluates retrieval-augmented generation (RAG) systems stage by stage. | added here |

Search them by keyword with the [Test Skill Finder MCP](../../../README.md), or install one in Claude Code by copying
its folder to `~/.claude/skills/`.
