"""Which test cases to run first: top lists, the smoke and regression suites, automation candidates."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from fastmcp.exceptions import ToolError

from .catalog import Case, Catalog
from .models import (
    PRIORITY_RANK, RUNNABLE, AutomationReport, ModuleAutomation, RankedTestCase, Suite, TopTestCases, resolve,
)
from .query import Filters

DEFAULT_WEIGHTS = {
    "priority": {"Highest": 100, "High": 70, "Medium": 40, "Low": 10, "Lowest": 0},
    "test_type": {"Security": 12, "Functional": 10, "Regression": 10, "API": 8, "Negative": 8, "Boundary": 6,
                  "Performance": 6, "Accessibility": 4, "UI/UX": 4},
}
AUTOMATABLE = ("Functional", "Regression", "API", "Negative", "Boundary")
MAX_OTHERS = 10  # environments listed per pick


@dataclass(frozen=True)
class Weights:
    priority: dict[str, int]
    test_type: dict[str, int]

    @classmethod
    def load(cls, path: Path | None) -> Weights:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) if path and path.is_file() else {}
        data = data or {}
        merged = {
            section: {**defaults, **{str(k): int(v) for k, v in (data.get(section) or {}).items()}}
            for section, defaults in DEFAULT_WEIGHTS.items()
        }
        return cls(merged["priority"], merged["test_type"])

    def score(self, case: Case) -> int:
        return self.priority.get(case.priority, 0) + self.test_type.get(case.test_type, 0)

    def describe(self) -> str:
        def points(table: dict[str, int]) -> str:
            return ", ".join(f"{name} {value}" for name, value in sorted(table.items(), key=lambda kv: -kv[1]) if value)

        return f"priority points ({points(self.priority)}) + test type points ({points(self.test_type)})"


@dataclass
class Pick:
    case: Case
    score: int
    others: list[Case] = field(default_factory=list)  # the same test idea in other environments


def eligible(case: Case, execution: str, include_drafts: bool) -> bool:
    if case.status == "Deprecated":
        return False
    if case.status == "Draft":
        return include_drafts and execution != "automated"
    if execution == "manual":
        return case.status == "Ready"
    if execution == "automated":
        return case.status == "Automated"
    return case.status in RUNNABLE


def rank(cases: list[Case], weights: Weights, one_per_idea: bool = True) -> list[Pick]:
    """Highest score first, ties to the lower key. One pick per test idea keeps near-copies out."""
    if one_per_idea:
        groups: dict[tuple, list[Case]] = defaultdict(list)
        for case in cases:
            groups[case.idea].append(case)
        picks = []
        for group in groups.values():
            group.sort(key=lambda c: (-weights.score(c), c.number))
            picks.append(Pick(group[0], weights.score(group[0]), group[1:]))
    else:
        picks = [Pick(case, weights.score(case)) for case in cases]
    picks.sort(key=lambda p: (-p.score, p.case.number))
    return picks


def why(pick: Pick) -> str:
    parts = [pick.case.priority, pick.case.test_type, pick.case.status]
    if pick.others:
        parts.append(f"best of {len(pick.others) + 1} eligible rows for this test idea")
    return " · ".join(parts)


def ranked(position: int, pick: Pick, detail: str, show_others: bool = True) -> RankedTestCase:
    others: list[str] = []
    if show_others:
        others = [f"{other.environment} ({other.issue_key})" for other in pick.others[:MAX_OTHERS]]
        if len(pick.others) > MAX_OTHERS:
            others.append(f"... and {len(pick.others) - MAX_OTHERS} more")
    return RankedTestCase(rank=position, score=pick.score, why=why(pick), test_case=pick.case.view(detail),
                          also_runnable_on=others)


def rules(weights: Weights, execution: str, include_drafts: bool = False, one_per_idea: bool = True) -> str:
    statuses = {"any": "Ready or Automated", "manual": "Ready", "automated": "Automated"}[execution]
    drafts = " (and Draft)" if include_drafts and execution != "automated" else ""
    text = f"Eligible: {statuses}{drafts}; Deprecated never. Score = {weights.describe()}; a tie goes to the lower key."
    if one_per_idea:
        text += " One row per test idea: the same check on other browsers and devices is listed under also_runnable_on."
    return text


def _min_priority(catalog: Catalog, value: str | None) -> str | None:
    return Filters(min_priority=value).resolve(catalog).min_priority if value else None


def _modules(catalog: Catalog, modules: list[str] | None) -> list[str]:
    if not modules:
        return list(catalog.modules)
    return list(dict.fromkeys(resolve(module, catalog.modules, "module") for module in modules))


def top_test_cases(catalog: Catalog, weights: Weights, module: str, limit: int, min_priority: str | None,
                   execution: str, one_per_idea: bool, include_drafts: bool, detail: str) -> TopTestCases:
    filters = Filters(module=module, min_priority=min_priority).resolve(catalog)
    pool = [case for case in catalog.cases if filters.match(case) and eligible(case, execution, include_drafts)]
    picks = rank(pool, weights, one_per_idea)[:limit]
    return TopTestCases(
        module=filters.module,
        execution=execution,
        eligible_rows=len(pool),
        eligible_test_ideas=len({case.idea for case in pool}),
        returned=len(picks),
        rules=rules(weights, execution, include_drafts, one_per_idea),
        picks=[ranked(n, pick, detail) for n, pick in enumerate(picks, 1)],
    )


def _suite(name: str, text: str, picks: list[Pick], notes: list[str], detail: str) -> Suite:
    picks = sorted(picks, key=lambda p: (-p.score, p.case.number))
    return Suite(
        name=name,
        rules=text,
        total=len(picks),
        per_module=dict(sorted(Counter(p.case.module for p in picks).items())),
        coverage={
            "browsers": sorted({p.case.browser for p in picks}),
            "devices": sorted({p.case.device for p in picks}),
            "test_types": sorted({p.case.test_type for p in picks}),
            "priorities": sorted({p.case.priority for p in picks}, key=lambda value: -PRIORITY_RANK.get(value, 0)),
        },
        notes=notes,
        test_cases=[ranked(n, pick, detail, show_others=False) for n, pick in enumerate(picks, 1)],
    )


def smoke_suite(catalog: Catalog, weights: Weights, modules: list[str] | None, per_module: int, max_total: int | None,
                min_priority: str | None, execution: str, detail: str) -> Suite:
    names = _modules(catalog, modules)
    low = _min_priority(catalog, min_priority)
    notes: list[str] = []
    best: dict[str, list[Pick]] = {}
    for name in names:
        pool = [c for c in catalog.cases if c.module == name and eligible(c, execution, False)
                and (low is None or c.priority_rank >= PRIORITY_RANK[low])]
        best[name] = rank(pool, weights)[:per_module]
        if len(best[name]) < per_module:
            notes.append(f"{name}: only {len(best[name])} eligible test ideas")
    # Take every module's first pick, then every module's second, so a max_total cut stays fair.
    layered: list[Pick] = []
    for position in range(per_module):
        layer = [best[name][position] for name in names if position < len(best[name])]
        layered.extend(sorted(layer, key=lambda p: (-p.score, p.case.number)))
    if max_total is not None and len(layered) > max_total:
        notes.append(f"max_total {max_total} left out {len(layered) - max_total} lower-ranked picks")
        layered = layered[:max_total]
    text = f"The top {per_module} test ideas of each module, best first. " + rules(weights, execution)
    return _suite("Smoke suite", text, layered, notes, detail)


def regression_suite(catalog: Catalog, weights: Weights, modules: list[str] | None, max_total: int, min_per_module: int,
                     max_per_module: int, min_priority: str | None, test_types: list[str] | None, cover_browsers: bool,
                     cover_devices: bool, execution: str, detail: str) -> Suite:
    names = _modules(catalog, modules)
    if min_per_module > max_per_module:
        raise ToolError(f"min_per_module ({min_per_module}) is above max_per_module ({max_per_module}).")
    if min_per_module * len(names) > max_total:
        raise ToolError(f"{len(names)} modules x min_per_module {min_per_module} = {min_per_module * len(names)} test cases, "
                        f"more than max_total {max_total}. Raise max_total or lower min_per_module.")
    types = {resolve(t, catalog.values("test_type"), "test_type") for t in test_types} if test_types else None
    low = _min_priority(catalog, min_priority)
    pool = [c for c in catalog.cases if c.module in names and eligible(c, execution, False)
            and (low is None or c.priority_rank >= PRIORITY_RANK[low]) and (types is None or c.test_type in types)]
    ranked_picks = rank(pool, weights)
    by_module: dict[str, list[Pick]] = defaultdict(list)
    for pick in ranked_picks:
        by_module[pick.case.module].append(pick)

    chosen: list[Pick] = []
    per: Counter = Counter()
    notes: list[str] = []
    for name in names:  # 1. the minimum of every module
        take = by_module[name][:min_per_module]
        if len(take) < min_per_module:
            notes.append(f"{name}: only {len(take)} eligible test ideas for min_per_module {min_per_module}")
        chosen.extend(take)
        per[name] += len(take)
    taken = {pick.case.idea for pick in chosen}
    for pick in ranked_picks:  # 2. the rest of the budget by score
        if len(chosen) >= max_total:
            break
        if pick.case.idea not in taken and per[pick.case.module] < max_per_module:
            chosen.append(pick)
            taken.add(pick.case.idea)
            per[pick.case.module] += 1

    guarded = [name for name, wanted in (("browser", cover_browsers), ("device", cover_devices)) if wanted]
    for dimension in guarded:  # 3. every browser and device at least once, when the limits allow it
        for value in catalog.values(dimension):
            if any(getattr(p.case, dimension) == value for p in chosen):
                continue
            candidates = sorted((c for c in pool if getattr(c, dimension) == value and c.idea not in taken),
                                key=lambda c: (-weights.score(c), c.number))
            placed = False
            for case in candidates:
                incoming = Pick(case, weights.score(case))
                if len(chosen) < max_total and per[case.module] < max_per_module:
                    chosen.append(incoming)
                else:
                    victim = _victim(chosen, per, case, min_per_module, max_per_module, guarded)
                    if victim is None:
                        continue
                    chosen.remove(victim)
                    per[victim.case.module] -= 1
                    taken.discard(victim.case.idea)
                    chosen.append(incoming)
                    notes.append(f"Swapped {victim.case.issue_key} for {case.issue_key} to cover {value}")
                taken.add(case.idea)
                per[case.module] += 1
                placed = True
                break
            if not placed:
                notes.append(f"No room for a {value} case within the limits" if candidates else f"No eligible case on {value}")

    parts = [f"Up to {max_total} test ideas, at least {min_per_module} and at most {max_per_module} per module"]
    if low:
        parts.append(f"priority {low} or above")
    if types:
        parts.append("test types " + ", ".join(sorted(types)))
    if guarded:
        parts.append("every " + " and ".join(guarded) + " covered when the limits allow")
    text = "; ".join(parts) + ". " + rules(weights, execution)
    return _suite("Regression suite", text, chosen, notes, detail)


def _victim(chosen: list[Pick], per: Counter, incoming: Case, min_per_module: int, max_per_module: int,
            guarded: list[str]) -> Pick | None:
    """The lowest-scoring pick that can leave without breaking a module limit or another covered value."""
    options = []
    for pick in chosen:
        same_module = pick.case.module == incoming.module
        if not same_module and (per[pick.case.module] <= min_per_module or per[incoming.module] >= max_per_module):
            continue
        if any(sum(1 for other in chosen if getattr(other.case, d) == getattr(pick.case, d)) == 1 for d in guarded):
            continue
        options.append(pick)
    return min(options, key=lambda p: (p.score, -p.case.number)) if options else None


def automation_candidates(catalog: Catalog, weights: Weights, module: str | None, min_priority: str | None,
                          limit: int, detail: str) -> AutomationReport:
    names = _modules(catalog, [module] if module else None)
    low = _min_priority(catalog, min_priority)
    automated_ideas = {case.idea for case in catalog.cases if case.status == "Automated"}
    pool = [c for c in catalog.cases if c.module in names and c.status == "Ready" and c.test_type in AUTOMATABLE
            and c.idea not in automated_ideas and (low is None or c.priority_rank >= PRIORITY_RANK[low])]
    picks = rank(pool, weights)[:limit]
    modules = []
    for name in names:
        runnable = [c for c in catalog.cases if c.module == name and c.runnable]
        automated = sum(1 for c in runnable if c.status == "Automated")
        share = round(100 * automated / len(runnable), 1) if runnable else 0.0
        modules.append(ModuleAutomation(module=name, runnable=len(runnable), automated=automated, automated_percent=share))
    text = (f"Ready {', '.join(AUTOMATABLE)} cases" + (f" at {low} priority or above" if low else "")
            + " whose test idea has no Automated row yet (a script that exists only needs another browser or device). "
            + f"Ranked by {weights.describe()}.")
    return AutomationReport(rules=text, modules=modules, candidates=[ranked(n, p, detail) for n, p in enumerate(picks, 1)])
