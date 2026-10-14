"""The server through MCP itself, the way a client sees it."""

import json

import pytest
from fastmcp import Client
from mcp.shared.exceptions import MCPError

from conftest import call, make_settings
from test_skill_finder_mcp import sync
from test_skill_finder_mcp.catalog import read_manifest
from test_skill_finder_mcp.server import build_server
from test_skill_finder_mcp.settings import DEFAULT_SKILLS_DIR

TOOLS = {
    "search_skills", "find_skill", "recommend_skills", "related_skills", "get_catalog_overview", "list_categories",
    "list_skills", "get_stlc_workflow", "get_skill", "get_skill_file", "download_skill", "validate_skills",
    "create_skill", "sync_upstream_skills",
}
WRITES = {"create_skill", "sync_upstream_skills"}


def example_input(description: str) -> dict:
    """The JSON after 'Example input' in a tool description."""
    text = description.split("Example input", 1)[1].split("Returns:", 1)[0]
    return json.loads(text[text.index("{"):])


@pytest.fixture
def offline_upstream(monkeypatch, skills_dir):
    """The upstream download replaced by the files the manifest says came from upstream."""
    files = {rel: (skills_dir / rel).read_bytes() for rel in read_manifest(skills_dir)["files"]}
    monkeypatch.setattr(sync, "fetch_upstream", lambda settings: (files, "abc123"))


async def test_fourteen_tools_each_with_a_title_and_an_example(client):
    tools = await client.list_tools()
    assert {tool.name for tool in tools} == TOOLS
    for tool in tools:
        assert tool.title, tool.name
        assert "Example input (paste with 'Edit as JSON' on):" in tool.description, tool.name
        assert "Returns:" in tool.description, tool.name
        example_input(tool.description)  # parses as JSON


async def test_every_documented_example_runs(write_client, offline_upstream):
    """The examples people see when they click a tool all work as written."""
    for tool in await write_client.list_tools():
        result = await write_client.call_tool(tool.name, example_input(tool.description), raise_on_error=False)
        assert not result.is_error, f"{tool.name}: {result.content[0].text}"


async def test_annotations_tell_clients_what_is_safe(client):
    tools = {tool.name: tool.annotations for tool in await client.list_tools()}
    for name, annotations in tools.items():
        assert annotations.read_only_hint is (name not in WRITES), name
    assert tools["sync_upstream_skills"].destructive_hint and tools["sync_upstream_skills"].open_world_hint
    assert not tools["create_skill"].destructive_hint


async def test_the_readonly_profile_hides_the_write_tools():
    server = build_server(make_settings(DEFAULT_SKILLS_DIR, profile="readonly"))
    async with Client(server) as connected:
        assert {tool.name for tool in await connected.list_tools()} == TOOLS - WRITES


async def test_the_server_introduces_itself(client):
    assert client.server_info.name == "Test Skill Finder" and client.server_info.version == "0.1.0"
    assert "serves 100 QA and test-automation skills" in client.instructions


# --- Finding ---------------------------------------------------------------------------------

async def test_search_ranks_explains_and_limits(client):
    result = await call(client, "search_skills", query="playwright api", limit=3)
    assert result["returned"] == 3 and result["total_matches"] >= 3
    first = result["hits"][0]
    assert (first["rank"], first["skill"]["name"]) == (1, "pw-api-tester")
    assert first["matched"] == ["playwright", "api"] and first["why"].startswith("name:")
    assert set(first["skill"]) == {"name", "title", "category", "summary", "source"}


async def test_search_filters_by_category_and_source(client):
    result = await call(client, "search_skills", query="flaky", category="cypress")
    assert result["filters"] == {"category": "Cypress pack"}
    assert [hit["skill"]["name"] for hit in result["hits"]] == ["cy-flaky-debugger"]
    upstream = await call(client, "search_skills", query="flaky", source="upstream", limit=25)
    assert {hit["skill"]["source"] for hit in upstream["hits"]} == {"upstream"}
    assert "cy-flaky-debugger" not in [hit["skill"]["name"] for hit in upstream["hits"]]


async def test_search_corrects_typos_and_says_so(client):
    result = await call(client, "search_skills", query="playwrite api")
    assert result["hits"][0]["skill"]["name"] == "pw-api-tester"
    assert "corrected from 'playwrite api'" in result["note"]


async def test_search_with_no_match_suggests_what_to_do(client):
    result = await call(client, "search_skills", query="xyzzy")
    assert result["hits"] == [] and result["total_matches"] == 0
    assert "list_categories" in result["note"]


async def test_inputs_pasted_whole_into_one_field_get_a_clear_message(client):
    for tool, arguments in [("search_skills", {"query": '{"query": "playwright api"}'}),
                            ("find_skill", {"name": '{"name": "bug"}'}),
                            ("get_skill", {"name": '{"name": "bug-reporter"}'})]:
        result = await client.call_tool(tool, arguments, raise_on_error=False)
        assert result.is_error and "Edit as JSON" in result.content[0].text, tool


async def test_an_unknown_category_lists_the_real_ones(client):
    result = await client.call_tool("search_skills", {"query": "api", "category": "cobol"}, raise_on_error=False)
    assert result.is_error and "Cypress pack" in result.content[0].text


async def test_find_skill_exact_close_and_missing(client):
    exact = await call(client, "find_skill", name="test plan generator")
    assert exact["exact"] and exact["match"]["name"] == "test-plan-generator"
    assert "test-plan-generator" not in [a["name"] for a in exact["alternatives"]]
    close = await call(client, "find_skill", name="pw api")
    assert not close["exact"] and close["match"]["name"] == "pw-api-tester"
    vague = await call(client, "find_skill", name="playwright")
    assert vague["match"] is None and vague["alternatives"][0]["name"].startswith("pw-")


async def test_recommend_returns_steps_in_testing_order(client):
    result = await call(client, "recommend_skills", task="test the new checkout API before the release")
    names = [step["skill"]["name"] for step in result["steps"]]
    assert names[0] == "test-strategy-designer" and names[-1] == "release-readiness-assessor"
    assert "api-test-designer" in names
    assert [step["step"] for step in result["steps"]] == list(range(1, len(names) + 1))


async def test_recommend_keeps_to_the_framework_named(client):
    result = await call(client, "recommend_skills", task="automate the login flow with playwright and run it in CI")
    categories = {step["category"] for step in result["steps"]}
    assert "Playwright pack" in categories and not categories & {"Cypress pack", "Selenium pack"}
    # Every framework has a flaky-test debugger; only Cypress's fits here.
    flaky = await call(client, "recommend_skills", task="debug flaky cypress tests")
    names = [step["skill"]["name"] for step in flaky["steps"]]
    assert "cy-flaky-debugger" in names and not {"pw-flaky-debugger", "se-flaky-debugger"} & set(names)


async def test_recommend_with_no_match_is_an_error(client):
    result = await client.call_tool("recommend_skills", {"task": "xyzzy plugh"}, raise_on_error=False)
    assert result.is_error and "No skill matches" in result.content[0].text


async def test_related_skills(client):
    result = await call(client, "related_skills", name="se-flaky-debugger", limit=3)
    assert result["skill"] == "se-flaky-debugger" and len(result["related"]) == 3


# --- Browsing --------------------------------------------------------------------------------

async def test_overview_counts(client):
    result = await call(client, "get_catalog_overview")
    assert (result["total_skills"], result["upstream_skills"], result["local_skills"], result["categories"]) == (100, 36, 64, 17)
    assert result["by_kind"] == {"stlc-phase": 33, "framework-pack": 36, "domain-pack": 31}
    assert result["upstream_repository"] == "https://github.com/PramodDutta/skillmasterclass"
    assert result["by_category"]["LLM evaluation pack"] == 7


async def test_list_categories(client):
    result = (await client.call_tool("list_categories", {})).structured_content["result"]
    assert len(result) == 17 and result[0]["name"] == "Requirement Analysis"
    last = result[-1]
    assert (last["name"], last["kind"], last["order"], last["folder"], last["skills"]) == (
        "MCP pack", "domain-pack", 109, "domain-packs/mcp-pack", 6)
    assert "mcp-server-builder" in last["skill_names"]


async def test_list_skills_pages_through_everything(client):
    seen, offset = [], 0
    while offset is not None:
        page = await call(client, "list_skills", limit=40, offset=offset)
        seen += [skill["name"] for skill in page["skills"]]
        offset = page["next_offset"]
    assert len(seen) == len(set(seen)) == 100
    local = await call(client, "list_skills", category="Security pack", source="local")
    assert local["total"] == 6 and local["filters"] == {"category": "Security pack", "source": "local"}


async def test_stlc_workflow_has_seven_phases_and_ten_packs(client):
    result = await call(client, "get_stlc_workflow")
    assert [phase["order"] for phase in result["phases"]] == [1, 2, 3, 4, 5, 6, 7]
    assert len(result["packs"]) == 10
    assert "Requirement Analysis" in result["flow"]


# --- Using a skill ---------------------------------------------------------------------------

async def test_get_skill_returns_the_whole_skill(client):
    result = await call(client, "get_skill", name="test plan generator")
    assert result["name"] == "test-plan-generator" and result["path"] == "skills/02-test-planning/test-plan-generator"
    assert result["content"].startswith("---") and "## Workflow" in result["content"]
    assert "references/test-plan-template.md" in result["files"]


async def test_get_skill_file_forgives_the_path_but_not_escapes(client):
    for path in ["references/test-plan-template.md", "./references/test-plan-template.md", "test-plan-template.md",
                 "skills\\02-test-planning\\test-plan-generator\\references\\test-plan-template.md"]:
        result = await call(client, "get_skill_file", name="test-plan-generator", path=path)
        assert result["path"] == "references/test-plan-template.md", path
        assert result["content"].startswith("# Test Plan") and not result["truncated"]
    for path in ["../../README.md", "/etc/passwd", "missing.md"]:
        result = await client.call_tool("get_skill_file", {"name": "test-plan-generator", "path": path},
                                        raise_on_error=False)
        assert result.is_error and "Its files:" in result.content[0].text, path


async def test_get_skill_file_asks_for_the_full_path_when_a_name_is_ambiguous(write_client, skills_dir):
    folder = skills_dir / "02-test-planning" / "test-plan-generator"
    for sub in ("copilot", "references"):
        (folder / sub / "notes.md").write_text(f"{sub} notes", encoding="utf-8")
    result = await write_client.call_tool("get_skill_file", {"name": "test-plan-generator", "path": "notes.md"},
                                          raise_on_error=False)
    assert result.is_error and "matches several files" in result.content[0].text
    exact = await call(write_client, "get_skill_file", name="test-plan-generator", path="references/notes.md")
    assert exact["content"] == "references notes"


async def test_download_skill_bundles_every_file(client):
    result = await call(client, "download_skill", name="test-plan-generator")
    assert [f["path"] for f in result["files"]] == [
        "SKILL.md", "copilot/test-plan.prompt.md", "references/requirement-checklist.md",
        "references/test-plan-template.md", "scripts/fetch_jira.sh"]
    assert "~/.claude/skills/test-plan-generator/" in result["install"]["claude_code_personal"]


# --- Maintaining -------------------------------------------------------------------------------

async def test_validate_finds_no_problems(client):
    result = await call(client, "validate_skills")
    assert (result["total"], result["valid"], result["problems"]) == (100, 100, [])


async def test_a_created_skill_is_searchable_at_once(write_client):
    created = await call(
        write_client, "create_skill", name="k6-soak-tester", category="performance",
        description="Plans k6 soak tests that run for hours to find memory leaks. Use when someone asks for a soak test.",
        when_to_use="A service must run for days", workflow="Agree the load, Script it in k6, Watch memory",
        output_shape="k6 script", guardrails='["Never run against production"]')
    assert created["path"] == "skills/domain-packs/performance-pack/k6-soak-tester/SKILL.md"
    assert "1. Agree the load\n2. Script it in k6\n3. Watch memory" in created["content"]
    found = await call(write_client, "search_skills", query="soak test memory leaks")
    assert found["hits"][0]["skill"]["name"] == "k6-soak-tester"
    report = await call(write_client, "validate_skills")
    assert (report["total"], report["valid"]) == (101, 101)


async def test_create_skill_refuses_a_name_in_use(write_client):
    result = await write_client.call_tool("create_skill", {
        "name": "bug-reporter", "category": "Defect Management", "description": "x" * 50,
        "when_to_use": ["a"], "workflow": ["b"], "output_shape": "c", "guardrails": ["d"]}, raise_on_error=False)
    assert result.is_error and "already exists" in result.content[0].text


async def test_sync_dry_run_reports_without_writing(write_client, offline_upstream, skills_dir):
    before = (skills_dir / ".upstream.json").read_text(encoding="utf-8")
    result = await call(write_client, "sync_upstream_skills")
    assert not result["applied"] and result["unchanged"] == 41
    assert result["added"] == result["updated"] == result["removed"] == result["conflicts"] == []
    assert (skills_dir / ".upstream.json").read_text(encoding="utf-8") == before


# --- Resources and prompts ----------------------------------------------------------------------

async def test_resources(client):
    assert {str(r.uri) for r in await client.list_resources()} == {"skills://catalog", "skills://categories"}
    templates = {t.uri_template for t in await client.list_resource_templates()}
    assert templates == {"skills://skill/{name}", "skills://skill/{name}/files/{path*}"}
    assert len(json.loads((await client.read_resource("skills://catalog"))[0].text)) == 100
    assert len(json.loads((await client.read_resource("skills://categories"))[0].text)) == 17
    skill = (await client.read_resource("skills://skill/pw-api-tester"))[0].text
    assert skill.startswith("---\nname: pw-api-tester")
    template = (await client.read_resource("skills://skill/test-plan-generator/files/references/test-plan-template.md"))[0]
    assert template.text.startswith("# Test Plan")


@pytest.mark.parametrize("uri", ["skills://skill/no-such-skill",
                                 "skills://skill/test-plan-generator/files/../../README.md",
                                 "skills://skill/test-plan-generator/files/missing.md",
                                 "skills://skill/test-plan-generator/files/SKILL.md"])  # has its own resource
async def test_resources_refuse_unknown_skills_and_escapes(client, uri):
    with pytest.raises(MCPError):
        await client.read_resource(uri)


async def test_prompts(client):
    assert {p.name for p in await client.list_prompts()} == {"use_skill", "find_skill_for_task", "stlc_walkthrough",
                                                             "compare_skills"}
    use = (await client.get_prompt("use_skill", {"skill": "bug reporter", "task": "login returns 500"})).messages[0]
    assert "login returns 500" in use.content.text and "# Bug Reporter" in use.content.text
    compare = (await client.get_prompt("compare_skills", {"first": "pw-flaky-debugger", "second": "se-flaky-debugger"}))
    assert "## pw-flaky-debugger" in compare.messages[0].content.text
    for name, arguments in [("find_skill_for_task", {"task": "load test the API"}), ("stlc_walkthrough", {"feature": "Login"})]:
        assert (await client.get_prompt(name, arguments)).messages[0].content.text


async def test_a_prompt_for_an_unknown_skill_fails_clearly(client):
    with pytest.raises(MCPError, match="no-such-skill"):
        await client.get_prompt("use_skill", {"skill": "no-such-skill", "task": "x"})
