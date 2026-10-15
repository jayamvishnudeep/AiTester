# Test Skill Finder screenshots

Test Skill Finder MCP in MCP Inspector, from real runs. The [README](../README.md#try-it-in-mcp-inspector) walks
through each one with the exact input behind it.

| Screenshot | Shows | Input |
|---|---|---|
| [01-test-skill-finder-connected.png](01-test-skill-finder-connected.png) | The card, connected over Streamable HTTP at `http://127.0.0.1:8933/mcp` | |
| [02-enter-input-edit-as-json.png](02-enter-input-edit-as-json.png) | Entering an input with **Edit as JSON** on | |
| [03-search-skills.png](03-search-skills.png) | `search_skills` | `{"query": "playwright api", "limit": 5}` |
| [04-recommend-skills.png](04-recommend-skills.png) | `recommend_skills` | `{"task": "test the new checkout API before the release", "limit": 5}` |
| [05-get-skill.png](05-get-skill.png) | `get_skill` | `{"name": "test-plan-generator"}` |
| [06-list-skills-security-pack.png](06-list-skills-security-pack.png) | `list_skills` | `{"category": "Security pack"}` |
| [07-prompt-use-skill.png](07-prompt-use-skill.png) | The `use_skill` prompt | skill `bug-reporter`, task "Login returns HTTP 500 when the password contains a + sign" |
| [08-resource-skill-md.png](08-resource-skill-md.png) | The `skills://skill/{name}` resource | name `pw-api-tester`, in View Source mode |
