"""Reading the skills folder: counts, categories, metadata, and what happens with broken skills."""

import time

import pytest
from fastmcp.exceptions import ToolError

from test_skill_finder_mcp.catalog import STLC_PHASES, CatalogError, CatalogStore, classify, load_catalog
from test_skill_finder_mcp.settings import DEFAULT_SKILLS_DIR

SKILL = """---
name: {name}
description: >-
  {description}
license: MIT
metadata:
  author: Tester
  {classifier}
  version: 1.0.0
---

# {title}

One line.

## When to use
- Always

## Workflow
1. Do it

## Output shape
```
done
```

## Guardrails
- Never guess
"""


def write_skill(root, folder, name, description="Does a thing well enough to be useful. Use when testing.",
                classifier="stlc-phase: Test Design", title="A Skill"):
    path = root / folder / name
    path.mkdir(parents=True)
    (path / "SKILL.md").write_text(SKILL.format(name=name, description=description, classifier=classifier, title=title),
                                   encoding="utf-8")
    return path


def test_a_hundred_skills_from_two_sources(catalog):
    assert len(catalog.skills) == 100
    assert sum(s.source == "upstream" for s in catalog.skills) == 36
    assert sum(s.source == "local" for s in catalog.skills) == 64
    assert catalog.warnings == ()


def test_every_skill_file_on_disk_is_in_the_catalog(catalog):
    on_disk = {p.parent.name for p in DEFAULT_SKILLS_DIR.rglob("SKILL.md")}
    assert on_disk == set(catalog.by_name)


def test_categories_follow_the_testing_life_cycle_then_the_packs(catalog):
    categories = catalog.categories
    assert [c.name for c in categories[:7]] == list(STLC_PHASES)
    assert [c.order for c in categories[:7]] == [1, 2, 3, 4, 5, 6, 7]
    assert {c.kind for c in categories[:7]} == {"stlc-phase"}
    assert {c.name: c.skills for c in categories[7:]} == {
        "Playwright pack": 11, "Selenium pack": 11, "Cypress pack": 6, "API testing pack": 6, "Mobile pack": 2,
        "Performance pack": 6, "Security pack": 6, "LLM evaluation pack": 7, "AI agents pack": 6, "MCP pack": 6,
    }
    assert sum(c.skills for c in categories) == 100
    kinds = {c.name: c.kind for c in categories}
    assert kinds["Cypress pack"] == "framework-pack" and kinds["MCP pack"] == "domain-pack"


def test_names_match_their_folders_and_are_unique(catalog):
    for skill in catalog.skills:
        assert skill.folder.rsplit("/", 1)[-1] == skill.name


def test_a_skill_carries_its_metadata_sections_and_files(catalog):
    skill = catalog.by_name["test-plan-generator"]
    assert skill.category == "Test Planning" and skill.kind == "stlc-phase" and skill.source == "upstream"
    assert skill.folder == "02-test-planning/test-plan-generator"
    assert skill.files == ("copilot/test-plan.prompt.md", "references/requirement-checklist.md",
                           "references/test-plan-template.md", "scripts/fetch_jira.sh")
    assert skill.title and skill.summary.endswith(".") and skill.version
    assert skill.content.startswith("---\nname: test-plan-generator")
    pack = catalog.by_name["cy-intercept-mocker"]
    assert (pack.category, pack.kind, pack.pack, pack.source) == ("Cypress pack", "framework-pack", "cypress", "local")
    assert pack.section("workflow") and pack.section("Guardrails")


@pytest.mark.parametrize("folder, metadata, expected", [
    ("03-test-design/x", {}, ("Test Design", "stlc-phase", 3)),
    ("framework-packs/playwright-pack/x", {"pack": "playwright"}, ("Playwright pack", "framework-pack", 100)),
    ("domain-packs/llm-evaluation-pack/x", {"pack": "llm-evaluation"}, ("LLM evaluation pack", "domain-pack", 107)),
    ("domain-packs/game-pack/x", {}, ("Game pack", "domain-pack", 150)),
])
def test_where_a_skill_lives_decides_its_category(folder, metadata, expected):
    assert classify(folder, metadata)[:3] == expected


def test_lookup_by_name_forgives_case_spaces_and_typos(catalog):
    assert catalog.get("Test-Plan-Generator").name == "test-plan-generator"
    assert catalog.get("test plan generator").name == "test-plan-generator"
    assert catalog.get("bugreporter").name == "bug-reporter"
    with pytest.raises(ToolError, match="matches several"):
        catalog.get("flaky")
    with pytest.raises(ToolError, match="Did you mean: test-case-writer"):
        catalog.get("test-case-writr-x")
    with pytest.raises(ToolError, match="Edit as JSON"):
        catalog.get('{"name": "bug-reporter"}')
    assert catalog.category("cypress").name == "Cypress pack"
    with pytest.raises(ToolError, match="Valid values"):
        catalog.category("cobol")


def test_broken_and_duplicate_skills_become_warnings_not_crashes(tmp_path):
    write_skill(tmp_path, "03-test-design", "good-skill")
    write_skill(tmp_path, "05-test-execution", "good-skill")  # same name again
    broken = tmp_path / "03-test-design" / "broken-skill"
    broken.mkdir()
    (broken / "SKILL.md").write_text("no frontmatter here", encoding="utf-8")
    catalog = load_catalog(tmp_path)
    assert [s.name for s in catalog.skills] == ["good-skill"]
    assert any("broken-skill" in w and "frontmatter" in w for w in catalog.warnings)
    assert any("already used" in w for w in catalog.warnings)


def test_a_missing_skills_folder_is_a_clear_error(tmp_path):
    with pytest.raises(CatalogError, match="TSF_SKILLS_DIR"):
        load_catalog(tmp_path / "nowhere")


def test_the_store_reloads_when_the_folder_changes(tmp_path):
    write_skill(tmp_path, "03-test-design", "first-skill")
    store = CatalogStore(tmp_path)
    first = store.get()
    assert store.get() is first  # unchanged folder: same snapshot
    time.sleep(0.02)
    write_skill(tmp_path, "framework-packs/cypress-pack", "second-skill", classifier="pack: cypress")
    second = store.get()
    assert second is not first
    assert {s.name: s.category for s in second.skills} == {"first-skill": "Test Design", "second-skill": "Cypress pack"}
