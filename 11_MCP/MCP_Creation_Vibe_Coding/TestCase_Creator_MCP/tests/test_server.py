"""The server through MCP itself, the way a client sees it."""

import json

import pytest
from fastmcp import Client

from conftest import call, make_settings
from test_creator_mcp.server import build_server

TOOLS = {
    "get_catalog_overview", "list_modules", "list_field_values", "get_test_cases", "get_test_cases_by_priority",
    "get_test_cases_by_module", "filter_test_cases", "count_test_cases", "search_test_cases", "get_top_test_cases",
    "build_smoke_suite", "build_regression_suite", "get_coverage_matrix", "find_duplicate_test_cases",
    "get_automation_candidates", "get_test_case_template", "validate_test_case", "create_test_case",
    "create_environment_variants", "export_test_cases",
}
WRITES = {"create_test_case", "create_environment_variants"}


def example_input(description: str) -> dict:
    """The JSON after 'Example input:' in a tool description."""
    text = description.split("Example input", 1)[1].split("Returns:", 1)[0]
    return json.loads(text[text.index("{"):])


async def test_twenty_tools_each_with_a_title_and_a_working_example(client):
    tools = await client.list_tools()
    assert {tool.name for tool in tools} == TOOLS
    for tool in tools:
        assert tool.title, tool.name
        assert "Example input (paste with 'Edit as JSON' on):" in tool.description and "Returns:" in tool.description, tool.name
        example_input(tool.description)  # parses as JSON


async def test_every_documented_example_runs(write_client):
    """The examples people see when they click a tool all work as written."""
    for tool in await write_client.list_tools():
        result = await write_client.call_tool(tool.name, example_input(tool.description), raise_on_error=False)
        assert not result.is_error, f"{tool.name}: {result.content[0].text}"


async def test_the_whole_example_pasted_into_one_field_still_works(client):
    """In MCP Inspector a list field has its own JSON box; people paste the whole example into it."""
    pasted = await call(client, "get_test_cases", issue_keys={"issue_keys": ["VWO-1001"]})
    assert [case["issue_key"] for case in pasted["found"]] == ["VWO-1001"]
    for typed in ("VWO-1001, 2453", '["VWO-1001", "VWO-2453"]', '{"issue_keys": ["VWO-1001", "VWO-2453"]}'):
        result = await call(client, "get_test_cases", issue_keys=typed)
        assert [case["issue_key"] for case in result["found"]] == ["VWO-1001", "VWO-2453"], typed
    one = await call(client, "get_test_cases", issue_keys="VWO-1001")
    assert [case["issue_key"] for case in one["found"]] == ["VWO-1001"]
    suite = await call(client, "build_smoke_suite", modules={"modules": ["Funnels"]}, per_module=1)
    assert suite["per_module"] == {"Funnels": 1}


async def test_a_bigger_example_in_one_field_says_where_it_goes(client):
    result = await client.call_tool("get_test_cases", {"issue_keys": {"issue_keys": ["VWO-1001"], "limit": 5}},
                                    raise_on_error=False)
    assert result.is_error and "Edit as JSON" in result.content[0].text
    result = await client.call_tool("get_test_cases_by_module", {"module": '{"module": "Funnels", "limit": 5}'},
                                    raise_on_error=False)
    assert result.is_error and "Edit as JSON" in result.content[0].text


async def test_a_draft_pasted_with_its_wrapper_validates(client):
    from test_authoring import EXAMPLE

    assert (await call(client, "validate_test_case", test_case={"test_case": EXAMPLE}))["valid"]


async def test_only_the_two_writing_tools_are_not_read_only(client):
    for tool in await client.list_tools():
        assert tool.annotations.read_only_hint is (tool.name not in WRITES), tool.name


async def test_readonly_profile_hides_the_writing_tools(tmp_path):
    async with Client(build_server(make_settings(tmp_path / "new.csv", profile="readonly"))) as client:
        names = {tool.name for tool in await client.list_tools()}
    assert names == TOOLS - WRITES


async def test_bad_input_comes_back_as_a_readable_error(client):
    result = await client.call_tool("get_test_cases_by_module", {"module": "Funels"}, raise_on_error=False)
    assert result.is_error and "Did you mean: Funnels" in result.content[0].text
    for limit in (0, 101):
        result = await client.call_tool("filter_test_cases", {"limit": limit}, raise_on_error=False)
        assert result.is_error
    result = await client.call_tool("get_test_cases_by_priority", {}, raise_on_error=False)
    assert result.is_error and "min_priority" in result.content[0].text


async def test_max_limit_setting_shapes_the_schema(tmp_path):
    async with Client(build_server(make_settings(tmp_path / "new.csv", max_limit=25))) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        assert tools["filter_test_cases"].input_schema["properties"]["limit"]["maximum"] == 25
        assert (await client.call_tool("filter_test_cases", {"limit": 26}, raise_on_error=False)).is_error


async def test_objective_tools_through_mcp(client):
    by_priority = await call(client, "get_test_cases_by_priority", priority="Highest", include_deprecated=True, limit=5)
    assert by_priority["total_matches"] == 396 and by_priority["returned"] == 5
    by_module = await call(client, "get_test_cases_by_module", module="Funnels", limit=3)
    assert by_module["test_cases"][0]["priority"] == "Highest" and by_module["next_offset"] == 3
    top = await call(client, "get_top_test_cases", module="Funnels", limit=5)
    assert [p["test_case"]["issue_key"] for p in top["picks"]] == ["VWO-3821", "VWO-1628", "VWO-2084", "VWO-2453", "VWO-5007"]


async def test_brief_rows_carry_no_empty_fields(client):
    page = await call(client, "filter_test_cases", module="Funnels", limit=2)
    assert set(page["test_cases"][0]) == {"issue_key", "summary", "module", "feature", "priority", "test_type",
                                          "status", "browser", "device"}


async def test_resources(client):
    case = json.loads((await client.read_resource("tc://test-cases/VWO-1001"))[0].text)
    assert case["issue_key"] == "VWO-1001" and len(case["steps"]) == 4
    schema = json.loads((await client.read_resource("tc://schema"))[0].text)
    assert "Funnels" in schema["modules"] and schema["allowed_values"]["priority"][0] == "Highest"
    modules = json.loads((await client.read_resource("tc://modules"))[0].text)
    assert len(modules) == 17 and "step drop-off" in modules["Funnels"]
    with pytest.raises(Exception):
        await client.read_resource("tc://test-cases/VWO-9999")


async def test_prompts(client):
    prompt = await client.get_prompt("release_run_plan", {"module": "Funnels", "count": "5"})
    text = prompt.messages[0].content.text
    assert "get_top_test_cases" in text and "limit=5" in text
    assert {p.name for p in await client.list_prompts()} == {"release_run_plan", "coverage_review", "write_test_cases"}
