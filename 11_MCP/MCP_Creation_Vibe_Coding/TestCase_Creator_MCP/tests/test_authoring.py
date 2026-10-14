import hashlib
import threading

import pytest
from fastmcp.exceptions import ToolError

from test_creator_mcp import authoring
from test_creator_mcp import models
from test_creator_mcp.settings import DEFAULT_CSV

EXAMPLE = {  # the example in validate_test_case's description
    "summary": "[Funnels] Functional: verify adding a step in the funnel builder",
    "module": "Funnels", "test_type": "Functional", "priority": "High",
    "description": "As a QA engineer, verify the funnel builder in the Funnels module to make sure a new step can be added on desktop (Chrome 148).",
    "preconditions": "A VWO account with access to Funnels; at least one active project; Chrome 148 on desktop.",
    "steps": ["Log in to VWO and open the Funnels module.", "Navigate to the funnel builder screen.",
              "Add a third step to an existing funnel and save.", "Observe the result on desktop using Chrome 148."],
    "expected_result": "The funnel saves with three steps and the drop-off chart shows all three.",
    "browser": "Chrome 148", "device": "desktop",
}


def draft(**changes) -> models.TestCaseDraft:
    return models.TestCaseDraft(**(EXAMPLE | changes))


def library_hash() -> str:
    return hashlib.sha256(DEFAULT_CSV.read_bytes()).hexdigest()


def test_template(catalog, weights):
    template = authoring.template(catalog, weights, "funnels", "functional", "builder")
    assert (template.module, template.feature, template.next_issue_key) == ("Funnels", "funnel builder", "VWO-6001")
    assert template.examples and all(e.module == "Funnels" and e.test_type == "Functional" and e.feature == "funnel builder"
                                     for e in template.examples)
    assert template.allowed_values["status"] == ["Draft", "Ready", "Automated"]


def test_the_documented_example_is_valid(catalog):
    report = authoring.validate(catalog, draft())
    assert report.valid and not report.errors
    assert report.test_case.issue_key == "NEW" and report.test_case.feature == "funnel builder"


def test_validation_errors(catalog):
    assert "exactly 4 steps" in authoring.validate(catalog, draft(steps=["one", "two", "three"])).errors[0]
    assert "Did you mean" in authoring.validate(catalog, draft(module="Funels")).errors[0]
    mismatch = authoring.validate(catalog, draft(summary="[Reports] Functional: verify something"))
    assert any("names module 'Reports'" in error for error in mismatch.errors)
    deprecated = authoring.validate(catalog, draft(status="Deprecated"))
    assert not deprecated.valid


def test_a_missing_prefix_is_added(catalog):
    report = authoring.validate(catalog, draft(summary="verify adding a step in the funnel builder"))
    assert report.valid and report.test_case.summary.startswith("[Funnels] Functional: ")
    assert any("prefix" in warning for warning in report.warnings)


def test_duplicates_are_refused_and_other_environments_flagged(catalog):
    source = catalog.get("VWO-3821")  # [Funnels] Security: check authorization for funnel builder, Edge 148 / desktop
    same = {"summary": "[Funnels] Security: verify authorization for funnel builder",  # another verb, the same idea
            "test_type": "Security", "description": source.description}
    copy = authoring.validate(catalog, draft(**same, browser=source.browser, device=source.device))
    assert not copy.valid and "Duplicate of VWO-3821" in copy.errors[0]

    used = {(c.browser, c.device) for c in catalog.ideas[source.idea] if c.status != "Deprecated"}
    browser, device = next((b, d) for b in catalog.values("browser") for d in catalog.values("device") if (b, d) not in used)
    moved = authoring.validate(catalog, draft(**same, browser=browser, device=device))
    assert moved.valid and "VWO-3821" in moved.similar_test_cases
    assert any("same check exists" in warning for warning in moved.warnings)


def test_create_appends_with_the_next_keys_and_never_touches_the_library(store):
    before = library_hash()
    first = authoring.create(store, draft())
    second = authoring.create(store, draft(summary="[Funnels] Functional: verify renaming a funnel"))
    assert [first.created[0].issue_key, second.created[0].issue_key] == ["VWO-6001", "VWO-6002"]
    assert store.get().get("VWO-6002").source == "created"
    assert store.new_cases_path.read_text(encoding="utf-8").count("\n") == 3  # header and two rows
    assert library_hash() == before


def test_create_refuses_an_invalid_draft(store):
    with pytest.raises(ToolError, match="was not created"):
        authoring.create(store, draft(steps=["only one"]))
    assert not store.new_cases_path.exists()


def test_parallel_creates_get_distinct_keys(store):
    created: list[str] = []

    def work(n: int):
        for i in range(5):
            result = authoring.create(store, draft(summary=f"[Funnels] Functional: verify parallel case {n}-{i}"))
            created.append(result.created[0].issue_key)

    threads = [threading.Thread(target=work, args=(n,)) for n in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(created) == [f"VWO-{n}" for n in range(6001, 6011)]


def test_environment_variants(store):
    result = authoring.environment_variants(store, "VWO-3821", ["Safari 19", "Firefox 141"], ["tablet"])
    assert {(c.browser, c.device) for c in result.created} == {("Safari 19", "tablet"), ("Firefox 141", "tablet")}
    for case in result.created:
        assert case.status == "Draft" and "Edge 148" not in case.description and case.device in case.preconditions
    again = authoring.environment_variants(store, "VWO-3821", ["Safari 19"], ["tablet"])
    assert not again.created and "already exists" in again.skipped[0]
    with pytest.raises(ToolError):
        authoring.environment_variants(store, "VWO-3821", None, None)


def test_exports(catalog):
    cases = [catalog.get("VWO-1001"), catalog.get("VWO-3821")]
    csv_text = authoring.export(cases, "csv", 100).content
    assert csv_text.splitlines()[0].startswith("Issue Type,Issue Key,Summary") and "VWO-3821" in csv_text
    markdown = authoring.export(cases, "markdown", 100).content
    assert "## VWO-1001" in markdown and "1. Log in to VWO" in markdown
    gherkin = authoring.export(cases, "gherkin", 100).content
    assert "Feature: Funnels" in gherkin and "    Given " in gherkin and "    Then " in gherkin
    cut = authoring.export(cases, "csv", 1)
    assert cut.count == 1 and cut.truncated
