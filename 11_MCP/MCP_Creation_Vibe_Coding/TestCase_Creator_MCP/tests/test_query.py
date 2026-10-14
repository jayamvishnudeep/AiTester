import pytest
from fastmcp.exceptions import ToolError

from test_creator_mcp.models import resolve
from test_creator_mcp.query import Filters, count, coverage_matrix, duplicate_report, page, select

RANK = {"Low": 1, "Medium": 2, "High": 3, "Highest": 4}


@pytest.mark.parametrize("typed, field, expected", [
    ("funnels", "module", "Funnels"),
    ("Funnel", "module", "Funnels"),
    ("heatmap", "module", "Heatmaps"),
    ("ab", "module", "A/B Testing"),
    ("billing", "module", "Account & Billing"),
    ("sdk", "module", "SDK / Server-Side API"),
    ("P1", "priority", "Highest"),
    ("minor", "priority", "Low"),
    ("a11y", "test_type", "Accessibility"),
    ("ui", "test_type", "UI/UX"),
    ("chrome", "browser", "Chrome 148"),
    ("ff", "browser", "Firefox 141"),
    ("android", "device", "mobile (Android)"),
    ("ios", "device", "mobile (iOS)"),
    ("ipad", "device", "tablet"),
])
def test_what_people_type_resolves(catalog, typed, field, expected):
    choices = ("Lowest", "Low", "Medium", "High", "Highest") if field == "priority" else catalog.values(field)
    assert resolve(typed, choices, field) == expected


def test_unknown_and_ambiguous_values_explain_themselves(catalog):
    with pytest.raises(ToolError, match="Did you mean: Funnels"):
        resolve("Funels", catalog.modules, "module")
    with pytest.raises(ToolError, match=r"mobile \(Android\).*mobile \(iOS\)|mobile \(iOS\).*mobile \(Android\)"):
        resolve("mobile", catalog.values("device"), "device")
    with pytest.raises(ToolError, match="Valid values"):
        resolve("Checkout", catalog.modules, "module")


def test_priority_exact_and_ranges_match_the_raw_csv(catalog, raw_rows):
    def expected(keep, deprecated=False):
        return sum(1 for r in raw_rows if keep(RANK[r["Priority"]]) and (deprecated or r["Status"] != "Deprecated"))

    assert len(select(catalog, Filters(priority="Highest").resolve(catalog))) == expected(lambda p: p == 4)
    assert len(select(catalog, Filters(priority="Highest", include_deprecated=True).resolve(catalog))) == 396
    assert len(select(catalog, Filters(min_priority="High").resolve(catalog))) == expected(lambda p: p >= 3)
    assert len(select(catalog, Filters(max_priority="Medium").resolve(catalog))) == expected(lambda p: p <= 2)
    both = Filters(min_priority="Medium", max_priority="High").resolve(catalog)
    assert len(select(catalog, both)) == expected(lambda p: 2 <= p <= 3)
    with pytest.raises(ToolError, match="above max_priority"):
        Filters(min_priority="Highest", max_priority="Low").resolve(catalog)


def test_combined_filters(catalog, raw_rows):
    filters = Filters(module="funnels", test_type="security", browser="safari", min_priority="high").resolve(catalog)
    cases = select(catalog, filters)
    assert cases and all(c.module == "Funnels" and c.test_type == "Security" and c.browser == "Safari 19" for c in cases)
    assert len(cases) == sum(1 for r in raw_rows if r["Component"] == "Funnels" and r["Test Type"] == "Security"
                             and r["Browser"] == "Safari 19" and RANK[r["Priority"]] >= 3 and r["Status"] != "Deprecated")
    assert all(c.feature == "step drop-off" for c in select(catalog, Filters(module="Funnels", feature="drop-off").resolve(catalog)))


def test_deprecated_is_left_out_unless_asked_for(catalog):
    assert not any(c.status == "Deprecated" for c in select(catalog, Filters().resolve(catalog)))
    assert len(select(catalog, Filters(status="Deprecated").resolve(catalog))) == 415


def test_paging(catalog):
    filters = Filters(module="Funnels").resolve(catalog)
    cases = select(catalog, filters, "priority")
    first = page(cases, filters, 20, 0, "brief")
    assert (first.total_matches, first.returned, first.next_offset) == (len(cases), 20, 20)
    last = page(cases, filters, 20, len(cases) - 5, "brief")
    assert (last.returned, last.next_offset) == (5, None)
    assert page(cases, filters, 20, len(cases) + 10, "brief").returned == 0
    keys = [c.issue_key for c in cases]
    assert [t.issue_key for t in first.test_cases] == keys[:20]
    assert "steps" not in first.test_cases[0].model_dump() and page(cases, filters, 1, 0, "full").test_cases[0].steps


def test_sort_by_priority_puts_highest_first(catalog):
    ranks = [c.priority_rank for c in select(catalog, Filters(module="Reports").resolve(catalog), "priority")]
    assert ranks == sorted(ranks, reverse=True)


def test_counts_group_by(catalog):
    result = count(catalog, Filters(module="Funnels", include_deprecated=True).resolve(catalog), "priority")
    assert result.total == 278 and result.counts == {"Highest": 18, "High": 88, "Medium": 122, "Low": 50}


def test_coverage_matrix_lists_the_gaps(catalog):
    filters = Filters(module="Funnels", runnable_only=True).resolve(catalog)
    matrix = coverage_matrix(catalog, filters, "feature", "test_type", only_gaps=False)
    assert matrix.total == len(select(catalog, filters))
    assert sum(sum(row.values()) for row in matrix.counts.values()) == matrix.total
    zero = {f"{r} x {c}" for r, row in matrix.counts.items() for c, n in row.items() if n == 0}
    assert set(matrix.empty_cells) == zero
    assert coverage_matrix(catalog, filters, "feature", "test_type", only_gaps=True).counts == {}
    with pytest.raises(ToolError):
        coverage_matrix(catalog, filters, "module", "feature", False)


def test_duplicates(catalog):
    exact = duplicate_report(list(catalog.cases), "exact", 100, 0)
    assert exact.duplicate_rows == 60
    same = duplicate_report(list(catalog.cases), "same_idea", 5, 0)
    assert same.total_groups == sum(1 for group in catalog.ideas.values() if len(group) > 1)
    assert same.next_offset == 5 and all(len(g.issue_keys) > 1 for g in same.groups)
