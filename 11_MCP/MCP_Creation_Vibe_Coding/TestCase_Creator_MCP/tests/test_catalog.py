import csv
from collections import Counter

import pytest

from test_creator_mcp.catalog import COLUMNS, CatalogError, CatalogStore, load_catalog, parse_case
from test_creator_mcp.settings import DEFAULT_CSV


def test_the_library_numbers_from_the_plan(catalog, raw_rows):
    assert len(catalog.cases) == len(raw_rows) == 5000
    assert (catalog.cases[0].issue_key, catalog.cases[-1].issue_key) == ("VWO-1001", "VWO-6000")
    assert catalog.counts("priority") == {"Highest": 396, "High": 1546, "Medium": 2198, "Low": 860}
    assert sum(case.runnable for case in catalog.cases) == 3828
    assert len(catalog.modules) == 17
    assert len({(case.module, case.feature) for case in catalog.cases}) == 72
    assert len(catalog.ideas) == 1244
    assert catalog.next_number() == 6001 and catalog.key_prefix == "VWO"


def test_every_field_matches_the_raw_csv(catalog, raw_rows):
    for row in raw_rows[:200] + raw_rows[-200:]:
        case = catalog.get(row["Issue Key"])
        assert case.summary == row["Summary"] and case.module == row["Component"]
        assert case.priority == row["Priority"] and case.status == row["Status"]
        assert case.row()["Steps"] == row["Steps"]  # parsing the steps and writing them back is lossless
    for field, column in (("module", "Component"), ("test_type", "Test Type"), ("browser", "Browser"),
                          ("device", "Device"), ("status", "Status"), ("priority", "Priority")):
        assert catalog.counts(field) == dict(Counter(row[column] for row in raw_rows))  # dict equality ignores order


def test_feature_steps_and_idea_are_derived():
    case = parse_case({
        "Issue Key": "VWO-1001", "Summary": "[SmartCode] Functional: ensure data collection",
        "Description": "As a QA engineer, ensure the data collection in the SmartCode module to make sure it works.",
        "Component": "SmartCode", "Test Type": "Functional", "Priority": "Medium", "Status": "Ready",
        "Steps": "1. Log in. | 2. Navigate. | 3. Act. | 4. Observe.",
    })
    assert case.feature == "data collection"
    assert case.steps == ("Log in.", "Navigate.", "Act.", "Observe.")
    assert case.idea == ("SmartCode", "Functional", "data collection")  # the verb "ensure" is dropped


def test_interchangeable_verbs_make_one_test_idea(catalog):
    keys = {"VWO-2453", "VWO-2633", "VWO-3173"}  # ensure / confirm / verify segment comparison
    assert len({catalog.get(key).idea for key in keys}) == 1


def test_bad_rows_are_skipped_with_a_warning(tmp_path):
    new = tmp_path / "new_test_cases.csv"
    with new.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow({column: "" for column in COLUMNS} | {"Issue Key": "not a key"})
        writer.writerow({column: "x" for column in COLUMNS} | {"Issue Key": "VWO-1001", "Component": "Funnels"})
    catalog = load_catalog(DEFAULT_CSV, new)
    assert len(catalog.cases) == 5000
    assert any("invalid issue key" in warning for warning in catalog.warnings)
    assert any("VWO-1001 is already in the library" in warning for warning in catalog.warnings)


def test_missing_file_and_missing_columns_are_clear_errors(tmp_path):
    with pytest.raises(CatalogError, match="TC_MCP_CSV"):
        load_catalog(tmp_path / "nope.csv", tmp_path / "new.csv")
    broken = tmp_path / "broken.csv"
    broken.write_text("Issue Key,Summary\nVWO-1,x\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="missing columns"):
        load_catalog(broken, tmp_path / "new.csv")


def test_the_store_reloads_when_the_new_cases_file_changes(store):
    first = store.get()
    assert store.get() is first  # unchanged files: the same snapshot
    source = first.get("VWO-1001")
    with store.new_cases_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(source.row() | {"Issue Key": "VWO-7000"})
    second = store.get()
    assert second is not first and len(second.cases) == 5001
    assert second.get("7000").source == "created" and second.next_number() == 7001
