"""Regression Plan Writer - a Langflow custom component.

Writes the regression plan and the machine-readable impacted-test list to disk.

The report is in two halves. The first is **computed**: which files changed,
which tests reach them, through how many hops, and the command to run them. An
SDET who does not believe the subset can follow the chain from any selected test
back to the diff, because each one carries the path it was reached by.

The second is the model's: what to run first and what the risk of the subset is.
It is labelled as the model's and sits under the evidence.

Every plan ends with what the analysis could not see. That section is not a
disclaimer, it is the most important part of a subset recommendation - the tests
being skipped are skipped on the strength of a static import graph, and the
reader has to know what that graph is blind to before they trust it.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from lfx.custom.custom_component.component import Component
from lfx.io import MessageTextInput, Output
from lfx.schema.data import Data
from lfx.schema.message import Message

_FENCE_WHOLE = re.compile(r"^\s*```[a-zA-Z]*[ \t]*\n(.*?)\n?[ \t]*```\s*$", re.DOTALL)


class RegressionPlanWriter(Component):
    display_name = "Regression Plan Writer"
    description = "Writes the regression plan and the impacted-test list to disk."
    documentation = "https://martinfowler.com/articles/rise-test-impact-analysis.html"
    icon = "file-text"
    name = "RegressionPlanWriter"

    inputs = [
        MessageTextInput(
            name="advice",
            display_name="Advice",
            info="The model's write-up. Placed under the computed evidence, not in place of it.",
            value="",
            required=True,
        ),
        MessageTextInput(
            name="output_dir",
            display_name="Reports folder",
            info=(
                "Where regression_plan.md is written, and where impacted_tests.json is read "
                "from. Point this at the same folder as the analyzer's Reports folder."
            ),
            value="",
        ),
        MessageTextInput(
            name="report_name",
            display_name="Report file name",
            value="regression_plan.md",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Summary", name="summary", method="write_report"),
        Output(display_name="Details", name="details", method="write_details"),
    ]

    FINDINGS_FILE = "impacted_tests.json"

    def _findings(self, folder: Path) -> dict:
        path = folder / self.FINDINGS_FILE
        if not path.is_file():
            msg = (f"No {self.FINDINGS_FILE} in {folder}. The Regression Impact Analyzer writes "
                   "it, so set its Reports folder to this same folder and run the analysis first.")
            raise ValueError(msg)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"{path.name} is not valid JSON - {exc}"
            raise ValueError(msg) from exc
        if not isinstance(data, dict) or "selected" not in data:
            msg = f"{path.name} does not look like an impact analysis; it has no selected tests."
            raise ValueError(msg)
        return data

    @staticmethod
    def _clean_markdown(text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            msg = "The model returned no advice to write."
            raise ValueError(msg)
        whole = _FENCE_WHOLE.match(raw)
        return (whole.group(1) if whole else raw).strip()

    # ------------------------------------------------------------ composing

    def _compose(self, f: dict, advice: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        selected = f.get("selected") or []
        counts = f.get("counts") or {}
        full = f.get("full_suite")

        out = [
            "# Regression plan",
            "",
            f"*Generated {stamp} by the Smart Regression Advisor. The selected set is computed "
            "from the repository's import graph — every test below carries the path it was "
            "reached by.*",
            "",
            "## At a glance",
            "",
            "| | |",
            "|---|---|",
            f"| Files changed | {f.get('files_changed', 0)} |",
            f"| Source files indexed | {f.get('source_files_indexed', 0)} |",
            f"| Tests in the suite | {f.get('tests_total', 0)} |",
        ]
        if full:
            out.append("| **Verdict** | **Run the whole suite** |")
        else:
            out.append(f"| **Tests selected** | **{f.get('tests_selected', 0)} of "
                       f"{f.get('tests_total', 0)}** — {f.get('percent_skipped', 0):.0f}% skipped |")
            out.append(f"| Must run | {counts.get('must_run', 0)} |")
            out.append(f"| Should run | {counts.get('should_run', 0)} |")
        out.append("")

        if f.get("escalations"):
            out.extend([
                "## Why the whole suite",
                "",
                "These changes cannot be modelled as edges in an import graph, so narrowing "
                "would be a guess dressed as arithmetic.",
                "",
                "| File | Rule | Why |",
                "|---|---|---|",
            ])
            for e in f["escalations"]:
                out.append(f"| `{e.get('file', '')}` | {e.get('rule', '')} | {e.get('why', '')} |")
            out.append("")

        changed = f.get("changed_files") or []
        if changed:
            out.extend(["## What changed", "", "| File | Change | Lines |", "|---|---|---:|"])
            for c in changed:
                out.append(f"| `{c.get('path', '')}` | {c.get('change', '')} "
                           f"| {c.get('lines_changed', 0)} |")
            out.append("")
        for s in f.get("skipped_changes") or []:
            out.append(f"- `{s.get('path', '')}` was ignored — {s.get('reason', '')}")
        if f.get("skipped_changes"):
            out.append("")

        if selected and not full:
            out.extend([
                "## Tests to run",
                "",
                "| Tier | Test | Reached from | Hops |",
                "|---|---|---|---:|",
            ])
            for r in selected:
                because = (r.get("because") or [{}])[0]
                out.append(f"| {r.get('tier', '')} | `{r.get('test', '')}` "
                           f"| `{because.get('changed', '')}` | {r.get('distance', '')} |")
            out.append("")
        elif full:
            out.extend([f"## Tests to run ({len(selected)})", "",
                        "The whole suite, for the reasons above.", ""])
        elif not selected:
            out.extend(["## Tests to run", "",
                        "**None.** Nothing in the diff reaches any test in this repository. "
                        "Read the blind spots below before taking that as permission to skip "
                        "the regression run.", ""])

        if f.get("commands"):
            out.extend(["## Run it", "", "```bash"])
            for c in f["commands"]:
                out.append(f"# {c.get('ecosystem', '')}")
                out.append(c.get("command", ""))
            out.extend(["```", ""])

        out.extend([
            "---",
            "",
            "## Advice",
            "",
            "*This section is written by a language model from the evidence above. The selected "
            "set is not its work; the ordering and the risk assessment are.*",
            "",
            advice,
            "",
            "---",
            "",
            "## What this analysis cannot see",
            "",
            "The tests left out are left out on the strength of a static import graph. These "
            "couplings are real and invisible to it, and any of them can mean a skipped test "
            "would have caught the change:",
            "",
        ])
        for spot in f.get("blind_spots") or []:
            out.append(f"- {spot}")
        out.append("")
        return "\n".join(out)

    # -------------------------------------------------------------- writing

    def _write(self) -> dict:
        folder_raw = (self.output_dir or "").strip().strip('"').strip("'")
        if not folder_raw:
            msg = "Set a reports folder on the Regression Plan Writer."
            raise ValueError(msg)
        folder = Path(folder_raw).expanduser()
        folder.mkdir(parents=True, exist_ok=True)

        findings = self._findings(folder)
        advice = self._clean_markdown(self.advice)

        name = Path((self.report_name or "regression_plan.md").strip()).name or "regression_plan.md"
        if not name.endswith(".md"):
            name += ".md"

        report_path = folder / name
        report = self._compose(findings, advice)
        report_path.write_text(report if report.endswith("\n") else report + "\n", encoding="utf-8")

        return {
            "report": str(report_path),
            "report_lines": len(report.splitlines()),
            "findings_json": str(folder / self.FINDINGS_FILE),
            "files_changed": findings.get("files_changed", 0),
            "tests_total": findings.get("tests_total", 0),
            "tests_selected": findings.get("tests_selected", 0),
            "percent_skipped": findings.get("percent_skipped", 0),
            "full_suite": findings.get("full_suite", False),
            "escalations": len(findings.get("escalations") or []),
        }

    def write_report(self) -> Message:
        r = self._write()
        self.status = ("full suite" if r["full_suite"]
                       else f"{r['tests_selected']}/{r['tests_total']} tests")
        if r["full_suite"]:
            headline = (f"Run the whole suite ({r['tests_total']} tests) - "
                        f"{r['escalations']} change(s) cannot be narrowed safely.")
        else:
            headline = (f"Run {r['tests_selected']} of {r['tests_total']} tests, "
                        f"skipping {r['percent_skipped']:.0f}% of the suite.")
        return Message(text="\n".join([
            headline,
            f"{r['files_changed']} file(s) changed.",
            "",
            f"Plan:     {r['report']}  ({r['report_lines']} lines)",
            f"Impacted: {r['findings_json']}",
        ]))

    def write_details(self) -> Data:
        r = self._write()
        self.status = ("full suite" if r["full_suite"]
                       else f"{r['tests_selected']}/{r['tests_total']} tests")
        return Data(data=r)
