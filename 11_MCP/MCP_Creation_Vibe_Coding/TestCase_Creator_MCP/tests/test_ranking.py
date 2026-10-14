import pytest
from fastmcp.exceptions import ToolError

from test_creator_mcp.ranking import AUTOMATABLE, DEFAULT_WEIGHTS, Weights, automation_candidates, regression_suite, smoke_suite, top_test_cases


def top(catalog, weights, module="Funnels", limit=10, **options):
    settings = {"min_priority": None, "execution": "any", "one_per_idea": True, "include_drafts": False, "detail": "brief"}
    return top_test_cases(catalog, weights, module, limit, **(settings | options))


def keys(result):
    return [pick.test_case.issue_key for pick in result.picks]


def test_the_shipped_weights_are_the_plan_weights(weights):
    assert weights.priority == DEFAULT_WEIGHTS["priority"] and weights.test_type == DEFAULT_WEIGHTS["test_type"]


def test_funnels_top_five_matches_the_plan(catalog, weights):
    result = top(catalog, weights, limit=5)
    assert keys(result) == ["VWO-3821", "VWO-1628", "VWO-2084", "VWO-2453", "VWO-5007"]
    assert [pick.score for pick in result.picks] == [112, 110, 110, 110, 110]
    assert result.picks[3].why.endswith("best of 19 eligible rows for this test idea")
    assert len(result.picks[3].also_runnable_on) == 11  # 10 environments and "... and 8 more"


def test_one_per_idea_keeps_near_copies_out(catalog, weights):
    collapsed = keys(top(catalog, weights, limit=50))
    assert "VWO-2453" in collapsed and "VWO-2633" not in collapsed and "VWO-3173" not in collapsed
    every_row = keys(top(catalog, weights, limit=50, one_per_idea=False))
    assert {"VWO-2453", "VWO-2633", "VWO-3173"} <= set(every_row)
    assert len({catalog.get(k).idea for k in collapsed}) == len(collapsed)


def test_execution_modes_and_statuses(catalog, weights):
    assert {p.test_case.status for p in top(catalog, weights, limit=50, execution="manual").picks} == {"Ready"}
    assert {p.test_case.status for p in top(catalog, weights, limit=50, execution="automated").picks} == {"Automated"}
    with_drafts = top(catalog, weights, limit=50, include_drafts=True)
    assert "Deprecated" not in {p.test_case.status for p in with_drafts.picks}
    assert with_drafts.eligible_rows > top(catalog, weights, limit=50).eligible_rows
    assert all(p.test_case.priority in ("High", "Highest") for p in top(catalog, weights, limit=50, min_priority="High").picks)


def test_custom_weights_change_the_order(catalog, tmp_path):
    custom = tmp_path / "ranking.yaml"
    custom.write_text("test_type:\n  UI/UX: 200\n", encoding="utf-8")
    result = top(catalog, Weights.load(custom), limit=3)
    assert all(p.test_case.test_type == "UI/UX" for p in result.picks)


def test_smoke_suite_takes_each_module_and_cuts_fairly(catalog, weights):
    suite = smoke_suite(catalog, weights, None, 2, None, None, "any", "brief")
    assert suite.total == 34 and set(suite.per_module.values()) == {2}
    capped = smoke_suite(catalog, weights, None, 2, 20, None, "any", "brief")
    assert capped.total == 20 and len(capped.per_module) == 17  # every module keeps its first pick
    assert any("max_total 20" in note for note in capped.notes)


def test_regression_suite_respects_every_limit(catalog, weights):
    suite = regression_suite(catalog, weights, ["Funnels", "Reports", "Surveys"], 30, 5, 12, "Medium", None,
                             True, True, "any", "brief")
    assert suite.total <= 30
    assert set(suite.per_module) == {"Funnels", "Reports", "Surveys"}
    assert all(5 <= n <= 12 for n in suite.per_module.values())
    assert len(suite.coverage["browsers"]) == 4 and len(suite.coverage["devices"]) == 4
    assert all(case.test_case.priority in ("Medium", "High", "Highest") for case in suite.test_cases)
    ideas = [catalog.get(case.test_case.issue_key).idea for case in suite.test_cases]
    assert len(ideas) == len(set(ideas))


def test_coverage_swaps_in_a_missing_browser_and_device(catalog, weights):
    # Funnels' best 4 run on Edge, Firefox and Safari only, on desktop, tablet and Android.
    plain = regression_suite(catalog, weights, ["Funnels"], 4, 1, 4, None, None, False, False, "any", "brief")
    assert "Chrome 148" not in plain.coverage["browsers"] and "mobile (iOS)" not in plain.coverage["devices"]
    browsers = regression_suite(catalog, weights, ["Funnels"], 4, 1, 4, None, None, True, False, "any", "brief")
    assert browsers.total == 4 and len(browsers.coverage["browsers"]) == 4
    assert any(note.startswith("Swapped") and "Chrome 148" in note for note in browsers.notes)
    devices = regression_suite(catalog, weights, ["Funnels"], 4, 1, 4, None, None, False, True, "any", "brief")
    assert len(devices.coverage["devices"]) == 4


def test_regression_suite_filters_and_impossible_limits(catalog, weights):
    only = regression_suite(catalog, weights, ["Funnels"], 10, 1, 10, None, ["Security"], False, False, "any", "brief")
    assert {case.test_case.test_type for case in only.test_cases} == {"Security"}
    with pytest.raises(ToolError, match="more than max_total"):
        regression_suite(catalog, weights, None, 30, 2, 10, None, None, True, True, "any", "brief")
    with pytest.raises(ToolError, match="above max_per_module"):
        regression_suite(catalog, weights, ["Funnels"], 30, 5, 3, None, None, True, True, "any", "brief")


def test_automation_candidates(catalog, weights):
    report = automation_candidates(catalog, weights, "Funnels", "High", 20, "brief")
    automated_ideas = {c.idea for c in catalog.cases if c.status == "Automated"}
    assert report.candidates
    for pick in report.candidates:
        case = catalog.get(pick.test_case.issue_key)
        assert case.status == "Ready" and case.test_type in AUTOMATABLE and case.priority in ("High", "Highest")
        assert case.idea not in automated_ideas
    [funnels] = report.modules
    assert funnels.module == "Funnels" and funnels.automated_percent == round(100 * funnels.automated / funnels.runnable, 1)
