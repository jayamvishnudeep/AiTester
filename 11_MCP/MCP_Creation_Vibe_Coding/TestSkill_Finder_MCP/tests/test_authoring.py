"""The house format: validating every skill, and scaffolding new ones that pass."""

import pytest
from fastmcp.exceptions import ToolError

from test_catalog import write_skill
from test_skill_finder_mcp import authoring
from test_skill_finder_mcp.catalog import load_catalog

ARGS = dict(description="Plans k6 soak tests that run for hours to find memory leaks. Use when asked for a soak test.",
            when_to_use=["A service must run for days"], workflow=["Agree the load", "Script it", "Watch memory"],
            output_shape="k6 script", guardrails=["Never run against production"])


def test_every_real_skill_passes(catalog):
    report = authoring.validate(catalog)
    assert (report.total, report.valid, report.problems) == (100, 100, [])


def test_validation_names_each_problem(tmp_path):
    write_skill(tmp_path, "03-test-design", "fine-skill")
    write_skill(tmp_path, "03-test-design", "Bad_Name")
    write_skill(tmp_path, "03-test-design", "short-description", description="Too short.")
    write_skill(tmp_path, "misc", "stray-skill")
    missing = write_skill(tmp_path, "03-test-design", "no-guardrails")
    text = (missing / "SKILL.md").read_text(encoding="utf-8")
    (missing / "SKILL.md").write_text(text.split("## Guardrails")[0], encoding="utf-8")
    renamed = write_skill(tmp_path, "03-test-design", "folder-name")
    (renamed / "SKILL.md").write_text(
        (renamed / "SKILL.md").read_text(encoding="utf-8").replace("name: folder-name", "name: other-name"),
        encoding="utf-8")

    report = authoring.validate(load_catalog(tmp_path))
    problems = {(p.skill, p.problem) for p in report.problems}
    assert ("Bad_Name", "name is not lower-case kebab-case") in problems
    assert ("short-description", "description is missing or shorter than 40 characters") in problems
    assert ("no-guardrails", "missing the '## Guardrails' section") in problems
    assert ("other-name", "name differs from its folder 'folder-name'") in problems
    assert any(skill == "stray-skill" and problem.startswith("not in an STLC phase folder") for skill, problem in problems)
    assert report.total == 6 and report.valid == 1
    assert "fine-skill" not in {p.skill for p in report.problems}


def test_created_skill_is_valid_and_lands_in_its_category(skills_dir):
    catalog = load_catalog(skills_dir)
    created = authoring.create(catalog, "k6-soak-tester", "Performance pack", **ARGS)
    assert created.category == "Performance pack" and created.warnings == []
    assert created.path == "skills/domain-packs/performance-pack/k6-soak-tester/SKILL.md"

    reloaded = load_catalog(skills_dir)
    skill = reloaded.by_name["k6-soak-tester"]
    assert (skill.pack, skill.source, skill.author, skill.version, skill.license) == (
        "performance", "local", "AiTester", "1.0.0", "MIT")
    assert skill.description == ARGS["description"]
    assert skill.section("Workflow") == "1. Agree the load\n2. Script it\n3. Watch memory"
    assert authoring.validate(reloaded).problems == []


def test_a_skill_in_a_phase_gets_the_phase(skills_dir):
    created = authoring.create(load_catalog(skills_dir), "pairwise-designer", "test design", title="Pairwise Designer",
                               summary="Designs pairwise combinations.", **ARGS)
    assert "  stlc-phase: Test Design\n" in created.content
    assert "# Pairwise Designer\n\nDesigns pairwise combinations.\n" in created.content
    assert load_catalog(skills_dir).by_name["pairwise-designer"].category == "Test Design"


def test_a_description_without_use_when_is_a_warning(skills_dir):
    args = {**ARGS, "description": "Plans k6 soak tests that run for hours to find memory leaks in services."}
    created = authoring.create(load_catalog(skills_dir), "k6-soak-tester", "Performance pack", **args)
    assert created.warnings and "Use when" in created.warnings[0]


@pytest.mark.parametrize("name, changes, message", [
    ("Bad Name", {}, "kebab-case"),
    ("bug-reporter", {}, "already exists"),
    ("new-skill", {"description": "short"}, "at least 40 characters"),
    ("new-skill", {"workflow": ["  "]}, "workflow needs at least one item"),
    ("new-skill", {"output_shape": " "}, "output_shape needs an example"),
])
def test_bad_input_creates_nothing(skills_dir, name, changes, message):
    catalog = load_catalog(skills_dir)
    with pytest.raises(ToolError, match=message):
        authoring.create(catalog, name, "Test Design", **{**ARGS, **changes})
    assert len(load_catalog(skills_dir).skills) == 100


def test_an_unknown_category_is_refused(skills_dir):
    with pytest.raises(ToolError, match="Unknown category"):
        authoring.create(load_catalog(skills_dir), "new-skill", "Gardening", **ARGS)
