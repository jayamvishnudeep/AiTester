"""Authoring: the house template, validation, new test cases, environment variants and exports.

The server never writes test case text itself; the client's model does. The server
supplies the format and examples, checks the draft, and appends it to a separate CSV.
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from fastmcp.exceptions import ToolError

from .catalog import COLUMNS, FEATURE, STEP_NUMBER, SUMMARY, Case, Catalog, CatalogStore, parse_case
from .models import (
    PRIORITY_RANK, CreatedTestCases, ExportResult, Template, TestCaseDraft, ValidationReport, norm, resolve,
)
from .ranking import Weights, rank

NEW_STATUSES = ("Draft", "Ready", "Automated")
MAX_VARIANTS = 16


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _priorities(catalog: Catalog) -> list[str]:
    return sorted(catalog.values("priority"), key=lambda p: -PRIORITY_RANK.get(p, 0))


# --- Template -------------------------------------------------------------------------------


def template(catalog: Catalog, weights: Weights, module: str, test_type: str, feature: str | None) -> Template:
    module = resolve(module, catalog.modules, "module")
    test_type = resolve(test_type, catalog.values("test_type"), "test_type")
    features = catalog.features(module)
    feature = resolve(feature, features, "feature") if feature else None

    def similar(match_feature: bool) -> list[Case]:
        return [c for c in catalog.cases if c.module == module and c.test_type == test_type and c.status != "Deprecated"
                and (not match_feature or c.feature == feature)]

    pool = similar(bool(feature)) or similar(False)
    examples = [pick.case.view("full") for pick in rank(pool, weights)[:3]]
    what = feature or "<feature>"
    return Template(
        module=module,
        feature=feature,
        test_type=test_type,
        next_issue_key=f"{catalog.key_prefix}-{catalog.next_number()}",
        rules=[
            "Exactly 4 steps, in order, without numbers.",
            "The summary starts with '[Module] Test type: ' and then names the check, e.g. 'verify step drop-off'.",
            "Name the feature in the description as 'the <feature> in the <module> module'; that is how tools find it.",
            "One browser and one device per case; add the others with create_environment_variants.",
            "New cases start as Draft unless you set Ready (or Automated, when a script exists).",
            "Check the draft with validate_test_case, then save it with create_test_case.",
        ],
        patterns={
            "summary": f"[{module}] {test_type}: <verb> {what}",
            "description": (f"As a QA engineer, <verb> the {what} in the {module} module to make sure it behaves "
                            f"correctly for {test_type.lower()} scenarios on <device> (<browser>)."),
            "preconditions": f"A VWO account with access to {module}; at least one active project; <browser> on <device>.",
            "steps": (f"1. Log in to VWO and open the {module} module. | 2. Navigate to the {what} screen. | "
                      f"3. <the action under test>. | 4. Observe the result on <device> using <browser>."),
            "expected_result": "One sentence that states the observable outcome.",
        },
        allowed_values={
            "priority": _priorities(catalog),
            "test_type": catalog.values("test_type"),
            "status": list(NEW_STATUSES),
            "browser": sorted(catalog.values("browser")),
            "device": sorted(catalog.values("device")),
        },
        features_in_module=features,
        examples=examples,
    )


# --- Validation -----------------------------------------------------------------------------


def check(catalog: Catalog, draft: TestCaseDraft) -> tuple[Case | None, list[str], list[str], list[str]]:
    """The normalized case (None when it has errors), errors, warnings and similar existing keys."""
    errors: list[str] = []
    warnings: list[str] = []

    def pick(value: str, choices: list[str], field: str) -> str | None:
        try:
            return resolve(value, choices, field)
        except ToolError as error:
            errors.append(str(error))
            return None

    module = pick(draft.module, catalog.modules, "module")
    test_type = pick(draft.test_type, catalog.values("test_type"), "test_type")
    priority = pick(draft.priority, _priorities(catalog), "priority")
    status = pick(draft.status, list(NEW_STATUSES), "status")
    browser = pick(draft.browser, catalog.values("browser"), "browser")
    device = pick(draft.device, catalog.values("device"), "device")

    steps = [STEP_NUMBER.sub("", step).strip() for step in draft.steps if step and step.strip()]
    if len(steps) != 4:
        errors.append(f"Write exactly 4 steps; this draft has {len(steps)}.")
    for name in ("description", "preconditions", "expected_result"):
        if not getattr(draft, name).strip():
            errors.append(f"The {name.replace('_', ' ')} is empty.")

    summary = " ".join(draft.summary.split())
    if not summary:
        errors.append("The summary is empty.")
    elif module and test_type:
        parsed = SUMMARY.match(summary)
        if not parsed:
            summary = f"[{module}] {test_type}: {summary}"
            warnings.append(f"Added the '[{module}] {test_type}: ' prefix to the summary.")
        else:
            if norm(parsed["module"]) != norm(module):
                errors.append(f"The summary names module '{parsed['module']}', but the module is '{module}'.")
            if norm(parsed["type"]) != norm(test_type):
                errors.append(f"The summary names test type '{parsed['type']}', but the test type is '{test_type}'.")
            summary = f"[{module}] {test_type}: {parsed['action'].strip()}"
    if errors:
        return None, errors, warnings, []

    labels = draft.labels or [slug(module), slug(test_type), "regression"]
    case = parse_case({
        "Issue Type": "Test", "Issue Key": "NEW-0", "Summary": summary, "Description": draft.description.strip(),
        "Priority": priority, "Component": module, "Labels": " ".join(labels), "Test Type": test_type,
        "Preconditions": draft.preconditions.strip(), "Steps": " | ".join(steps),
        "Expected Result": draft.expected_result.strip(), "Browser": browser, "Device": device, "Status": status,
    }, source="created")

    named = FEATURE.search(case.description)
    if not named:
        warnings.append("Name the feature in the description as 'the <feature> in the <module> module' so it can be found by feature.")
    elif norm(named["module"]) != norm(module):
        warnings.append(f"The description names the {named['module']} module, but the module is {module}.")
    elif case.feature not in catalog.features(module):
        warnings.append(f"'{case.feature}' is a new feature for {module}. Existing ones: {', '.join(catalog.features(module))}.")

    same_idea = [c for c in catalog.ideas.get(case.idea, []) if c.status != "Deprecated"]
    exact = [c for c in same_idea if c.browser == case.browser and c.device == case.device]
    if exact:
        errors.append(f"Duplicate of {exact[0].issue_key}: the same check on {case.environment} already exists.")
        return None, errors, warnings, [c.issue_key for c in same_idea[:10]]
    if same_idea:
        warnings.append(f"The same check exists for other environments ({len(same_idea)} rows, e.g. {same_idea[0].issue_key}). "
                        "If you only need another browser or device, use create_environment_variants.")
    return case, errors, warnings, [c.issue_key for c in same_idea[:10]]


def validate(catalog: Catalog, draft: TestCaseDraft) -> ValidationReport:
    case, errors, warnings, similar = check(catalog, draft)
    view = case.view("full").model_copy(update={"issue_key": "NEW"}) if case else None
    return ValidationReport(valid=not errors, errors=errors, warnings=warnings, similar_test_cases=similar, test_case=view)


# --- Writing --------------------------------------------------------------------------------


if os.name == "nt":
    import msvcrt

    def _lock(handle) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

    def _unlock(handle) -> None:
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _lock(handle) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(handle) -> None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def file_lock(path: Path, timeout: float = 10.0) -> Iterator[None]:
    """One writer at a time across processes (say a Claude Code server and an HTTP server)."""
    digest = hashlib.sha1(str(path.resolve()).lower().encode()).hexdigest()[:12]
    lock_path = Path(tempfile.gettempdir()) / f"tc-mcp-{digest}.lock"
    with open(lock_path, "a+b") as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                _lock(handle)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise ToolError("Another process is adding test cases. Try again in a moment.") from None
                time.sleep(0.05)
        try:
            yield
        finally:
            _unlock(handle)


def append(store: CatalogStore, cases: list[Case]) -> list[Case]:
    """Give the cases the next free keys and append them to the new-cases file."""
    path = store.new_cases_path
    with file_lock(path):
        catalog = store.get()  # re-read: another process may have just appended
        for case in cases:  # checked again under the lock, in case someone saved the same case a moment ago
            for other in catalog.ideas.get(case.idea, []):
                if other.status != "Deprecated" and (other.browser, other.device) == (case.browser, case.device):
                    raise ToolError(f"'{case.summary}' on {case.environment} was just saved as {other.issue_key}.")
        first = catalog.next_number()
        numbered = [replace(case, issue_key=f"{catalog.key_prefix}-{first + n}", number=first + n, source="created")
                    for n, case in enumerate(cases)]
        path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not path.exists() or path.stat().st_size == 0
        if not fresh:
            with path.open("rb") as handle:
                handle.seek(-1, os.SEEK_END)
                needs_newline = handle.read(1) not in (b"\n", b"\r")
        with path.open("a", encoding="utf-8", newline="") as handle:
            if not fresh and needs_newline:
                handle.write("\n")
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, lineterminator="\n")
            if fresh:
                writer.writeheader()
            for case in numbered:
                writer.writerow(case.row())
    return numbered


def create(store: CatalogStore, draft: TestCaseDraft) -> CreatedTestCases:
    case, errors, warnings, _ = check(store.get(), draft)
    if errors:
        raise ToolError("The test case was not created:\n- " + "\n- ".join(errors))
    [saved] = append(store, [case])
    return CreatedTestCases(created=[saved.view("full")], skipped=[], warnings=warnings, file=store.new_cases_path.name)


def environment_variants(store: CatalogStore, issue_key: str, browsers: list[str] | None,
                         devices: list[str] | None) -> CreatedTestCases:
    catalog = store.get()
    source = catalog.get(issue_key)
    if source is None:
        raise ToolError(f"No test case {catalog.normalize_key(issue_key)}.")
    if not (browsers or devices):
        raise ToolError("Give browsers, devices or both, e.g. browsers=['Safari 19', 'Edge 148'].")
    targets_b = [resolve(b, catalog.values("browser"), "browser") for b in browsers] if browsers else [source.browser]
    targets_d = [resolve(d, catalog.values("device"), "device") for d in devices] if devices else [source.device]
    combos = [(b, d) for b in dict.fromkeys(targets_b) for d in dict.fromkeys(targets_d) if (b, d) != (source.browser, source.device)]
    if not combos:
        raise ToolError(f"{source.issue_key} already runs on {source.environment}; name a different browser or device.")
    if len(combos) > MAX_VARIANTS:
        raise ToolError(f"That makes {len(combos)} variants; the most at once is {MAX_VARIANTS}.")

    existing = {(c.browser, c.device): c for c in catalog.ideas.get(source.idea, []) if c.status != "Deprecated"}
    mentions = any(source.browser in text or source.device in text
                   for text in (source.description, source.preconditions, *source.steps))
    new_cases, skipped = [], []
    for browser, device in combos:
        if (browser, device) in existing:
            skipped.append(f"{browser} / {device}: already exists as {existing[(browser, device)].issue_key}")
            continue

        def swap(text: str) -> str:
            return text.replace(source.browser, browser).replace(source.device, device)

        new_cases.append(replace(source, browser=browser, device=device, description=swap(source.description),
                                 preconditions=swap(source.preconditions), steps=tuple(swap(s) for s in source.steps),
                                 status="Draft"))
    warnings = [] if mentions or not new_cases else [
        f"{source.issue_key}'s text does not mention its browser or device, so only those two fields changed."]
    saved = append(store, new_cases) if new_cases else []
    return CreatedTestCases(created=[c.view("full") for c in saved], skipped=skipped, warnings=warnings,
                            file=store.new_cases_path.name)


# --- Export ---------------------------------------------------------------------------------


def export(cases: list[Case], fmt: str, limit: int) -> ExportResult:
    chosen = cases[:limit]
    if fmt == "csv":
        content = _csv(chosen)
    elif fmt == "markdown":
        content = _markdown(chosen)
    else:
        content = _gherkin(chosen)
    return ExportResult(format=fmt, count=len(chosen), truncated=len(cases) > limit, content=content)


def _csv(cases: list[Case]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for case in cases:
        writer.writerow(case.row())
    return buffer.getvalue()


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _markdown(cases: list[Case]) -> str:
    lines = [f"# Test cases ({len(cases)})", ""]
    for case in cases:
        lines += [
            f"## {case.issue_key} · {case.summary}", "",
            "| Priority | Module | Feature | Test type | Status | Browser | Device |",
            "|---|---|---|---|---|---|---|",
            "| " + " | ".join(_cell(v) for v in (case.priority, case.module, case.feature, case.test_type, case.status,
                                                   case.browser, case.device)) + " |",
            "",
            f"**Preconditions:** {case.preconditions}", "",
            *[f"{n}. {step}" for n, step in enumerate(case.steps, 1)], "",
            f"**Expected result:** {case.expected_result}", "",
        ]
    return "\n".join(lines)


def _gherkin(cases: list[Case]) -> str:
    lines: list[str] = []
    for module in sorted({case.module for case in cases}):
        lines += [f"Feature: {module}", ""]
        for case in (c for c in cases if c.module == module):
            tags = f"@{case.issue_key} @{slug(case.priority)} @{slug(case.test_type)} @{slug(case.status)}"
            lines += [f"  {tags}", f"  Scenario: {case.issue_key} {case.summary} on {case.environment}",
                      f"    Given {case.preconditions}"]
            for n, step in enumerate(case.steps):
                lines.append(f"    {'When' if n == 0 else 'And'} {step}")
            lines += [f"    Then {case.expected_result}", ""]
    return "\n".join(lines)
