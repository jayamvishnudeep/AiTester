"""Filters, priority ranges, paging, counts, the coverage matrix and duplicate groups."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from typing import Any

from fastmcp.exceptions import ToolError

from .catalog import Case, Catalog
from .models import (
    PRIORITY_ORDER, PRIORITY_RANK, STATUS_ORDER, CasePage, CountResult, CoverageMatrix, DuplicateGroup,
    DuplicateReport, resolve,
)


@dataclass(frozen=True)
class Filters:
    module: str | None = None
    feature: str | None = None
    priority: str | None = None
    min_priority: str | None = None
    max_priority: str | None = None
    test_type: str | None = None
    status: str | None = None
    browser: str | None = None
    device: str | None = None
    label: str | None = None
    include_deprecated: bool = False
    runnable_only: bool = False

    def resolve(self, catalog: Catalog) -> Filters:
        """The same filters with every value matched to a real one; unknown values raise ToolError."""

        def pick(value: str | None, field: str) -> str | None:
            return resolve(value, catalog.values(field), field) if value else None

        def scale(value: str | None, field: str) -> str | None:
            return resolve(value, PRIORITY_ORDER, field) if value else None

        module = pick(self.module, "module")
        feature = resolve(self.feature, catalog.features(module), "feature") if self.feature else None
        low, high = scale(self.min_priority, "min_priority"), scale(self.max_priority, "max_priority")
        if low and high and PRIORITY_RANK[low] > PRIORITY_RANK[high]:
            raise ToolError(f"min_priority {low} is above max_priority {high}. The scale is {' < '.join(PRIORITY_ORDER)}.")
        status = pick(self.status, "status")
        return replace(
            self,
            module=module,
            feature=feature,
            priority=scale(self.priority, "priority"),
            min_priority=low,
            max_priority=high,
            test_type=pick(self.test_type, "test_type"),
            status=status,
            browser=pick(self.browser, "browser"),
            device=pick(self.device, "device"),
            label=self.label.strip().lower() if self.label and self.label.strip() else None,
            include_deprecated=self.include_deprecated or status == "Deprecated",
        )

    def match(self, case: Case) -> bool:
        if self.module and case.module != self.module:
            return False
        if self.feature and case.feature != self.feature:
            return False
        if self.priority and case.priority != self.priority:
            return False
        if self.min_priority and case.priority_rank < PRIORITY_RANK[self.min_priority]:
            return False
        if self.max_priority and case.priority_rank > PRIORITY_RANK[self.max_priority]:
            return False
        if self.test_type and case.test_type != self.test_type:
            return False
        if self.status and case.status != self.status:
            return False
        if not self.include_deprecated and case.status == "Deprecated":
            return False
        if self.runnable_only and not case.runnable:
            return False
        if self.browser and case.browser != self.browser:
            return False
        if self.device and case.device != self.device:
            return False
        if self.label and self.label not in (tag.lower() for tag in case.labels):
            return False
        return True

    def applied(self) -> dict[str, Any]:
        return {name: value for name, value in asdict(self).items() if value not in (None, False)}


SORT_KEYS = {
    "key": lambda c: (c.number,),
    "priority": lambda c: (-c.priority_rank, c.number),
    "module": lambda c: (c.module, -c.priority_rank, c.number),
    "test_type": lambda c: (c.test_type, -c.priority_rank, c.number),
    "status": lambda c: (STATUS_ORDER.index(c.status) if c.status in STATUS_ORDER else 9, c.number),
}


def select(catalog: Catalog, filters: Filters, sort_by: str = "key") -> list[Case]:
    return sorted((case for case in catalog.cases if filters.match(case)), key=SORT_KEYS[sort_by])


def page(cases: list[Case], filters: Filters, limit: int, offset: int, detail: str) -> CasePage:
    chunk = cases[offset : offset + limit]
    end = offset + len(chunk)
    return CasePage(
        total_matches=len(cases),
        returned=len(chunk),
        offset=offset,
        next_offset=end if end < len(cases) else None,
        filters=filters.applied(),
        test_cases=[case.view(detail) for case in chunk],
    )


def count(catalog: Catalog, filters: Filters, group_by: str | None) -> CountResult:
    cases = select(catalog, filters)
    return CountResult(
        total=len(cases),
        group_by=group_by,
        counts=catalog.counts(group_by, cases) if group_by else {},
        filters=filters.applied(),
    )


def _dimension(catalog: Catalog, field: str, filters: Filters) -> list[str]:
    fixed = getattr(filters, field, None)
    if field == "priority" and filters.priority:
        fixed = filters.priority
    if fixed:
        return [fixed]
    if field == "feature":
        return catalog.features(filters.module)
    values = catalog.values(field)
    if field == "status" and not filters.include_deprecated:
        values = [v for v in values if v != "Deprecated"]
    if field == "priority":
        low = PRIORITY_RANK.get(filters.min_priority or "", 0)
        high = PRIORITY_RANK.get(filters.max_priority or "", 99)
        values = [v for v in values if low <= PRIORITY_RANK.get(v, 0) <= high]
    return values


def coverage_matrix(catalog: Catalog, filters: Filters, rows: str, columns: str, only_gaps: bool) -> CoverageMatrix:
    if rows == columns:
        raise ToolError("rows and columns must be two different fields.")
    if {rows, columns} == {"module", "feature"}:
        raise ToolError("Every feature belongs to one module, so module x feature is not a useful grid. "
                        "Filter by module and pair feature with test_type, priority, browser or device.")
    cases = select(catalog, filters)
    row_values, column_values = _dimension(catalog, rows, filters), _dimension(catalog, columns, filters)
    grid = {r: {c: 0 for c in column_values} for r in row_values}
    for case in cases:
        r, c = getattr(case, rows), getattr(case, columns)
        if r in grid and c in grid[r]:
            grid[r][c] += 1
    empty = [f"{r} x {c}" for r in row_values for c in column_values if grid[r][c] == 0]
    return CoverageMatrix(
        rows=rows, columns=columns, filters=filters.applied(), total=len(cases),
        counts={} if only_gaps else grid, empty_cells=empty,
    )


def duplicate_groups(cases: list[Case], mode: str) -> list[list[Case]]:
    """Exact: identical in every field but the key. same_idea: one check repeated across environments."""

    def exact(case: Case) -> tuple:
        return (case.summary, case.description, case.priority, case.module, case.labels, case.test_type,
                case.preconditions, case.steps, case.expected_result, case.browser, case.device, case.status)

    keyer = exact if mode == "exact" else (lambda case: case.idea)
    groups: dict[tuple, list[Case]] = defaultdict(list)
    for case in cases:
        groups[keyer(case)].append(case)
    return sorted((group for group in groups.values() if len(group) > 1), key=lambda group: group[0].number)


def duplicate_report(cases: list[Case], mode: str, limit: int, offset: int) -> DuplicateReport:
    groups = duplicate_groups(cases, mode)
    chunk = groups[offset : offset + limit]
    end = offset + len(chunk)
    return DuplicateReport(
        mode=mode,
        total_groups=len(groups),
        duplicate_rows=sum(len(group) - 1 for group in groups),
        returned=len(chunk),
        offset=offset,
        next_offset=end if end < len(groups) else None,
        groups=[
            DuplicateGroup(
                test_idea=group[0].idea[2],
                module=group[0].module,
                test_type=group[0].test_type,
                summary=group[0].summary,
                issue_keys=[case.issue_key for case in group],
                environments=sorted({case.environment for case in group}),
                priorities=sorted({case.priority for case in group}, key=lambda p: -PRIORITY_RANK.get(p, 0)),
            )
            for group in chunk
        ],
    )
