# AI agents pack

A domain pack: 6 skills that plug into the STLC phases. Each folder holds a `SKILL.md`: a short header plus the instructions an AI assistant follows.

| Skill | What it does | From |
|---|---|---|
| [agent-guardrail-tester](agent-guardrail-tester/SKILL.md) | Tests the safety boundaries of AI agents that can take actions. | added here |
| [agent-observability-reviewer](agent-observability-reviewer/SKILL.md) | Reviews and sets up observability for LLM apps and AI agents: traces, metrics and logs for every model and tool call. | added here |
| [agent-trajectory-evaluator](agent-trajectory-evaluator/SKILL.md) | Evaluates an AI agent's trajectory — the sequence of reasoning steps and tool calls it took — against expected behaviour. | added here |
| [ai-agent-test-planner](ai-agent-test-planner/SKILL.md) | Plans testing for LLM-based AI agents that use tools, memory and multi-step reasoning. | added here |
| [multi-agent-workflow-tester](multi-agent-workflow-tester/SKILL.md) | Tests multi-agent systems where several AI agents hand work to each other (for example planner, researcher, writer, reviewer). | added here |
| [tool-call-tester](tool-call-tester/SKILL.md) | Tests an LLM's function or tool calling: whether it picks the right tool, fills valid arguments, and handles tool errors. | added here |

Search them by keyword with the [Test Skill Finder MCP](../../../README.md), or install one in Claude Code by copying
its folder to `~/.claude/skills/`.
