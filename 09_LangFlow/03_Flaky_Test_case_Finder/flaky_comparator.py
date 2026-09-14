"""Flaky Test Comparator - a Langflow custom component.

Reads two Playwright JSON reports from the same suite and works out which tests
did not agree with themselves. A test is flaky when its outcome is not the same
in both runs, or when Playwright already had to retry it inside a single run.

A test that fails in both runs is not flaky. It is broken, and the report keeps
the two apart so nobody wastes a morning re-running a genuine defect.

The comparison is plain Python, so the counts are exact and repeatable. The
language model downstream only writes the summary - it never does the counting.
"""

import json
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, MultilineInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

# Playwright's per-test status -> the word this component uses for it.
_OUTCOME = {
    "expected": "passed",
    "unexpected": "failed",
    "flaky": "passed on retry",
    "skipped": "skipped",
}


class FlakyTestComparator(Component):
    display_name = "Flaky Test Comparator"
    description = "Compares two Playwright JSON reports and names the flaky tests."
    documentation = "https://playwright.dev/docs/test-reporters#json-reporter"
    icon = "activity"
    name = "FlakyTestComparator"

    inputs = [
        MessageTextInput(
            name="results_dir",
            display_name="Results folder",
            info=(
                "Folder holding the two Playwright JSON reports. Anything that is not a real "
                "folder is ignored, so the Playground can send a greeting without breaking the run."
            ),
            value="",
            tool_mode=True,
        ),
        MessageTextInput(
            name="fallback_dir",
            display_name="Default results folder",
            info="Used whenever the folder above is empty or does not exist.",
            value="",
        ),
        MessageTextInput(
            name="run1_file",
            display_name="Run 1 file name",
            value="result1.json",
            advanced=True,
        ),
        MessageTextInput(
            name="run2_file",
            display_name="Run 2 file name",
            value="result2.json",
            advanced=True,
        ),
        MultilineInput(
            name="run1_json",
            display_name="Run 1 JSON",
            info="Paste a report here to use it instead of reading run 1 from disk.",
            value="",
            advanced=True,
        ),
        MultilineInput(
            name="run2_json",
            display_name="Run 2 JSON",
            info="Paste a report here to use it instead of reading run 2 from disk.",
            value="",
            advanced=True,
        ),
        IntInput(
            name="max_listed",
            display_name="Max tests listed",
            info="Caps how many tests are named under each heading.",
            value=15,
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Comparison", name="report", method="build_report"),
        Output(display_name="Findings", name="findings", method="build_findings"),
    ]

    # ------------------------------------------------------------- reading

    def _folder(self) -> str:
        """The first of the two folder fields that actually exists on disk.

        The Playground sends whatever the user typed into this component, so a
        greeting must not be mistaken for a path. Anything that is not a real
        folder falls through to the default.
        """
        for candidate in (self.results_dir, self.fallback_dir):
            cleaned = (candidate or "").strip().strip('"').strip("'")
            if cleaned and Path(cleaned).is_dir():
                return cleaned
        return ""

    def _load(self, pasted: str, file_name: str, label: str) -> dict:
        """Take the pasted report if there is one, otherwise read it from disk."""
        pasted = (pasted or "").strip()
        if pasted:
            try:
                return json.loads(pasted)
            except json.JSONDecodeError as exc:
                msg = f"{label}: the pasted JSON could not be parsed - {exc}"
                raise ValueError(msg) from exc

        folder = self._folder()
        if not folder:
            msg = (
                f"{label}: no readable results folder. Set 'Default results folder' on the "
                "Flaky Test Comparator to the folder holding result1.json and result2.json."
            )
            raise ValueError(msg)

        path = Path(folder) / (file_name or "").strip()
        if not path.is_file():
            msg = f"{label}: no file at {path}"
            raise ValueError(msg)

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"{label}: {path.name} is not valid JSON - {exc}"
            raise ValueError(msg) from exc

    # ------------------------------------------------------------- parsing

    @staticmethod
    def _first_error(test: dict) -> str:
        """The first line of the first error, which is enough to tell flake apart."""
        for result in test.get("results") or []:
            for err in result.get("errors") or []:
                message = (err.get("message") or "").strip()
                if message:
                    # strip the ANSI colour codes Playwright writes into the message
                    cleaned, skipping = [], False
                    for ch in message:
                        if ch == "\x1b":
                            skipping = True
                        elif skipping:
                            if ch.isalpha():
                                skipping = False
                        else:
                            cleaned.append(ch)
                    return "".join(cleaned).splitlines()[0].strip()
        return ""

    def _walk(self, suite: dict, trail: list, found: dict) -> None:
        """Collect every test in a suite tree. Describe blocks nest, so recurse."""
        title = (suite.get("title") or "").strip()
        file_name = suite.get("file") or ""
        # the top suite repeats the file name as its title; do not say it twice
        crumbs = trail if not title or title == file_name else [*trail, title]

        for spec in suite.get("specs") or []:
            spec_file = spec.get("file") or file_name
            spec_title = spec.get("title") or ""
            for test in spec.get("tests") or []:
                project = test.get("projectName") or test.get("projectId") or ""
                spec_id = spec.get("id") or ""
                key = f"{spec_id}|{project}" if spec_id else f"{spec_file}|{'>'.join([*crumbs, spec_title])}|{project}"
                attempts = [r.get("status") or "" for r in test.get("results") or []]
                found[key] = {
                    "file": spec_file,
                    "name": " > ".join([*crumbs, spec_title]) if crumbs else spec_title,
                    "title": spec_title,
                    "project": project,
                    "outcome": _OUTCOME.get(test.get("status") or "", test.get("status") or "unknown"),
                    "attempts": attempts,
                    "retries": max(len(attempts) - 1, 0),
                    "error": self._first_error(test),
                    "line": spec.get("line"),
                }

        for child in suite.get("suites") or []:
            self._walk(child, crumbs, found)

    def _collect(self, report: dict) -> dict:
        found: dict = {}
        for suite in report.get("suites") or []:
            self._walk(suite, [], found)
        return found

    # ----------------------------------------------------------- comparing

    def _compare(self) -> dict:
        run1 = self._load(self.run1_json, self.run1_file, "Run 1")
        run2 = self._load(self.run2_json, self.run2_file, "Run 2")

        tests1 = self._collect(run1)
        tests2 = self._collect(run2)
        if not tests1 or not tests2:
            msg = "One of the reports contained no tests. Check that both files are Playwright JSON reports."
            raise ValueError(msg)

        flaky, broken, stable, skipped, only1, only2 = [], [], [], [], [], []

        for key in sorted(set(tests1) | set(tests2)):
            a, b = tests1.get(key), tests2.get(key)

            if a and not b:
                only1.append({**a, "reason": "ran in run 1 only"})
                continue
            if b and not a:
                only2.append({**b, "reason": "ran in run 2 only"})
                continue

            o1, o2 = a["outcome"], b["outcome"]
            entry = {
                "file": a["file"],
                "name": a["name"],
                "project": a["project"],
                "run1": o1,
                "run2": o2,
                "run1_attempts": a["attempts"],
                "run2_attempts": b["attempts"],
                "error": a["error"] or b["error"],
            }

            if "skipped" in (o1, o2):
                skipped.append({**entry, "reason": f"{o1} in run 1, {o2} in run 2"})
            elif o1 == "passed on retry" or o2 == "passed on retry":
                run = "run 1" if o1 == "passed on retry" else "run 2"
                entry["reason"] = f"needed a retry in {run} - Playwright marked it flaky"
                entry["evidence"] = "retry inside a single run"
                flaky.append(entry)
            elif o1 != o2:
                entry["reason"] = f"{o1} in run 1, {o2} in run 2"
                entry["evidence"] = "outcome changed between runs"
                flaky.append(entry)
            elif o1 == "failed":
                entry["reason"] = "failed in both runs"
                broken.append(entry)
            else:
                stable.append(entry)

        total = len(set(tests1) | set(tests2))
        return {
            "flaky": flaky,
            "broken": broken,
            "stable": stable,
            "skipped": skipped,
            "only_run1": only1,
            "only_run2": only2,
            "totals": {
                "compared": total,
                "run1_tests": len(tests1),
                "run2_tests": len(tests2),
                "flaky": len(flaky),
                "consistently_failing": len(broken),
                "stable": len(stable),
                "flake_rate_percent": round(100.0 * len(flaky) / total, 2) if total else 0.0,
            },
            "run1_stats": run1.get("stats") or {},
            "run2_stats": run2.get("stats") or {},
        }

    # ------------------------------------------------------------ outputs

    @staticmethod
    def _stat_line(label: str, stats: dict, counted: int) -> str:
        if not stats:
            return f"{label}: {counted} tests"
        bits = [
            f"{stats.get('expected', 0)} passed",
            f"{stats.get('unexpected', 0)} failed",
            f"{stats.get('flaky', 0)} flaky",
        ]
        if stats.get("skipped"):
            bits.append(f"{stats['skipped']} skipped")
        return f"{label}: {counted} tests - " + ", ".join(bits)

    def build_report(self) -> Message:
        result = self._compare()
        cap = max(int(self.max_listed or 15), 1)
        totals = result["totals"]
        lines = [
            "# Flaky test comparison",
            "",
            self._stat_line("Run 1", result["run1_stats"], totals["run1_tests"]),
            self._stat_line("Run 2", result["run2_stats"], totals["run2_tests"]),
            f"Tests compared: {totals['compared']}",
            "",
            f"FLAKY: {totals['flaky']}",
            f"CONSISTENTLY FAILING: {totals['consistently_failing']}",
            f"STABLE: {totals['stable']}",
            f"Flake rate: {totals['flake_rate_percent']}%",
        ]

        def block(heading: str, rows: list, note: str = "") -> None:
            if not rows:
                return
            lines.extend(["", f"## {heading} ({len(rows)})"])
            if note:
                lines.append(note)
            for i, row in enumerate(rows[:cap], 1):
                lines.append(f"{i}. {row['file']} > {row.get('name', '')}")
                lines.append(f"   - {row.get('reason', '')}")
                a1 = ", ".join(row.get("run1_attempts") or []) or "-"
                a2 = ", ".join(row.get("run2_attempts") or []) or "-"
                lines.append(f"   - attempts: run 1 [{a1}] / run 2 [{a2}]")
                if row.get("error"):
                    lines.append(f"   - error: {row['error']}")
            if len(rows) > cap:
                lines.append(f"   ... and {len(rows) - cap} more")

        block("Flaky tests", result["flaky"],
              "These did not agree with themselves. Quarantine before trusting them.")
        block("Consistently failing", result["broken"],
              "Failed in both runs, so these are defects rather than flake.")
        block("Only in one run", result["only_run1"] + result["only_run2"])
        block("Skipped", result["skipped"])

        self.status = f"{totals['flaky']} flaky of {totals['compared']} compared"
        return Message(text="\n".join(lines))

    def build_findings(self) -> Data:
        result = self._compare()
        self.status = f"{result['totals']['flaky']} flaky of {result['totals']['compared']} compared"
        return Data(data=result)
