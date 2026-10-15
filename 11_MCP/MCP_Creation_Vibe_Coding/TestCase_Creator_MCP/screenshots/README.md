# Test Creator screenshots

Test Creator MCP in MCP Inspector, from real runs. The [README](../README.md#try-it-in-mcp-inspector) walks through
each one with the exact input behind it.

| Screenshot | Tool | Input |
|---|---|---|
| [01-test-creator-connected.png](01-test-creator-connected.png) | | The Test Creator card, connected over Streamable HTTP at `http://127.0.0.1:8932/mcp` |
| [02-enter-input-edit-as-json.png](02-enter-input-edit-as-json.png) | `get_test_cases` | Entering an input with **Edit as JSON** on |
| [03-get-test-cases.png](03-get-test-cases.png) | `get_test_cases` | `{"issue_keys": ["VWO-1001"]}` |
| [04-get-test-cases-by-priority.png](04-get-test-cases-by-priority.png) | `get_test_cases_by_priority` | `{"priority": "Highest", "module": "Reports", "limit": 5}` |
| [05-get-test-cases-by-module.png](05-get-test-cases-by-module.png) | `get_test_cases_by_module` | `{"module": "Funnels", "feature": "step drop-off", "limit": 5}` |
| [06-get-top-test-cases.png](06-get-top-test-cases.png) | `get_top_test_cases` | `{"module": "Funnels", "limit": 5}` |
| [07-count-test-cases.png](07-count-test-cases.png) | `count_test_cases` | `{"module": "Funnels", "min_priority": "High", "group_by": "browser"}` |
| [08-build-regression-suite.png](08-build-regression-suite.png) | `build_regression_suite` | `{"modules": ["Funnels", "Reports", "Surveys"], "max_total": 30, "min_per_module": 5, "max_per_module": 12, "min_priority": "Medium"}` |
