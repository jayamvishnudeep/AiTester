"""The library's vocabulary (priority scale, aliases) and the shapes the tools return."""

from __future__ import annotations

import difflib
import json
import re
from collections.abc import Iterable
from typing import Any, Literal

from fastmcp.exceptions import ToolError
from pydantic import BaseModel, BeforeValidator, Field, model_validator

PRIORITY_ORDER = ("Lowest", "Low", "Medium", "High", "Highest")  # Jira's scale, lowest first
PRIORITY_RANK = {name: rank for rank, name in enumerate(PRIORITY_ORDER, 1)}
RUNNABLE = ("Ready", "Automated")
STATUS_ORDER = ("Ready", "Automated", "Draft", "Deprecated")

Detail = Literal["brief", "full"]
Execution = Literal["any", "manual", "automated"]
CaseField = Literal["priority", "module", "feature", "test_type", "status", "browser", "device"]
SortBy = Literal["key", "priority", "module", "test_type", "status"]

# Shortcuts people type, mapped to text that then resolves to a real value.
ALIASES: dict[str, dict[str, str]] = {
    "priority": {
        "p1": "Highest", "critical": "Highest", "blocker": "Highest", "urgent": "Highest",
        "p2": "High", "major": "High",
        "p3": "Medium", "normal": "Medium",
        "p4": "Low", "minor": "Low",
        "p5": "Lowest", "trivial": "Lowest",
    },
    "module": {
        "ab": "A/B Testing", "mvt": "Multivariate Testing", "users": "User Management",
        "flags": "Feature Rollout", "featureflags": "Feature Rollout", "forms": "Form Analytics",
    },
    "test_type": {"a11y": "Accessibility", "ux": "UI/UX"},
    "status": {"auto": "Automated", "obsolete": "Deprecated", "todo": "Draft"},
    "browser": {"ff": "Firefox"},
    "device": {"ipad": "tablet", "iphone": "mobile (iOS)", "pc": "desktop", "laptop": "desktop", "web": "desktop"},
}


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def label(field: str) -> str:
    return field.replace("_", " ")


def pasted_example(field: str) -> str:
    return (f"The whole example seems to be pasted into the '{field}' field. Type only that field's value there, "
            "or turn on 'Edit as JSON' above the form and paste the whole example.")


def flexible_list(field: str) -> BeforeValidator:
    """A list parameter that also takes what people type into a form field.

    Accepts the list itself, one value ("VWO-1001"), comma-separated text ("VWO-1001, VWO-2453"), and the
    whole example pasted into the field ({"issue_keys": [...]}), as long as it holds only this field.
    """

    def coerce(value: Any) -> Any:
        if isinstance(value, dict):
            if set(value) != {field}:
                raise ValueError(pasted_example(field))
            value = value[field]
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("{"):
                try:
                    return coerce(json.loads(text))
                except json.JSONDecodeError:
                    raise ValueError(pasted_example(field)) from None
            if text.startswith("["):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    text = text.strip("[]")
            return [part.strip().strip("'\"") for part in text.split(",") if part.strip().strip("'\"")]
        return value

    return BeforeValidator(coerce)


def resolve(value: str, choices: Iterable[str], field: str) -> str:
    """Match what a user typed to one real value, or explain which values exist."""
    if value.strip().startswith("{"):
        raise ToolError(pasted_example(field))
    choices = list(choices)
    by_norm = {norm(choice): choice for choice in choices}
    key = norm(value)
    if not key:
        raise ToolError(f"Empty {label(field)}. Valid values: {', '.join(choices)}.")
    if key in by_norm:
        return by_norm[key]
    alias = ALIASES.get(field, {}).get(key)
    if alias:
        target = norm(alias)
        if target in by_norm:  # "minor" -> Low, not Lowest
            return by_norm[target]
        hits = [choice for n, choice in by_norm.items() if n.startswith(target)]
        if len(hits) == 1:
            return hits[0]
    starts = [choice for n, choice in by_norm.items() if n.startswith(key)]
    if len(starts) == 1:
        return starts[0]
    inside = [choice for n, choice in by_norm.items() if key in n] if len(key) >= 3 else []
    if not starts and len(inside) == 1:
        return inside[0]
    if starts or inside:
        raise ToolError(f"'{value}' matches several {label(field)} values: {', '.join(starts or inside)}. Pick one.")
    close = [by_norm[n] for n in difflib.get_close_matches(key, list(by_norm), n=3, cutoff=0.5)]
    hint = f" Did you mean: {', '.join(close)}?" if close else ""
    raise ToolError(f"Unknown {label(field)} '{value}'.{hint} Valid values: {', '.join(choices)}.")


# --- What the tools return ----------------------------------------------------------------


class TestCaseBrief(BaseModel):
    issue_key: str
    summary: str
    module: str
    feature: str
    priority: str
    test_type: str
    status: str
    browser: str
    device: str


class TestCaseFull(TestCaseBrief):
    description: str
    preconditions: str
    steps: list[str]
    expected_result: str
    labels: list[str]
    source: str = Field(description="'library' for the CSV, 'created' for cases added with create_test_case")


TestCaseView = TestCaseFull | TestCaseBrief


class CasePage(BaseModel):
    total_matches: int
    returned: int
    offset: int
    next_offset: int | None = Field(description="Pass as offset to get the next page; null on the last page")
    filters: dict[str, Any]
    test_cases: list[TestCaseView]


class CasesByKey(BaseModel):
    found: list[TestCaseFull]
    not_found: list[str]


class ValueCount(BaseModel):
    value: str
    count: int


class FieldValues(BaseModel):
    field: str
    values: list[ValueCount]
    aliases: dict[str, str]


class FeatureInfo(BaseModel):
    name: str
    test_cases: int


class ModuleInfo(BaseModel):
    name: str
    test_cases: int
    runnable: int
    automated_percent: float
    by_priority: dict[str, int]
    features: list[FeatureInfo]


class Overview(BaseModel):
    total_test_cases: int
    library_test_cases: int
    created_test_cases: int
    issue_keys: str
    next_issue_key: str
    runnable: int
    test_ideas: int
    exact_duplicates: int
    counts: dict[str, dict[str, int]]
    data_file: str
    created_file: str
    loaded_at: str
    warnings: list[str]


class CountResult(BaseModel):
    total: int
    group_by: str | None
    counts: dict[str, int]
    filters: dict[str, Any]


class SearchHit(BaseModel):
    score: float
    matched_terms: list[str]
    test_case: TestCaseView


class SearchResult(BaseModel):
    query: str
    total_matches: int
    returned: int
    offset: int
    next_offset: int | None
    filters: dict[str, Any]
    hits: list[SearchHit]


class RankedTestCase(BaseModel):
    rank: int
    score: int
    why: str
    test_case: TestCaseView
    also_runnable_on: list[str] = Field(default_factory=list, description="Other rows of the same test idea: browser / device (key)")


class TopTestCases(BaseModel):
    module: str
    execution: str
    eligible_rows: int
    eligible_test_ideas: int
    returned: int
    rules: str
    picks: list[RankedTestCase]


class Suite(BaseModel):
    name: str
    rules: str
    total: int
    per_module: dict[str, int]
    coverage: dict[str, list[str]]
    notes: list[str]
    test_cases: list[RankedTestCase]


class CoverageMatrix(BaseModel):
    rows: str
    columns: str
    filters: dict[str, Any]
    total: int
    counts: dict[str, dict[str, int]]
    empty_cells: list[str]


class DuplicateGroup(BaseModel):
    test_idea: str
    module: str
    test_type: str
    summary: str
    issue_keys: list[str]
    environments: list[str]
    priorities: list[str]


class DuplicateReport(BaseModel):
    mode: str
    total_groups: int
    duplicate_rows: int = Field(description="Rows beyond the first one in each group")
    returned: int
    offset: int
    next_offset: int | None
    groups: list[DuplicateGroup]


class ModuleAutomation(BaseModel):
    module: str
    runnable: int
    automated: int
    automated_percent: float


class AutomationReport(BaseModel):
    rules: str
    modules: list[ModuleAutomation]
    candidates: list[RankedTestCase]


# --- Authoring ----------------------------------------------------------------------------


class TestCaseDraft(BaseModel):
    """A new test case in the library's format."""

    summary: str = Field(description="'[Module] Test type: what is checked', e.g. '[Funnels] Functional: verify step drop-off'. The prefix is added when missing")
    module: str = Field(description="One of the library's modules, e.g. 'Funnels'")
    test_type: str = Field(description="Functional, Negative, UI/UX, API, Boundary, Regression, Security, Accessibility or Performance")
    priority: str = Field("Medium", description="Highest, High, Medium or Low")
    description: str = Field(description="'As a QA engineer, <verb> the <feature> in the <module> module to make sure ...'")
    preconditions: str
    steps: list[str] = Field(description="Exactly 4 steps in order, without numbers")
    expected_result: str
    browser: str = Field(description="One of the library's browsers, e.g. 'Chrome 148'")
    device: str = Field(description="desktop, mobile (Android), mobile (iOS) or tablet")
    status: str = Field("Draft", description="Draft (default) or Ready; Automated only when a script exists")
    labels: list[str] | None = Field(None, description="Tags; generated from the module and test type when omitted")

    @model_validator(mode="before")
    @classmethod
    def unwrap_pasted_example(cls, data: Any) -> Any:
        """The whole example ({"test_case": {...}}) pasted into the test_case field works too."""
        if isinstance(data, dict) and set(data) == {"test_case"} and isinstance(data["test_case"], dict):
            return data["test_case"]
        return data


class Template(BaseModel):
    module: str
    feature: str | None
    test_type: str
    next_issue_key: str
    rules: list[str]
    patterns: dict[str, str]
    allowed_values: dict[str, list[str]]
    features_in_module: list[str]
    examples: list[TestCaseFull]


class ValidationReport(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]
    similar_test_cases: list[str]
    test_case: TestCaseFull | None = Field(description="The draft after normalizing; issue_key is 'NEW' until it is created")


class CreatedTestCases(BaseModel):
    created: list[TestCaseFull]
    skipped: list[str]
    warnings: list[str]
    file: str


class ExportResult(BaseModel):
    format: str
    count: int
    truncated: bool
    content: str
