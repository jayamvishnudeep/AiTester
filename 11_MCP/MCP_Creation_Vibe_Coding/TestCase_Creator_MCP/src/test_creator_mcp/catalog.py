"""Loads the test case CSV, derives each case's feature and test idea, and reloads when the file changes."""

from __future__ import annotations

import csv
import datetime as dt
import re
import threading
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .models import PRIORITY_RANK, RUNNABLE, STATUS_ORDER, TestCaseBrief, TestCaseFull

COLUMNS = (
    "Issue Type", "Issue Key", "Summary", "Description", "Priority", "Component", "Labels", "Test Type",
    "Preconditions", "Steps", "Expected Result", "Browser", "Device", "Status",
)
# Summaries use interchangeable verbs: "verify", "check" and "ensure" step drop-off are one test idea.
LEADING_VERB = re.compile(r"^(?:verify|check|validate|ensure|confirm|re-verify|regression-check|measure)\s+", re.I)
SUMMARY = re.compile(r"^\[(?P<module>[^\]]+)\]\s*(?P<type>[^:]+):\s*(?P<action>.+)$")
FEATURE = re.compile(r"\bthe (?P<feature>.+?) in the (?P<module>.+?) module\b")
KEY = re.compile(r"^(?P<prefix>[A-Z][A-Z0-9]*)-(?P<number>\d+)$")
STEP_NUMBER = re.compile(r"^\s*\d+[.)]\s*")
STEP_SPLIT = re.compile(r"\s*\|\s*")

Idea = tuple[str, str, str]  # module, test type, the check without its leading verb


class CatalogError(RuntimeError):
    """The test case file is missing or cannot be read."""


@dataclass(frozen=True)
class Case:
    issue_key: str
    number: int
    issue_type: str
    summary: str
    description: str
    priority: str
    module: str
    labels: tuple[str, ...]
    test_type: str
    preconditions: str
    steps: tuple[str, ...]
    expected_result: str
    browser: str
    device: str
    status: str
    feature: str
    action: str  # the summary after "[Module] Type: "
    idea: Idea
    source: str = "library"

    @property
    def priority_rank(self) -> int:
        return PRIORITY_RANK.get(self.priority, 0)

    @property
    def runnable(self) -> bool:
        return self.status in RUNNABLE

    @property
    def environment(self) -> str:
        return f"{self.browser} / {self.device}"

    def view(self, detail: str = "brief") -> TestCaseBrief | TestCaseFull:
        brief = {
            "issue_key": self.issue_key, "summary": self.summary, "module": self.module, "feature": self.feature,
            "priority": self.priority, "test_type": self.test_type, "status": self.status,
            "browser": self.browser, "device": self.device,
        }
        if detail != "full":
            return TestCaseBrief(**brief)
        return TestCaseFull(
            **brief, description=self.description, preconditions=self.preconditions, steps=list(self.steps),
            expected_result=self.expected_result, labels=list(self.labels), source=self.source,
        )

    def row(self) -> dict[str, str]:
        """The case as a CSV row in the library's own format."""
        return {
            "Issue Type": self.issue_type, "Issue Key": self.issue_key, "Summary": self.summary,
            "Description": self.description, "Priority": self.priority, "Component": self.module,
            "Labels": " ".join(self.labels), "Test Type": self.test_type, "Preconditions": self.preconditions,
            "Steps": " | ".join(f"{n}. {step}" for n, step in enumerate(self.steps, 1)),
            "Expected Result": self.expected_result, "Browser": self.browser, "Device": self.device,
            "Status": self.status,
        }


def parse_case(row: dict[str, str], source: str = "library") -> Case:
    def cell(name: str) -> str:
        return (row.get(name) or "").strip()

    key = cell("Issue Key").upper()
    match = KEY.match(key)
    if not match:
        raise ValueError(f"invalid issue key {key!r}")
    summary, module, test_type, description = cell("Summary"), cell("Component"), cell("Test Type"), cell("Description")
    if not (summary and module and test_type):
        raise ValueError(f"{key} needs a summary, a component and a test type")
    parsed = SUMMARY.match(summary)
    action = parsed.group("action").strip() if parsed else summary
    check = LEADING_VERB.sub("", action).strip()
    named = FEATURE.search(description)
    return Case(
        issue_key=key,
        number=int(match.group("number")),
        issue_type=cell("Issue Type") or "Test",
        summary=summary,
        description=description,
        priority=cell("Priority"),
        module=module,
        labels=tuple(cell("Labels").split()),
        test_type=test_type,
        preconditions=cell("Preconditions"),
        steps=tuple(STEP_NUMBER.sub("", step).strip() for step in STEP_SPLIT.split(cell("Steps")) if step.strip()),
        expected_result=cell("Expected Result"),
        browser=cell("Browser"),
        device=cell("Device"),
        status=cell("Status"),
        feature=named.group("feature").strip() if named else check,
        action=action,
        idea=(module, test_type, check.lower()),
        source=source,
    )


def ordered_counts(field: str, counter: Counter) -> dict[str, int]:
    """Priorities highest first, statuses in workflow order, anything else most common first."""
    if field == "priority":
        keys = sorted(counter, key=lambda p: (-PRIORITY_RANK.get(p, 0), p))
    elif field == "status":
        keys = sorted(counter, key=lambda s: (STATUS_ORDER.index(s) if s in STATUS_ORDER else len(STATUS_ORDER), s))
    else:
        keys = sorted(counter, key=lambda v: (-counter[v], v))
    return {key: counter[key] for key in keys}


class Catalog:
    """One snapshot of the library plus the cases created through the server."""

    def __init__(self, cases: list[Case], csv_path: Path, new_cases_path: Path, warnings: list[str]):
        self.cases = tuple(sorted(cases, key=lambda c: c.number))
        self.by_key = {case.issue_key: case for case in self.cases}
        self.csv_path = csv_path
        self.new_cases_path = new_cases_path
        self.warnings = tuple(warnings)
        self.loaded_at = dt.datetime.now().isoformat(timespec="seconds")

    @cached_property
    def key_prefix(self) -> str:
        return Counter(case.issue_key.rsplit("-", 1)[0] for case in self.cases).most_common(1)[0][0]

    def normalize_key(self, key: str) -> str:
        key = key.strip().upper()
        return f"{self.key_prefix}-{key}" if key.isdigit() else key

    def get(self, key: str) -> Case | None:
        return self.by_key.get(self.normalize_key(key))

    @cached_property
    def modules(self) -> list[str]:
        return sorted({case.module for case in self.cases})

    def features(self, module: str | None = None) -> list[str]:
        return sorted({case.feature for case in self.cases if module is None or case.module == module})

    def values(self, field: str) -> list[str]:
        return list(self.counts(field))

    def counts(self, field: str, cases: Iterable[Case] | None = None) -> dict[str, int]:
        return ordered_counts(field, Counter(getattr(case, field) for case in (self.cases if cases is None else cases)))

    @cached_property
    def ideas(self) -> dict[Idea, list[Case]]:
        groups: dict[Idea, list[Case]] = defaultdict(list)
        for case in self.cases:
            groups[case.idea].append(case)
        return dict(groups)

    def next_number(self) -> int:
        return max((case.number for case in self.cases), default=0) + 1

    @cached_property
    def search_index(self):
        from .search import SearchIndex  # built on first search, once per snapshot

        return SearchIndex(self.cases)


def load_catalog(csv_path: Path, new_cases_path: Path) -> Catalog:
    if not csv_path.is_file():
        raise CatalogError(f"Test case file not found: {csv_path}. Set TC_MCP_CSV to the CSV's path.")
    warnings: list[str] = []
    cases = _read(csv_path, "library", warnings)
    if not cases:
        raise CatalogError(f"No test cases in {csv_path}")
    known = {case.issue_key for case in cases}
    if new_cases_path.is_file():
        try:
            created = _read(new_cases_path, "created", warnings)
        except CatalogError as error:  # a broken file of new cases must not hide the library
            warnings.append(str(error))
            created = []
        for case in created:
            if case.issue_key in known:
                warnings.append(f"{new_cases_path.name}: {case.issue_key} is already in the library, skipped")
                continue
            known.add(case.issue_key)
            cases.append(case)
    return Catalog(cases, csv_path, new_cases_path, warnings)


def _read(path: Path, source: str, warnings: list[str]) -> list[Case]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise CatalogError(f"{path.name} is missing columns: {', '.join(missing)}")
        cases: list[Case] = []
        seen: set[str] = set()
        for number, row in enumerate(reader, 1):
            try:
                case = parse_case(row, source)
            except ValueError as error:
                warnings.append(f"{path.name} row {number}: {error}, skipped")
                continue
            if case.issue_key in seen:
                warnings.append(f"{path.name} row {number}: {case.issue_key} appears twice, skipped")
                continue
            seen.add(case.issue_key)
            cases.append(case)
    return cases


def _stamp(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None
    return stat.st_mtime_ns, stat.st_size


class CatalogStore:
    """Hands out the current snapshot and reloads it when either CSV changes on disk."""

    def __init__(self, csv_path: Path, new_cases_path: Path):
        self.csv_path = csv_path
        self.new_cases_path = new_cases_path
        self._lock = threading.Lock()
        self._catalog: Catalog | None = None
        self._stamp: tuple | None = None

    def get(self) -> Catalog:
        stamp = (_stamp(self.csv_path), _stamp(self.new_cases_path))
        if self._catalog is None or stamp != self._stamp:
            with self._lock:
                stamp = (_stamp(self.csv_path), _stamp(self.new_cases_path))
                if self._catalog is None or stamp != self._stamp:
                    self._catalog = load_catalog(self.csv_path, self.new_cases_path)
                    self._stamp = stamp
        return self._catalog
