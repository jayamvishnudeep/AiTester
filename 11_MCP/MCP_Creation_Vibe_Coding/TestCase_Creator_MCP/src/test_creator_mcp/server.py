"""The Test Creator MCP server: the VWO test case library as MCP tools, resources and prompts.

Every tool description ends with an example input, so a person browsing the tools (for
example in MCP Inspector) can see how to call it.
"""

# No `from __future__ import annotations` here: the tools are defined inside build_server and
# their parameter types (such as the limit, which depends on settings) must exist when FastMCP
# reads them.

import json
from collections import Counter
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__, authoring
from .catalog import CatalogStore
from .models import (
    ALIASES, PRIORITY_ORDER, AutomationReport, CaseField, CasePage, CasesByKey, CountResult, CoverageMatrix,
    CreatedTestCases, Detail, DuplicateReport, Execution, ExportResult, FeatureInfo, FieldValues, ModuleInfo,
    Overview, SearchHit, SearchResult, SortBy, Suite, Template, TestCaseDraft, TopTestCases, ValidationReport,
    ValueCount, flexible_list,
)
from .query import Filters, count, coverage_matrix, duplicate_groups, duplicate_report, page, select
from .ranking import Weights, automation_candidates, regression_suite, smoke_suite, top_test_cases
from .settings import Settings, load_settings

READ = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)

INSTRUCTIONS = """\
Test Creator serves the VWO test case library: 5,000 Jira/Xray test cases with a key, summary, priority,
module, feature, test type, status, browser, device, 4 steps and an expected result.

- Learn the valid values first: get_catalog_overview or list_modules.
- "What should we run for <module>?": get_top_test_cases (ranked, one row per test idea, with reasons).
- Exact lookups: get_test_cases_by_priority, get_test_cases_by_module, filter_test_cases, get_test_cases.
  Counts: count_test_cases. Free text: search_test_cases.
- Lists are paged: pass next_offset back as offset. Ask for detail="full" only when you need the steps.
- Suites and hygiene: build_smoke_suite, build_regression_suite, get_coverage_matrix,
  find_duplicate_test_cases, get_automation_candidates.
- New cases: get_test_case_template, then validate_test_case, then create_test_case. New cases go to a
  separate CSV; the library file is never edited. Never invent issue keys.
"""

# Parameters that several tools share.
Module = Annotated[str | None, Field(description="Module (the CSV's Component). Case-insensitive; shortcuts like 'ab' or 'billing' work.",
                                     examples=["Funnels", "A/B Testing"])]
ModuleRequired = Annotated[str, Field(description="Module (the CSV's Component). Case-insensitive; shortcuts like 'ab' or 'billing' work.",
                                      examples=["Funnels", "A/B Testing"])]
Feature = Annotated[str | None, Field(description="Feature inside the module (see list_modules).", examples=["step drop-off"])]
Priority = Annotated[str | None, Field(description="Exact priority: Highest, High, Medium or Low (P1-P4 also work).", examples=["High"])]
MinPriority = Annotated[str | None, Field(description="Lowest priority to include: 'High' means High and Highest.", examples=["High"])]
MaxPriority = Annotated[str | None, Field(description="Highest priority to include: 'Medium' means Medium and Low.", examples=["Medium"])]
TestType = Annotated[str | None, Field(description="Functional, Negative, UI/UX, API, Boundary, Regression, Security, Accessibility or Performance.",
                                       examples=["Security"])]
Status = Annotated[str | None, Field(description="Ready, Automated, Draft or Deprecated.", examples=["Ready"])]
Browser = Annotated[str | None, Field(description="Browser; 'chrome' is enough for 'Chrome 148'.", examples=["Safari 19"])]
Device = Annotated[str | None, Field(description="desktop, mobile (Android), mobile (iOS) or tablet; 'android' and 'ios' work.",
                                     examples=["tablet"])]
LabelTag = Annotated[str | None, Field(description="One label tag.", examples=["regression"])]
IncludeDeprecated = Annotated[bool, Field(description="Include Deprecated cases (left out by default).")]
Offset = Annotated[int, Field(ge=0, description="Skip this many matches. Pass next_offset from the previous reply to get the next page.")]
DetailLevel = Annotated[Detail, Field(description="'brief': key, summary, module, feature, priority, test type, status, browser, device. "
                                                  "'full' adds description, preconditions, steps, expected result and labels.")]
Sort = Annotated[SortBy, Field(description="key, priority (highest first), module, test_type or status.")]
ExecutionMode = Annotated[Execution, Field(description="any = Ready or Automated; manual = Ready only; automated = Automated only.")]
Modules = Annotated[list[str] | None, flexible_list("modules"),
                    Field(description='Modules to include, as a list such as ["Funnels", "Reports"]; all modules when left out.',
                          examples=[["Funnels", "Reports"]])]


def build_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or load_settings()
    store = CatalogStore(settings.csv_path, settings.new_cases_path)
    store.get()  # fail at start-up, not on the first call, when the CSV is missing
    weights = Weights.load(settings.ranking_path)
    mcp = FastMCP("Test Creator", instructions=INSTRUCTIONS, version=__version__)
    Limit = Annotated[int, Field(ge=1, le=settings.max_limit, description=f"Most results to return (1-{settings.max_limit}).")]

    # --- Discovery ------------------------------------------------------------------------

    @mcp.tool(title="Catalog overview", annotations=READ, tags={"read"})
    def get_catalog_overview() -> Overview:
        """What the library holds: totals, runnable cases, test ideas, the next free key, and counts by
        priority, module, test type, status, browser and device. Call it first to learn the valid values.

        Example input (paste with 'Edit as JSON' on):
        {}

        Returns: totals plus a counts table per field.
        """
        catalog = store.get()
        library = sum(1 for case in catalog.cases if case.source == "library")
        return Overview(
            total_test_cases=len(catalog.cases),
            library_test_cases=library,
            created_test_cases=len(catalog.cases) - library,
            issue_keys=f"{catalog.cases[0].issue_key} to {catalog.cases[-1].issue_key}",
            next_issue_key=f"{catalog.key_prefix}-{catalog.next_number()}",
            runnable=sum(1 for case in catalog.cases if case.runnable),
            test_ideas=len(catalog.ideas),
            exact_duplicates=sum(len(group) - 1 for group in duplicate_groups(list(catalog.cases), "exact")),
            counts={field: catalog.counts(field) for field in ("priority", "module", "test_type", "status", "browser", "device")},
            data_file=catalog.csv_path.name,
            created_file=catalog.new_cases_path.name,
            loaded_at=catalog.loaded_at,
            warnings=list(catalog.warnings[:20]),
        )

    @mcp.tool(title="Modules and their features", annotations=READ, tags={"read"})
    def list_modules() -> list[ModuleInfo]:
        """Every module with its features, case counts, priority split and automated share.

        Example input (paste with 'Edit as JSON' on):
        {}

        Returns: one entry per module, e.g. Funnels with conversion rate, segment comparison, step drop-off
        and funnel builder.
        """
        catalog = store.get()
        result = []
        for name in catalog.modules:
            cases = [case for case in catalog.cases if case.module == name]
            runnable = [case for case in cases if case.runnable]
            automated = sum(1 for case in runnable if case.status == "Automated")
            features = Counter(case.feature for case in cases)
            result.append(ModuleInfo(
                name=name,
                test_cases=len(cases),
                runnable=len(runnable),
                automated_percent=round(100 * automated / len(runnable), 1) if runnable else 0.0,
                by_priority=catalog.counts("priority", cases),
                features=[FeatureInfo(name=feature, test_cases=n) for feature, n in features.most_common()],
            ))
        return result

    @mcp.tool(title="Allowed values of a field", annotations=READ, tags={"read"})
    def list_field_values(
        field: Annotated[CaseField, Field(description="priority, module, feature, test_type, status, browser or device.")],
    ) -> FieldValues:
        """The values a field takes in the library, with counts and the shortcuts the tools accept.

        Example input (paste with 'Edit as JSON' on):
        {"field": "test_type"}

        Returns: [{"value": "Functional", "count": 1516}, ...] and aliases such as {"a11y": "Accessibility"}.
        """
        counts = store.get().counts(field)
        return FieldValues(field=field, values=[ValueCount(value=v, count=n) for v, n in counts.items()],
                           aliases=ALIASES.get(field, {}))

    # --- Lookup and query -------------------------------------------------------------------

    @mcp.tool(title="Test cases by issue key", annotations=READ, tags={"read"})
    def get_test_cases(
        issue_keys: Annotated[list[str], flexible_list("issue_keys"),
                              Field(min_length=1, max_length=50,
                                    description='1-50 keys as a list, e.g. ["VWO-1001", "VWO-2453"]; "1001" means VWO-1001.',
                                    examples=[["VWO-1001", "VWO-2453"]])],
    ) -> CasesByKey:
        """Full test cases by key: description, preconditions, the 4 steps, expected result and labels.

        Example input (paste with 'Edit as JSON' on):
        {"issue_keys": ["VWO-1001", "VWO-2453"]}

        Returns: found (full test cases) and not_found (keys that do not exist).
        """
        catalog = store.get()
        found, missing = [], []
        for key in dict.fromkeys(issue_keys):
            case = catalog.get(key)
            if case:
                found.append(case.view("full"))
            else:
                missing.append(catalog.normalize_key(key))
        return CasesByKey(found=found, not_found=missing)

    @mcp.tool(title="Test cases by priority", annotations=READ, tags={"read"})
    def get_test_cases_by_priority(
        priority: Priority = None,
        min_priority: MinPriority = None,
        max_priority: MaxPriority = None,
        module: Module = None,
        include_deprecated: IncludeDeprecated = False,
        sort_by: Sort = "priority",
        limit: Limit = 20,
        offset: Offset = 0,
        detail: DetailLevel = "brief",
    ) -> CasePage:
        """Test cases of one priority, or of a priority range, optionally in one module.
        The scale is Low < Medium < High < Highest.

        Example input (paste with 'Edit as JSON' on):
        {"min_priority": "High", "module": "Reports", "limit": 10}

        Returns: a page of test cases with total_matches and next_offset for the next page.
        """
        if not (priority or min_priority or max_priority):
            raise ToolError("Give priority (e.g. 'High'), or min_priority and/or max_priority.")
        catalog = store.get()
        filters = Filters(module=module, priority=priority, min_priority=min_priority, max_priority=max_priority,
                          include_deprecated=include_deprecated).resolve(catalog)
        return page(select(catalog, filters, sort_by), filters, limit, offset, detail)

    @mcp.tool(title="Test cases by module", annotations=READ, tags={"read"})
    def get_test_cases_by_module(
        module: ModuleRequired,
        feature: Feature = None,
        min_priority: MinPriority = None,
        max_priority: MaxPriority = None,
        include_deprecated: IncludeDeprecated = False,
        sort_by: Sort = "priority",
        limit: Limit = 20,
        offset: Offset = 0,
        detail: DetailLevel = "brief",
    ) -> CasePage:
        """Test cases of one module, highest priority first, optionally narrowed to a feature or priority range.

        Example input (paste with 'Edit as JSON' on):
        {"module": "Funnels", "feature": "step drop-off", "limit": 10}

        Returns: a page of test cases with total_matches and next_offset for the next page.
        """
        catalog = store.get()
        filters = Filters(module=module, feature=feature, min_priority=min_priority, max_priority=max_priority,
                          include_deprecated=include_deprecated).resolve(catalog)
        return page(select(catalog, filters, sort_by), filters, limit, offset, detail)

    @mcp.tool(title="Filter test cases", annotations=READ, tags={"read"})
    def filter_test_cases(
        module: Module = None,
        feature: Feature = None,
        priority: Priority = None,
        min_priority: MinPriority = None,
        max_priority: MaxPriority = None,
        test_type: TestType = None,
        status: Status = None,
        browser: Browser = None,
        device: Device = None,
        label: LabelTag = None,
        include_deprecated: IncludeDeprecated = False,
        sort_by: Sort = "key",
        limit: Limit = 20,
        offset: Offset = 0,
        detail: DetailLevel = "brief",
    ) -> CasePage:
        """Test cases matching any combination of filters. Every filter is optional; leave out what you don't need.

        Example input (paste with 'Edit as JSON' on):
        {"module": "Funnels", "test_type": "Security", "min_priority": "High", "browser": "Safari 19", "limit": 5}

        Returns: a page of test cases with total_matches and next_offset for the next page.
        """
        catalog = store.get()
        filters = Filters(module=module, feature=feature, priority=priority, min_priority=min_priority,
                          max_priority=max_priority, test_type=test_type, status=status, browser=browser,
                          device=device, label=label, include_deprecated=include_deprecated).resolve(catalog)
        return page(select(catalog, filters, sort_by), filters, limit, offset, detail)

    @mcp.tool(title="Count test cases", annotations=READ, tags={"read"})
    def count_test_cases(
        group_by: Annotated[CaseField | None, Field(description="Split the count by this field.")] = None,
        module: Module = None,
        feature: Feature = None,
        priority: Priority = None,
        min_priority: MinPriority = None,
        max_priority: MaxPriority = None,
        test_type: TestType = None,
        status: Status = None,
        browser: Browser = None,
        device: Device = None,
        include_deprecated: IncludeDeprecated = False,
    ) -> CountResult:
        """How many test cases match, optionally split by a field. Cheap: returns numbers, not test cases.

        Example input (paste with 'Edit as JSON' on):
        {"module": "Funnels", "min_priority": "High", "group_by": "browser"}

        Returns: {"total": 104, "counts": {"Safari 19": 30, ...}} (numbers depend on the filters).
        """
        catalog = store.get()
        filters = Filters(module=module, feature=feature, priority=priority, min_priority=min_priority,
                          max_priority=max_priority, test_type=test_type, status=status, browser=browser,
                          device=device, include_deprecated=include_deprecated).resolve(catalog)
        return count(catalog, filters, group_by)

    @mcp.tool(title="Search test cases", annotations=READ, tags={"read"})
    def search_test_cases(
        query: Annotated[str, Field(min_length=1, description="Words to look for in the summary, feature, description, steps and expected result.",
                                    examples=["segment comparison"])],
        module: Module = None,
        test_type: TestType = None,
        min_priority: MinPriority = None,
        status: Status = None,
        include_deprecated: IncludeDeprecated = False,
        limit: Limit = 10,
        offset: Offset = 0,
        detail: DetailLevel = "brief",
    ) -> SearchResult:
        """Keyword search (BM25) across the test cases, best match first.

        Example input (paste with 'Edit as JSON' on):
        {"query": "keyboard access scheduled email", "module": "Reports", "limit": 5}

        Returns: hits with a score, the words that matched, and the test case.
        """
        catalog = store.get()
        filters = Filters(module=module, test_type=test_type, min_priority=min_priority, status=status,
                          include_deprecated=include_deprecated).resolve(catalog)
        hits = catalog.search_index.search(query, filters.match)
        chunk = hits[offset : offset + limit]
        end = offset + len(chunk)
        return SearchResult(
            query=query, total_matches=len(hits), returned=len(chunk), offset=offset,
            next_offset=end if end < len(hits) else None, filters=filters.applied(),
            hits=[SearchHit(score=score, matched_terms=terms, test_case=case.view(detail)) for case, score, terms in chunk],
        )

    # --- Planning ------------------------------------------------------------------------------

    @mcp.tool(title="Top test cases to run for a module", annotations=READ, tags={"read"})
    def get_top_test_cases(
        module: ModuleRequired,
        limit: Annotated[int, Field(ge=1, le=50, description="How many picks (1-50).")] = 10,
        min_priority: MinPriority = None,
        execution: ExecutionMode = "any",
        one_per_idea: Annotated[bool, Field(description="Collapse the same check on other browsers and devices into its best row.")] = True,
        include_drafts: Annotated[bool, Field(description="Let Draft cases compete too.")] = False,
        detail: DetailLevel = "brief",
    ) -> TopTestCases:
        """The top N test cases to execute for one module, ranked, with the reason for each pick.
        Score = priority points + test type points (see the rules in the reply). Ready and Automated
        cases only; Deprecated never.

        Example input (paste with 'Edit as JSON' on):
        {"module": "Funnels", "limit": 5, "min_priority": "High", "execution": "manual"}

        Returns: picks with rank, score, why, the test case, and the other environments it also runs on.
        """
        return top_test_cases(store.get(), weights, module, limit, min_priority, execution, one_per_idea, include_drafts, detail)

    @mcp.tool(title="Smoke suite", annotations=READ, tags={"plan"})
    def build_smoke_suite(
        modules: Modules = None,
        per_module: Annotated[int, Field(ge=1, le=10, description="Top test ideas per module (1-10).")] = 2,
        max_total: Annotated[int | None, Field(ge=1, le=500, description="Cap on the suite size; lower-ranked picks go first.")] = None,
        min_priority: MinPriority = None,
        execution: ExecutionMode = "any",
        detail: DetailLevel = "brief",
    ) -> Suite:
        """A smoke suite: the top test ideas of every module (or of the modules you name).

        Example input (paste with 'Edit as JSON' on):
        {"per_module": 2, "max_total": 30, "min_priority": "High"}

        Returns: the suite with per-module counts, the browsers, devices and test types it covers, and notes.
        """
        return smoke_suite(store.get(), weights, modules, per_module, max_total, min_priority, execution, detail)

    @mcp.tool(title="Regression suite", annotations=READ, tags={"plan"})
    def build_regression_suite(
        modules: Modules = None,
        max_total: Annotated[int, Field(ge=1, le=500, description="Most test cases in the suite.")] = 50,
        min_per_module: Annotated[int, Field(ge=0, le=50, description="At least this many per module.")] = 1,
        max_per_module: Annotated[int, Field(ge=1, le=100, description="At most this many per module.")] = 10,
        min_priority: MinPriority = None,
        test_types: Annotated[list[str] | None, flexible_list("test_types"),
                              Field(description='Only these test types, e.g. ["Functional", "Regression"].',
                                    examples=[["Functional", "Regression"]])] = None,
        cover_browsers: Annotated[bool, Field(description="Make sure every browser appears at least once.")] = True,
        cover_devices: Annotated[bool, Field(description="Make sure every device appears at least once.")] = True,
        execution: ExecutionMode = "any",
        detail: DetailLevel = "brief",
    ) -> Suite:
        """A regression suite within a budget: minimum and maximum per module, a total cap, and every browser and
        device covered when the limits allow. Notes say what did not fit.

        Example input (paste with 'Edit as JSON' on):
        {"modules": ["Funnels", "Reports", "Surveys"], "max_total": 30, "min_per_module": 5, "max_per_module": 12, "min_priority": "Medium"}

        Returns: the suite with per-module counts, coverage and notes.
        """
        return regression_suite(store.get(), weights, modules, max_total, min_per_module, max_per_module, min_priority,
                                test_types, cover_browsers, cover_devices, execution, detail)

    @mcp.tool(title="Coverage matrix and gaps", annotations=READ, tags={"plan"})
    def get_coverage_matrix(
        rows: Annotated[CaseField, Field(description="Field for the rows.")] = "module",
        columns: Annotated[CaseField, Field(description="Field for the columns.")] = "test_type",
        module: Module = None,
        min_priority: MinPriority = None,
        max_priority: MaxPriority = None,
        status: Status = None,
        runnable_only: Annotated[bool, Field(description="Count only Ready and Automated cases.")] = False,
        include_deprecated: IncludeDeprecated = False,
        only_gaps: Annotated[bool, Field(description="Return only the empty cells.")] = False,
    ) -> CoverageMatrix:
        """A grid of case counts for two fields, with every empty cell listed as a coverage gap.

        Example input (paste with 'Edit as JSON' on):
        {"rows": "feature", "columns": "test_type", "module": "Funnels", "runnable_only": true}

        Returns: counts[row][column] and empty_cells such as "step drop-off x Performance".
        """
        catalog = store.get()
        filters = Filters(module=module, min_priority=min_priority, max_priority=max_priority, status=status,
                          include_deprecated=include_deprecated, runnable_only=runnable_only).resolve(catalog)
        return coverage_matrix(catalog, filters, rows, columns, only_gaps)

    @mcp.tool(title="Duplicate test cases", annotations=READ, tags={"plan"})
    def find_duplicate_test_cases(
        mode: Annotated[Literal["exact", "same_idea"], Field(description="exact = identical apart from the key; same_idea = one check repeated on other browsers/devices.")] = "exact",
        module: Module = None,
        limit: Limit = 20,
        offset: Offset = 0,
    ) -> DuplicateReport:
        """Groups of duplicate test cases: exact copies, or the same test idea repeated across environments.

        Example input (paste with 'Edit as JSON' on):
        {"mode": "exact", "limit": 10}

        Returns: groups with their keys, environments and priorities, plus totals.
        """
        catalog = store.get()
        filters = Filters(module=module, include_deprecated=True).resolve(catalog)
        return duplicate_report([case for case in catalog.cases if filters.match(case)], mode, limit, offset)

    @mcp.tool(title="Automation candidates", annotations=READ, tags={"plan"})
    def get_automation_candidates(
        module: Module = None,
        min_priority: MinPriority = "High",
        limit: Annotated[int, Field(ge=1, le=50, description="How many candidates (1-50).")] = 20,
        detail: DetailLevel = "brief",
    ) -> AutomationReport:
        """Ready test cases worth automating next, plus the automated share of every module. Leaves out test ideas
        that already have an Automated row (the script only needs another browser or device).

        Example input (paste with 'Edit as JSON' on):
        {"module": "Funnels", "min_priority": "High", "limit": 5}

        Returns: per-module automation shares and ranked candidates.
        """
        return automation_candidates(store.get(), weights, module, min_priority, limit, detail)

    # --- Authoring -----------------------------------------------------------------------------

    @mcp.tool(title="Template for a new test case", annotations=READ, tags={"author"})
    def get_test_case_template(
        module: ModuleRequired,
        test_type: Annotated[str, Field(description="Test type of the new case.", examples=["Functional"])],
        feature: Feature = None,
    ) -> Template:
        """The house format for a new test case: patterns, rules, allowed values, the next free key, and up to
        3 similar existing cases as examples. Use it before writing a draft.

        Example input (paste with 'Edit as JSON' on):
        {"module": "Funnels", "test_type": "Functional", "feature": "funnel builder"}

        Returns: patterns for every field, rules, allowed values and example cases.
        """
        return authoring.template(store.get(), weights, module, test_type, feature)

    @mcp.tool(title="Validate a draft test case", annotations=READ, tags={"author"})
    def validate_test_case(test_case: TestCaseDraft) -> ValidationReport:
        """Checks a draft without saving it: allowed values, exactly 4 steps, the '[Module] Type: check' summary,
        the feature, and duplicates of existing cases.

        Example input (paste with 'Edit as JSON' on):
        {"test_case": {"summary": "[Funnels] Functional: verify adding a step in the funnel builder",
          "module": "Funnels", "test_type": "Functional", "priority": "High",
          "description": "As a QA engineer, verify the funnel builder in the Funnels module to make sure a new step can be added on desktop (Chrome 148).",
          "preconditions": "A VWO account with access to Funnels; at least one active project; Chrome 148 on desktop.",
          "steps": ["Log in to VWO and open the Funnels module.", "Navigate to the funnel builder screen.",
                    "Add a third step to an existing funnel and save.", "Observe the result on desktop using Chrome 148."],
          "expected_result": "The funnel saves with three steps and the drop-off chart shows all three.",
          "browser": "Chrome 148", "device": "desktop"}}

        Returns: valid, errors, warnings, similar existing keys and the normalized case.
        """
        return authoring.validate(store.get(), test_case)

    @mcp.tool(title="Create a test case", annotations=WRITE, tags={"write"})
    def create_test_case(test_case: TestCaseDraft) -> CreatedTestCases:
        """Validates a draft and saves it with the next free key (e.g. VWO-6001) to the new-cases CSV. The library
        file is never edited. Fails with the list of problems when the draft is not valid.

        Example input (paste with 'Edit as JSON' on): the same shape as validate_test_case.
        {"test_case": {"summary": "[Funnels] Functional: verify adding a step in the funnel builder", "module": "Funnels",
          "test_type": "Functional", "priority": "High", "description": "...", "preconditions": "...",
          "steps": ["...", "...", "...", "..."], "expected_result": "...", "browser": "Chrome 148", "device": "desktop"}}

        Returns: the created test case with its key, warnings, and the file it was saved to.
        """
        return authoring.create(store, test_case)

    @mcp.tool(title="Copy a test case to other browsers and devices", annotations=WRITE, tags={"write"})
    def create_environment_variants(
        issue_key: Annotated[str, Field(description="The case to copy.", examples=["VWO-3821"])],
        browsers: Annotated[list[str] | None, flexible_list("browsers"),
                            Field(description='Browsers for the copies, e.g. ["Safari 19", "Firefox 141"].',
                                  examples=[["Safari 19", "Firefox 141"]])] = None,
        devices: Annotated[list[str] | None, flexible_list("devices"),
                           Field(description='Devices for the copies, e.g. ["tablet"].', examples=[["tablet"]])] = None,
    ) -> CreatedTestCases:
        """Copies a test case to other browser and device pairs, rewriting the browser and device in its text, the way
        the library's own variants look. Pairs that already exist are skipped. Copies start as Draft.

        Example input (paste with 'Edit as JSON' on):
        {"issue_key": "VWO-3821", "browsers": ["Safari 19", "Firefox 141"], "devices": ["tablet"]}

        Returns: the created copies with their keys, and the pairs that were skipped.
        """
        return authoring.environment_variants(store, issue_key, browsers, devices)

    @mcp.tool(title="Export test cases", annotations=READ, tags={"author"})
    def export_test_cases(
        format: Annotated[Literal["csv", "markdown", "gherkin"], Field(description="csv = Jira/Xray import format; markdown; gherkin (Given/When/Then).")] = "csv",
        issue_keys: Annotated[list[str] | None, flexible_list("issue_keys"),
                              Field(description='Export these keys, e.g. ["VWO-3821", "VWO-1628"]; or use the filters.',
                                    examples=[["VWO-3821", "VWO-1628"]])] = None,
        module: Module = None,
        feature: Feature = None,
        min_priority: MinPriority = None,
        test_type: TestType = None,
        status: Status = None,
        include_deprecated: IncludeDeprecated = False,
        limit: Annotated[int, Field(ge=1, le=500, description="Most test cases to export (1-500).")] = 100,
    ) -> ExportResult:
        """Test cases as text: Jira/Xray CSV (the library's own columns), Markdown, or Gherkin feature files.

        Example input (paste with 'Edit as JSON' on):
        {"format": "gherkin", "module": "Funnels", "min_priority": "Highest", "status": "Ready", "limit": 3}

        Returns: the content as one string, the count, and whether the limit cut it short.
        """
        catalog = store.get()
        if issue_keys:
            cases, missing = [], []
            for key in dict.fromkeys(issue_keys):
                case = catalog.get(key)
                (cases if case else missing).append(case or catalog.normalize_key(key))
            if missing:
                raise ToolError(f"Unknown issue keys: {', '.join(missing)}.")
        else:
            filters = Filters(module=module, feature=feature, min_priority=min_priority, test_type=test_type,
                              status=status, include_deprecated=include_deprecated).resolve(catalog)
            cases = select(catalog, filters)
        return authoring.export(cases, format, limit)

    # --- Resources -----------------------------------------------------------------------------

    @mcp.resource("tc://schema", name="schema", title="Test case schema", mime_type="application/json",
                  description="The fields of a test case, their allowed values and formats.")
    def schema_resource() -> str:
        catalog = store.get()
        return json.dumps({
            "fields": {
                "issue_key": "e.g. VWO-1001", "summary": "[Module] Test type: <check>", "module": "the CSV's Component",
                "feature": "named in the description: 'the <feature> in the <module> module'",
                "priority": " < ".join(PRIORITY_ORDER), "test_type": "kind of test", "status": "workflow state",
                "browser": "one browser per case", "device": "one device per case",
                "steps": "exactly 4, in order", "expected_result": "one observable outcome",
            },
            "allowed_values": {field: catalog.values(field) for field in ("priority", "test_type", "status", "browser", "device")},
            "modules": catalog.modules,
        }, indent=1)

    @mcp.resource("tc://modules", name="modules", title="Modules and features", mime_type="application/json",
                  description="Every module and its features.")
    def modules_resource() -> str:
        catalog = store.get()
        return json.dumps({module: catalog.features(module) for module in catalog.modules}, indent=1)

    @mcp.resource("tc://test-cases/{issue_key}", name="test_case", title="One test case", mime_type="application/json",
                  description="One test case in full, e.g. tc://test-cases/VWO-1001.")
    def test_case_resource(issue_key: str) -> str:
        case = store.get().get(issue_key)
        if case is None:
            raise ResourceError(f"No test case {issue_key}.")
        return case.view("full").model_dump_json(indent=1)

    # --- Prompts -------------------------------------------------------------------------------

    @mcp.prompt(name="release_run_plan", title="Release run plan", tags={"read"},
                description="Plan which test cases to run for a module before a release.")
    def release_run_plan(module: str, count: int = 10) -> str:
        return (f"Plan a release test run for the {module} module with the Test Creator tools.\n"
                f"1. Call get_top_test_cases with module='{module}' and limit={count}.\n"
                "2. Show a table: rank, key, summary, priority, test type, status, browser / device.\n"
                "3. Under the table, give each pick's reason from its 'why', and the other environments it can run on.\n"
                "4. Add an empty Owner column for the team. Do not invent owners, dates or results.")

    @mcp.prompt(name="coverage_review", title="Coverage review", tags={"plan"},
                description="Summarise a module's test coverage, gaps and automation for a QA lead.")
    def coverage_review(module: str) -> str:
        return (f"Review the test coverage of the {module} module with the Test Creator tools.\n"
                f"1. get_coverage_matrix with rows='feature', columns='test_type', module='{module}', runnable_only=true.\n"
                f"2. get_automation_candidates with module='{module}'.\n"
                f"3. find_duplicate_test_cases with module='{module}' and mode='exact'.\n"
                "Then write a short review: the gaps (empty cells) that matter most, the automated share and the next "
                "5 cases to automate, and any duplicates to clean up. Quote issue keys; do not invent numbers.")

    @mcp.prompt(name="write_test_cases", title="Write new test cases", tags={"author"},
                description="Draft new test cases for a feature in the house format, check them, then save them.")
    def write_test_cases(module: str, feature: str, count: int = 3) -> str:
        return (f"Write {count} new test cases for the {feature} feature of the {module} module.\n"
                f"1. Call get_test_case_template with module='{module}', feature='{feature}' and the test type you need.\n"
                "2. Draft each case in that format, covering checks the existing examples do not.\n"
                "3. Run validate_test_case on every draft and fix every error.\n"
                "4. Show me the drafts and wait for my go-ahead before calling create_test_case.")

    if settings.profile == "readonly":
        mcp.disable(tags={"write"})
    return mcp


mcp = build_server()  # for `fastmcp run`, `fastmcp dev inspector` and the tc-mcp command
